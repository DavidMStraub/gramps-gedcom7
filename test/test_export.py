"""Tests for exporting a Gramps database to GEDCOM 7."""

from __future__ import annotations

import io
import pathlib
import re

import gedcom7
import pytest
from gedcom7 import const as g7const
from gramps.gen.db.utils import make_database
from gramps.gen.lib import (
    Address,
    Attribute,
    AttributeType,
    Citation,
    Date,
    Event,
    EventRef,
    EventRoleType,
    EventType,
    Family,
    Media,
    Name,
    NameType,
    Note,
    NoteType,
    Person,
    RepoRef,
    Repository,
    RepositoryType,
    Source,
    SourceMediaType,
    Surname,
)

from gramps_gedcom7 import process
from gramps_gedcom7.export import db_to_structures, export_gedcom
from gramps_gedcom7.export import util as export_util
from gramps_gedcom7.export.xrefs import XrefMap
from gramps_gedcom7.importer import import_gedcom

DATA = pathlib.Path(__file__).parent / "data"
DATA_FILES = sorted(DATA.glob("*.ged"))
V7 = "https://gedcom.io/terms/v7/"


def empty_db():
    db = make_database("sqlite")
    db.load(":memory:")
    return db


def db_from_objects(*objects):
    """Build a database from Gramps objects, as the import would."""
    db = empty_db()
    process.add_objects_to_database(list(objects), db)
    return db


def db_from_file(path) -> object:
    db = empty_db()
    import_gedcom(path, db)
    return db


def reimport(records) -> object:
    """Write a dataset and read it back into a fresh database."""
    return db_from_file(io.BytesIO(gedcom7.dumps(records).encode("utf-8")))


def counts(db) -> tuple[int, ...]:
    return (
        db.get_number_of_people(),
        db.get_number_of_families(),
        db.get_number_of_events(),
        db.get_number_of_places(),
    )


def find(structure, tag):
    """Get the first substructure with a tag, or None."""
    return next((c for c in structure.children if c.tag == tag), None)


def find_all(structure, tag):
    return [c for c in structure.children if c.tag == tag]


def records_by_tag(records, tag):
    return [r for r in records if r.tag == tag]


def make_person(gramps_id="I0001", given="John", surname="Doe", handle="p1"):
    person = Person()
    person.handle = handle
    person.gramps_id = gramps_id
    name = Name()
    name.set_first_name(given)
    if surname:
        surname_object = Surname()
        surname_object.set_surname(surname)
        name.add_surname(surname_object)
    person.set_primary_name(name)
    person.set_gender(Person.MALE)
    return person


def make_event(handle="e1", event_type=EventType.BIRTH, gramps_id="E0001"):
    event = Event()
    event.handle = handle
    event.gramps_id = gramps_id
    event.set_type(EventType(event_type))
    return event


@pytest.mark.parametrize("path", DATA_FILES, ids=lambda p: p.name)
def test_exported_dataset_conforms(path):
    """Everything the import reads can be written back as a valid dataset."""
    records = db_to_structures(db_from_file(str(path)))
    assert gedcom7.validate(records) == []


@pytest.mark.parametrize("path", DATA_FILES, ids=lambda p: p.name)
def test_round_trip_preserves_objects(path):
    """Reading an exported file back gives the same objects it was written from."""
    db = db_from_file(str(path))
    assert counts(reimport(db_to_structures(db))) == counts(db)


def test_dataset_begins_with_a_header_and_ends_with_a_trailer():
    records = db_to_structures(empty_db())
    assert records[0].tag == g7const.HEAD
    assert records[-1].tag == g7const.TRLR
    version = find(find(records[0], g7const.GEDC), g7const.VERS)
    assert version.text == "7.0"


def test_person_is_written_as_an_individual_record():
    records = db_to_structures(db_from_objects(make_person()))
    (individual,) = records_by_tag(records, g7const.INDI)
    assert individual.xref == "@I0001@"
    assert find(individual, g7const.NAME).text == "John /Doe/"
    assert find(individual, g7const.SEX).text == "M"
    assert find(find(individual, g7const.NAME), g7const.SURN).text == "Doe"


