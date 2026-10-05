"""FR-101, FR-102, FR-1005: file parsing, encodings and column suggestions (no database)."""

import io

import pytest
from openpyxl import Workbook

from app.services.errors import Invalid
from app.services.ingest import norm_header, parse_table, suggest_mapping, validate_mapping
from tests.coreenv import dictionary


def test_utf8_csv_with_bom_and_semicolons() -> None:
    data = "﻿Material;Description\nA1;GATE VALVE 4IN\n".encode()
    t = parse_table(data, "a.csv")
    assert t.encoding == "utf-8" and t.headers == ["Material", "Description"]
    assert t.rows == [["A1", "GATE VALVE 4IN"]]


def test_latin1_sample_shows_no_garbled_characters() -> None:
    """FR-101: a Latin-1 / cp1252 file keeps its accents."""
    data = 'code,text\nA1,MANGUERA PRESIÓN ÁNGULO 4"\n'.encode("cp1252")
    t = parse_table(data, "a.csv")
    assert t.encoding != "utf-8" and "PRESIÓN ÁNGULO" in t.rows[0][1]


def test_xlsx_first_sheet_numbers_become_text_without_point_zero() -> None:
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.append(["MATNR", "MAKTX", "ANNUAL"])
    ws.append([100234, "PIPE SMLS 4IN SCH40", 1250.0])
    ws.append([100235, "PIPE SMLS 6IN SCH40", 12.5])
    buf = io.BytesIO()
    wb.save(buf)
    t = parse_table(buf.getvalue(), "m.xlsx")
    assert t.encoding == "xlsx" and t.rows == [
        ["100234", "PIPE SMLS 4IN SCH40", "1250"],
        ["100235", "PIPE SMLS 6IN SCH40", "12.5"],
    ]


@pytest.mark.parametrize(
    ("data", "name", "title"),
    [
        (b"", "a.csv", "Empty file"),
        (b"a,b\n", "a.csv", "Empty file"),  # header only is fine; checked below
        (b"x", "a.pdf", "Unsupported file type"),
        (b"a,a\n1,2\n", "a.csv", "Duplicate column headers"),
    ],
)
def test_bad_files_are_rejected_with_a_title(data: bytes, name: str, title: str) -> None:
    if data == b"a,b\n":
        assert parse_table(data, name).rows == []  # header only: zero rows, not an error
        return
    with pytest.raises(Invalid) as err:
        parse_table(data, name)
    assert err.value.title == title


def test_blank_rows_are_dropped_and_short_rows_padded() -> None:
    t = parse_table(b"a,b,c\n1,2\n\n,,\n3,4,5\n", "a.csv")
    assert t.rows == [["1", "2", ""], ["3", "4", "5"]]


def test_norm_header_ignores_case_and_punctuation() -> None:
    assert norm_header("MARA-MATNR") == norm_header("mara matnr") == "mara matnr"


def test_generic_headers_are_suggested() -> None:
    headers = ["Material Code", "Short Text", "Long Description", "UoM", "Make", "Part Number"]
    mapping, preset = suggest_mapping(headers, dictionary())
    assert mapping == {
        "Material Code": "legacy_code", "Short Text": "short_text",
        "Long Description": "long_text", "UoM": "uom", "Make": "manufacturer",
        "Part Number": "mpn",
    }  # fmt: skip
    assert preset is None


def test_sap_preset_is_detected_and_mapped_without_manual_work() -> None:
    """FR-1005: a SAP-style extract maps with no manual mapping (Appendix H.2)."""
    headers = ["MARA-MATNR", "MAKT-MAKTX", "MARA-MEINS", "MARA-MATKL", "MARC-WERKS", "LABST"]
    mapping, preset = suggest_mapping(headers, dictionary())
    assert preset == "SAP"
    assert mapping == {
        "MARA-MATNR": "legacy_code", "MAKT-MAKTX": "short_text", "MARA-MEINS": "uom",
        "MARA-MATKL": "mat_group", "MARC-WERKS": "plant", "LABST": "stock_qty",
    }  # fmt: skip


def test_the_generators_own_headers_map_themselves() -> None:
    from app.eval.generator import RECORD_COLUMNS

    mapping, _ = suggest_mapping(RECORD_COLUMNS, dictionary())
    assert mapping == {c: c for c in RECORD_COLUMNS}


def test_each_target_is_suggested_once() -> None:
    mapping, _ = suggest_mapping(["Material Code", "Item Code"], dictionary())
    assert list(mapping.values()) == ["legacy_code"]


@pytest.mark.parametrize(
    ("mapping", "message"),
    [
        ({"A": "legacy_code"}, "short_text or long_text"),
        ({"A": "short_text"}, "legacy_code"),
        ({"A": "legacy_code", "B": "legacy_code", "C": "short_text"}, "Two columns map"),
        ({"A": "legacy_code", "B": "colour"}, "Unknown target"),
        ({"A": "legacy_code", "Z": "short_text"}, "not in the file"),
    ],
)
def test_mapping_is_validated(mapping: dict[str, str], message: str) -> None:
    with pytest.raises(Invalid, match=message):
        validate_mapping(mapping, ["A", "B", "C"])
