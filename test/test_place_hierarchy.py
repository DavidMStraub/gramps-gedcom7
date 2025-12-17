"""Test place hierarchy implementation."""

from gramps.gen.db import DbWriteBase
from gramps.gen.db.utils import make_database
from gramps.gen.lib import PlaceType

from gramps_gedcom7.importer import import_gedcom


def test_place_hierarchy_created():
    """Test that a place with multiple jurisdictions creates a hierarchy.
    
    "Baltimore, , Maryland, USA" should create 4 places:
    - USA (top)
    - Maryland (child of USA)
    - (empty county) (child of Maryland)
    - Baltimore (child of empty county, referenced by event)
    """
    gedcom_file = "test/data/place_deduplication.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    
    # Should have 4 places in the hierarchy
    assert db.get_number_of_places() == 4, (
        "Should have 4 places for 'Baltimore, , Maryland, USA' hierarchy"
    )
    
    # Get person and their birth event
    p1 = db.get_person_from_gramps_id("I1")
    birth_ref = p1.get_event_ref_list()[0]
    event = db.get_event_from_handle(birth_ref.ref)
    
    # Event should reference Baltimore (lowest level)
    place_handle = event.get_place_handle()
    baltimore = db.get_place_from_handle(place_handle)
    
    assert baltimore.get_name().get_value() == "Baltimore"
    
    # Baltimore should have a parent (empty county)
    placeref_list = baltimore.get_placeref_list()
    assert len(placeref_list) == 1, "Baltimore should have one parent"
    
    # Get the parent (empty county)
    county_handle = placeref_list[0].get_reference_handle()
    county = db.get_place_from_handle(county_handle)
    
    # Empty county should have empty name
    assert county.get_name().get_value() == ""
    
    # County should have a parent (Maryland)
    placeref_list = county.get_placeref_list()
    assert len(placeref_list) == 1, "County should have one parent"
    
    maryland_handle = placeref_list[0].get_reference_handle()
    maryland = db.get_place_from_handle(maryland_handle)
    
    assert maryland.get_name().get_value() == "Maryland"
    
    # Maryland should have a parent (USA)
    placeref_list = maryland.get_placeref_list()
    assert len(placeref_list) == 1, "Maryland should have one parent"
    
    usa_handle = placeref_list[0].get_reference_handle()
    usa = db.get_place_from_handle(usa_handle)
    
    assert usa.get_name().get_value() == "USA"
    
    # USA should have no parent (top level)
    placeref_list = usa.get_placeref_list()
    assert len(placeref_list) == 0, "USA should have no parent"


def test_place_hierarchy_deduplication():
    """Test that hierarchy places are deduplicated across events.
    
    Two events in "Baltimore, , Maryland, USA" should share all 4 hierarchy places.
    """
    gedcom_file = "test/data/place_deduplication.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    
    # Get both people
    p1 = db.get_person_from_gramps_id("I1")
    p2 = db.get_person_from_gramps_id("I2")
    
    # Get their birth events
    birth_ref1 = p1.get_event_ref_list()[0]
    birth_ref2 = p2.get_event_ref_list()[0]
    
    event1 = db.get_event_from_handle(birth_ref1.ref)
    event2 = db.get_event_from_handle(birth_ref2.ref)
    
    # Both events should reference the same Baltimore place
    assert event1.get_place_handle() == event2.get_place_handle()
    
    # Should still have only 4 places total (shared hierarchy)
    assert db.get_number_of_places() == 4


def test_different_place_hierarchies():
    """Test that different hierarchies don't share parent places.
    
    "Baltimore, , Maryland, USA" and "Baltimore, , Cork, Ireland" should have:
    - 2 separate Baltimore places (different parents)
    - 2 separate empty counties (different parents)
    - Separate state/province level (Maryland vs Cork)
    - Separate countries (USA vs Ireland)
    Total: 8 places
    """
    gedcom_file = "test/data/place_different.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    
    # Should have 8 places total (4 for each hierarchy)
    assert db.get_number_of_places() == 8, (
        "Should have 8 places for two different 4-level hierarchies"
    )
    
    # Get both people
    p1 = db.get_person_from_gramps_id("I1")
    p2 = db.get_person_from_gramps_id("I2")
    
    birth_ref1 = p1.get_event_ref_list()[0]
    birth_ref2 = p2.get_event_ref_list()[0]
    
    event1 = db.get_event_from_handle(birth_ref1.ref)
    event2 = db.get_event_from_handle(birth_ref2.ref)
    
    # The two Baltimore places should be different
    place_handle1 = event1.get_place_handle()
    place_handle2 = event2.get_place_handle()
    
    assert place_handle1 != place_handle2, (
        "Different jurisdiction hierarchies should have different place handles"
    )
    
    # But both should be named Baltimore
    baltimore1 = db.get_place_from_handle(place_handle1)
    baltimore2 = db.get_place_from_handle(place_handle2)
    
    assert baltimore1.get_name().get_value() == "Baltimore"
    assert baltimore2.get_name().get_value() == "Baltimore"
    
    # Trace up hierarchy for Baltimore 1 (should end in USA)
    parent_handle = baltimore1.get_placeref_list()[0].get_reference_handle()
    parent = db.get_place_from_handle(parent_handle)
    parent_handle = parent.get_placeref_list()[0].get_reference_handle()
    parent = db.get_place_from_handle(parent_handle)  # Maryland
    parent_handle = parent.get_placeref_list()[0].get_reference_handle()
    country1 = db.get_place_from_handle(parent_handle)  # USA
    
    assert country1.get_name().get_value() == "USA"
    
    # Trace up hierarchy for Baltimore 2 (should end in Ireland)
    parent_handle = baltimore2.get_placeref_list()[0].get_reference_handle()
    parent = db.get_place_from_handle(parent_handle)
    parent_handle = parent.get_placeref_list()[0].get_reference_handle()
    parent = db.get_place_from_handle(parent_handle)  # Cork
    parent_handle = parent.get_placeref_list()[0].get_reference_handle()
    country2 = db.get_place_from_handle(parent_handle)  # Ireland
    
    assert country2.get_name().get_value() == "Ireland"


def test_empty_places_not_deduplicated():
    """Test that places with no jurisdiction list are NOT deduplicated.
    
    Two events with empty PLAC structures but different coordinates should
    create separate place objects, not be merged together.
    """
    gedcom_file = "test/data/place_empty.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    
    # Should have 2 separate places (not deduplicated)
    assert db.get_number_of_places() == 2, (
        "Empty places with different properties should not be deduplicated"
    )
    
    # Get both people
    p1 = db.get_person_from_gramps_id("I1")
    p2 = db.get_person_from_gramps_id("I2")
    
    birth_ref1 = p1.get_event_ref_list()[0]
    birth_ref2 = p2.get_event_ref_list()[0]
    
    event1 = db.get_event_from_handle(birth_ref1.ref)
    event2 = db.get_event_from_handle(birth_ref2.ref)
    
    # The two places should be different
    place_handle1 = event1.get_place_handle()
    place_handle2 = event2.get_place_handle()
    
    assert place_handle1 != place_handle2, (
        "Empty places should not be deduplicated"
    )
    
    # Verify they have different coordinates
    place1 = db.get_place_from_handle(place_handle1)
    place2 = db.get_place_from_handle(place_handle2)
    
    # Place 1 should have NYC coordinates
    assert place1.get_latitude() == "N40.7128"
    assert place1.get_longitude() == "W74.0060"
    
    # Place 2 should have London coordinates
    assert place2.get_latitude() == "N51.5074"
    assert place2.get_longitude() == "W0.1278"

