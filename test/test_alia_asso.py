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
    
    # Verify the references point to actual persons
    alia_handles = [ref.get_reference_handle() for ref in alia_refs]
    for handle in alia_handles:
        alia_person = db.get_person_from_handle(handle)
        assert alia_person is not None


def test_alia_void_skipped(db):
    """Test that ALIA with @VOID@ pointer is correctly skipped."""
    person = db.get_person_from_gramps_id("I1")
    assert person is not None
    
    person_refs = person.get_person_ref_list()
    alia_refs = [ref for ref in person_refs if ref.get_relation() == "ALIA"]
    
    # Verify that none of the PersonRef objects have empty handles
    # (which would indicate a void pointer was processed)
    for ref in alia_refs:
        handle = ref.get_reference_handle()
        assert handle  # Should not be empty/None
        # Should be able to retrieve the person
        person = db.get_person_from_handle(handle)
        assert person is not None


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
    
    # Should have associations with these roles (6 valid, 1 void skipped)
    assert "FRIEND" in roles
    assert "GODP" in roles
    assert "SPOU" in roles
    assert "CLERGY" in roles
    assert "WITN" in roles
    assert "Teacher" in roles  # ROLE OTHER with PHRASE "Teacher"
    # WITN with @VOID@ should NOT be in the list (only the valid one with @I8@)
    assert len(asso_refs) == 6


def test_asso_void_skipped(db):
    """Test that ASSO with @VOID@ pointer is correctly skipped."""
    person = db.get_person_from_gramps_id("I1")
    assert person is not None
    
    person_refs = person.get_person_ref_list()
    asso_refs = [ref for ref in person_refs if ref.get_relation() != "ALIA"]
    
    # Should have exactly 6 valid associations
    # The WITN with @VOID@ should be skipped (but WITN with @I8@ should be present)
    assert len(asso_refs) == 6
    
    # Count WITN roles - should be exactly 1 (the valid one)
    witn_roles = [ref for ref in asso_refs if ref.get_relation() == "WITN"]
    assert len(witn_roles) == 1


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


def test_asso_note_has_association_type(db):
    """Test that notes on PersonRef (ASSO) have NoteType.ASSOCIATION."""
    from gramps.gen.lib import NoteType
    
    person = db.get_person_from_gramps_id("I1")
    assert person is not None
    
    person_refs = person.get_person_ref_list()
    # Get ASSO with PHRASE (GODP)
    godp_refs = [ref for ref in person_refs if ref.get_relation() == "GODP"]
    assert len(godp_refs) == 1
    
    godp_ref = godp_refs[0]
    notes = godp_ref.get_note_list()
    assert len(notes) == 1
    
    note = db.get_note_from_handle(notes[0])
    # Note should have type ASSOCIATION, not GENERAL
    assert note.get_type() == NoteType.ASSOCIATION


def test_alia_note_has_association_type(db):
    """Test that notes on PersonRef (ALIA) have NoteType.ASSOCIATION."""
    from gramps.gen.lib import NoteType
    
    person = db.get_person_from_gramps_id("I1")
    assert person is not None
    
    person_refs = person.get_person_ref_list()
    alia_refs = [ref for ref in person_refs if ref.get_relation() == "ALIA"]
    
    # Find the ALIA with PHRASE
    alia_with_phrase = None
    for ref in alia_refs:
        notes = ref.get_note_list()
        if notes:
            note = db.get_note_from_handle(notes[0])
            if note.get() == "Also known as":
                alia_with_phrase = note
                break
    
    assert alia_with_phrase is not None
    # Note should have type ASSOCIATION, not GENERAL
    assert alia_with_phrase.get_type() == NoteType.ASSOCIATION


def test_asso_with_shared_note(db):
    """Test that ASSO with shared note (SNOTE) references it correctly."""
    person = db.get_person_from_gramps_id("I1")
    assert person is not None
    
    person_refs = person.get_person_ref_list()
    
    # Find the CLERGY association which has a shared note
    clergy_refs = [ref for ref in person_refs if ref.get_relation() == "CLERGY"]
    assert len(clergy_refs) == 1
    
    clergy_ref = clergy_refs[0]
    notes = clergy_ref.get_note_list()
    assert len(notes) == 1
    
    # Verify the shared note content
    note = db.get_note_from_handle(notes[0])
    assert note.get() == "Officiated at the wedding ceremony"


def test_asso_with_citation(db):
    """Test that ASSO with citation (SOUR) references it correctly."""
    person = db.get_person_from_gramps_id("I1")
    assert person is not None
    
    person_refs = person.get_person_ref_list()
    
    # Find the WITN association which has a citation
    witn_refs = [ref for ref in person_refs if ref.get_relation() == "WITN"]
    assert len(witn_refs) == 1
    
    witn_ref = witn_refs[0]
    citations = witn_ref.get_citation_list()
    assert len(citations) == 1
    
    # Verify the citation exists and references a source
    citation = db.get_citation_from_handle(citations[0])
    assert citation is not None
    
    source_handle = citation.get_reference_handle()
    source = db.get_source_from_handle(source_handle)
    assert source is not None
    assert source.get_title() == "Church Records"


def test_asso_role_with_phrase(db):
    """Test that ASSO ROLE with PHRASE uses the phrase as the relation."""
    person = db.get_person_from_gramps_id("I1")
    assert person is not None
    
    person_refs = person.get_person_ref_list()
    
    # Find the association with ROLE OTHER and PHRASE "Teacher"
    # The relation should be "Teacher", not "OTHER"
    teacher_refs = [ref for ref in person_refs if ref.get_relation() == "Teacher"]
    assert len(teacher_refs) == 1
    
    # Verify it references the correct person (I9)
    teacher_ref = teacher_refs[0]
    teacher_handle = teacher_ref.get_reference_handle()
    teacher_person = db.get_person_from_handle(teacher_handle)
    assert teacher_person is not None
    assert teacher_person.get_gramps_id() == "I9"
    
    # Verify that "OTHER" is NOT used as the relation
    other_refs = [ref for ref in person_refs if ref.get_relation() == "OTHER"]
    assert len(other_refs) == 0
