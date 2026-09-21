"""biblatex data model: field types and per-entry-type default fields.

Field types:
  literal   str
  text      str (multi-line)
  integer   int
  range     str, e.g. "12--34"
  name      list of {family, given, prefix, suffix}
  list      list of str
  date      str, ISO 8601 / EDTF-ish ("2020", "2020-05", "2020-05-17", "2020/2021")
  uri       str
  verbatim  str
  key       str, one of `choices` if given
"""

import re

NAME_PARTS = ("family", "given", "prefix", "suffix")

# Core fields every source has, stored at top level alongside biblatex fields.
CORE = {"key", "entrytype", "title", "aliases"}

# Ordered: this is the display order in the form.
FIELDS: dict[str, dict] = {
    # people
    "author": {"type": "name"},
    "editor": {"type": "name"},
    "editora": {"type": "name"},
    "editorb": {"type": "name"},
    "editorc": {"type": "name"},
    "translator": {"type": "name"},
    "commentator": {"type": "name"},
    "annotator": {"type": "name"},
    "introduction": {"type": "name"},
    "foreword": {"type": "name"},
    "afterword": {"type": "name"},
    "bookauthor": {"type": "name"},
    "holder": {"type": "name"},
    "namea": {"type": "name"},
    "nameb": {"type": "name"},
    "namec": {"type": "name"},
    # titles
    "subtitle": {"type": "literal"},
    "titleaddon": {"type": "literal"},
    "shorttitle": {"type": "literal"},
    "maintitle": {"type": "literal"},
    "mainsubtitle": {"type": "literal"},
    "maintitleaddon": {"type": "literal"},
    "booktitle": {"type": "literal"},
    "booksubtitle": {"type": "literal"},
    "booktitleaddon": {"type": "literal"},
    "journaltitle": {"type": "literal"},
    "journalsubtitle": {"type": "literal"},
    "issuetitle": {"type": "literal"},
    "issuesubtitle": {"type": "literal"},
    "origtitle": {"type": "literal"},
    "eventtitle": {"type": "literal"},
    "eventtitleaddon": {"type": "literal"},
    "reprinttitle": {"type": "literal"},
    "series": {"type": "literal"},
    # dates
    "date": {"type": "date"},
    "origdate": {"type": "date"},
    "eventdate": {"type": "date"},
    "urldate": {"type": "date"},
    # publication
    "type": {"type": "literal"},
    "entrysubtype": {"type": "literal"},
    "edition": {"type": "literal"},
    "volume": {"type": "integer"},
    "volumes": {"type": "integer"},
    "number": {"type": "literal"},
    "issue": {"type": "literal"},
    "part": {"type": "literal"},
    "chapter": {"type": "literal"},
    "pages": {"type": "range"},
    "pagetotal": {"type": "literal"},
    "version": {"type": "literal"},
    "howpublished": {"type": "literal"},
    "pubstate": {
        "type": "key",
        "choices": ["inpreparation", "submitted", "forthcoming", "inpress", "prepublished"],
    },
    "publisher": {"type": "list"},
    "organization": {"type": "list"},
    "institution": {"type": "list"},
    "location": {"type": "list"},
    "venue": {"type": "literal"},
    "origlocation": {"type": "list"},
    "origpublisher": {"type": "list"},
    "language": {"type": "list"},
    "origlanguage": {"type": "list"},
    # identifiers
    "doi": {"type": "verbatim"},
    "isbn": {"type": "verbatim"},
    "issn": {"type": "verbatim"},
    "isrn": {"type": "verbatim"},
    "eprint": {"type": "verbatim"},
    "eprinttype": {"type": "literal"},
    "eprintclass": {"type": "literal"},
    "url": {"type": "uri"},
    "file": {"type": "verbatim"},
    "library": {"type": "literal"},
    # text
    "abstract": {"type": "text"},
    "annotation": {"type": "text"},
    "note": {"type": "text"},
    "addendum": {"type": "text"},
    "keywords": {"type": "literal"},
    # relations
    "crossref": {"type": "literal"},
    "xref": {"type": "literal"},
    "related": {"type": "list"},
    "relatedtype": {"type": "literal"},
    "relatedstring": {"type": "literal"},
    "entryset": {"type": "list"},
    # sorting / labels
    "shortauthor": {"type": "literal"},
    "shorteditor": {"type": "literal"},
    "shorthand": {"type": "literal"},
    "shorthandintro": {"type": "literal"},
    "label": {"type": "literal"},
    "sortkey": {"type": "literal"},
    "sorttitle": {"type": "literal"},
    "sortyear": {"type": "integer"},
    "sortname": {"type": "literal"},
    "sortshorthand": {"type": "literal"},
    "indextitle": {"type": "literal"},
    "indexsorttitle": {"type": "literal"},
    "langid": {"type": "literal"},
    "langidopts": {"type": "literal"},
    "options": {"type": "literal"},
    "presort": {"type": "literal"},
    "execute": {"type": "literal"},
    "gender": {"type": "literal"},
    "hyphenation": {"type": "literal"},
    "pagination": {"type": "literal"},
    "bookpagination": {"type": "literal"},
    "ids": {"type": "list"},
    # user-defined
    **{f"user{c}": {"type": "literal"} for c in "abcdef"},
    **{f"verb{c}": {"type": "verbatim"} for c in "abc"},
}

