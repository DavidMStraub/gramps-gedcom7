"""Test GEDCOM attributes read as events, and those kept as attributes."""

import io
import pathlib

import gedcom7
import pytest
from gedcom7 import const as g7const
from gramps.gen.db.utils import make_database
from gramps.gen.lib import AttributeType, EventType

from gramps_gedcom7 import process
from gramps_gedcom7.export import db_to_structures, export_gedcom
from gramps_gedcom7.importer import import_gedcom

GEDCOM_FILE = pathlib.Path(__file__).parent / "data" / "attribute_events.ged"


def import_source(source):
    db = make_database("sqlite")
    db.load(":memory:")
    import_gedcom(source, db)
    return db


def reimport(db):
    records = db_to_structures(db)
    assert gedcom7.validate(records) == []
    return import_source(io.StringIO(gedcom7.dumps(records)))


@pytest.fixture(params=["imported", "reimported"])
def db(request):
    """The fixture as imported, and after an export and an import of that."""
    database = import_source(str(GEDCOM_FILE))
    return database if request.param == "imported" else reimport(database)


def event_of(db, obj, event_type):
    (event,) = [
        e
        for e in (db.get_event_from_handle(r.ref) for r in obj.get_event_ref_list())
        if e.get_type() == event_type
    ]
    return event


def place_title(db, event):
    names = []
    handle = event.get_place_handle()
    while handle:
        place = db.get_place_from_handle(handle)
        names.append(place.get_name().get_value())
        refs = place.get_placeref_list()
        handle = refs[0].ref if refs else None
    return ", ".join(names)


def citations(db, obj):
    found = []
    for handle in obj.get_citation_list():
        citation = db.get_citation_from_handle(handle)
        source = db.get_source_from_handle(citation.get_reference_handle())
        found.append((source.get_title(), citation.get_page()))
    return found


def notes(db, obj):
    return [db.get_note_from_handle(h).get() for h in obj.get_note_list()]


def person(db):
    return db.get_person_from_gramps_id("I1")


def test_residence_keeps_its_date_place_note_and_citations(db):
    residence = event_of(db, person(db), EventType.RESIDENCE)
    assert residence.get_description() == "Hauptstraße 5"
    date = residence.get_date_object()
    assert (date.get_start_date()[2], date.get_stop_date()[2]) == (1900, 1910)
    assert place_title(db, residence) == "Berlin, Preußen, Deutschland"
    assert notes(db, residence) == ["Lived above the bakery"]
    assert citations(db, residence) == [
        ("Adressbuch Berlin 1905", "S. 412"),
        ("Volkszählung 1905", "Bd. 3"),
    ]


def test_occupation_keeps_its_date_place_and_citation(db):
    occupation = event_of(db, person(db), EventType.OCCUPATION)
    assert occupation.get_description() == "Bäcker"
    assert occupation.get_date_object().get_year() == 1905
    assert place_title(db, occupation) == "Berlin, Preußen, Deutschland"
    assert citations(db, occupation) == [("Adressbuch Berlin 1905", "S. 413")]


def test_title_is_a_nobility_title_event(db):
    title = event_of(db, person(db), EventType.NOB_TITLE)
    assert title.get_description() == "Freiherr"


def test_family_residence_is_a_family_event(db):
    family = db.get_family_from_gramps_id("F1")
    residence = event_of(db, family, EventType.RESIDENCE)
    assert residence.get_description() == "Gartenweg 2"
    assert place_title(db, residence) == "Potsdam, Preußen, Deutschland"
    assert citations(db, residence) == [("Volkszählung 1905", "Bd. 9")]


def test_generic_event_keeps_its_payload(db):
    (exam,) = [
        db.get_event_from_handle(r.ref)
        for r in person(db).get_event_ref_list()
        if db.get_event_from_handle(r.ref).get_type().xml_str() == "Examination"
    ]
    assert exam.get_description() == "Gesellenprüfung"


def test_attribute_keeps_its_note_citation_and_privacy(db):
    (nationality,) = [
        a
        for a in person(db).get_attribute_list()
        if a.get_type() == AttributeType.NATIONAL
    ]
    assert nationality.get_value() == "deutsch"
    assert nationality.get_privacy()
    assert notes(db, nationality) == ["According to the census"]
    assert citations(db, nationality) == [("Volkszählung 1905", "Bd. 4")]


def test_nothing_becomes_both_an_event_and_an_attribute(db):
    names = {a.get_type().xml_str() for a in person(db).get_attribute_list()}
    assert not names & {"Occupation", "Residence", "Title"}


def test_events_are_written_as_the_attributes_they_came_from():
    records = db_to_structures(import_source(str(GEDCOM_FILE)))
    (individual,) = [r for r in records if r.xref == "@I1@"]
    tags = [(c.tag, c.text) for c in individual.children]
    assert (g7const.RESI, "Hauptstraße 5") in tags
    assert (g7const.OCCU, "Bäcker") in tags
    assert (g7const.TITL, "Freiherr") in tags
    assert [t for t in tags if t[0] == g7const.EVEN] == [
        (g7const.EVEN, "Gesellenprüfung")
    ]


def test_privacy_with_nowhere_to_go_is_reported():
    """AGNC takes no RESN, so a private agency cannot say it is private."""
    db = import_source(
        io.StringIO(
            "0 HEAD\n1 GEDC\n2 VERS 7.0\n0 @I1@ INDI\n1 BIRT\n2 AGNC Registry\n0 TRLR\n"
        )
    )
    person = db.get_person_from_gramps_id("I1")
    event = db.get_event_from_handle(person.get_event_ref_list()[0].ref)
    (agency,) = event.get_attribute_list()
    agency.set_privacy(True)
    process.add_objects_to_database([event], db)
    report = export_gedcom(db, io.BytesIO())
    assert any("privacy of attribute" in str(entry) for entry in report)
