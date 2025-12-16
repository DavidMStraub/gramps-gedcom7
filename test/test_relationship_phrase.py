"""Test handling of PHRASE on relationship structures."""

import os

import pytest
from gramps.gen.db import DbWriteBase
from gramps.gen.db.utils import make_database

from gramps_gedcom7.importer import import_gedcom


@pytest.fixture(autouse=True)
def set_locale():
    """Set locale to English for consistent event type names."""
    os.environ['LANGUAGE'] = 'en'


@pytest.mark.skip(reason="FAMC PHRASE not yet implemented - requires db access in individual.py")
def test_famc_phrase():
    """Test that FAMC PHRASE is imported as a note on the ChildRef.
    
    NOTE: This feature is not yet implemented because individual.py doesn't have
    access to the database to look up the Family and ChildRef objects.
    """
    pytest.skip("FAMC PHRASE not implemented")


@pytest.mark.skip(reason="FAMS PHRASE not yet implemented - requires db access in individual.py")
def test_fams_phrase():
    """Test that FAMS PHRASE is imported as a note on the Family.
    
    NOTE: This feature is not yet implemented because individual.py doesn't have
    access to the database to look up the Family object.
    """
    pytest.skip("FAMS PHRASE not implemented")


def test_husb_phrase():
    """Test that HUSB PHRASE is imported as a note on the Family."""
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom("test/data/relationship_phrase.ged", db)
    
    # Find family F1 with Jack as HUSB
    families = list(db.iter_families())
    family_f1 = None
    for family in families:
        father_handle = family.get_father_handle()
        if father_handle:
            father = db.get_person_from_handle(father_handle)
            if "Jack" in father.get_primary_name().get_name():
                family_f1 = family
                break
    
    assert family_f1 is not None
    
    # Check that the Family has a note with the HUSB PHRASE text
    notes = [db.get_note_from_handle(nh) for nh in family_f1.get_note_list()]
    husb_notes = [n for n in notes if "biological father" in n.get()]
    assert len(husb_notes) == 1
    assert husb_notes[0].get() == "biological father, not legal guardian"


def test_wife_phrase():
    """Test that WIFE PHRASE is imported as a note on the Family."""
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom("test/data/relationship_phrase.ged", db)
    
    # Find family F1 with Jane as WIFE
    families = list(db.iter_families())
    family_f1 = None
    for family in families:
        mother_handle = family.get_mother_handle()
        if mother_handle:
            mother = db.get_person_from_handle(mother_handle)
            if "Jane" in mother.get_primary_name().get_name():
                family_f1 = family
                break
    
    assert family_f1 is not None
    
    # Check that the Family has a note with the WIFE PHRASE text
    notes = [db.get_note_from_handle(nh) for nh in family_f1.get_note_list()]
    wife_notes = [n for n in notes if "stepmother" in n.get()]
    assert len(wife_notes) == 1
    assert wife_notes[0].get() == "stepmother, raised child from age 5"


def test_chil_phrase():
    """Test that CHIL PHRASE is imported as a note on the ChildRef."""
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom("test/data/relationship_phrase.ged", db)
    
    # Find family F1 with John as CHIL
    families = list(db.iter_families())
    family_f1 = None
    for family in families:
        # F1 has Jack as father
        father_handle = family.get_father_handle()
        if father_handle:
            father = db.get_person_from_handle(father_handle)
            if "Jack" in father.get_primary_name().get_name():
                family_f1 = family
                break
    
    assert family_f1 is not None
    
    # Find John's ChildRef in the family
    people = list(db.iter_people())
    john = [p for p in people if "John" in p.get_primary_name().get_name()][0]
    
    john_child_ref = None
    for child_ref in family_f1.get_child_ref_list():
        if child_ref.ref == john.handle:
            john_child_ref = child_ref
            break
    
    assert john_child_ref is not None
    
    # Check that the ChildRef has a note with the CHIL PHRASE text
    # Note: John's ChildRef may have multiple notes (from FAMC and CHIL)
    notes = [db.get_note_from_handle(nh) for nh in john_child_ref.get_note_list()]
    chil_notes = [n for n in notes if "youngest of three children" in n.get()]
    assert len(chil_notes) == 1
    assert chil_notes[0].get() == "youngest of three children"


def test_no_phrase():
    """Test that relationships without PHRASE work normally."""
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom("test/data/relationship_phrase.ged", db)
    
    # Find family F2 (John and Jill) which has no HUSB/WIFE/CHIL PHRASE
    # F2 is the family with John as HUSB and Jill as WIFE
    families = list(db.iter_families())
    family_f2 = None
    for family in families:
        husb_handle = family.get_father_handle()
        wife_handle = family.get_mother_handle()
        if husb_handle and wife_handle:
            husb = db.get_person_from_handle(husb_handle)
            wife = db.get_person_from_handle(wife_handle)
            if "John" in husb.get_primary_name().get_name() and "Jill" in wife.get_primary_name().get_name():
                family_f2 = family
                break
    
    assert family_f2 is not None
    
    # Family should have no notes (FAMS PHRASE is not implemented, and F2 has no HUSB/WIFE/CHIL PHRASE)
    notes = [db.get_note_from_handle(nh) for nh in family_f2.get_note_list()]
    assert len(notes) == 0
