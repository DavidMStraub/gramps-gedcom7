"""Tests for GEDCOM family record handling."""

import pytest
from gedcom7 import const as g7const
from gedcom7 import types as g7types
from gramps.gen.db import DbWriteBase
from gramps.gen.lib import ChildRef, Family, Person

from util import import_to_memory


GRAMPS_ID = "F1"


def get_family(
    children_structures: list[g7types.GedcomStructure],
) -> g7types.GedcomStructure:
    """Get a GEDCOM family record with the given children."""

    xref = f"@{GRAMPS_ID}@"
    return g7types.GedcomStructure(
        tag=g7const.FAM,
        pointer="",
        text="",
        xref=xref,
        children=children_structures,
    )


def test_family_minimal():
    """Test importing a minimal family record."""
    family = get_family([])
    db: DbWriteBase = import_to_memory([family])

    assert db.get_number_of_families() == 1
    family_obj = db.get_family_from_gramps_id("F1")
    assert isinstance(family_obj, Family)
    assert not family_obj.private
    assert not family_obj.father_handle
    assert not family_obj.mother_handle
    assert len(family_obj.get_child_ref_list()) == 0


def test_family_with_father():
    """Test importing a family with a father."""
    # Create a person to be the father
    father_xref = "@I2@"
    father = g7types.GedcomStructure(
        tag=g7const.INDI, pointer="", text="", xref=father_xref
    )

    # Create family with husband
    children = [
        g7types.GedcomStructure(tag=g7const.HUSB, pointer=father_xref, text="", xref="")
    ]
    family = get_family(children)

    # Import family and father
    db: DbWriteBase = import_to_memory([family, father])

    family_obj = db.get_family_from_gramps_id("F1")
    assert isinstance(family_obj, Family)
    assert family_obj.father_handle is not None

    # Get the father from the database and verify
    father_person = db.get_person_from_handle(family_obj.father_handle)
    assert isinstance(father_person, Person)
    assert father_person.gramps_id == "I2"


def test_family_with_mother():
    """Test importing a family with a mother."""
    # Create a person to be the mother
    mother_xref = "@I2@"
    mother = g7types.GedcomStructure(
        tag=g7const.INDI, pointer="", text="", xref=mother_xref
    )

    # Create family with wife
    children = [
        g7types.GedcomStructure(tag=g7const.WIFE, pointer=mother_xref, text="", xref="")
    ]
    family = get_family(children)

    # Import family and mother
    db: DbWriteBase = import_to_memory([family, mother])

    family_obj = db.get_family_from_gramps_id("F1")
    assert isinstance(family_obj, Family)
    assert family_obj.mother_handle is not None

    # Get the mother from the database and verify
    mother_person = db.get_person_from_handle(family_obj.mother_handle)
    assert isinstance(mother_person, Person)
    assert mother_person.gramps_id == "I2"


def test_family_with_child():
    """Test importing a family with a child."""
    # Create a person to be the child
    child_xref = "@I2@"
    child = g7types.GedcomStructure(
        tag=g7const.INDI, pointer="", text="", xref=child_xref
    )

    # Create family with child
    children = [
        g7types.GedcomStructure(tag=g7const.CHIL, pointer=child_xref, text="", xref="")
    ]
    family = get_family(children)

    # Import family and child
    db: DbWriteBase = import_to_memory([family, child])

    family_obj = db.get_family_from_gramps_id("F1")
    assert isinstance(family_obj, Family)
    assert len(family_obj.get_child_ref_list()) == 1

    # Get the child reference and verify
    child_ref = family_obj.get_child_ref_list()[0]
    assert isinstance(child_ref, ChildRef)

    # Get the child from the database and verify
    child_person = db.get_person_from_handle(child_ref.ref)
    assert isinstance(child_person, Person)
    assert child_person.gramps_id == "I2"


def test_family_with_multiple_children():
    """Test importing a family with multiple children."""
    # Create children
    child1_xref = "@I2@"
    child1 = g7types.GedcomStructure(
        tag=g7const.INDI, pointer="", text="", xref=child1_xref
    )

    child2_xref = "@I3@"
    child2 = g7types.GedcomStructure(
        tag=g7const.INDI, pointer="", text="", xref=child2_xref
    )

    # Create family with children
    family_children = [
        g7types.GedcomStructure(
            tag=g7const.CHIL, pointer=child1_xref, text="", xref=""
        ),
        g7types.GedcomStructure(
            tag=g7const.CHIL, pointer=child2_xref, text="", xref=""
        ),
    ]
    family = get_family(family_children)

    # Import family and children
    db: DbWriteBase = import_to_memory([family, child1, child2])

    family_obj = db.get_family_from_gramps_id("F1")
    assert isinstance(family_obj, Family)
    assert family_obj.father_handle is None
    assert family_obj.mother_handle is None
    assert len(family_obj.get_child_ref_list()) == 2

    # Verify child IDs
    child_ids = {
        db.get_person_from_handle(child_ref.ref).gramps_id
        for child_ref in family_obj.get_child_ref_list()
    }
    assert child_ids == {"I2", "I3"}


def test_family_complete():
    """Test importing a complete family with father, mother, and children."""
    # Create family members
    father_xref = "@I2@"
    father = g7types.GedcomStructure(
        tag=g7const.INDI, pointer="", text="", xref=father_xref
    )

    mother_xref = "@I3@"
    mother = g7types.GedcomStructure(
        tag=g7const.INDI, pointer="", text="", xref=mother_xref
    )

    child1_xref = "@I4@"
    child1 = g7types.GedcomStructure(
        tag=g7const.INDI, pointer="", text="", xref=child1_xref
    )

    child2_xref = "@I5@"
    child2 = g7types.GedcomStructure(
        tag=g7const.INDI, pointer="", text="", xref=child2_xref
    )

    # Create family structure
    family_children = [
        g7types.GedcomStructure(
            tag=g7const.HUSB, pointer=father_xref, text="", xref=""
        ),
        g7types.GedcomStructure(
            tag=g7const.WIFE, pointer=mother_xref, text="", xref=""
        ),
        g7types.GedcomStructure(
            tag=g7const.CHIL, pointer=child1_xref, text="", xref=""
        ),
        g7types.GedcomStructure(
            tag=g7const.CHIL, pointer=child2_xref, text="", xref=""
        ),
    ]
    family = get_family(family_children)

    # Import family and all members
    db: DbWriteBase = import_to_memory([family, father, mother, child1, child2])

    family_obj = db.get_family_from_gramps_id("F1")
    assert isinstance(family_obj, Family)

    # Verify father
    assert family_obj.father_handle is not None
    father_person = db.get_person_from_handle(family_obj.father_handle)
    assert father_person.gramps_id == "I2"

    # Verify mother
    assert family_obj.mother_handle is not None
    mother_person = db.get_person_from_handle(family_obj.mother_handle)
    assert mother_person.gramps_id == "I3"

    # Verify children
    assert len(family_obj.get_child_ref_list()) == 2
    child_ids = {
        db.get_person_from_handle(child_ref.ref).gramps_id
        for child_ref in family_obj.get_child_ref_list()
    }
    assert child_ids == {"I4", "I5"}


def test_invalid_person_reference():
    """Test that referencing a non-existent person raises an error."""
    children = [
        g7types.GedcomStructure(
            tag=g7const.HUSB, pointer="@NONEXISTENT@", text="", xref=""
        )
    ]
    family = get_family(children)

    with pytest.raises(ValueError, match="Person @NONEXISTENT@ not found"):
        import_to_memory([family])
