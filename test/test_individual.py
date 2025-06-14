import pytest
from util import import_to_memory

from gramps.gen.db import DbWriteBase
from gramps.gen.lib import Citation, Person

from gedcom7 import cast as g7cast
from gedcom7 import const as g7const
from gedcom7 import types as g7types

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


def _recursively_add_value_and_parent(structure):
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