def test_person_without_a_surname_is_written_without_slashes():
    person = make_person(given="Madonna", surname="")
    records = db_to_structures(db_from_objects(person))
    (individual,) = records_by_tag(records, g7const.INDI)
    assert find(individual, g7const.NAME).text == "Madonna"


def test_person_without_a_name_gets_no_name_structure():
    """The payload of a name cannot be empty, so an empty name is not written."""
    person = make_person(given="", surname="")
    records = db_to_structures(db_from_objects(person))
    (individual,) = records_by_tag(records, g7const.INDI)
    assert find(individual, g7const.NAME) is None
    assert gedcom7.validate(records) == []


def test_private_person_is_written_as_confidential():
    person = make_person()
    person.set_privacy(True)
    records = db_to_structures(db_from_objects(person))
    (individual,) = records_by_tag(records, g7const.INDI)
    assert find(individual, g7const.RESN).text == "CONFIDENTIAL"


def test_change_date_is_written_in_utc():
    # Committing an object stamps it with the time of the commit, so the value
    # is given to the writer directly rather than through a database.
    record = gedcom7.types.GedcomStructure(tag=g7const.INDI, xref="@I1@")
    export_util.add_change_date(record, 1_700_000_000)  # 2023-11-14 22:13:20 UTC
    date = find(find(record, g7const.CHAN), g7const.DATE)
    assert date.text == "14 NOV 2023"
    assert find(date, g7const.TIME).text == "22:13:20Z"


def test_object_never_changed_gets_no_change_date():
    record = gedcom7.types.GedcomStructure(tag=g7const.INDI, xref="@I1@")
    export_util.add_change_date(record, 0)
    assert find(record, g7const.CHAN) is None


def test_family_links_its_members():
    father = make_person(gramps_id="I0001", handle="p1")
    child = make_person(gramps_id="I0002", handle="p2", given="Jane")
    family = Family()
    family.handle = "f1"
    family.gramps_id = "F0001"
    family.set_father_handle("p1")
    family.add_child_ref(_child_ref("p2"))
    father.add_family_handle("f1")
    child.add_parent_family_handle("f1")
    records = db_to_structures(db_from_objects(father, child, family))
    (fam,) = records_by_tag(records, g7const.FAM)
    assert find(fam, g7const.HUSB).pointer == "@I0001@"
    assert find(fam, g7const.CHIL).pointer == "@I0002@"
    assert gedcom7.validate(records) == []


def _child_ref(handle):
    from gramps.gen.lib import ChildRef

    child_ref = ChildRef()
    child_ref.ref = handle
    return child_ref


def test_event_is_written_under_the_person_that_points_at_it():
    person = make_person()
    event = make_event()
    event.set_date_object(Date())
    event.get_date_object().set_yr_mon_day(1900, 5, 1)
    event_ref = EventRef()
    event_ref.ref = "e1"
    person.add_event_ref(event_ref)
    records = db_to_structures(db_from_objects(person, event))
    (individual,) = records_by_tag(records, g7const.INDI)
    birth = find(individual, g7const.BIRT)
    assert find(birth, g7const.DATE).text == "1 MAY 1900"


def test_shared_event_is_written_once_with_the_others_as_associates():
    """A Gramps event may be shared; a GEDCOM event lives in one record."""
    first = make_person(gramps_id="I0001", handle="p1")
    second = make_person(gramps_id="I0002", handle="p2", given="Jane")
    event = make_event(event_type=EventType.CENSUS)
    for person, role in ((first, EventRoleType.PRIMARY), (second, EventRoleType.WITNESS)):
        event_ref = EventRef()
        event_ref.ref = "e1"
        event_ref.set_role(EventRoleType(role))
        person.add_event_ref(event_ref)
    records = db_to_structures(db_from_objects(first, second, event))
    first_record, second_record = records_by_tag(records, g7const.INDI)
    assert find(first_record, g7const.CENS) is not None
    assert find(second_record, g7const.CENS) is None
    associate = find(find(first_record, g7const.CENS), g7const.ASSO)
    assert associate.pointer == "@I0002@"
    assert find(associate, g7const.ROLE).text == "WITN"
    assert gedcom7.validate(records) == []


