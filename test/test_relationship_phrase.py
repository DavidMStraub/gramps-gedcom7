"""Test handling of PHRASE on relationship structures."""

import os

import pytest

from gramps_gedcom7.importer import import_gedcom


@pytest.fixture(autouse=True)
def set_locale():
    """Set locale to English for consistent event type names."""
    os.environ['LANGUAGE'] = 'en'


def test_famc_phrase():
    """Test that FAMC PHRASE is imported as a note on the ChildRef."""
    db, objects = import_gedcom("test/data/relationship_phrase.ged")
    
    # Find John Doe who has FAMC PHRASE
    people = [obj for obj in objects if obj.__class__.__name__ == "Person"]
    john = [p for p in people if "John" in p.get_primary_name().get_name()][0]
    
    # John should have one parent family
    assert len(john.get_parent_family_handle_list()) == 1
    parent_family_handle = john.get_parent_family_handle_list()[0]
    parent_family = db.get_family_from_handle(parent_family_handle)
    
    # Find the ChildRef for John in the family
    john_child_ref = None
    for child_ref in parent_family.get_child_ref_list():
        if child_ref.ref == john.handle:
            john_child_ref = child_ref
            break
    
    assert john_child_ref is not None
    
    # Check that the ChildRef has a note with the PHRASE text
    assert len(john_child_ref.get_note_list()) == 1
    note_handle = john_child_ref.get_note_list()[0]
    note = db.get_note_from_handle(note_handle)
    assert note.get_text() == "Pedigree: adopted informally by the family"


def test_fams_phrase():
    """Test that FAMS PHRASE is imported as a note on the Family."""
    db, objects = import_gedcom("test/data/relationship_phrase.ged")
    
    # Find John Doe who has FAMS PHRASE
    people = [obj for obj in objects if obj.__class__.__name__ == "Person"]
    john = [p for p in people if "John" in p.get_primary_name().get_name()][0]
    
    # John should have one family (F2) as spouse
    john_family_handles = john.get_family_handle_list()
    assert len(john_family_handles) >= 1
    
    # Find the family F2 (with Jill)
    family_f2 = None
    for fh in john_family_handles:
        family = db.get_family_from_handle(fh)
        wife_handle = family.get_mother_handle()
        if wife_handle:
            wife = db.get_person_from_handle(wife_handle)
            if "Jill" in wife.get_primary_name().get_name():
                family_f2 = family
                break
    
    assert family_f2 is not None
    
    # Check that the Family has a note with the FAMS PHRASE text
    notes = [db.get_note_from_handle(nh) for nh in family_f2.get_note_list()]
    fams_notes = [n for n in notes if "Spouse" in n.get_text() and "common-law" in n.get_text()]
    assert len(fams_notes) == 1
    assert "Spouse (John Doe): common-law marriage, never legally formalized" in fams_notes[0].get_text()


def test_husb_phrase():
    """Test that HUSB PHRASE is imported as a note on the Family."""
    db, objects = import_gedcom("test/data/relationship_phrase.ged")
    
    # Find family F1 with Jack as HUSB
    families = [obj for obj in objects if obj.__class__.__name__ == "Family"]
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
    husb_notes = [n for n in notes if "Father:" in n.get_text()]
    assert len(husb_notes) == 1
    assert husb_notes[0].get_text() == "Father: biological father, not legal guardian"


def test_wife_phrase():
    """Test that WIFE PHRASE is imported as a note on the Family."""
    db, objects = import_gedcom("test/data/relationship_phrase.ged")
    
    # Find family F1 with Jane as WIFE
    families = [obj for obj in objects if obj.__class__.__name__ == "Family"]
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
    wife_notes = [n for n in notes if "Mother:" in n.get_text()]
    assert len(wife_notes) == 1
    assert wife_notes[0].get_text() == "Mother: stepmother, raised child from age 5"


def test_chil_phrase():
    """Test that CHIL PHRASE is imported as a note on the ChildRef."""
    db, objects = import_gedcom("test/data/relationship_phrase.ged")
    
    # Find family F1 with John as CHIL
    families = [obj for obj in objects if obj.__class__.__name__ == "Family"]
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
    people = [obj for obj in objects if obj.__class__.__name__ == "Person"]
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
    chil_notes = [n for n in notes if "youngest of three children" in n.get_text()]
    assert len(chil_notes) == 1
    assert chil_notes[0].get_text() == "youngest of three children"


def test_no_phrase():
    """Test that relationships without PHRASE work normally."""
    db, objects = import_gedcom("test/data/relationship_phrase.ged")
    
    # Find family F2 (John and Jill) which has no HUSB/WIFE/CHIL PHRASE
    people = [obj for obj in objects if obj.__class__.__name__ == "Person"]
    jill = [p for p in people if "Jill" in p.get_primary_name().get_name()][0]
    
    # Jill should have one family
    assert len(jill.get_family_handle_list()) == 1
    family_handle = jill.get_family_handle_list()[0]
    family = db.get_family_from_handle(family_handle)
    
    # Family should have notes only from FAMS PHRASE, not from HUSB/WIFE (which don't have PHRASE)
    notes = [db.get_note_from_handle(nh) for nh in family.get_note_list()]
    # Should only have FAMS PHRASE note
    assert len(notes) == 1
    assert "Spouse" in notes[0].get_text()
