"""Test place deduplication."""

from gramps.gen.db import DbWriteBase
from gramps.gen.db.utils import make_database

from gramps_gedcom7.importer import import_gedcom


def test_places_are_deduplicated():
    """Test that two events with the same place share a single Place object.
    
    Two people with birth events in "Baltimore, , Maryland, USA" should
    reference the same Place object in the database.
    The hierarchy creates 4 places: Baltimore -> (empty county) -> Maryland -> USA,
    but all levels should be deduplicated across both events.
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
    
    # Get the place handles
    place_handle1 = event1.get_place_handle()
    place_handle2 = event2.get_place_handle()
    
    # Places should be deduplicated - same handle for same location
    assert place_handle1 == place_handle2, (
        "Places with identical jurisdiction lists should share the same handle"
    )
    
    # Get the actual place object (Baltimore)
    place1 = db.get_place_from_handle(place_handle1)
    
    # Verify the place name
    assert place1.get_name().get_value() == "Baltimore"
    
    # Count total places in database - should be 4 (Baltimore, empty county, Maryland, USA)
    # All deduplicated across both events
    assert db.get_number_of_places() == 4, (
        "Should have 4 places in hierarchy: Baltimore -> county -> Maryland -> USA"
    )
    
    # Verify the hierarchy
    placeref_list = place1.get_placeref_list()
    assert len(placeref_list) == 1, "Baltimore should have one parent (the county)"
    
    # Get parent (empty county)
    county_handle = placeref_list[0].get_reference_handle()
    county_place = db.get_place_from_handle(county_handle)
    assert county_place.get_name().get_value() == "", "County should be empty string"
    
    # Verify county has parent (Maryland)
    assert len(county_place.get_placeref_list()) == 1
    maryland_handle = county_place.get_placeref_list()[0].get_reference_handle()
    maryland_place = db.get_place_from_handle(maryland_handle)
    assert maryland_place.get_name().get_value() == "Maryland"
    
    # Verify Maryland has parent (USA)
    assert len(maryland_place.get_placeref_list()) == 1
    usa_handle = maryland_place.get_placeref_list()[0].get_reference_handle()
    usa_place = db.get_place_from_handle(usa_handle)
    assert usa_place.get_name().get_value() == "USA"
    
    # Verify USA has no parent (top of hierarchy)
    assert len(usa_place.get_placeref_list()) == 0


def test_different_places_not_deduplicated():
    """Test that places with different jurisdiction lists are NOT deduplicated.
    
    "Baltimore, , Maryland, USA" and "Baltimore, , Cork, Ireland" should be
    two separate Place objects even though they share the name "Baltimore".
    With hierarchy, we get:
    - Baltimore (MD) -> county -> Maryland -> USA
    - Baltimore (Cork) -> county -> Cork -> Ireland
    Total: 8 places (2 Baltimores, 2 counties, Maryland, USA, Cork, Ireland)
    But USA, Maryland, Cork, Ireland should each appear only once.
    Actually: 2 Baltimores + 2 empty counties + Maryland + USA + Cork + Ireland = 8 places
    """
    gedcom_file = "test/data/place_different.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    
    # Should have 8 places total in hierarchy
    assert db.get_number_of_places() == 8, (
        "Should have 8 places: 2 Baltimores, 2 counties, Maryland, USA, Cork, Ireland"
    )
    
    # Get both people
    p1 = db.get_person_from_gramps_id("I1")
    p2 = db.get_person_from_gramps_id("I2")
    
    # Get their birth events
    birth_ref1 = p1.get_event_ref_list()[0]
    birth_ref2 = p2.get_event_ref_list()[0]
    
    event1 = db.get_event_from_handle(birth_ref1.ref)
    event2 = db.get_event_from_handle(birth_ref2.ref)
    
    # Get the place handles - should be different
    place_handle1 = event1.get_place_handle()
    place_handle2 = event2.get_place_handle()
    
    assert place_handle1 != place_handle2, (
        "Different jurisdiction lists should create different place objects"
    )
    
    # Both places should be named Baltimore
    place1 = db.get_place_from_handle(place_handle1)
    place2 = db.get_place_from_handle(place_handle2)
    
    assert place1.get_name().get_value() == "Baltimore"
    assert place2.get_name().get_value() == "Baltimore"
    
    # Verify they have different parent hierarchies
    # Place 1: Baltimore -> county -> Maryland -> USA
    county1_handle = place1.get_placeref_list()[0].get_reference_handle()
    county1 = db.get_place_from_handle(county1_handle)
    state1_handle = county1.get_placeref_list()[0].get_reference_handle()
    state1 = db.get_place_from_handle(state1_handle)
    assert state1.get_name().get_value() == "Maryland"
    
    # Place 2: Baltimore -> county -> Cork -> Ireland
    county2_handle = place2.get_placeref_list()[0].get_reference_handle()
    county2 = db.get_place_from_handle(county2_handle)
    state2_handle = county2.get_placeref_list()[0].get_reference_handle()
    state2 = db.get_place_from_handle(state2_handle)
    assert state2.get_name().get_value() == "Cork"
