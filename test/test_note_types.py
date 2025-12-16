"""Test that notes get appropriate NoteType based on object type."""

import tempfile
import os
from gramps.gen.db import DbWriteBase
from gramps.gen.db.utils import make_database
from gramps.gen.lib import NoteType
from gramps_gedcom7.importer import import_gedcom


def test_family_note_type():
    """Test that HUSB/WIFE PHRASE notes get NoteType.FAMILY."""
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom("test/data/family_phrase.ged", db)
    
    # Get family F1 with HUSB and WIFE PHRASE
    families = list(db.iter_families())
    family_with_notes = [f for f in families if len(f.get_note_list()) > 0]
    assert len(family_with_notes) > 0
    
    family = family_with_notes[0]
    note_handles = family.get_note_list()
    
    # Check that notes have FAMILY type
    for note_handle in note_handles:
        note = db.get_note_from_handle(note_handle)
        assert note.get_type() == NoteType.FAMILY, f"Expected NoteType.FAMILY, got {note.get_type()}"


def test_childref_note_type():
    """Test that CHIL PHRASE notes get NoteType.CHILDREF."""
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom("test/data/family_phrase.ged", db)
    
    # Get family F1 with CHIL PHRASE
    families = list(db.iter_families())
    family_with_child_notes = None
    
    for family in families:
        child_refs = family.get_child_ref_list()
        for child_ref in child_refs:
            if len(child_ref.get_note_list()) > 0:
                family_with_child_notes = family
                break
        if family_with_child_notes:
            break
    
    assert family_with_child_notes is not None, "No family with child notes found"
    
    # Check that ChildRef notes have CHILDREF type
    child_refs = family_with_child_notes.get_child_ref_list()
    for child_ref in child_refs:
        note_handles = child_ref.get_note_list()
        for note_handle in note_handles:
            note = db.get_note_from_handle(note_handle)
            assert note.get_type() == NoteType.CHILDREF, f"Expected NoteType.CHILDREF, got {note.get_type()}"


def test_person_note_type():
    """Test that person notes get NoteType.PERSON."""
    gedcom_data = """0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 NAME John /Doe/
1 NOTE This is a person note
0 TRLR
"""
    
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    
    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ged', delete=False) as f:
        f.write(gedcom_data)
        temp_path = f.name
    
    try:
        import_gedcom(temp_path, db)
        
        persons = list(db.iter_people())
        assert len(persons) == 1
        
        person = persons[0]
        note_handles = person.get_note_list()
        assert len(note_handles) == 1
        
        note = db.get_note_from_handle(note_handles[0])
        assert note.get_type() == NoteType.PERSON, f"Expected NoteType.PERSON, got {note.get_type()}"
    finally:
        os.unlink(temp_path)


def test_event_note_type():
    """Test that event notes get NoteType.EVENT."""
    gedcom_data = """0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 NAME John /Doe/
1 BIRT
2 DATE 1 JAN 1900
2 NOTE This is a birth event note
0 TRLR
"""
    
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ged', delete=False) as f:
        f.write(gedcom_data)
        temp_path = f.name
    
    try:
        import_gedcom(temp_path, db)
        
        events = list(db.iter_events())
        assert len(events) == 1
        
        event = events[0]
        note_handles = event.get_note_list()
        assert len(note_handles) == 1
        
        note = db.get_note_from_handle(note_handles[0])
        assert note.get_type() == NoteType.EVENT, f"Expected NoteType.EVENT, got {note.get_type()}"
    finally:
        os.unlink(temp_path)


def test_place_note_type():
    """Test that place notes get NoteType.PLACE."""
    gedcom_data = """0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 NAME John /Doe/
1 BIRT
2 PLAC London, England
3 NOTE This is a place note
0 TRLR
"""
    
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ged', delete=False) as f:
        f.write(gedcom_data)
        temp_path = f.name
    
    try:
        import_gedcom(temp_path, db)
        
        places = list(db.iter_places())
        assert len(places) == 1
        
        place = places[0]
        note_handles = place.get_note_list()
        assert len(note_handles) == 1
        
        note = db.get_note_from_handle(note_handles[0])
        assert note.get_type() == NoteType.PLACE, f"Expected NoteType.PLACE, got {note.get_type()}"
    finally:
        os.unlink(temp_path)


def test_source_note_type():
    """Test that source notes get NoteType.SOURCE."""
    gedcom_data = """0 HEAD
1 GEDC
2 VERS 7.0
0 @S1@ SOUR
1 TITL Test Source
1 NOTE This is a source note
0 TRLR
"""
    
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ged', delete=False) as f:
        f.write(gedcom_data)
        temp_path = f.name
    
    try:
        import_gedcom(temp_path, db)
        
        sources = list(db.iter_sources())
        assert len(sources) == 1
        
        source = sources[0]
        note_handles = source.get_note_list()
        assert len(note_handles) == 1
        
        note = db.get_note_from_handle(note_handles[0])
        assert note.get_type() == NoteType.SOURCE, f"Expected NoteType.SOURCE, got {note.get_type()}"
    finally:
        os.unlink(temp_path)
