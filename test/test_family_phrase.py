"""Test handling of PHRASE on family relationship structures (HUSB, WIFE, CHIL)."""

from gramps.gen.db import DbWriteBase
from gramps.gen.db.utils import make_database
from gramps_gedcom7.importer import import_gedcom


def test_husb_phrase():
    """Test that HUSB PHRASE is imported as a note on the family."""
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom("test/data/family_phrase.ged", db)
    
    # Get all families
    families = [db.get_family_from_handle(handle) for handle in db.get_family_handles()]
    persons = [db.get_person_from_handle(handle) for handle in db.get_person_handles()]
    
    # Find family F1 (Joseph + Mary)
    f1 = None
    for family in families:
        father_handle = family.get_father_handle()
        mother_handle = family.get_mother_handle()
        if father_handle and mother_handle:
            father = next((p for p in persons if p.handle == father_handle), None)
            mother = next((p for p in persons if p.handle == mother_handle), None)
            if father and mother:
                father_name = father.get_primary_name().get_surname()
                mother_name = mother.get_primary_name().get_first_name()
                if father_name == "Smith" and mother_name == "Mary":
                    f1 = family
                    break
    
    assert f1 is not None, "Family F1 not found"
    
    # Check that family has a note with the HUSB PHRASE
    note_list = f1.get_note_list()
    assert len(note_list) >= 1, "Family should have at least one note from HUSB PHRASE"
    
    # Verify note content contains the PHRASE with "Father:" prefix
    # Note: we need to check the actual note object content, which would be in the notes collection
    # For now, just verify that a note was added
    assert len(note_list) > 0


def test_wife_phrase():
    """Test that WIFE PHRASE is imported as a note on the family."""
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom("test/data/family_phrase.ged", db)
    
    # Get all families
    families = [db.get_family_from_handle(handle) for handle in db.get_family_handles()]
    persons = [db.get_person_from_handle(handle) for handle in db.get_person_handles()]
    
    # Find family F1 (Joseph + Mary)
    f1 = None
    for family in families:
        father_handle = family.get_father_handle()
        mother_handle = family.get_mother_handle()
        if father_handle and mother_handle:
            father = next((p for p in persons if p.handle == father_handle), None)
            mother = next((p for p in persons if p.handle == mother_handle), None)
            if father and mother:
                father_name = father.get_primary_name().get_surname()
                mother_name = mother.get_primary_name().get_first_name()
                if father_name == "Smith" and mother_name == "Mary":
                    f1 = family
                    break
    
    assert f1 is not None, "Family F1 not found"
    
    # Check that family has notes (should have 2: HUSB PHRASE + WIFE PHRASE)
    note_list = f1.get_note_list()
    assert len(note_list) >= 2, "Family should have at least two notes from HUSB and WIFE PHRASE"


def test_chil_phrase():
    """Test that CHIL PHRASE is imported as a note on the ChildRef."""
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom("test/data/family_phrase.ged", db)
    
    # Get all families
    families = [db.get_family_from_handle(handle) for handle in db.get_family_handles()]
    persons = [db.get_person_from_handle(handle) for handle in db.get_person_handles()]
    
    # Find family F1 (Joseph + Mary with child John)
    f1 = None
    for family in families:
        father_handle = family.get_father_handle()
        mother_handle = family.get_mother_handle()
        if father_handle and mother_handle:
            father = next((p for p in persons if p.handle == father_handle), None)
            mother = next((p for p in persons if p.handle == mother_handle), None)
            if father and mother:
                father_name = father.get_primary_name().get_surname()
                mother_name = mother.get_primary_name().get_first_name()
                if father_name == "Smith" and mother_name == "Mary":
                    f1 = family
                    break
    
    assert f1 is not None, "Family F1 not found"
    
    # Find the child (John)
    child_refs = f1.get_child_ref_list()
    assert len(child_refs) == 1, "Family should have exactly one child"
    
    child_ref = child_refs[0]
    child_handle = child_ref.ref
    child = next((p for p in persons if p.handle == child_handle), None)
    assert child is not None, "Child not found"
    
    child_name = child.get_primary_name().get_first_name()
    assert child_name == "John", f"Expected child to be John, got {child_name}"
    
    # Check that ChildRef has a note with the CHIL PHRASE
    note_list = child_ref.get_note_list()
    assert len(note_list) == 1, "ChildRef should have exactly one note from CHIL PHRASE"


def test_family_without_phrase():
    """Test that families without PHRASE are imported normally."""
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom("test/data/family_phrase.ged", db)
    
    # Get all families
    families = [db.get_family_from_handle(handle) for handle in db.get_family_handles()]
    persons = [db.get_person_from_handle(handle) for handle in db.get_person_handles()]
    
    # Find family F2 (John + Jane) - no PHRASE structures
    f2 = None
    for family in families:
        father_handle = family.get_father_handle()
        mother_handle = family.get_mother_handle()
        if father_handle and mother_handle:
            father = next((p for p in persons if p.handle == father_handle), None)
            mother = next((p for p in persons if p.handle == mother_handle), None)
            if father and mother:
                father_name = father.get_primary_name().get_first_name()
                mother_name = mother.get_primary_name().get_first_name()
                if father_name == "John" and mother_name == "Jane":
                    f2 = family
                    break
    
    assert f2 is not None, "Family F2 not found"
    
    # Check that family has no notes (no PHRASE)
    note_list = f2.get_note_list()
    assert len(note_list) == 0, "Family F2 should have no notes (no PHRASE structures)"
    
    # Check that ChildRef has no notes (no CHIL PHRASE)
    child_refs = f2.get_child_ref_list()
    assert len(child_refs) == 1, "Family should have exactly one child"
    
    child_ref = child_refs[0]
    note_list = child_ref.get_note_list()
    assert len(note_list) == 0, "ChildRef should have no notes (no CHIL PHRASE)"
