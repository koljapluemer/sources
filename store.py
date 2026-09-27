"""Config and one-json-file-per-source storage."""

import json
import os
from pathlib import Path

from fields import KEY_RE, ValidationError, normalise

CONFIG_PATH = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "sources" / "config.json"

_FIRST = ("key", "entrytype", "title", "aliases")


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
    return _dir() / f"{key}.json"


def _write(path: Path, source: dict) -> None:
    ordered = {k: source[k] for k in _FIRST if k in source}
    ordered.update({k: v for k, v in source.items() if k not in ordered})
    text = json.dumps(ordered, indent=2, ensure_ascii=False) + "\n"
    try:
        if path.read_text(encoding="utf-8") == text:
            return  # unchanged: keep mtime so "recently edited" stays meaningful
    except OSError:
        pass
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def list_sources() -> list[dict]:
    out = []
    for f in sorted(_dir().glob("*.json")):
        try:
            out.append(json.loads(f.read_text(encoding="utf-8")))
        except ValueError:
            continue
    return out


def recent(n: int = 3) -> list[str]:
    """Keys of the n most recently modified sources, newest first."""
    files = sorted(_dir().glob("*.json"), key=lambda f: f.stat().st_mtime_ns, reverse=True)
    return [f.stem for f in files[:n]]


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
    _write(new, source)
    if new != old:
        old.unlink()
    return source


def delete(key: str) -> None:
    path = _file(key)
    if not path.exists():
        raise NotFound(key)
    path.unlink()
