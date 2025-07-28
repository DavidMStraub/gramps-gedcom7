"""Test GEDCOM 7 extension support."""

import pytest
from gedcom7 import parse
from gramps.gen.db import DbTxn
from gramps.gen.lib import Event, EventRef, EventType, Note, Person

from gramps_gedcom7.settings import ImportSettings
from gramps_gedcom7.process_enhanced import process_gedcom_structures


CENSUS_EXAMPLE = """
0 HEAD
1 GEDC
2 VERS 7.0
1 SCHMA
2 TAG _TMPLT https://github.com/dthaler/gedcom-citations
2 TAG _FIEL https://github.com/dthaler/gedcom-citations
2 TAG _OCUR https://github.com/glamberson/gedcom-occurrences
2 TAG _OCREF https://github.com/glamberson/gedcom-occurrences
2 TAG _PART https://github.com/glamberson/gedcom-occurrences
2 TAG _EVID https://github.com/glamberson/gedcom-evidence
2 TAG _FIND https://github.com/glamberson/gedcom-evidence
2 TAG _CONF https://github.com/glamberson/gedcom-evidence

0 @S1@ SOUR
1 TITL 1850 U.S. Federal Census
1 _TMPLT Census
2 _FIEL Year
3 TEXT 1850
2 _FIEL Jurisdiction
3 TEXT Worcester County, Massachusetts

0 @E1@ _EVID
1 _ID John Smith (census)
1 _FIND John Smith, 42, farmer, born Ohio
1 SOUR @S1@
2 PAGE Line 15

0 @O1@ _OCUR
1 TYPE Census
1 DATE 15 AUG 1850
1 PLAC Worcester, Massachusetts
1 _PART @I1@
2 ROLE Head

0 @I1@ INDI
1 NAME John /Smith/
2 _EVID @E1@
3 _CONF Medium
1 SEX M
1 _OCREF @O1@
2 ROLE Head

0 TRLR
"""


HTML_NOTE_EXAMPLE = """
0 HEAD
1 GEDC
2 VERS 7.0

0 @N1@ SNOTE This is <b>bold</b> and <i>italic</i> text.
1 CONT With <sup>superscript</sup> and <sub>subscript</sub>.
1 CONT And even <a href="https://example.com">links</a>.
1 MIME text/html

0 @I1@ INDI
1 NAME Test /Person/
1 NOTE Note with <u>underline</u> formatting
2 MIME text/html
1 SNOTE @N1@

0 TRLR
"""


class MockDatabase:
    """Mock Gramps database for testing."""
    
    def __init__(self):
        self.persons = {}
        self.events = {}
        self.notes = {}
        self.sources = {}
        self.tags = {}
    
    def add_person(self, person, transaction):
        self.persons[person.handle] = person
    
    def add_event(self, event, transaction):
        self.events[event.handle] = event
    
    def add_note(self, note, transaction):
        self.notes[note.handle] = note
    
    def add_source(self, source, transaction):
        self.sources[source.handle] = source
    
    def add_tag(self, tag, transaction):
        self.tags[tag.handle] = tag
    
    def get_person_from_handle(self, handle):
        return self.persons.get(handle)
    
    def get_event_from_handle(self, handle):
        return self.events.get(handle)


def test_occurrence_extension():
    """Test processing of occurrence extension."""
    # Parse GEDCOM
    structures = parse(CENSUS_EXAMPLE)
    
    # Create mock database
    db = MockDatabase()
    settings = ImportSettings()
    
    # Process structures
    process_gedcom_structures(structures, db, settings)
    
    # Verify event was created
    assert len(db.events) == 1
    event = list(db.events.values())[0]
    assert event.get_type() == EventType.CENSUS
    assert event.get_date_object().get_text() == "15 AUG 1850"
    
    # Verify person was created
    assert len(db.persons) == 1
    person = list(db.persons.values())[0]
    assert person.get_primary_name().get_name() == "John Smith"
    
    # Verify person has event reference
    event_refs = person.get_event_ref_list()
    assert len(event_refs) > 0
    
    # Find the census event reference
    census_ref = None
    for ref in event_refs:
        if db.events[ref.get_reference_handle()].get_type() == EventType.CENSUS:
            census_ref = ref
            break
    
    assert census_ref is not None
    assert census_ref.get_role().xml_str() == "Head"


