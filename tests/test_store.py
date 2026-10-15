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
        "key": "a", "title": "T", "volume": "3", "date": "2017-06-12", "number": "7",
        "author": [{"family": "Doe", "given": "J", "prefix": ""}, {}],
        "extra": "  free: text\nmedia x.png\n",
    })
    assert (data_dir / "a.txt").read_text() == (
        "T\n\nsource\n"
        "data\n"
        "entrytype: misc\n"
        "author:\n- {family: Doe, given: J}\n"
        "date: 2017-06-12\n"
        "number: '7'\n"
        "volume: 3\n"
        "extra\n"
        "free: text\n"
        " media x.png\n"
    )
    [src] = store.list_sources()
    assert src == {
        "key": "a", "entrytype": "misc", "title": "T",
        "author": [{"family": "Doe", "given": "J"}], "date": "2017-06-12",
        "number": "7", "volume": 3, "extra": "free: text\n media x.png",
    }


def test_title_falls_back_to_key(data_dir):
    store.create({"key": "a"})
    assert store.list_sources()[0]["title"] == "a"


def test_rewrite_keeps_foreign_lines(data_dir):
    (data_dir / "a.txt").write_text(
        "Old\nsecond body line\n\nsource\n-> see @other-123456\ntasks fix\n"
        "data\nentrytype: book\nwhatever: 1\nextra\nnotes\n"
    )
    store.update("a", {"key": "a", "entrytype": "book", "title": "New", "extra": "notes"})
    assert (data_dir / "a.txt").read_text() == (
        "New\nsecond body line\n\nsource\n-> see @other-123456\ntasks fix\n"
        "data\nentrytype: book\nwhatever: 1\nextra\nnotes\n"
    )


def test_tags_line_after_data_survives_a_save(data_dir):
    (data_dir / "a.txt").write_text("Old\nsource\ndata\nentrytype: book\ntags read-later 2026\n")
    assert store.list_sources()[0]["entrytype"] == "book"
    store.update("a", {"key": "a", "entrytype": "book", "title": "New"})
    assert (data_dir / "a.txt").read_text() == "New\n\nsource\ndata\nentrytype: book\ntags read-later 2026\n"


def test_notes_are_not_sources(data_dir):
    (data_dir / "n.txt").write_text("Just a note\nrecurring mo\n")
    store.create({"key": "a"})
    assert [s["key"] for s in store.list_sources()] == ["a"]
    assert store.recent() == ["a"]


def test_rename_and_conflict(data_dir):
    store.create({"key": "a"})
    store.create({"key": "b"})
    with pytest.raises(store.Conflict):
        store.update("a", {"key": "b"})
    store.update("a", {"key": "c"})
    assert sorted(p.name for p in data_dir.iterdir()) == ["b.txt", "c.txt"]
    store.delete("c")
    with pytest.raises(store.NotFound):
        store.delete("c")


def test_recent(data_dir):
    for i, k in enumerate("abcd"):
        store.create({"key": k})
        os.utime(data_dir / f"{k}.txt", ns=(i * 10**9, i * 10**9))
    assert store.recent() == ["d", "c", "b"]
    store.update("a", {"key": "a"})  # unchanged content: no rewrite
    assert store.recent() == ["d", "c", "b"]
    store.update("a", {"key": "a", "title": "T"})
    assert store.recent() == ["a", "d", "c"]


@pytest.mark.parametrize("bad", [
    {"key": "a b"}, {"key": "../x"}, {"key": "a", "entrytype": "nope"},
    {"key": "a", "volume": "x"}, {"key": "a", "date": "yesterday"},
    {"key": "a", "bogus": "1"}, {"key": "a", "extra": 1},
])
def test_invalid(bad):
    with pytest.raises(ValidationError):
        store.create(bad)