def test_custom_event_type_is_written_as_a_generic_event():
    person = make_person()
    event = make_event(event_type=EventType.OCCUPATION)
    event.set_description("Baker")
    event_ref = EventRef()
    event_ref.ref = "e1"
    person.add_event_ref(event_ref)
    records = db_to_structures(db_from_objects(person, event))
    (individual,) = records_by_tag(records, g7const.INDI)
    generic = find(individual, g7const.EVEN)
    assert generic.text == "Baker"
    # The untranslated name, so that the file does not depend on the locale.
    assert find(generic, g7const.TYPE).text == "Occupation"


def test_attribute_with_nowhere_to_go_is_left_out():
    """An attribute the structure cannot hold is dropped, not made invalid."""
    person = make_person()
    attribute = Attribute()
    attribute.set_type(AttributeType(AttributeType.CASTE))
    attribute.set_value("Caste")
    event = make_event()
    event.add_attribute(attribute)
    event_ref = EventRef()
    event_ref.ref = "e1"
    person.add_event_ref(event_ref)
    records = db_to_structures(db_from_objects(person, event))
    assert find(find(records_by_tag(records, g7const.INDI)[0], g7const.BIRT),
                g7const.CAST) is None
    assert gedcom7.validate(records) == []


def test_identifiers_keep_their_type():
    person = make_person()
    attribute = Attribute()
    attribute.set_type(AttributeType((AttributeType.CUSTOM, "EXID:http://example.com")))
    attribute.set_value("123")
    person.add_attribute(attribute)
    records = db_to_structures(db_from_objects(person))
    (individual,) = records_by_tag(records, g7const.INDI)
    external = find(individual, g7const.EXID)
    assert external.text == "123"
    assert find(external, g7const.TYPE).text == "http://example.com"


@pytest.mark.parametrize(
    ["setup", "expected"],
    [
        (lambda d: d.set_yr_mon_day(1900, 5, 1), "1 MAY 1900"),
        (lambda d: d.set_yr_mon_day(1900, 5, 0), "MAY 1900"),
        (lambda d: d.set_yr_mon_day(1900, 0, 0), "1900"),
        (
            lambda d: d.set(modifier=Date.MOD_ABOUT, value=(1, 5, 1900, False)),
            "ABT 1 MAY 1900",
        ),
        (
            lambda d: d.set(modifier=Date.MOD_BEFORE, value=(0, 0, 1900, False)),
            "BEF 1900",
        ),
        (
            lambda d: d.set(modifier=Date.MOD_AFTER, value=(0, 0, 1900, False)),
            "AFT 1900",
        ),
        (
            lambda d: d.set(
                modifier=Date.MOD_RANGE, value=(0, 0, 1900, False, 0, 0, 1910, False)
            ),
            "BET 1900 AND 1910",
        ),
        (
            lambda d: d.set(
                modifier=Date.MOD_SPAN, value=(0, 0, 1900, False, 0, 0, 1910, False)
            ),
            "FROM 1900 TO 1910",
        ),
        (
            lambda d: d.set(quality=Date.QUAL_ESTIMATED, value=(0, 0, 1900, False)),
            "EST 1900",
        ),
        (
            lambda d: d.set(quality=Date.QUAL_CALCULATED, value=(0, 0, 1900, False)),
            "CAL 1900",
        ),
        (
            lambda d: d.set(calendar=Date.CAL_JULIAN, value=(1, 5, 1900, False)),
            "JULIAN 1 MAY 1900",
        ),
    ],
)
def test_dates_are_written_as_the_specification_spells_them(setup, expected):
    date = Date()
    setup(date)
    value = export_util.date_to_date_value(date)
    assert gedcom7.format_value(value, V7 + "DATE") == expected


def test_date_before_the_common_era_gets_an_epoch():
    date = Date()
    date.set_yr_mon_day(-44, 3, 15)
    value = export_util.date_to_date_value(date)
    assert gedcom7.format_value(value, V7 + "DATE") == "15 MAR 44 BCE"


