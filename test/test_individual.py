import pytest
from gedcom7 import cast as g7cast
from gedcom7 import const as g7const
from gedcom7 import types as g7types
from gramps.gen.db import DbWriteBase
from gramps.gen.lib import (
    Citation,
    Event,
    EventType,
    Media,
    NameType,
    Note,
    Person,
    Source,
)
from util import import_to_memory

GRAMPS_ID = "I1"


def get_individual(
    children_structures: list[g7types.GedcomStructure],
) -> g7types.GedcomStructure:

    xref = f"@{GRAMPS_ID}@"
    individual = g7types.GedcomStructure(
        tag=g7const.INDI, pointer="", text="", xref=xref
    )
    if not children_structures:
        return individual
    individual.children = children_structures
    _recursively_add_value_and_parent(individual)
    return individual


def _recursively_add_value_and_parent(structure: g7types.GedcomStructure) -> None:
    """Recursively add value and parent to all children of the structure."""
    structure.value = g7cast.cast_value(text=structure.text, type_id=structure.type_id)
    for child in structure.children:
        child.parent = structure
        child.value = g7cast.cast_value(text=child.text, type_id=child.type_id)
        _recursively_add_value_and_parent(child)


def test_individual_minimal():
    individual = get_individual([])
    db: DbWriteBase = import_to_memory([individual])
    assert db.get_number_of_people() == 1
    person = db.get_person_from_gramps_id(GRAMPS_ID)
    assert isinstance(person, Person)
    assert not person.private


def test_individual_resn():
    for text in ["CONFIDENTIAL", "PRIVACY", "CONFIDENTIAL, LOCKED"]:
        children = [
            g7types.GedcomStructure(tag=g7const.RESN, pointer="", text=text, xref="")
        ]
        individual = get_individual(children)
        db: DbWriteBase = import_to_memory([individual])
        person = db.get_person_from_gramps_id(GRAMPS_ID)
        assert isinstance(person, Person)
        assert person.private


@pytest.mark.parametrize(
    ["text", "gramps_gender"],
    [
        ("M", Person.MALE),
        ("F", Person.FEMALE),
        ("X", Person.OTHER),
        ("U", Person.UNKNOWN),
    ],
)
def test_sex(text, gramps_gender):
    children = [
        g7types.GedcomStructure(tag=g7const.SEX, pointer="", text=text, xref="")
    ]
    individual = get_individual(children)
    db: DbWriteBase = import_to_memory([individual])
    person = db.get_person_from_gramps_id(GRAMPS_ID)
    assert isinstance(person, Person)
    assert person.gender == gramps_gender


def test_citation_without_source():
    children = [
        g7types.GedcomStructure(tag=g7const.SOUR, pointer="@VOID@", text="", xref="")
    ]
    individual = get_individual(children)
    db: DbWriteBase = import_to_memory([individual])
    assert db.get_number_of_citations() == 1
    assert db.get_number_of_sources() == 0
    person = db.get_person_from_gramps_id(GRAMPS_ID)
    assert isinstance(person, Person)
    assert len(person.citation_list) == 1
    citation_handle = person.citation_list[0]
    citation = db.get_citation_from_handle(citation_handle)
    assert citation.gramps_id


def test_citation_with_source():
    # Create a source reference with valid xref
    children = [
        g7types.GedcomStructure(tag=g7const.SOUR, pointer="@S1@", text="", xref="")
    ]
    individual = get_individual(children)
    # Create a source structure with matching xref
    source = g7types.GedcomStructure(tag=g7const.SOUR, pointer="", text="", xref="@S1@")
    db: DbWriteBase = import_to_memory([individual, source])
    assert db.get_number_of_citations() == 1
    assert db.get_number_of_sources() == 1
    person = db.get_person_from_gramps_id(GRAMPS_ID)
    assert isinstance(person, Person)
    assert len(person.citation_list) == 1
    citation_handle = person.citation_list[0]
    citation = db.get_citation_from_handle(citation_handle)
    assert isinstance(citation, Citation)
    assert citation.gramps_id
    gramps_source: Source = db.get_source_from_gramps_id("S1")
    assert citation.source_handle == gramps_source.handle


def test_invalid_sex():
    """Test that an invalid sex value raises a ValueError."""
    children = [g7types.GedcomStructure(tag=g7const.SEX, pointer="", text="Z", xref="")]
    individual = get_individual(children)
    with pytest.raises(ValueError, match="SEX value 'Z' is not valid"):
        import_to_memory([individual])


def create_name_structure(name_value):
    """Helper function to create a NAME structure with the given value and children."""
    # Create the NAME structure
    name_structure = g7types.GedcomStructure(
        tag=g7const.NAME, pointer="", text=name_value, xref=""
    )
    name_structure.children = []
    return name_structure


