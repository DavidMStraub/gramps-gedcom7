"""Test the people at an event, as its ASSO structures name them."""

import io
import pathlib

import gedcom7
import pytest
from gedcom7 import const as g7const
from gramps.gen.db.utils import make_database
from gramps.gen.lib import EventRoleType, EventType

from gramps_gedcom7.export import db_to_structures
from gramps_gedcom7.importer import import_gedcom

GEDCOM_FILE = pathlib.Path(__file__).parent / "data" / "event_asso.ged"


def import_file(source):
    db = make_database("sqlite")
    db.load(":memory:")
    report = import_gedcom(source, db)
    return db, report


@pytest.fixture
def db():
    database, _ = import_file(str(GEDCOM_FILE))
    return database


def refs_to(db, gramps_id, event_type):
    """The person's references to events of a type, with the events."""
    person = db.get_person_from_gramps_id(gramps_id)
    found = []
    for event_ref in person.get_event_ref_list():
        event = db.get_event_from_handle(event_ref.ref)
        if event.get_type() == event_type:
            found.append((event_ref, event))
    return found


def note_texts(db, obj):
    return [db.get_note_from_handle(handle).get() for handle in obj.get_note_list()]


def find(structure, tag):
    return next((c for c in structure.children if c.tag == tag), None)


def find_all(structure, tag):
    return [c for c in structure.children if c.tag == tag]


def record(records, xref):
    return next(r for r in records if r.xref == xref)


def test_godparent_shares_the_birth(db):
    ((principal_ref, birth),) = refs_to(db, "I2", EventType.BIRTH)
    ((godparent_ref, godparent_birth),) = refs_to(db, "I1", EventType.BIRTH)
    assert godparent_birth.handle == birth.handle
    assert principal_ref.get_role() == EventRoleType.PRIMARY
    assert godparent_ref.get_role() == EventRoleType.GODPARENT
    assert note_texts(db, godparent_ref) == ["Stood in for his brother"]


def test_other_role_is_named_by_its_phrase(db):
    ((midwife_ref, _),) = refs_to(db, "I3", EventType.BIRTH)
    assert midwife_ref.get_role().is_custom()
    assert str(midwife_ref.get_role()) == "Midwife"


def test_witnesses_share_the_family_event(db):
    (marriage,) = [
        e for e in db.iter_events() if e.get_type() == EventType.MARRIAGE
    ]
    for gramps_id in ("I1", "I4"):
        ((witness_ref, event),) = refs_to(db, gramps_id, EventType.MARRIAGE)
        assert event.handle == marriage.handle
        assert witness_ref.get_role() == EventRoleType.WITNESS
    ((best_man_ref, _),) = refs_to(db, "I4", EventType.MARRIAGE)
    assert note_texts(db, best_man_ref) == ["Best man"]


def test_void_associate_is_reported():
    _, report = import_file(str(GEDCOM_FILE))
    assert any(
        "MARR > ASSO > ROLE" in str(entry) for entry in report
    ), report.messages()


def test_event_is_written_by_its_principal_with_the_others_as_associates(db):
    records = db_to_structures(db)
    assert gedcom7.validate(records) == []
    godparent = record(records, "@I1@")
    assert find(godparent, g7const.BIRT) is None
    assert find(godparent, g7const.EVEN) is None
    birth = find(record(records, "@I2@"), g7const.BIRT)
    godp, midwife = find_all(birth, g7const.ASSO)
    assert (godp.pointer, find(godp, g7const.ROLE).text) == ("@I1@", "GODP")
    assert find(godp, g7const.NOTE).text == "Stood in for his brother"
    role = find(midwife, g7const.ROLE)
    assert (role.text, find(role, g7const.PHRASE).text) == ("OTHER", "Midwife")


def test_family_event_is_written_by_the_family(db):
    records = db_to_structures(db)
    marriage = find(record(records, "@F1@"), g7const.MARR)
    associates = find_all(marriage, g7const.ASSO)
    assert [(a.pointer, find(a, g7const.ROLE).text) for a in associates] == [
        ("@I1@", "WITN"),
        ("@I4@", "WITN"),
    ]
    for xref in ("@I1@", "@I4@"):
        assert find(record(records, xref), g7const.EVEN) is None


@pytest.mark.parametrize("role", ["SPOU", "OTHER"])
def test_role_without_a_gramps_one_survives_a_round_trip(role):
    source = f"""0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 NAME A /B/
1 CENS
2 ASSO @I2@
3 ROLE {role}
0 @I2@ INDI
1 NAME C /D/
0 TRLR
"""
    db, _ = import_file(io.StringIO(source))
    records = db_to_structures(db)
    census = find(record(records, "@I1@"), g7const.CENS)
    role_structure = find(find(census, g7const.ASSO), g7const.ROLE)
    assert role_structure.text == role
    assert find(role_structure, g7const.PHRASE) is None


def test_associate_that_is_not_an_individual_is_reported():
    source = """0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 NAME A /B/
1 CENS
2 ASSO @F1@
3 ROLE WITN
0 @F1@ FAM
0 TRLR
"""
    db, report = import_file(io.StringIO(source))
    assert any("does not point at an individual" in str(e) for e in report)
    (person,) = db.iter_people()
    assert len(person.get_event_ref_list()) == 1