def test_evidence_extension():
    """Test processing of evidence extension."""
    # Parse GEDCOM
    structures = parse(CENSUS_EXAMPLE)
    
    # Create mock database
    db = MockDatabase()
    settings = ImportSettings()
    
    # Process structures
    process_gedcom_structures(structures, db, settings)
    
    # Verify evidence was created as a note
    evidence_notes = [
        note for note in db.notes.values()
        if "EVIDENCE CONTAINER" in note.get()
    ]
    assert len(evidence_notes) == 1
    
    evidence = evidence_notes[0]
    assert "John Smith, 42, farmer, born Ohio" in evidence.get()
    
    # Verify person has evidence reference
    person = list(db.persons.values())[0]
    # Should have attribute linking to evidence
    attrs = person.get_attribute_list()
    evidence_attrs = [
        attr for attr in attrs
        if attr.get_value().startswith("Evidence:")
    ]
    assert len(evidence_attrs) > 0


def test_citation_template():
    """Test processing of citation templates."""
    # Parse GEDCOM
    structures = parse(CENSUS_EXAMPLE)
    
    # Create mock database
    db = MockDatabase()
    settings = ImportSettings()
    
    # Process structures
    process_gedcom_structures(structures, db, settings)
    
    # Verify source was created with template
    assert len(db.sources) == 1
    source = list(db.sources.values())[0]
    
    # Check for template attributes
    attrs = source.get_attribute_list()
    template_attrs = [
        attr for attr in attrs
        if attr.get_type() == "Citation Template"
    ]
    assert len(template_attrs) == 1
    assert template_attrs[0].get_value() == "Census"
    
    # Check for template fields
    field_attrs = [
        attr for attr in attrs
        if attr.get_type().startswith("Template Field:")
    ]
    assert len(field_attrs) == 2
    
    # Verify field values
    field_dict = {
        attr.get_type()[16:]: attr.get_value()
        for attr in field_attrs
    }
    assert field_dict["Year"] == "1850"
    assert field_dict["Jurisdiction"] == "Worcester County, Massachusetts"


def test_html_formatting():
    """Test HTML subset formatting in notes."""
    # Parse GEDCOM
    structures = parse(HTML_NOTE_EXAMPLE)
    
    # Create mock database
    db = MockDatabase()
    settings = ImportSettings()
    
    # Process structures
    process_gedcom_structures(structures, db, settings)
    
    # Check shared note
    shared_notes = [
        note for note in db.notes.values()
        if note.get().startswith("This is")
    ]
    assert len(shared_notes) == 1
    
    note = shared_notes[0]
    styled_text = note.get_styledtext()
    
    # Verify text content
    assert "This is bold and italic text." in styled_text.get_text()
    
    # Verify tags were created
    tags = styled_text.get_tags()
    assert len(tags) > 0
    
    # Check for specific formatting
    tag_types = [tag.get_type() for tag in tags]
    assert any(t == "bold" for t in tag_types)
    assert any(t == "italic" for t in tag_types)


def test_extension_interoperability_limitations():
    """Test and document extension interoperability limitations."""
    # This test documents the current GEDCOM 7 limitation where
    # extensions cannot formally modify each other's structures
    
    # Example of what we'd like but can't do:
    informal_agreement = """
    # Informal agreement between extensions:
    # gedcom-evidence can add _ELEM substructures to gedcom-citations
    
    0 @S1@ SOUR
    1 _TMPLT Census
    1 SOUR @S1@
    2 PAGE Line 23
    2 _ELEM Name          # From evidence extension
    3 TEXT "John Smith"   # Adding to citation structure
    3 _CONF High         # Confidence in this element
    """
    
    # Document the workaround - parallel structures
    workaround = """
    # Current workaround - parallel structures that align conceptually
    
    0 @S1@ SOUR
    1 _TMPLT Census
    
    0 @C1@ _CITE         # Hypothetical enhanced citation
    1 SOUR @S1@
    2 PAGE Line 23
    2 _ELEM Name
    3 TEXT "John Smith"
    3 _CONF High
    """
    
    # This is more of a documentation test
    assert informal_agreement != workaround
    assert "extensions cannot modify each other" not in ""