def test_date_held_only_as_text_becomes_a_phrase():
    """A date GEDCOM cannot express is carried by the phrase beside it."""
    person = make_person()
    event = make_event()
    date = Date()
    date.set_as_text("the summer after the war")
    event.set_date_object(date)
    event_ref = EventRef()
    event_ref.ref = "e1"
    person.add_event_ref(event_ref)
    records = db_to_structures(db_from_objects(person, event))
    birth = find(records_by_tag(records, g7const.INDI)[0], g7const.BIRT)
    date_structure = find(birth, g7const.DATE)
    assert date_structure.text == ""
    assert find(date_structure, g7const.PHRASE).text == "the summer after the war"
    assert gedcom7.validate(records) == []


def test_empty_date_is_not_written():
    assert export_util.date_to_date_value(Date()) is None
    assert export_util.date_to_date_value(None) is None


class TestXrefs:
    def test_gramps_id_is_kept_where_it_can_be(self):
        xrefs = XrefMap()
        assert xrefs.add("h1", "I0001", "I") == "@I0001@"

    def test_characters_the_grammar_forbids_are_replaced(self):
        xrefs = XrefMap()
        assert xrefs.add("h1", "person one", "I") == "@PERSON_ONE@"

    def test_the_same_spelling_is_never_allocated_twice(self):
        xrefs = XrefMap()
        assert xrefs.add("h1", "X", "I") == "@X@"
        assert xrefs.add("h2", "X", "I") == "@X_2@"

    def test_an_object_without_an_id_falls_back_to_its_prefix(self):
        xrefs = XrefMap()
        assert xrefs.add("h1", "", "I") == "@I@"

    def test_a_record_may_not_claim_the_void_pointer(self):
        xrefs = XrefMap()
        assert xrefs.add("h1", "VOID", "I") == "@VOID_2@"

    def test_a_reference_to_nothing_is_written_as_the_void_pointer(self):
        assert XrefMap().pointer("missing") == g7const.VOIDPTR


def test_export_writes_a_file(tmp_path):
    path = tmp_path / "out.ged"
    export_gedcom(db_from_objects(make_person()), path)
    data = path.read_bytes()
    assert data.startswith("﻿".encode("utf-8"))
    assert b"0 @I0001@ INDI" in data


def test_export_writes_to_a_binary_stream():
    stream = io.BytesIO()
    export_gedcom(db_from_objects(make_person()), stream)
    assert b"1 NAME John /Doe/" in stream.getvalue()


def test_export_refuses_a_text_stream():
    with pytest.raises(TypeError):
        export_gedcom(db_from_objects(make_person()), io.StringIO())


def test_export_refuses_to_write_an_invalid_dataset(monkeypatch):
    """Validation is the safety net between a Gramps quirk and an unreadable file."""
    from gramps_gedcom7.export import exporter

    def broken(db, settings=None):
        return [gedcom7.types.GedcomStructure(tag=g7const.TRLR)]

    monkeypatch.setattr(exporter, "db_to_structures", broken)
    with pytest.raises(gedcom7.GedcomValidationError):
        exporter.export_gedcom(empty_db(), io.BytesIO())


def make_source(handle="s1", gramps_id="S0001", title="Parish register"):
    source = Source()
    source.handle = handle
    source.gramps_id = gramps_id
    source.set_title(title)
    return source


def make_note(handle="n1", gramps_id="N0001", text="A note", note_type=NoteType.PERSON):
    note = Note()
    note.handle = handle
    note.gramps_id = gramps_id
    note.set(text)
    note.set_type(NoteType(note_type))
    return note


def test_source_is_written_as_a_source_record():
    source = make_source()
    source.set_author("A Vicar")
    source.set_publication_info("Diocese, 1850")
    source.set_abbreviation("PR")
    records = db_to_structures(db_from_objects(source))
    (record,) = records_by_tag(records, g7const.SOUR)
    assert record.xref == "@S0001@"
    assert find(record, g7const.TITL).text == "Parish register"
    assert find(record, g7const.AUTH).text == "A Vicar"
    assert find(record, g7const.PUBL).text == "Diocese, 1850"
    assert find(record, g7const.ABBR).text == "PR"


