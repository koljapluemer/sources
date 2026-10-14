"""Source data model: the biblatex subset needed to cite in ACM/IEEE/APA, plus a canonical url.

Field types:
  literal   str
  integer   int
  range     str, e.g. "12--34"
  name      list of {family, given, prefix, suffix}
  list      list of str
  date      str, ISO 8601 / EDTF-ish ("2020", "2020-05", "2020-05-17", "2020/2021")
  uri       str
  verbatim  str

`extra` is free text, kept next to the fields but not part of them.
"""

import re

NAME_PARTS = ("family", "given", "prefix", "suffix")

# Core fields every source has: the key is the file name, the title the first line.
CORE = {"key", "entrytype", "title"}

# Ordered: this is the display order in the form and in the file.
FIELDS: dict[str, dict] = {
    "author": {"type": "name"},
    "editor": {"type": "name"},
    "date": {"type": "date"},
    "urldate": {"type": "date"},
    "journaltitle": {"type": "literal"},
    "booktitle": {"type": "literal"},
    "series": {"type": "literal"},
    "type": {"type": "literal"},
    "number": {"type": "literal"},
    "volume": {"type": "integer"},
    "edition": {"type": "literal"},
    "version": {"type": "literal"},
    "pages": {"type": "range"},
    "publisher": {"type": "list"},
    "institution": {"type": "list"},
    "organization": {"type": "list"},
    "location": {"type": "list"},
    "doi": {"type": "verbatim"},
    "isbn": {"type": "verbatim"},
    "eprint": {"type": "verbatim"},
    "eprinttype": {"type": "literal"},
    "url": {"type": "uri"},
}

_ARTICLE = ["author", "journaltitle", "date", "volume", "number", "pages", "doi", "url", "urldate"]
_BOOK = ["author", "date", "edition", "volume", "series", "publisher", "location", "isbn", "doi", "url"]

# Fields shown by default per entry type; anything else is added on demand.
ENTRY_TYPES: dict[str, list[str]] = {
    "article": _ARTICLE,
    "book": _BOOK,
    "incollection": ["author", "booktitle", "editor", "date", "publisher", "location", "pages", "doi", "url"],
    "inproceedings": ["author", "booktitle", "editor", "date", "publisher", "location", "pages", "doi", "url"],
    "thesis": ["author", "type", "institution", "date", "location", "doi", "url", "urldate"],
    "report": ["author", "type", "number", "institution", "date", "location", "url", "urldate"],
    "online": ["author", "date", "organization", "url", "urldate"],
    "software": ["author", "date", "version", "publisher", "doi", "url", "urldate"],
    "misc": ["author", "date", "type", "url", "urldate"],
}

DATE_RE = re.compile(
    r"^(?=.)(?:-?\d{4}(?:-\d{2}(?:-\d{2})?)?)?(?:/(?:-?\d{4}(?:-\d{2}(?:-\d{2})?)?)?)?$"
)
KEY_RE = re.compile(r"^[A-Za-z0-9_:.\-/+]+$")


def schema() -> dict:
    return {
        "fields": FIELDS,
        "entryTypes": ENTRY_TYPES,
        "nameParts": NAME_PARTS,
    }


class ValidationError(ValueError):
    pass


def _clean_str(v, field: str) -> str:
    if not isinstance(v, str):
        raise ValidationError(f"{field}: expected string")
    return v.strip()


def normalise(source: dict) -> dict:
    """Validate a source against the schema, strip empties, order keys.

    Raises ValidationError. Unknown top-level fields are rejected; `extra`
    is free text.
    """
    if not isinstance(source, dict):
        raise ValidationError("expected object")
    key = _clean_str(source.get("key", ""), "key")
    if not KEY_RE.match(key):
        raise ValidationError("key: must be a valid bibtex key")
    entrytype = _clean_str(source.get("entrytype") or "misc", "entrytype")
    if entrytype not in ENTRY_TYPES:
        raise ValidationError(f"entrytype: unknown '{entrytype}'")

    out: dict = {"key": key, "entrytype": entrytype}
    title = _clean_str(source.get("title", ""), "title")
    if title:
        out["title"] = title
    extra = source.get("extra") or ""
    if not isinstance(extra, str):
        raise ValidationError("extra: expected text")
    extra = extra.strip()

    for name, value in source.items():
        if name in CORE or name == "extra":
            continue
        spec = FIELDS.get(name)
        if spec is None:
            raise ValidationError(f"unknown field '{name}'")
        cleaned = _clean_value(name, spec, value)
        if cleaned not in (None, "", []):
            out[name] = cleaned
    if extra:
        out["extra"] = extra
    return out


def _clean_value(name: str, spec: dict, value):
    t = spec["type"]
    if value is None or value == "":
        return None
    if t == "integer":
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
        try:
            n = int(value)
        except (TypeError, ValueError):
            raise ValidationError(f"{name}: expected integer") from None
        return n
    if t == "name":
        if not isinstance(value, list):
            raise ValidationError(f"{name}: expected list of names")
        names = []
        for n in value:
            if not isinstance(n, dict) or set(n) - set(NAME_PARTS):
                raise ValidationError(f"{name}: invalid name")
            parts = {p: _clean_str(n.get(p, ""), name) for p in NAME_PARTS}
            parts = {p: v for p, v in parts.items() if v}
            if parts:
                names.append(parts)
        return names
    if t == "list":
        if not isinstance(value, list):
            raise ValidationError(f"{name}: expected list")
        return [v for v in (_clean_str(v, name) for v in value) if v]
    s = _clean_str(value, name)
    if t == "date" and s and not DATE_RE.match(s):
        raise ValidationError(f"{name}: invalid date '{s}'")
    return s
