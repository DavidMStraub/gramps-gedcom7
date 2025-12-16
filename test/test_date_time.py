"""Test TIME substructure import."""

import os
from gramps.gen.db import DbWriteBase
from gramps.gen.db.utils import make_database
from gramps.gen.lib import EventType
from gramps_gedcom7.importer import import_gedcom


def test_date_time_on_birth():
    """Test that TIME is imported as an Event Attribute."""
    # Set language to English for consistent event type names
    os.environ['LANGUAGE'] = 'en'
    gedcom_file = "test/data/date_time.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    
    # Should have two people (John Smith and Jane Doe)
    assert db.get_number_of_people() == 2
    
    # Get the person
    people = list(db.iter_people())
    person = [p for p in people if "John" in p.get_primary_name().get_first_name()][0]
    assert "John" in person.get_primary_name().get_first_name()
    assert "Smith" in person.get_primary_name().get_surname()
    
    # Get birth event
    event_refs = person.get_event_ref_list()
    # Person has Birth, Death, and Burial events
    assert len(event_refs) == 3
    birth = None
    for ref in event_refs:
        event = db.get_event_from_handle(ref.ref)
        if str(event.get_type()) == "Birth":
            birth = event
            break
    assert birth is not None
    
    # Check date
    date = birth.get_date_object()
    assert date.get_year() == 1850
    assert date.get_month() == 6
    assert date.get_day() == 15
    
    # Check TIME attribute
    attributes = birth.get_attribute_list()
    assert len(attributes) == 1
    time_attr = attributes[0]
    assert str(time_attr.get_type()) == "Time"
    assert time_attr.get_value() == "14:30:00"


def test_date_time_utc():
    """Test that TIME with UTC indicator (Z) is imported correctly."""
    os.environ['LANGUAGE'] = 'en'
    gedcom_file = "test/data/date_time.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    
    # Should have two people
    people = list(db.iter_people())
    person = [p for p in people if "John" in p.get_primary_name().get_first_name()][0]
    
    # Get death event (has UTC time)
    event_refs = person.get_event_ref_list()
    death = None
    for ref in event_refs:
        event = db.get_event_from_handle(ref.ref)
        if str(event.get_type()) == "Death":
            death = event
            break
    
    assert death is not None, "Death event not found"
    
    # Check TIME attribute with Z (UTC)
    attributes = death.get_attribute_list()
    assert len(attributes) == 1
    time_attr = attributes[0]
    assert str(time_attr.get_type()) == "Time"
    assert time_attr.get_value() == "09:15:30Z"


def test_date_without_time():
    """Test that dates without TIME don't get a Time attribute."""
    os.environ['LANGUAGE'] = 'en'
    gedcom_file = "test/data/date_time.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    
    # Get the family
    families = list(db.iter_families())
    assert len(families) == 1
    family = families[0]
    
    # Get marriage event
    event_refs = family.get_event_ref_list()
    assert len(event_refs) == 1
    marriage_ref = event_refs[0]
    marriage = db.get_event_from_handle(marriage_ref.ref)
    
    # Check there are NO attributes (no TIME was specified)
    attributes = marriage.get_attribute_list()
    assert len(attributes) == 0


def test_time_with_phrase():
    """Test that both TIME and PHRASE can coexist on the same date."""
    os.environ['LANGUAGE'] = 'en'
    gedcom_file = "test/data/date_time.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    
    # Find the burial event
    burial = None
    for handle in db.get_event_handles():
        event = db.get_event_from_handle(handle)
        if str(event.get_type()) == "Burial":
            burial = event
            break
    
    assert burial is not None, "Burial event not found"
    
    # Check date has PHRASE in date.text
    date = burial.get_date_object()
    assert date.get_text() == "around sunset"
    
    # Check TIME is in attribute
    attributes = burial.get_attribute_list()
    assert len(attributes) == 1
    time_attr = attributes[0]
    assert str(time_attr.get_type()) == "Time"
    assert time_attr.get_value() == "18:45:00"