def test_name_simple():
    """Test handling a simple name with just a fullname."""
    name = create_name_structure("John Smith")
    individual = get_individual([name])
    db: DbWriteBase = import_to_memory([individual])
    person = db.get_person_from_gramps_id(GRAMPS_ID)
    assert isinstance(person, Person)
    assert person.get_primary_name().first_name == "John Smith"
    assert len(person.get_primary_name().get_surname_list()) == 0


def test_name_with_parts():
    """Test handling a name with explicit GIVN, SURN, and other part tags."""
    name_structure = create_name_structure("John /Smith/")

    givn = g7types.GedcomStructure(
        tag=g7const.GIVN, pointer="", text="Jonathan", xref=""
    )
    givn.value = "Jonathan"
    givn.parent = name_structure

    surn = g7types.GedcomStructure(
        tag=g7const.SURN, pointer="", text="Smithson", xref=""
    )
    surn.parent = name_structure

    npfx = g7types.GedcomStructure(tag=g7const.NPFX, pointer="", text="Dr.", xref="")
    npfx.value = "Dr."
    npfx.parent = name_structure

    nsfx = g7types.GedcomStructure(tag=g7const.NSFX, pointer="", text="Jr.", xref="")
    nsfx.value = "Jr."
    nsfx.parent = name_structure

    nick = g7types.GedcomStructure(tag=g7const.NICK, pointer="", text="Jon", xref="")
    nick.value = "Jon"
    nick.parent = name_structure

    spfx = g7types.GedcomStructure(tag=g7const.SPFX, pointer="", text="van", xref="")
    spfx.value = "van"
    spfx.parent = name_structure

    name_structure.children = [givn, surn, npfx, nsfx, nick, spfx]

    individual = get_individual([name_structure])
    db: DbWriteBase = import_to_memory([individual])
    person: Person = db.get_person_from_gramps_id(GRAMPS_ID)
    primary_name = person.get_primary_name()

    assert primary_name.first_name == "Jonathan"
    assert primary_name.suffix == "Jr."
    assert primary_name.title == "Dr."
    assert primary_name.nick == "Jon"
    assert len(primary_name.get_surname_list()) == 1
    surname = primary_name.get_surname_list()[0]
    assert surname.get_surname() == "Smithson"
    assert surname.get_prefix() == "van"


def test_name_type():
    """Test handling of name types."""
    for name_type, expected_type in [
        ("BIRTH", NameType.BIRTH),
        ("AKA", NameType.AKA),
        ("MARR", NameType.MARRIED),
        ("OTHER", NameType.CUSTOM),
    ]:
        name_structure = create_name_structure("Test Name")

        # Add TYPE tag
        type_struct = g7types.GedcomStructure(
            tag=g7const.TYPE, pointer="", text=name_type, xref=""
        )
        type_struct.value = name_type
        type_struct.parent = name_structure
        name_structure.children = [type_struct]

        individual = get_individual([name_structure])
        db: DbWriteBase = import_to_memory([individual])
        person = db.get_person_from_gramps_id(GRAMPS_ID)
        assert person.get_primary_name().get_type() == expected_type


def test_note_on_person():
    """Test handling of direct notes on a person."""
    note_struct = g7types.GedcomStructure(
        tag=g7const.NOTE, pointer="", text="Test note text", xref=""
    )
    note_struct.value = "Test note text"

    individual = get_individual([note_struct])
    db: DbWriteBase = import_to_memory([individual])
    person = db.get_person_from_gramps_id(GRAMPS_ID)

    assert len(person.get_note_list()) == 1
    note_handle = person.get_note_list()[0]
    note = db.get_note_from_handle(note_handle)
    assert isinstance(note, Note)
    assert note.get() == "Test note text"


def test_shared_note_on_person():
    """Test handling of shared notes on a person."""
    shared_note_xref = "@N1@"
    shared_note = g7types.GedcomStructure(
        tag=g7const.SNOTE, pointer="", text="Shared note text", xref=shared_note_xref
    )
    _recursively_add_value_and_parent(shared_note)
    note_ref = g7types.GedcomStructure(
        tag=g7const.SNOTE, pointer=shared_note_xref, text="", xref=""
    )
    individual = get_individual([note_ref])

    db: DbWriteBase = import_to_memory([individual, shared_note])
    assert db.get_number_of_people() == 1
    assert db.get_number_of_notes() == 1
    person: Person = db.get_person_from_gramps_id(GRAMPS_ID)
    assert len(person.get_note_list()) == 1
    note_handle = person.get_note_list()[0]
    note = db.get_note_from_handle(note_handle)
    assert isinstance(note, Note)
    assert note.get() == "Shared note text"


