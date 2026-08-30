"""Golden end-to-end baseline (spec 0005): pins the exact pipeline output.

Written and green before the refactor. If any refactoring changes the
manifest bytes, the destination files or the exit code, this test fails.
"""

import json
from pathlib import Path

from memory_drawer.__main__ import main


def build_fixture(tmp_path):
    master = tmp_path / "master"
    master.mkdir()
    src1 = tmp_path / "bkp1"
    src2 = tmp_path / "bkp2"
    src2.mkdir(parents=True)
    (src1 / "viagens" / "2020").mkdir(parents=True)
    (src1 / "viagens" / "2020" / "IMG_0001.JPG").write_bytes(b"foto 2020")
    (src1 / "viagens" / "2020" / "IMG_0001.JPG.json").write_text(
        '{"photoTakenTime": {"timestamp": "1588291200"}}', encoding="utf-8"
    )
    (src1 / "dupe.txt").write_text("duplicata", encoding="utf-8")
    (src2 / "dupe.txt").write_text("duplicata", encoding="utf-8")
    (src1 / "vazio.txt").write_bytes(b"")
    (src1 / "foto ção é 😀.JPG").write_bytes(b"unicode")
    cfg = tmp_path / "config.json"
    cfg.write_text(
        json.dumps(
            {
                "master": str(master),
                "sources": [
                    {"id": "bkp1", "path": str(src1)},
                    {"id": "bkp2", "path": str(src2)},
                ],
            }
        ),
        encoding="utf-8",
    )
    return master, cfg


def test_golden_consolidate(tmp_path, capsys):
    master, cfg = build_fixture(tmp_path)
    assert main(["consolidate", "--config", str(cfg)]) == 0
    out = capsys.readouterr().out
    assert "Copied: 6 files, 81 B" in out
    assert "Errors: 0" in out

    lines = Path(master / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
    assert lines[0] == "# memory-drawer manifest v1"
    records = [json.loads(line) for line in lines[1:]]
    assert len(records) == 6
    assert [(r["rel_path"], r["kind"], r["size"]) for r in records] == [
        ("dupe.txt", "file", 9),
        ("foto ção é 😀.JPG", "file", 7),
        ("vazio.txt", "file", 0),
        ("viagens/2020/IMG_0001.JPG", "file", 9),
        ("viagens/2020/IMG_0001.JPG.json", "sidecar", 47),
        ("dupe.txt", "file", 9),
    ]

    media = records[3]
    side = records[4]
    assert media["sha256"] == "116e3e34275a45e9e9b044905da8043e8a301987e890fdb331fd4464c161d6df"
    assert side["sidecar_of"] == "IMG_0001.JPG"
    assert side["sha256"] == "cea146c2da3a5f0272013a3f0bb381f007d6daefb9fcd4503dcd0585b6a37dd9"
    assert (
        records[2]["sha256"] == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )

    dest = master / "consolidated" / "bkp1" / "viagens" / "2020" / "IMG_0001.JPG"
    assert dest.read_bytes() == b"foto 2020"
    assert (master / "consolidated" / "bkp2" / "dupe.txt").read_text() == "duplicata"
    assert (master / "consolidated" / "bkp1" / "vazio.txt").stat().st_size == 0
