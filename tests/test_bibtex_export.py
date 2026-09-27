import pytest

import bibtex_export
import bibtex_import
import store


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "CONFIG_PATH", tmp_path / "cfg" / "config.json")
    store.set_path(str(tmp_path / "data"))
    return tmp_path / "data"


SOURCE = {
    "key": "doe2020", "entrytype": "article", "title": "R&D at 50% — Müller",
    "aliases": ["x"],
    "author": [
        {"family": "Doe", "given": "Jane", "suffix": "Jr."},
        {"family": "Beethoven", "given": "Ludwig", "prefix": "van"},
        {"family": "World Health Organization"},
    ],
    "journaltitle": "Nature", "volume": 3, "date": "2020-05",
    "location": ["Berlin", "Rock and Roll"], "url": "https://x.org/a_b",
    "extra": {"entrytype": "weird", "custom": "v", "bad key": "v"},
}


def test_render_roundtrip():
    text = bibtex_export.render([SOURCE])
    assert text.startswith(bibtex_export.HEADER)
    assert "url = {https://x.org/a_b}" in text
    assert "location = {Berlin and {Rock and Roll}}" in text
    assert "bad key" not in text and "weird" not in text
    [back] = bibtex_import.parse(text)
    expected = {k: v for k, v in SOURCE.items() if k not in ("aliases", "extra", "location")}
    assert {k: v for k, v in back.items() if k not in ("extra", "location")} == expected
    assert back["extra"] == {"custom": "v"}


def test_sync(tmp_path):
    store.create(SOURCE)
    out = tmp_path / "out"
    out.mkdir()
    foreign = tmp_path / "mine.bib"
    foreign.write_text("@misc{a}\n")
    paths = store.set_bib_paths([str(out), "", str(foreign), "rel.bib", str(tmp_path / "x.txt"), str(out)])
    assert paths == [str(out / "sources.bib"), str(foreign), "rel.bib", str(tmp_path / "x.txt")]

    bibtex_export.sync()
    assert bibtex_export.status[paths[0]] is None
    assert "not generated" in bibtex_export.status[paths[1]]
    assert "absolute" in bibtex_export.status[paths[2]]
    assert ".bib" in bibtex_export.status[paths[3]]
    assert foreign.read_text() == "@misc{a}\n"

    target = out / "sources.bib"
    mtime = target.stat().st_mtime_ns
    bibtex_export.sync()
    assert target.stat().st_mtime_ns == mtime  # unchanged: not rewritten
    store.delete("doe2020")
    bibtex_export.sync()
    assert "doe2020" not in target.read_text()