def test_note_on_name():
    """Test handling of notes attached to a name."""
    name_structure = create_name_structure("Test Name")

    note_struct = g7types.GedcomStructure(
        tag=g7const.NOTE, pointer="", text="Name note", xref=""
    )
    note_struct.value = "Name note"
    note_struct.parent = name_structure
    name_structure.children = [note_struct]

    individual = get_individual([name_structure])
    db: DbWriteBase = import_to_memory([individual])
    person = db.get_person_from_gramps_id(GRAMPS_ID)

    # The note should be on the name, not directly on the person
    assert len(person.get_note_list()) == 0
    primary_name = person.get_primary_name()
    assert len(primary_name.get_note_list()) == 1

    note_handle = primary_name.get_note_list()[0]
    note = db.get_note_from_handle(note_handle)
    assert isinstance(note, Note)
    assert note.get() == "Name note"


def test_media_reference():
    """Test handling of media references."""
    media_xref = "@M1@"
    media_obj = g7types.GedcomStructure(
        tag=g7const.OBJE,
        pointer="",
        text="",
        xref=media_xref,
        children=[
            g7types.GedcomStructure(
                tag=g7const.FILE,
                pointer="",
                text="path/to/media.jpg",
                xref="",
                children=[
                    g7types.GedcomStructure(
                        tag=g7const.FORM, pointer="", text="image/jpeg", xref=""
                    ),
                    g7types.GedcomStructure(
                        tag=g7const.TITL, pointer="", text="Media Title", xref=""
                    ),
                ],
            ),
        ],
    )
    _recursively_add_value_and_parent(media_obj)

    media_ref = g7types.GedcomStructure(
        tag=g7const.OBJE, pointer=media_xref, text="", xref=""
    )

    individual = get_individual([media_ref])

    db: DbWriteBase = import_to_memory([individual, media_obj])
    person: Person = db.get_person_from_gramps_id(GRAMPS_ID)

    assert len(person.get_media_list()) == 1
    media_ref = person.get_media_list()[0]
    media_handle = media_ref.get_reference_handle()
    media = db.get_media_from_handle(media_handle)
    assert isinstance(media, Media)
    assert media.get_path() == "path/to/media.jpg"
    assert media.get_mime_type() == "image/jpeg"
    assert media.desc == "Media Title"


def test_event_references():
    """Test handling of event references."""
    for tag, event_type in [
        (g7const.BIRT, EventType.BIRTH),
        (g7const.DEAT, EventType.DEATH),
        (g7const.EVEN, EventType.CUSTOM),
    ]:
        event_struct = g7types.GedcomStructure(tag=tag, pointer="", text="", xref="")

        individual = get_individual([event_struct])
        db: DbWriteBase = import_to_memory([individual])
        person = db.get_person_from_gramps_id(GRAMPS_ID)

        assert len(person.get_event_ref_list()) == 1
        event_ref = person.get_event_ref_list()[0]
        event_handle = event_ref.get_reference_handle()
        event = db.get_event_from_handle(event_handle)
        assert isinstance(event, Event)
        assert event.get_type() == event_type


def test_parent_family_references():
    """Test handling of FAMC (parent family) references."""
    family_xref = "@F1@"
    family = g7types.GedcomStructure(
        tag=g7const.FAM, pointer="", text="", xref=family_xref
    )

    famc_ref = g7types.GedcomStructure(
        tag=g7const.FAMC, pointer=family_xref, text="", xref=""
    )

    individual = get_individual([famc_ref])

    db: DbWriteBase = import_to_memory([individual, family])
    person: Person = db.get_person_from_gramps_id(GRAMPS_ID)

    assert len(person.get_parent_family_handle_list()) == 1
    family_handle = person.get_parent_family_handle_list()[0]
    assert family_handle in db.get_family_handles()


def test_spouse_family_references():
    """Test handling of FAMS (spouse family) references."""
    family_xref = "@F1@"
    family = g7types.GedcomStructure(
        tag=g7const.FAM, pointer="", text="", xref=family_xref
    )

    fams_ref = g7types.GedcomStructure(
        tag=g7const.FAMS, pointer=family_xref, text="", xref=""
    )

    individual = get_individual([fams_ref])

    db: DbWriteBase = import_to_memory([individual, family])
    person: Person = db.get_person_from_gramps_id(GRAMPS_ID)

    assert len(person.get_family_handle_list()) == 1
    family_handle = person.get_family_handle_list()[0]
    assert family_handle in db.get_family_handles()


def test_invalid_family_reference():
    """Test that referencing a non-existent family raises an error."""
    famc_ref = g7types.GedcomStructure(
        tag=g7const.FAMC, pointer="@NONEXISTENT@", text="", xref=""
    )
    individual = get_individual([famc_ref])

    with pytest.raises(ValueError, match="Family @NONEXISTENT@ not found"):
        import_to_memory([individual])
