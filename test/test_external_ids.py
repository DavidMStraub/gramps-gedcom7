"""Test import of external IDs (EXID and REFN)."""

from gramps.gen.db import DbWriteBase
from gramps.gen.db.utils import make_database
from gramps.gen.lib import AttributeType, EventType
from gramps_gedcom7.importer import import_gedcom


def test_individual_external_ids():
    """Test import of EXID and REFN for individuals."""
    gedcom_file = "test/data/external_ids.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    
    # Get John Smith
    persons = list(db.iter_people())
    john = [p for p in persons if "John" in p.get_primary_name().get_first_name()][0]
    
    # Check attributes
    attrs = john.get_attribute_list()
    
    # Check REFN attributes
    refn_attrs = [a for a in attrs if a.get_type().string and a.get_type().string.startswith("REFN")]
    assert len(refn_attrs) == 2
    
    # Check first REFN with TYPE
    refn1 = [a for a in refn_attrs if a.get_value() == "12345"][0]
    assert refn1.get_value() == "12345"
    assert refn1.get_type().string == "REFN:Employee ID"
    
    # Check second REFN with TYPE
    refn2 = [a for a in refn_attrs if a.get_value() == "ABC-789"][0]
    assert refn2.get_value() == "ABC-789"
    assert refn2.get_type().string == "REFN:Customer Number"
    
    # Check EXID attributes
    exid_attrs = [a for a in attrs if a.get_type().string and a.get_type().string.startswith("EXID")]
    assert len(exid_attrs) == 2
    
    # Check first EXID with TYPE
    exid1 = [a for a in exid_attrs if a.get_value() == "EXT-001"][0]
    assert exid1.get_value() == "EXT-001"
    assert exid1.get_type().string == "EXID:http://example.com/person"
    
    # Check second EXID with TYPE
    exid2 = [a for a in exid_attrs if a.get_value() == "SYS-9876"][0]
    assert exid2.get_value() == "SYS-9876"
    assert exid2.get_type().string == "EXID:http://other-system.org"


def test_individual_external_ids_without_type():
    """Test import of EXID and REFN without TYPE substructure."""
    gedcom_file = "test/data/external_ids.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    
    # Get Jane Doe
    persons = list(db.iter_people())
    jane = [p for p in persons if "Jane" in p.get_primary_name().get_first_name()][0]
    
    # Check attributes
    attrs = jane.get_attribute_list()
    
    # Check REFN without TYPE
    refn_attrs = [a for a in attrs if a.get_type().string and a.get_type().string == "REFN"]
    assert len(refn_attrs) == 1
    assert refn_attrs[0].get_value() == "USER-999"
    assert refn_attrs[0].get_type().string == "REFN"
    
    # Check EXID without TYPE
    exid_attrs = [a for a in attrs if a.get_type().string and a.get_type().string == "EXID"]
    assert len(exid_attrs) == 1
    assert exid_attrs[0].get_value() == "SIMPLE-ID"
    assert exid_attrs[0].get_type().string == "EXID"


def test_family_external_ids():
    """Test import of EXID and REFN for families."""
    gedcom_file = "test/data/external_ids.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    
    # Get family
    families = list(db.iter_families())
    assert len(families) == 1
    family = families[0]
    
    # Check attributes
    attrs = family.get_attribute_list()
    
    # Check REFN
    refn_attrs = [a for a in attrs if a.get_type().string and a.get_type().string.startswith("REFN")]
    assert len(refn_attrs) == 1
    assert refn_attrs[0].get_value() == "FAM-001"
    assert refn_attrs[0].get_type().string == "REFN:Family Registry"
    
    # Check EXID
    exid_attrs = [a for a in attrs if a.get_type().string and a.get_type().string.startswith("EXID")]
    assert len(exid_attrs) == 1
    assert exid_attrs[0].get_value() == "FAM-EXT-123"
    assert exid_attrs[0].get_type().string == "EXID:http://family-db.com"


