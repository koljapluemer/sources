from pathlib import Path

import pytest

import dsl

EXAMPLES = Path(__file__).parent.parent.parent / "dsl" / "spec" / "examples"


def test_blocks_end_at_next_keyword():
    doc = dsl.parse("T\n\nsource\ndata\na: 1\nmedia x.png\nextra\ntext\n unknownword\nunknownword 1\n")
    assert doc.title == "T"
    assert doc.section[0] == "source"
    assert doc.block("data").lines == ["a: 1"]
    assert doc.section[2] == "media x.png"
    assert doc.block("extra").lines == ["text", " unknownword", "unknownword 1"]


def test_render_roundtrip_and_escape():
    text = "T\nmore\n\nsource\ndata\na: 1\nextra\ntext\n"
    doc = dsl.parse(text)
    assert dsl.render(doc) == text
    doc.block("extra").lines.append("tasks fix")
    assert dsl.render(doc).endswith("text\n tasks fix\n")


def test_extra_credit_is_body():
    assert dsl.parse("T\nextra credit\nsource\n").body == ["T", "extra credit"]


def test_yaml_scalars():
    doc = dsl.parse("T\ndata\ndate: 2017-06-12\nvolume: 3\n")
    assert dsl.load_data(doc.block("data")) == {"date": "2017-06-12", "volume": 3}
    assert dsl.load_data(dsl.Block("data", ["- a"])) is None
    assert dsl.load_data(dsl.Block("data", ["a: [1"])) is None


@pytest.mark.skipif(not EXAMPLES.exists(), reason="no ../dsl")
def test_blocks_match_conformance_examples():
    import json

    for txt in sorted(EXAMPLES.glob("*.txt")):
        expected = json.loads(txt.with_suffix(".json").read_text())
        if "extra" not in expected or "errors" in expected and expected["errors"]:
            continue
        doc = dsl.parse(txt.read_text())
        block = doc.block("extra")
        assert (None if block is None else "\n".join(block.lines)) == expected["extra"], txt.name
