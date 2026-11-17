"""Test details Gramps' own GEDCOM import keeps, which this one now keeps too."""

import io
import pathlib

import gedcom7
import pytest
from gedcom7 import const as g7const
from gramps.gen.db.utils import make_database
from gramps.gen.lib import (
    Attribute,
    AttributeType,
    Event,
    EventRef,
    EventType,
    NoteType,
    Person,
)

from gramps_gedcom7 import process
from gramps_gedcom7.export import db_to_structures
from gramps_gedcom7.importer import import_gedcom

GEDCOM_FILE = pathlib.Path(__file__).parent / "data" / "details.ged"


def import_source(source):
    db = make_database("sqlite")
    db.load(":memory:")
    report = import_gedcom(source, db)
    return db, report


def reimport(db):
    records = db_to_structures(db)
    assert gedcom7.validate(records) == []
    return import_source(io.StringIO(gedcom7.dumps(records)))


@pytest.fixture(params=["imported", "reimported"])
def imported(request):
    """The fixture as imported, and after an export and an import of that."""
    db, report = import_source(str(GEDCOM_FILE))
    return (db, report) if request.param == "imported" else reimport(db)


@pytest.fixture
def db(imported):
    return imported[0]


def find(structure, tag):
    return next((c for c in structure.children if c.tag == tag), None)


def notes(db, obj):
    return [db.get_note_from_handle(h) for h in obj.get_note_list()]


def person(db):
    return db.get_person_from_gramps_id("I1")


def event_and_ref(db, obj, event_type):
    for ref in obj.get_event_ref_list():
        event = db.get_event_from_handle(ref.ref)
        if event.get_type() == event_type:
            return event, ref
    raise AssertionError(f"no {event_type}")


def attributes(obj):
    return {
        a.get_type().xml_str(): a.get_value() for a in obj.get_attribute_list()
    }


def test_nothing_is_reported():
    _, report = import_source(str(GEDCOM_FILE))
    assert [str(entry) for entry in report] == []


def test_citation_data_gives_its_date_and_text(db):
    birth, _ = event_and_ref(db, person(db), EventType.BIRTH)
    (citation,) = [db.get_citation_from_handle(h) for h in birth.get_citation_list()]
    assert citation.get_date_object().get_ymd() == (1900, 1, 3)
    (text,) = notes(db, citation)
    assert text.get() == "Johann, ehelicher Sohn des ..."
    assert text.get_type() == NoteType.SOURCE_TEXT


def test_name_keeps_its_citation(db):
    name = person(db).get_primary_name()
    (citation,) = [db.get_citation_from_handle(h) for h in name.get_citation_list()]
    assert citation.get_page() == "S. 7"


def test_type_of_a_birth_is_its_description(db):
    birth, _ = event_and_ref(db, person(db), EventType.BIRTH)
    assert birth.get_description() == "Hausgeburt"


def test_ages_are_kept_on_the_references(db):
    _, birth_ref = event_and_ref(db, person(db), EventType.BIRTH)
    _, death_ref = event_and_ref(db, person(db), EventType.DEATH)
    assert attributes(birth_ref) == {"Age": "0y (newborn)"}
    assert attributes(death_ref) == {"Age": "> 70y"}
    family = db.get_family_from_gramps_id("F2")
    _, marriage_ref = event_and_ref(db, family, EventType.MARRIAGE)
    assert attributes(marriage_ref) == {
        "Father Age": "25y",
        "Mother Age": "about twenty",
    }


def test_notes_on_links_to_families_are_the_persons(db):
    texts = [n.get() for n in notes(db, person(db))]
    assert "Raised by his grandparents" in texts
    assert "His second marriage" in texts


def test_repository_reference_keeps_its_note(db):
    source = db.get_source_from_gramps_id("S1")
    (reference,) = source.get_reporef_list()
    assert reference.get_call_number() == "KB-12"
    (note,) = notes(db, reference)
    assert note.get() == "Regal 3, oben"
    assert note.get_type() == NoteType.REPOREF


def test_media_keeps_its_medium(db):
    media = db.get_media_from_gramps_id("O1")
    assert attributes(media)["Media-Type"] == "Tombstone"


def test_export_writes_them_where_they_came_from():
    db, _ = import_source(str(GEDCOM_FILE))
    records = {r.xref: r for r in db_to_structures(db)}
    birth = find(records["@I1@"], g7const.BIRT)
    assert find(birth, g7const.TYPE).text == "Hausgeburt"
    assert find(birth, g7const.NOTE) is None
    age = find(birth, g7const.AGE)
    assert (age.text, find(age, g7const.PHRASE).text) == ("0y", "newborn")
    data = find(find(birth, g7const.SOUR), g7const.DATA)
    assert find(data, g7const.DATE).text == "3 JAN 1900"
    assert find(data, g7const.TEXT).text == "Johann, ehelicher Sohn des ..."
    marriage = find(records["@F2@"], g7const.MARR)
    assert find(find(marriage, g7const.HUSB), g7const.AGE).text == "25y"
    wife_age = find(find(marriage, g7const.WIFE), g7const.AGE)
    assert (wife_age.text, find(wife_age, g7const.PHRASE).text) == ("", "about twenty")
    reference = find(records["@S1@"], g7const.REPO)
    assert find(reference, g7const.NOTE).text == "Regal 3, oben"
    form = find(find(records["@O1@"], g7const.FILE), g7const.FORM)
    assert find(form, g7const.MEDI).text == "TOMBSTONE"


def test_age_not_in_gedcom_syntax_is_written_as_its_phrase():
    """An age entered in Gramps need not be one GEDCOM can read."""
    person = Person()
    person.handle, person.gramps_id = "p1", "I1"
    event = Event()
    event.handle, event.gramps_id = "e1", "E1"
    event.set_type(EventType(EventType.DEATH))
    ref = EventRef()
    ref.ref = "e1"
    age = Attribute()
    age.set_type(AttributeType(AttributeType.AGE))
    age.set_value("about 80")
    ref.add_attribute(age)
    person.add_event_ref(ref)
    db = make_database("sqlite")
    db.load(":memory:")
    process.add_objects_to_database([person, event], db)
    records = db_to_structures(db)
    assert gedcom7.validate(records) == []
    (individual,) = [r for r in records if r.tag == g7const.INDI]
    written = find(find(individual, g7const.DEAT), g7const.AGE)
    assert (written.text, find(written, g7const.PHRASE).text) == ("", "about 80")
