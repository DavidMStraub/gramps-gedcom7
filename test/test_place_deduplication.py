"""Test place deduplication."""

from gramps.gen.db import DbWriteBase
from gramps.gen.db.utils import make_database

from gramps_gedcom7.importer import import_gedcom


def test_places_are_deduplicated():
    """Test that two events with the same place share a single Place object.
    
    Two people with birth events in "Baltimore, , Maryland, USA" should
    reference the same Place object in the database.
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
    
    # Get the actual place object
    place1 = db.get_place_from_handle(place_handle1)
    
    # Verify the place name
    assert place1.get_name().get_value() == "Baltimore"
    
    # Count total places in database - should be 1 (deduplicated)
    assert db.get_number_of_places() == 1, (
        "Should have only 1 place object in database after deduplication"
    )


def test_different_places_not_deduplicated():
    """Test that places with different jurisdiction lists are NOT deduplicated.
    
    "Baltimore, , Maryland, USA" and "Baltimore, , Cork, Ireland" should be
    two separate Place objects even though they share the name "Baltimore".
    """
    gedcom_file = "test/data/place_different.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    
    # Should have 2 different places
    assert db.get_number_of_places() == 2, (
        "Should have 2 separate places for different jurisdictions"
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
