"""Test that place properties follow first-event-wins policy for deduplicated places."""

from gramps.cli.clidbman import CLIDbManager
from gramps.gen.db.utils import make_database
from gramps.gen.dbstate import DbState

from gramps_gedcom7.importer import import_gedcom


def test_place_properties_first_event_wins():
    """Test that when two events have same place with different properties, first wins.
    
    Two events at "Baltimore, Maryland, USA" with different MAP coordinates:
    - Event 1: N39.2904, W76.6122 (correct coordinates)
    - Event 2: N40.0000, W77.0000 (different coordinates)
    
    The first event's coordinates should be preserved on the deduplicated place.
    """
    gedcom_file = "test/data/place_properties_dedup.ged"
    db = make_database("sqlite")
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
    
    # Both events should reference the same Baltimore place (deduplicated)
    place_handle1 = event1.get_place_handle()
    place_handle2 = event2.get_place_handle()
    assert place_handle1 == place_handle2, "Places should be deduplicated"
    
    # Get the shared place
    place = db.get_place_from_handle(place_handle1)
    assert place.get_name().get_value() == "Baltimore"
    
    # First event's coordinates should be preserved (first-event-wins)
    assert place.get_latitude() == "N39.2904", (
        f"Expected first event's latitude N39.2904, got {place.get_latitude()}"
    )
    assert place.get_longitude() == "W76.6122", (
        f"Expected first event's longitude W76.6122, got {place.get_longitude()}"
    )