def test_source_points_at_its_repository_with_a_call_number():
    repository = Repository()
    repository.handle = "r1"
    repository.gramps_id = "R0001"
    repository.set_name("County Archive")
    source = make_source()
    repo_ref = RepoRef()
    repo_ref.ref = "r1"
    repo_ref.set_call_number("MS 42")
    repo_ref.set_media_type(SourceMediaType(SourceMediaType.BOOK))
    source.add_repo_reference(repo_ref)
    records = db_to_structures(db_from_objects(source, repository))
    (record,) = records_by_tag(records, g7const.SOUR)
    reference = find(record, g7const.REPO)
    assert reference.pointer == "@R0001@"
    call_number = find(reference, g7const.CALN)
    assert call_number.text == "MS 42"
    assert find(call_number, g7const.MEDI).text == "BOOK"
    assert gedcom7.validate(records) == []


def test_repository_address_payload_is_the_street_alone():
    """The import reads the whole payload as the street, so only the street goes there."""
    repository = Repository()
    repository.handle = "r1"
    repository.gramps_id = "R0001"
    repository.set_name("County Archive")
    address = Address()
    address.set_street("1 Long Road")
    address.set_city("Springfield")
    address.set_postal_code("62701")
    repository.add_address(address)
    records = db_to_structures(db_from_objects(repository))
    (record,) = records_by_tag(records, g7const.REPO)
    addr = find(record, g7const.ADDR)
    assert addr.text == "1 Long Road"
    assert find(addr, g7const.CITY).text == "Springfield"
    assert find(addr, g7const.POST).text == "62701"


def test_repository_standing_for_a_submitter_is_written_as_one():
    """The import has nowhere but a repository to keep a submitter."""
    repository = Repository()
    repository.handle = "r1"
    repository.gramps_id = "R0001"
    repository.set_name("Submitter: John Doe")
    repository_type = RepositoryType()
    repository_type.set((RepositoryType.CUSTOM, "GEDCOM data"))
    repository.set_type(repository_type)
    records = db_to_structures(db_from_objects(repository))
    assert records_by_tag(records, g7const.REPO) == []
    (record,) = records_by_tag(records, g7const.SUBM)
    assert find(record, g7const.NAME).text == "John Doe"


def test_media_is_written_as_a_multimedia_record():
    media = Media()
    media.handle = "m1"
    media.gramps_id = "O0001"
    media.set_path("/photos/john.jpg")
    media.set_mime_type("image/jpeg")
    media.set_description("John as a boy")
    records = db_to_structures(db_from_objects(media))
    (record,) = records_by_tag(records, g7const.OBJE)
    file_structure = find(record, g7const.FILE)
    assert file_structure.text == "/photos/john.jpg"
    assert find(file_structure, g7const.FORM).text == "image/jpeg"
    assert find(file_structure, g7const.TITL).text == "John as a boy"


def test_media_without_a_type_is_given_one():
    """A file has to say what it is, so the name answers for it where Gramps cannot."""
    media = Media()
    media.handle = "m1"
    media.gramps_id = "O0001"
    media.set_path("/photos/john.png")
    records = db_to_structures(db_from_objects(media))
    (record,) = records_by_tag(records, g7const.OBJE)
    assert find(find(record, g7const.FILE), g7const.FORM).text == "image/png"


def test_note_belonging_to_one_record_is_written_inside_it():
    person = make_person()
    note = make_note(note_type=NoteType.PERSON)
    person.add_note("n1")
    records = db_to_structures(db_from_objects(person, note))
    (individual,) = records_by_tag(records, g7const.INDI)
    assert find(individual, g7const.NOTE).text == "A note"
    assert records_by_tag(records, g7const.SNOTE) == []


def test_general_note_is_written_as_a_shared_note():
    """Gramps calls a note general when nothing said what kind it was."""
    person = make_person()
    note = make_note(note_type=NoteType.GENERAL)
    person.add_note("n1")
    records = db_to_structures(db_from_objects(person, note))
    (individual,) = records_by_tag(records, g7const.INDI)
    (shared,) = records_by_tag(records, g7const.SNOTE)
    assert find(individual, g7const.SNOTE).pointer == shared.xref
    assert shared.text == "A note"


def test_note_two_records_share_is_written_as_a_shared_note():
    first = make_person(gramps_id="I0001", handle="p1")
    second = make_person(gramps_id="I0002", handle="p2", given="Jane")
    note = make_note(note_type=NoteType.PERSON)
    first.add_note("n1")
    second.add_note("n1")
    records = db_to_structures(db_from_objects(first, second, note))
    (shared,) = records_by_tag(records, g7const.SNOTE)
    for individual in records_by_tag(records, g7const.INDI):
        assert find(individual, g7const.SNOTE).pointer == shared.xref
        assert find(individual, g7const.NOTE) is None


