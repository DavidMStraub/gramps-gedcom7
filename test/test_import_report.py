"""Tests for what an import reports, and for what it no longer refuses."""

from __future__ import annotations

import io
import pathlib

import gedcom7
import pytest
from gramps.gen.db.utils import make_database
from gramps.gen.lib import Date

from gramps_gedcom7 import process
from gramps_gedcom7.importer import import_gedcom
from gramps_gedcom7.settings import ImportSettings

DATA = pathlib.Path(__file__).parent / "data"


def gedcom(body: str) -> str:
    return "0 HEAD\n1 GEDC\n2 VERS 7.0\n" + body + "0 TRLR\n"


def empty_db():
    db = make_database("sqlite")
    db.load(":memory:")
    return db


def import_text(body: str, **kwargs):
    db = empty_db()
    report = import_gedcom(io.StringIO(gedcom(body)), db, **kwargs)
    return db, report


def first_event_date(db) -> Date:
    (event,) = db.iter_events()
    return event.get_date_object()


@pytest.mark.parametrize(
    "value",
    [
        "BET JULIAN 1 JAN 1700 AND GREGORIAN 5 JAN 1700",
        "FROM JULIAN 1700 TO 1701",
    ],
)
def test_date_in_two_calendars_is_imported_as_text(value):
    db, report = import_text(f"0 @I1@ INDI\n1 BIRT\n2 DATE {value}\n")
    date = first_event_date(db)
    assert date.get_modifier() == Date.MOD_TEXTONLY
    assert date.get_text() == value
    assert [entry.where for entry in report] == ["@I1@ INDI > BIRT > DATE"]


def test_date_in_one_calendar_is_still_a_date():
    """Gregorian is what a date naming no calendar is in."""
    db, report = import_text(
        "0 @I1@ INDI\n1 BIRT\n2 DATE BET GREGORIAN 1700 AND 1701\n"
    )
    assert first_event_date(db).get_modifier() == Date.MOD_RANGE
    assert len(report) == 0


def records_with_broken_pointer():
    """A family pointing at a person not in the file.

    The parser refuses such a file, so the pointer is broken after parsing.
    """
    records = gedcom7.loads(gedcom("0 @I1@ INDI\n0 @F3@ FAM\n1 HUSB @I1@\n1 WIFE @I1@\n"))
    family = next(r for r in records if r.xref == "@F3@")
    family.children[0].pointer = "@I9@"
    return records


def test_broken_pointer_is_named_with_where_it_is():
    with pytest.raises(process.BrokenPointersError) as caught:
        process.process_gedcom_structures(
            records_with_broken_pointer(), empty_db(), ImportSettings()
        )
    assert str(caught.value.broken[0]) == "@F3@ FAM > HUSB points at missing @I9@"


def test_broken_pointer_can_be_left_out():
    db = empty_db()
    report = process.process_gedcom_structures(
        records_with_broken_pointer(), db, ImportSettings(void_broken_pointers=True)
    )
    (family,) = db.iter_families()
    assert family.get_father_handle() is None
    assert family.get_mother_handle() is not None
    assert report.messages() == [
        "@F3@ FAM > HUSB: points at missing @I9@, so the link was left out"
    ]


def test_file_with_broken_pointers_imports_when_asked():
    text = gedcom("0 @F3@ FAM\n1 HUSB @I9@\n1 SNOTE @N1@\n")
    try:
        gedcom7.loads(text)
    except gedcom7.GedcomParseError:
        pytest.skip("this gedcom7 refuses dangling pointers when parsing")
    with pytest.raises(process.BrokenPointersError) as caught:
        import_text("0 @F3@ FAM\n1 HUSB @I9@\n1 SNOTE @N1@\n")
    assert len(caught.value.broken) == 2
    db, report = import_text(
        "0 @F3@ FAM\n1 HUSB @I9@\n1 SNOTE @N1@\n",
        settings=ImportSettings(void_broken_pointers=True),
    )
    assert db.get_number_of_families() == 1
    assert len(report) == 2


def test_what_is_not_imported_is_reported():
    _, report = import_text(
        "1 SCHMA\n2 TAG _FOO https://example.com/foo\n"
        "0 @I1@ INDI\n1 _FOO bar\n1 NAME John /Doe/\n2 TRAN Jan /Doe/\n3 LANG nl\n"
        "0 @I2@ INDI\n1 NAME Jane /Doe/\n2 TRAN Jana /Doe/\n"
        "0 @X1@ _REC\n1 NOTE lost\n"
    )
    assert report.messages() == [
        # A declared extension tag is known by its URI.
        "INDI > https://example.com/foo: not imported (first in @I1@)",
        "INDI > NAME > TRAN: not imported, 2 times (first in @I1@)",
        "_REC: not imported (first in @X1@)",
    ]


def test_example_file_reports_no_header_bookkeeping():
    report = import_gedcom(DATA / "maximal70.ged", empty_db())
    paths = {entry.where for entry in report}
    assert "INDI > NAME > TRAN" in paths
    assert not any(path.startswith("HEAD > GEDC") for path in paths)
    assert not any(path.endswith("CHAN > DATE > TIME") for path in paths)


def test_change_time_is_imported():
    db, _ = import_text(
        "0 @I1@ INDI\n1 CHAN\n2 DATE 1 JAN 2020\n3 TIME 12:30:00Z\n"
    )
    (person,) = db.iter_people()
    assert person.change % 86400 == 12 * 3600 + 30 * 60


def test_progress_rises_to_twice_the_records():
    calls = []
    import_gedcom(
        DATA / "maximal70.ged",
        empty_db(),
        progress=lambda done, total: calls.append((done, total)),
    )
    done = [d for d, _ in calls]
    assert done == sorted(done)
    total = calls[-1][1]
    assert {t for _, t in calls} == {total}
    assert calls[-1] == (total, total)


def test_import_leaves_parsed_structures_as_it_found_them():
    records = gedcom7.loads(gedcom("0 @I1@ INDI\n1 NAME John /Doe/\n"))
    process.process_gedcom_structures(records, empty_db(), ImportSettings())
    assert all(type(r) is gedcom7.types.GedcomStructure for r in records)
