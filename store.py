"""Config and one-json-file-per-source storage."""

import json
import os
from pathlib import Path

import dsl
from fields import ENTRY_TYPES, FIELDS, KEY_RE, ValidationError, normalise

CONFIG_PATH = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "sources" / "config.json"

class Conflict(Exception):
    pass


class NotFound(Exception):
    pass


def _config() -> dict:
    try:
        cfg = json.loads(CONFIG_PATH.read_text())
    except (OSError, ValueError):
        return {}
    return cfg if isinstance(cfg, dict) else {}


def _save_config(**changes) -> None:
    cfg = _config() | changes
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2) + "\n")


def get_path() -> Path | None:
    p = _config().get("path")
    return Path(p) if p else None


def set_path(path: str) -> Path:
    p = Path(path).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    _save_config(path=str(p))
    return p


def get_bib_paths() -> list[str]:
    return list(_config().get("bibtex") or [])


def set_bib_paths(paths: list[str]) -> list[str]:
    """Store .bib export targets. `~` is expanded, a directory gets `sources.bib` appended."""
    if not isinstance(paths, list) or not all(isinstance(p, str) for p in paths):
        raise ValidationError("bibtex: expected list of paths")
    out: list[str] = []
    for raw in paths:
        if not raw.strip():
            continue
        p = Path(raw.strip()).expanduser()
        if p.is_absolute():
            p = p.resolve()
            if p.is_dir():
                p = p / "sources.bib"
        if str(p) not in out:
            out.append(str(p))
    _save_config(bibtex=out)
    return out


def _dir() -> Path:
    p = get_path()
    if p is None or not p.is_dir():
        raise ValidationError("path not set")
    return p


def _file(key: str) -> Path:
    if not KEY_RE.match(key) or key.startswith("."):
        raise ValidationError("invalid key")
    return _dir() / f"{key}.txt"


def _coerce(name: str, value):
    """A YAML value as the model's type for the field."""
    t = FIELDS[name]["type"]
    if t == "integer":
        return value if isinstance(value, int) and not isinstance(value, bool) else str(value)
    if t == "name":
        return value if isinstance(value, list) else []
    if t == "list":
        return [str(v) for v in value] if isinstance(value, list) else [str(value)]
    return str(value)


def _read(path: Path) -> dict | None:
    """The source in a file, or None when it's not a source (or unreadable)."""
    try:
        doc = dsl.parse(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return None
    if not doc.has_keyword("source"):
        return None
    block = doc.block("data")
    data = dsl.load_data(block) if block else {}
    if data is None:
        return None
    entrytype = data.get("entrytype")
    source = {
        "key": path.stem,
        "entrytype": entrytype if entrytype in ENTRY_TYPES else "misc",
        "title": doc.title,
    }
    source.update({n: _coerce(n, data[n]) for n in FIELDS if data.get(n) not in (None, "", [])})
    extra = doc.block("extra")
    if extra and extra.lines:
        source["extra"] = "\n".join(extra.lines)
    return source


def _set_block(doc: dsl.Document, keyword: str, lines: list[str]) -> None:
    """Replaces the block's content (or removes the block when `lines` is empty)."""
    block = doc.block(keyword)
    if block is not None:
        if lines:
            block.lines = lines
        else:
            doc.section.remove(block)
    elif lines:
        extra = doc.block("extra")
        at = doc.section.index(extra) if extra is not None and keyword != "extra" else len(doc.section)
        doc.section.insert(at, dsl.Block(keyword, lines))


def _text(source: dict, base: str | None) -> str:
    """The file text for `source`, keeping what `base` (the file's current text) holds beyond it."""
    doc = dsl.parse(base) if base else dsl.Document()
    doc.body = [source.get("title") or source["key"], *doc.body[1:]]
    if not doc.has_keyword("source"):
        doc.section.insert(0, "source")
    data = {"entrytype": source["entrytype"]}
    data.update({n: source[n] for n in FIELDS if n in source})
    # keys the app doesn't know stay as they are
    old = dsl.load_data(doc.block("data")) or {}
    data.update({k: v for k, v in old.items() if k not in data and k not in FIELDS})
    _set_block(doc, "data", dsl.dump_data(data))
    _set_block(doc, "extra", source.get("extra", "").split("\n") if source.get("extra") else [])
    return dsl.render(doc)


def _write(path: Path, source: dict, base: str | None = None) -> None:
    text = _text(source, base)
    try:
        if path.read_text(encoding="utf-8") == text:
            return  # unchanged: keep mtime so "recently edited" stays meaningful
    except OSError:
        pass
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _files() -> list[Path]:
    return sorted(f for f in _dir().glob("*.txt") if not f.name.startswith("."))


def list_sources() -> list[dict]:
    return [s for s in map(_read, _files()) if s is not None]


def recent(n: int = 3) -> list[str]:
    """Keys of the n most recently modified sources, newest first."""
    files = sorted(_files(), key=lambda f: f.stat().st_mtime_ns, reverse=True)
    return [f.stem for f in files if _read(f) is not None][:n]


def create(source: dict) -> dict:
    source = normalise(source)
    path = _file(source["key"])
    if path.exists():
        raise Conflict(f"key '{source['key']}' exists")
    _write(path, source)
    return source


def update(old_key: str, source: dict) -> dict:
    source = normalise(source)
    old = _file(old_key)
    if not old.exists():
        raise NotFound(old_key)
    new = _file(source["key"])
    if new != old and new.exists():
        raise Conflict(f"key '{source['key']}' exists")
    _write(new, source, old.read_text(encoding="utf-8"))
    if new != old:
        old.unlink()
    return source


def delete(key: str) -> None:
    path = _file(key)
    if not path.exists():
        raise NotFound(key)
    path.unlink()
