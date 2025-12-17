"""Test ALIA and ASSO structures."""

import pytest

from gramps.gen.db import DbWriteBase
from gramps.gen.db.utils import make_database
from gramps_gedcom7.importer import import_gedcom

GEDCOM_FILE = "test/data/alia_asso.ged"


@pytest.fixture
def db():
    """Import test GEDCOM and return database."""
    database: DbWriteBase = make_database("sqlite")
    database.load(":memory:", callback=None)
    import_gedcom(GEDCOM_FILE, database)
    return database


def test_alia_valid_pointer(db):
    """Test that ALIA with valid pointer creates PersonRef."""
    person = db.get_person_from_gramps_id("I1")
    assert person is not None
    
    person_refs = person.get_person_ref_list()
    # Should have 2 ALIA references (I5 and I6) - void is skipped
    alia_refs = [ref for ref in person_refs if ref.get_relation() == "ALIA"]
    assert len(alia_refs) == 2


def test_alia_void_skipped(db):
    """Test that ALIA with @VOID@ pointer is correctly skipped."""
    person = db.get_person_from_gramps_id("I1")
    assert person is not None
    
    person_refs = person.get_person_ref_list()
    # Only the valid ALIA @I5@ and @I6@ should create PersonRefs
    alia_refs = [ref for ref in person_refs if ref.get_relation() == "ALIA"]
    # Should be exactly 2, not 3 (void should be skipped)
    assert len(alia_refs) == 2


def test_alia_phrase(db):
    """Test that ALIA PHRASE creates note on PersonRef."""
    person = db.get_person_from_gramps_id("I1")
    assert person is not None
    
    person_refs = person.get_person_ref_list()
    alia_refs = [ref for ref in person_refs if ref.get_relation() == "ALIA"]
    
    # Find the ALIA with PHRASE "Also known as"
    alia_with_phrase = None
    for ref in alia_refs:
        notes = ref.get_note_list()
        if notes:
            note = db.get_note_from_handle(notes[0])
            if note.get() == "Also known as":
                alia_with_phrase = ref
                break
    
    assert alia_with_phrase is not None


def test_asso_with_role(db):
    """Test that ASSO with ROLE creates PersonRef with correct relation."""
    person = db.get_person_from_gramps_id("I1")
    assert person is not None
    
    person_refs = person.get_person_ref_list()
    # Filter out ALIA refs to get only ASSO refs
    asso_refs = [ref for ref in person_refs if ref.get_relation() != "ALIA"]
    roles = [ref.get_relation() for ref in asso_refs]
    
    # Should have associations with these roles (3 valid, 1 void skipped)
    assert "FRIEND" in roles
    assert "GODP" in roles
    assert "SPOU" in roles
    # WITN with @VOID@ should NOT be in the list
    assert "WITN" not in roles
    assert len(asso_refs) == 3


def test_asso_void_skipped(db):
    """Test that ASSO with @VOID@ pointer is correctly skipped."""
    person = db.get_person_from_gramps_id("I1")
    assert person is not None
    
    person_refs = person.get_person_ref_list()
    asso_refs = [ref for ref in person_refs if ref.get_relation() != "ALIA"]
    
    # Should have exactly 3 valid associations
    # The WITN with @VOID@ should be skipped
    assert len(asso_refs) == 3
    
    # Verify WITN role is not present
    roles = [ref.get_relation() for ref in asso_refs]
    assert "WITN" not in roles


def test_asso_phrase(db):
    """Test that ASSO PHRASE creates note on PersonRef."""
    person = db.get_person_from_gramps_id("I1")
    assert person is not None
    
    person_refs = person.get_person_ref_list()
    
    # Find the GODP association which has a PHRASE
    godp_refs = [ref for ref in person_refs if ref.get_relation() == "GODP"]
    assert len(godp_refs) == 1
    
    godp_ref = godp_refs[0]
    notes = godp_ref.get_note_list()
    assert len(notes) == 1
    
    note = db.get_note_from_handle(notes[0])
    assert note.get() == "Godfather at baptism"


def test_asso_with_note(db):
    """Test that ASSO with inline NOTE creates note on PersonRef."""
    person = db.get_person_from_gramps_id("I1")
    assert person is not None
    
    person_refs = person.get_person_ref_list()
    
    # Find the SPOU association which has a NOTE
    spou_refs = [ref for ref in person_refs if ref.get_relation() == "SPOU"]
    assert len(spou_refs) == 1
    
    spou_ref = spou_refs[0]
    notes = spou_ref.get_note_list()
    assert len(notes) == 1
    
    note = db.get_note_from_handle(notes[0])
    assert note.get() == "Witnessed marriage"


def test_asso_references_actual_person(db):
    """Test that ASSO creates reference to actual person."""
    person = db.get_person_from_gramps_id("I1")
    assert person is not None
    
    person_refs = person.get_person_ref_list()
    # Get FRIEND association
    friend_refs = [ref for ref in person_refs if ref.get_relation() == "FRIEND"]
    assert len(friend_refs) == 1
    
    # Get the referenced person
    friend_handle = friend_refs[0].get_reference_handle()
    friend_person = db.get_person_from_handle(friend_handle)
    assert friend_person is not None
    assert friend_person.get_gramps_id() == "I2"


def test_alia_references_actual_person(db):
    """Test that ALIA creates reference to actual person."""
    person = db.get_person_from_gramps_id("I1")
    assert person is not None
    
    person_refs = person.get_person_ref_list()
    alia_refs = [ref for ref in person_refs if ref.get_relation() == "ALIA"]
    assert len(alia_refs) == 2
    
    # Get the referenced persons
    alia_handles = [ref.get_reference_handle() for ref in alia_refs]
    alia_ids = []
    for handle in alia_handles:
        alia_person = db.get_person_from_handle(handle)
        assert alia_person is not None
        alia_ids.append(alia_person.get_gramps_id())
    
    # Should reference I5 and I6
    assert "I5" in alia_ids
    assert "I6" in alia_ids
