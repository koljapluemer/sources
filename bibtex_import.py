"""BibTeX/biblatex text -> source dicts (biblatex model)."""

import re

import bibtexparser
from bibtexparser.middlewares import (
    LatexDecodingMiddleware,
    NormalizeFieldKeys,
    SeparateCoAuthors,
    SplitNameParts,
)
from bibtexparser.model import Entry
from pylatexenc.latex2text import LatexNodes2Text

from fields import DATE_RE, ENTRY_TYPES, FIELDS

NAME_FIELDS = tuple(n for n, s in FIELDS.items() if s["type"] == "name")

# legacy bibtex/biblatex type -> (biblatex type, extra fields)
TYPE_ALIASES = {
    "conference": ("inproceedings", {}),
    "electronic": ("online", {}),
    "www": ("online", {}),
    "phdthesis": ("thesis", {"type": "phdthesis"}),
    "mastersthesis": ("thesis", {"type": "mathesis"}),
    "techreport": ("report", {"type": "techreport"}),
}

# legacy bibtex field -> biblatex field
FIELD_ALIASES = {
    "journal": "journaltitle",
    "address": "location",
    "school": "institution",
    "key": "sortkey",
    "annote": "annotation",
    "archiveprefix": "eprinttype",
    "primaryclass": "eprintclass",
    "pdf": "file",
}

MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]

_latex = LatexNodes2Text()


def _decode(s: str) -> str:
    return _latex.latex_to_text(s).strip()


def _name(parts) -> dict:
    name = {
        "given": " ".join(parts.first),
        "prefix": " ".join(parts.von),
        "family": " ".join(parts.last),
        "suffix": " ".join(parts.jr),
    }
    return {k: _decode(v) for k, v in name.items() if v}


def _month(value: str) -> int | None:
    v = value.strip().lower()
    if v.isdigit() and 1 <= int(v) <= 12:
        return int(v)
    return MONTHS.index(v[:3]) + 1 if v[:3] in MONTHS else None


def _convert(entry: Entry) -> dict:
    etype = entry.entry_type.lower()
    out: dict = {"key": re.sub(r"[^A-Za-z0-9_:.\-/+]", "_", entry.key) or "source"}
    extra: dict[str, str] = {}

    fixed: dict = {}
    if etype in TYPE_ALIASES:
        etype, fixed = TYPE_ALIASES[etype]
    if etype not in ENTRY_TYPES:
        extra["entrytype"] = entry.entry_type
        etype = "misc"
    out["entrytype"] = etype

    fields: dict = {}
    for name, field in entry.fields_dict.items():
        fields[FIELD_ALIASES.get(name, name)] = field.value
    for name, value in fixed.items():
        fields.setdefault(name, value)

    # year/month -> date
    year, month = fields.pop("year", None), fields.pop("month", None)
    if year and "date" not in fields:
        date = str(year).strip()
        m = _month(str(month)) if month else None
        if m and re.fullmatch(r"\d{4}", date):
            date = f"{date}-{m:02d}"
        fields["date"] = date
    elif month:
        extra["month"] = str(month)

    # howpublished holding only a url is really the url
    hp = fields.get("howpublished")
    if isinstance(hp, str) and "url" not in fields:
        m = re.fullmatch(r"(?:\\url\{)?(https?://[^\s}]+)\}?", hp.strip())
        if m:
            fields["url"] = m.group(1)
            del fields["howpublished"]

    for name, value in fields.items():
        if name == "title":
            out["title"] = value
            continue
        spec = FIELDS.get(name)
        if spec is None:
            extra[name] = value if isinstance(value, str) else str(value)
            continue
        t = spec["type"]
        if t == "name":
            if isinstance(value, list):
                out[name] = [_name(p) for p in value]
            else:
                extra[name] = str(value)
        elif t == "list":
            out[name] = [p.strip() for p in re.split(r"\s+and\s+", value) if p.strip()]
        elif t == "integer":
            if str(value).strip().isdigit():
                out[name] = int(value)
            else:
                extra[name] = str(value)
        elif t == "date":
            if DATE_RE.match(str(value)):
                out[name] = str(value)
            else:
                extra[name] = str(value)
        elif t == "key":
            if value in spec["choices"]:
                out[name] = value
            else:
                extra[name] = str(value)
        else:
            out[name] = value
    if extra:
        out["extra"] = extra
    return out


def parse(text: str) -> list[dict]:
    """Parse bibtex/biblatex text. Raises ValueError if no entries found."""
    library = bibtexparser.parse_string(
        text,
        append_middleware=[
            NormalizeFieldKeys(),
            SeparateCoAuthors(name_fields=NAME_FIELDS),
            SplitNameParts(name_fields=NAME_FIELDS),
            LatexDecodingMiddleware(),
        ],
    )
    sources = [_convert(e) for e in library.entries]
    if not sources:
        raise ValueError("no bibtex entries found")
    return sources