def test_note_on_a_child_reference_is_written_as_its_phrase():
    """A child reference has nowhere to carry a note, but it has a phrase."""
    child = make_person(gramps_id="I0002", handle="p2", given="Jane")
    family = Family()
    family.handle = "f1"
    family.gramps_id = "F0001"
    child_ref = _child_ref("p2")
    child_ref.add_note("n1")
    family.add_child_ref(child_ref)
    child.add_parent_family_handle("f1")
    note = make_note(text="youngest of three", note_type=NoteType.CHILDREF)
    records = db_to_structures(db_from_objects(child, family, note))
    (fam,) = records_by_tag(records, g7const.FAM)
    assert find(find(fam, g7const.CHIL), g7const.PHRASE).text == "youngest of three"
    assert records_by_tag(records, g7const.SNOTE) == []


def test_source_text_is_written_as_the_text_of_the_source():
    source = make_source()
    source.add_note("n1")
    note = make_note(text="In the year of our Lord", note_type=NoteType.SOURCE_TEXT)
    records = db_to_structures(db_from_objects(source, note))
    (record,) = records_by_tag(records, g7const.SOUR)
    assert find(record, g7const.TEXT).text == "In the year of our Lord"
    assert find(record, g7const.NOTE) is None


def test_citation_is_written_where_it_is_cited():
    person = make_person()
    source = make_source()
    citation = Citation()
    citation.handle = "c1"
    citation.gramps_id = "C0001"
    citation.set_reference_handle("s1")
    citation.set_page("page 42")
    citation.set_confidence_level(Citation.CONF_HIGH)
    person.add_citation("c1")
    records = db_to_structures(db_from_objects(person, source, citation))
    (individual,) = records_by_tag(records, g7const.INDI)
    cited = find(individual, g7const.SOUR)
    assert cited.pointer == "@S0001@"
    assert find(cited, g7const.PAGE).text == "page 42"
    assert find(cited, g7const.QUAY).text == "3"
    assert gedcom7.validate(records) == []


@pytest.mark.parametrize(
    ["confidence", "expected"],
    [
        (Citation.CONF_VERY_LOW, "0"),
        (Citation.CONF_LOW, "1"),
        (Citation.CONF_NORMAL, "2"),
        (Citation.CONF_HIGH, "3"),
        (Citation.CONF_VERY_HIGH, "3"),
    ],
)
def test_confidence_inverts_what_the_import_reads(confidence, expected):
    from gramps_gedcom7.citation import CONFIDENCE_MAP
    from gramps_gedcom7.export.citation import CONFIDENCE_ENUMS

    assert CONFIDENCE_ENUMS[confidence] == expected
    # Every quality the import reads comes back as the quality it was read from.
    if expected in CONFIDENCE_MAP:
        assert CONFIDENCE_MAP[expected] == confidence or confidence == Citation.CONF_VERY_HIGH


def date_payload(date):
    """The payload a Gramps date is written with, or None where it is not."""
    value = export_util.date_to_date_value(date)
    return None if value is None else gedcom7.format_value(value, V7 + "DATE")


def gramps_date(calendar, day, month, year):
    date = Date()
    date.set(calendar=calendar, value=(day, month, year, False))
    return date


def test_julian_date_keeps_its_calendar():
    assert date_payload(gramps_date(Date.CAL_JULIAN, 3, 3, 1750)) == "JULIAN 3 MAR 1750"


def test_complete_date_in_another_calendar_is_converted():
    """5 Tishrei 5785 is 7 October 2024; converting says the same day."""
    assert date_payload(gramps_date(Date.CAL_HEBREW, 5, 1, 5785)) == "7 OCT 2024"
    assert date_payload(gramps_date(Date.CAL_ISLAMIC, 5, 1, 1440)) == "16 SEP 2018"


def test_date_with_no_month_is_not_converted():
    """Gramps reads a missing month as January, so converting would invent a day."""
    assert date_payload(gramps_date(Date.CAL_HEBREW, 0, 0, 5785)) == "HEBREW 5785"
    assert date_payload(gramps_date(Date.CAL_FRENCH, 0, 0, 12)) == "FRENCH_R 12"


