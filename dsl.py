"""The item language from ../dsl, just far enough to read and rewrite a source file.

Keywords come from spec/keywords.yaml (copied in from ../dsl via `just sync-spec`).
A file is its body lines plus the keyword section, in order, as plain lines and
blocks; lines this app doesn't own are written back untouched.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

SPEC_PATH = Path(__file__).parent / "spec" / "keywords.yaml"

_KEYWORD = re.compile(r"^([a-z]+)(?=\s|$)")
_STATE = re.compile(r"^\(([a-z]+)(?=[\s)]|$)")
_RELATION = re.compile(r"^->\s")
_OPENING_ROLES = ("primary", "property")


class _CoreLoader(yaml.SafeLoader):
    """YAML 1.2 core scalars: `2017-06-12` stays a string."""


class _CoreDumper(yaml.SafeDumper):
    pass


for _cls in (_CoreLoader, _CoreDumper):
    _cls.yaml_implicit_resolvers = {
        ch: [(tag, rx) for tag, rx in rs if tag != "tag:yaml.org,2002:timestamp"]
        for ch, rs in yaml.SafeLoader.yaml_implicit_resolvers.items()
    }


class _Flow(dict):
    pass


class _FlowList(list):
    pass


_CoreDumper.add_representer(_Flow, lambda d, v: d.represent_mapping("tag:yaml.org,2002:map", v, flow_style=True))
_CoreDumper.add_representer(_FlowList, lambda d, v: d.represent_sequence("tag:yaml.org,2002:seq", v, flow_style=True))


def _flowed(value):
    """Nested mappings and lists of scalars on one line, the rest in block style."""
    if isinstance(value, dict):
        return _Flow(value)
    if isinstance(value, list) and not any(isinstance(v, (dict, list)) for v in value):
        return _FlowList(value)
    if isinstance(value, list):
        return [_flowed(v) for v in value]
    return value


def load_keywords(path: Path = SPEC_PATH) -> dict[str, dict]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))["keywords"]


KEYWORDS = load_keywords()


@dataclass
class Block:
    keyword: str
    lines: list[str]


@dataclass
class Document:
    body: list[str] = field(default_factory=list)
    section: list[str | Block] = field(default_factory=list)

    @property
    def title(self) -> str:
        return self.body[0].strip() if self.body else ""

    def has_keyword(self, keyword: str) -> bool:
        return any(isinstance(e, str) and e.split()[:1] == [keyword] for e in self.section)

    def block(self, keyword: str) -> Block | None:
        return next((e for e in self.section if isinstance(e, Block) and e.keyword == keyword), None)


def _starts_line(line: str, roles: tuple[str, ...] | None) -> bool:
    """A keyword (of `roles`, any if None), relationship or state line at column 0."""
    if _RELATION.match(line):
        return line.split()[-1].startswith("@")
    if m := _STATE.match(line):
        return KEYWORDS.get(m[1], {}).get("role") == "state" and (roles is None or "state" in roles)
    if m := _KEYWORD.match(line):
        spec = KEYWORDS.get(m[1])
        if spec is None or (roles is not None and spec["role"] not in roles):
            return False
        return not spec.get("block") or line.rstrip() == m[1]
    return False


def _block_keyword(line: str) -> str | None:
    name = line.rstrip()
    return name if KEYWORDS.get(name, {}).get("block") else None


def parse(text: str) -> Document:
    lines = text.replace("\r", "").split("\n")
    first = next((i for i, l in enumerate(lines) if l.strip()), None)
    if first is None:
        return Document()
    boundary = next(
        (i for i in range(first + 1, len(lines)) if _starts_line(lines[i], _OPENING_ROLES)), len(lines)
    )
    doc = Document(body=_trim(lines[first:boundary]))
    i = boundary
    while i < len(lines):
        keyword = _block_keyword(lines[i])
        if keyword is None:
            if lines[i].strip():
                doc.section.append(lines[i].strip())
            i += 1
            continue
        end = next((j for j in range(i + 1, len(lines)) if _starts_line(lines[j], None)), len(lines))
        doc.section.append(Block(keyword, _trim(lines[i + 1 : end])))
        i = end
    return doc


def render(doc: Document) -> str:
    out = list(doc.body)
    if doc.section:
        out.append("")
    for entry in doc.section:
        if isinstance(entry, str):
            out.append(entry)
            continue
        out.append(entry.keyword)
        # a line that would end the block is indented to stay in it
        out.extend(f" {l}" if _starts_line(l, None) else l for l in entry.lines)
    return "\n".join(out) + "\n"


def _trim(lines: list[str]) -> list[str]:
    start, end = 0, len(lines)
    while start < end and not lines[start].strip():
        start += 1
    while end > start and not lines[end - 1].strip():
        end -= 1
    return lines[start:end]


def load_data(block: Block | None) -> dict | None:
    """The `data` block as a mapping, or None when absent or invalid."""
    if block is None:
        return None
    try:
        value = yaml.load("\n".join(block.lines), Loader=_CoreLoader)
    except yaml.YAMLError:
        return None
    return value if isinstance(value, dict) else None


def dump_data(data: dict) -> list[str]:
    text = yaml.dump(
        {k: _flowed(v) for k, v in data.items()},
        Dumper=_CoreDumper,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=10**6,
    )
    return text.rstrip("\n").split("\n")
