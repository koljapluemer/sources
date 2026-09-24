import json
import os

import pytest

import store
from fields import ValidationError


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "CONFIG_PATH", tmp_path / "cfg" / "config.json")
    store.set_path(str(tmp_path / "data"))
    return tmp_path / "data"


def test_roundtrip_and_stripping(data_dir):
    store.create({
        "key": "a", "title": "T", "aliases": ["x", ""], "volume": "3",
        "author": [{"family": "Doe", "given": "J", "prefix": ""}, {}],
    })
    saved = json.loads((data_dir / "a.json").read_text())
    assert saved == {
        "key": "a", "entrytype": "misc", "title": "T", "aliases": ["x"],
        "author": [{"family": "Doe", "given": "J"}], "volume": 3,
    }
    assert store.list_sources() == [saved]


def test_rename_and_conflict(data_dir):
    store.create({"key": "a"})
    store.create({"key": "b"})
    with pytest.raises(store.Conflict):
        store.update("a", {"key": "b"})
    store.update("a", {"key": "c"})
    assert sorted(p.name for p in data_dir.iterdir()) == ["b.json", "c.json"]
    store.delete("c")
    with pytest.raises(store.NotFound):
        store.delete("c")


def test_recent(data_dir):
    for i, k in enumerate("abcd"):
        store.create({"key": k})
        os.utime(data_dir / f"{k}.json", ns=(i * 10**9, i * 10**9))
    assert store.recent() == ["d", "c", "b"]
    store.update("a", {"key": "a"})  # unchanged content: no rewrite
    assert store.recent() == ["d", "c", "b"]
    store.update("a", {"key": "a", "title": "T"})
    assert store.recent() == ["a", "d", "c"]


@pytest.mark.parametrize("bad", [
    {"key": "a b"}, {"key": "../x"}, {"key": "a", "entrytype": "nope"},
    {"key": "a", "volume": "x"}, {"key": "a", "date": "yesterday"},
    {"key": "a", "bogus": "1"}, {"key": "a", "pubstate": "maybe"},
])
def test_invalid(bad):
    with pytest.raises(ValidationError):
        store.create(bad)