def test_incomplete_date_in_a_calendar_gedcom_cannot_name_is_not_written():
    """Nothing true can be said of it, so nothing is said."""
    assert date_payload(gramps_date(Date.CAL_ISLAMIC, 0, 0, 1440)) is None


def test_month_lost_by_the_import_is_not_invented_on_the_way_out():
    """The import cannot read a Hebrew month, and this must not make one up."""
    source = b"""0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 NAME Test /Person/
1 BIRT
2 DATE HEBREW 5 TSH 5785
0 TRLR
"""
    records = db_to_structures(db_from_file(io.BytesIO(source)))
    (individual,) = records_by_tag(records, g7const.INDI)
    assert find(find(individual, g7const.BIRT), g7const.DATE).text == "HEBREW 5785"


def named(person, kind):
    """Give a person's primary name a type, standard or custom."""
    name = person.get_primary_name()
    name.set_type(NameType(kind))
    return person


def test_standard_name_type_is_written_as_its_own_value():
    """MAIDEN is a value the specification lists; Gramps keeps it as free text."""
    person = named(make_person(), (NameType.CUSTOM, "MAIDEN"))
    records = db_to_structures(db_from_objects(person))
    (individual,) = records_by_tag(records, g7const.INDI)
    type_structure = find(find(individual, g7const.NAME), g7const.TYPE)
    assert type_structure.text == "MAIDEN"
    assert find(type_structure, g7const.PHRASE) is None


def test_married_name_uses_the_value_the_specification_defines():
    person = named(make_person(), NameType.MARRIED)
    records = db_to_structures(db_from_objects(person))
    (individual,) = records_by_tag(records, g7const.INDI)
    assert find(find(individual, g7const.NAME), g7const.TYPE).text == "MARRIED"


def test_name_type_outside_the_vocabulary_is_written_as_other_with_a_phrase():
    person = named(make_person(), (NameType.CUSTOM, "Nom de plume"))
    records = db_to_structures(db_from_objects(person))
    (individual,) = records_by_tag(records, g7const.INDI)
    type_structure = find(find(individual, g7const.NAME), g7const.TYPE)
    assert type_structure.text == "OTHER"
    assert find(type_structure, g7const.PHRASE).text == "Nom de plume"


def test_name_type_survives_two_round_trips():
    """A name type used to decay to the literal "OTHER" on the second pass."""
    source = b"""0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 NAME Nom /Plume/
2 TYPE OTHER
3 PHRASE Nom de plume
1 NAME Maiden /Name/
2 TYPE MAIDEN
0 TRLR
"""
    first = db_to_structures(db_from_file(io.BytesIO(source)))
    second = db_to_structures(reimport(first))

    def name_types(records):
        (individual,) = records_by_tag(records, g7const.INDI)
        return [
            (find(name, g7const.TYPE).text, getattr(
                find(find(name, g7const.TYPE), g7const.PHRASE), "text", None))
            for name in find_all(individual, g7const.NAME)
        ]

    assert name_types(first) == [("OTHER", "Nom de plume"), ("MAIDEN", None)]
    assert name_types(second) == name_types(first)


@pytest.mark.parametrize("path", DATA_FILES, ids=lambda p: p.name)
def test_export_is_reproducible(path):
    """The same data gives the same file, whatever order the database yields it in."""
    db = db_from_file(str(path))
    first = gedcom7.dumps(db_to_structures(db))
    second = gedcom7.dumps(db_to_structures(reimport(db_to_structures(db))))
    volatile = re.compile(r"^(1 DATE |2 TIME |1 CHAN$|2 DATE |3 TIME )")
    keep = lambda text: [l for l in text.splitlines() if not volatile.match(l)]
    assert keep(first) == keep(second)


def test_records_are_written_in_a_settled_order():
    people = [make_person(gramps_id=f"I000{n}", handle=f"p{n}") for n in (3, 1, 2)]
    records = db_to_structures(db_from_objects(*people))
    assert [r.xref for r in records_by_tag(records, g7const.INDI)] == [
        "@I0001@",
        "@I0002@",
        "@I0003@",
    ]
