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


def get_path() -> Path | None:
    try:
        p = json.loads(CONFIG_PATH.read_text()).get("path")
    except (OSError, ValueError):
        return None
    return Path(p) if p else None


def set_path(path: str) -> Path:
    p = Path(path).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps({"path": str(p)}, indent=2) + "\n")
    return p


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