def test_source_external_ids():
    """Test import of EXID and REFN for sources."""
    gedcom_file = "test/data/external_ids.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    
    # Get source
    sources = list(db.iter_sources())
    assert len(sources) == 1
    source = sources[0]
    
    # Check attributes
    attrs = source.get_attribute_list()
    
    # Check REFN
    refn_attrs = [a for a in attrs if a.get_type().string and a.get_type().string.startswith("REFN")]
    assert len(refn_attrs) == 1
    assert refn_attrs[0].get_value() == "DOC-001"
    assert refn_attrs[0].get_type().string == "REFN:Document Number"
    
    # Check EXID
    exid_attrs = [a for a in attrs if a.get_type().string and a.get_type().string.startswith("EXID")]
    assert len(exid_attrs) == 1
    assert exid_attrs[0].get_value() == "SOURCE-EXT-456"
    assert exid_attrs[0].get_type().string == "EXID:http://archives.gov"


def test_media_external_ids():
    """Test import of EXID and REFN for media objects."""
    gedcom_file = "test/data/external_ids.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    
    # Get media
    media_objects = list(db.iter_media())
    assert len(media_objects) == 1
    media = media_objects[0]
    
    # Check attributes
    attrs = media.get_attribute_list()
    
    # Check REFN
    refn_attrs = [a for a in attrs if a.get_type().string and a.get_type().string.startswith("REFN")]
    assert len(refn_attrs) == 1
    assert refn_attrs[0].get_value() == "IMG-001"
    assert refn_attrs[0].get_type().string == "REFN:Photo Archive ID"
    
    # Check EXID
    exid_attrs = [a for a in attrs if a.get_type().string and a.get_type().string.startswith("EXID")]
    assert len(exid_attrs) == 1
    assert exid_attrs[0].get_value() == "MEDIA-789"
    assert exid_attrs[0].get_type().string == "EXID:http://media-library.org"


def test_place_external_ids():
    """Test import of EXID for places."""
    gedcom_file = "test/data/external_ids.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    
    # Get place through birth event
    persons = list(db.iter_people())
    jane = [p for p in persons if "Jane" in p.get_primary_name().get_first_name()][0]
    
    # Get birth event
    event_refs = jane.get_event_ref_list()
    events = [db.get_event_from_handle(ref.ref) for ref in event_refs]
    birth_events = [e for e in events if e.get_type() == EventType.BIRTH]
    assert len(birth_events) == 1
    birth = birth_events[0]
    
    # Get place
    place = db.get_place_from_handle(birth.get_place_handle())
    assert place is not None
    assert place.get_name().get_value() == "Test City"
    
    # Check place URLs (EXID stored as URL for places)
    urls = place.get_url_list()
    exid_urls = [u for u in urls if "External ID" in u.get_description()]
    assert len(exid_urls) == 1
    assert exid_urls[0].get_path() == "PLACE-123"
    assert exid_urls[0].get_description() == "External ID: PLACE-123"


def test_multiple_external_ids():
    """Test that multiple EXID and REFN instances are preserved."""
    gedcom_file = "test/data/external_ids.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    
    # Get John Smith (has 2 REFN and 2 EXID)
    persons = list(db.iter_people())
    john = [p for p in persons if "John" in p.get_primary_name().get_first_name()][0]
    
    attrs = john.get_attribute_list()
    refn_attrs = [a for a in attrs if a.get_type().string and a.get_type().string.startswith("REFN")]
    exid_attrs = [a for a in attrs if a.get_type().string and a.get_type().string.startswith("EXID")]
    
    # Verify multiple instances preserved
    assert len(refn_attrs) == 2
    assert len(exid_attrs) == 2
    
    # Verify each has unique values
    refn_values = [a.get_value() for a in refn_attrs]
    assert "12345" in refn_values
    assert "ABC-789" in refn_values
    
    # Verify type strings
    refn_types = [a.get_type().string for a in refn_attrs]
    assert "REFN:Employee ID" in refn_types
    assert "REFN:Customer Number" in refn_types
    
    exid_values = [a.get_value() for a in exid_attrs]
    assert "EXT-001" in exid_values
    assert "SYS-9876" in exid_values
    
    # Verify type strings
    exid_types = [a.get_type().string for a in exid_attrs]
    assert "EXID:http://example.com/person" in exid_types
    assert "EXID:http://other-system.org" in exid_types