_ARTICLE = ["author", "journaltitle", "date", "volume", "number", "pages", "doi", "url", "urldate"]
_BOOK = ["author", "date", "edition", "volume", "series", "publisher", "location", "isbn", "doi", "url"]
_COLL = ["author", "booktitle", "editor", "date", "publisher", "location", "pages", "doi", "url"]
_PROC = ["editor", "date", "eventtitle", "publisher", "location", "series", "volume", "isbn", "doi", "url"]

# Fields shown by default per entry type; anything else is added on demand.
ENTRY_TYPES: dict[str, list[str]] = {
    "article": _ARTICLE,
    "book": _BOOK,
    "mvbook": ["author", "date", "volumes", "publisher", "location", "isbn", "url"],
    "inbook": _COLL + ["bookauthor"],
    "bookinbook": _COLL + ["bookauthor"],
    "suppbook": _COLL + ["bookauthor"],
    "booklet": ["author", "date", "howpublished", "location", "url"],
    "collection": _BOOK[:1] + ["editor"] + _BOOK[1:],
    "mvcollection": ["editor", "date", "volumes", "publisher", "location", "isbn", "url"],
    "incollection": _COLL,
    "suppcollection": _COLL,
    "dataset": ["author", "date", "type", "version", "publisher", "location", "doi", "url", "urldate"],
    "manual": ["author", "organization", "date", "edition", "type", "version", "location", "url"],
    "misc": ["author", "date", "type", "howpublished", "url", "urldate"],
    "online": ["author", "date", "organization", "url", "urldate"],
    "patent": ["author", "holder", "number", "type", "date", "location", "url"],
    "periodical": ["editor", "date", "volume", "issn", "url"],
    "suppperiodical": _ARTICLE,
    "proceedings": _PROC,
    "mvproceedings": ["editor", "date", "eventtitle", "volumes", "publisher", "location", "isbn", "url"],
    "inproceedings": _PROC + ["author", "booktitle", "pages"],
    "reference": _BOOK[:1] + ["editor"] + _BOOK[1:],
    "mvreference": ["editor", "date", "volumes", "publisher", "location", "isbn", "url"],
    "inreference": _COLL,
    "report": ["author", "type", "number", "institution", "date", "location", "url", "urldate"],
    "software": ["author", "date", "version", "publisher", "location", "doi", "url", "urldate"],
    "thesis": ["author", "type", "institution", "date", "location", "doi", "url", "urldate"],
    "unpublished": ["author", "date", "howpublished", "location", "url", "note"],
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
    (str->str) holds leftovers from imports.
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
    aliases = source.get("aliases") or []
    if not isinstance(aliases, list):
        raise ValidationError("aliases: expected list")
    aliases = [a for a in (_clean_str(a, "aliases") for a in aliases) if a]
    if aliases:
        out["aliases"] = aliases

    for name, value in source.items():
        if name in CORE:
            continue
        if name == "extra":
            if not isinstance(value, dict) or not all(
                isinstance(k, str) and isinstance(v, str) for k, v in value.items()
            ):
                raise ValidationError("extra: expected string map")
            if value:
                out["extra"] = value
            continue
        spec = FIELDS.get(name)
        if spec is None:
            raise ValidationError(f"unknown field '{name}'")
        cleaned = _clean_value(name, spec, value)
        if cleaned not in (None, "", []):
            out[name] = cleaned
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
    if t == "key" and s and s not in spec.get("choices", [s]):
        raise ValidationError(f"{name}: invalid value '{s}'")
    return s
