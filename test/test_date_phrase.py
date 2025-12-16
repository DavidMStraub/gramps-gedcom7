"""Test import of DATE PHRASE structures."""

from gramps.gen.db import DbWriteBase
from gramps.gen.db.utils import make_database
from gramps.gen.lib import EventType
from gramps_gedcom7.importer import import_gedcom


def test_date_phrase_on_birth():
    """Test import of PHRASE substructure on birth event DATE."""
    gedcom_file = "test/data/date_phrase.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    
    # Get the person (John Smith)
    persons = list(db.iter_people())
    assert len(persons) == 2
    person = [p for p in persons if "John" in p.get_primary_name().get_first_name()][0]
    
    # Get birth event
    event_refs = person.get_event_ref_list()
    events = [db.get_event_from_handle(ref.ref) for ref in event_refs]
    birth_events = [e for e in events if e.get_type() == EventType.BIRTH]
    assert len(birth_events) == 1
    birth = birth_events[0]
    
    # Check date
    date = birth.get_date_object()
    assert not date.is_empty()
    
    # Check that the date has the PHRASE stored in its text field
    assert date.get_text() == "30th of January, 1648/9"
    
    # Verify the structured date is correct (30 JAN 1649)
    assert date.get_day() == 30
    assert date.get_month() == 1
    assert date.get_year() == 1649


def test_date_phrase_on_marriage():
    """Test import of PHRASE on marriage event with period date."""
    gedcom_file = "test/data/date_phrase.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    
    # Get family
    families = list(db.iter_families())
    assert len(families) == 1
    family = families[0]
    
    # Get marriage event
    event_refs = family.get_event_ref_list()
    events = [db.get_event_from_handle(ref.ref) for ref in event_refs]
    marriage_events = [e for e in events if e.get_type() == EventType.MARRIAGE]
    assert len(marriage_events) == 1
    marriage = marriage_events[0]
    
    # Check date
    date = marriage.get_date_object()
    assert not date.is_empty()
    
    # Check that the PHRASE is stored
    assert date.get_text() == "During America's involvement in the Great War"
    
    # Verify it's a range/span date
    assert date.is_compound()


def test_date_without_phrase():
    """Test that dates without PHRASE still import correctly."""
    gedcom_file = "test/data/date_phrase.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    
    # Get Jane Doe who has a death event without PHRASE
    persons = list(db.iter_people())
    jane = [p for p in persons if "Jane" in p.get_primary_name().get_first_name()][0]
    
    # Get death event
    event_refs = jane.get_event_ref_list()
    events = [db.get_event_from_handle(ref.ref) for ref in event_refs]
    death_events = [e for e in events if e.get_type() == EventType.DEATH]
    assert len(death_events) == 1
    death = death_events[0]
    
    # Check date exists and is structured
    date = death.get_date_object()
    assert not date.is_empty()
    assert date.is_valid()  # Not text-only
    
    # Check that text field is empty (no PHRASE)
    assert date.get_text() == "" or date.get_text() is None
    
    # Verify the structured date is correct (15 MAR 1720)
    assert date.get_day() == 15
    assert date.get_month() == 3
    assert date.get_year() == 1720


def test_date_phrase_preserves_non_textonly_modifier():
    """Test that PHRASE doesn't convert structured dates to text-only."""
    gedcom_file = "test/data/date_phrase.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    
    # Get John Smith's birth
    persons = list(db.iter_people())
    john = [p for p in persons if "John" in p.get_primary_name().get_first_name()][0]
    event_refs = john.get_event_ref_list()
    events = [db.get_event_from_handle(ref.ref) for ref in event_refs]
    birth = [e for e in events if e.get_type() == EventType.BIRTH][0]
    
    date = birth.get_date_object()
    
    # Verify it's NOT text-only despite having text content
    from gramps.gen.lib import Date
    assert date.get_modifier() != Date.MOD_TEXTONLY
    assert date.is_valid()  # Structured date is valid
    
    # But it should have the text field populated
    assert date.get_text() == "30th of January, 1648/9"
