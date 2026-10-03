"""Phase 4 CLI (Implementation Plan section 4): generate, decide --file, decide --a/--b, extract."""

from pathlib import Path

import pytest

from app.cli import main


def test_generate_then_decide_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "seed-7"
    main(["generate", "--seed", "7", "--n-entities", "120", "--out", str(out)])
    text = capsys.readouterr().out
    assert text.startswith("SYNTHETIC DATA") and "sha256" in text
    assert (out / "manifest.json").exists() and (out / "truth_pairs.csv").exists()

    main(["decide", "--file", str(out)])
    text = capsys.readouterr().out
    assert "Verdict mix by truth label" in text and "NOT_EQUIVALENT_HARD" in text
    assert "rows without a rule ID or rule text: 0" in text


def test_decide_one_pair_prints_the_evidence_card(capsys: pytest.CaptureFixture[str]) -> None:
    main(
        [
            "decide",
            "--a",
            "VALVE GATE 4IN CL150 A216 WCB FLGD RF",
            "--b",
            "GV 100NB 150# WCB RF FLANGED",
        ]
    )
    text = capsys.readouterr().out
    assert "verdict EQUIVALENT · route REVIEW" in text
    assert "VALVE.size_dn" in text and "4 IN = DN100" in text and "100 NB = DN100" in text
    assert "critical class: maker-checker" in text


def test_extract_and_usage(capsys: pytest.CaptureFixture[str]) -> None:
    main(["extract", "--text", "PIPE SMLS 6IN SCH40 A106 GR.B"])
    text = capsys.readouterr().out
    assert "category:   PIPE (RULE)" in text and "short:      PIPE SMLS 6IN SCH40 A106-B" in text
    with pytest.raises(SystemExit):
        main(["decide", "--a", "only one side"])
