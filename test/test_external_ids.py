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
    refn_attrs = [a for a in attrs if "REFN:" in a.get_value()]
    assert len(refn_attrs) == 2
    
    # Check first REFN with TYPE
    refn1 = [a for a in refn_attrs if "12345" in a.get_value()][0]
    assert refn1.get_value() == "REFN:12345 (Type: Employee ID)"
    assert refn1.get_type() == AttributeType.CUSTOM
    
    # Check second REFN with TYPE
    refn2 = [a for a in refn_attrs if "ABC-789" in a.get_value()][0]
    assert refn2.get_value() == "REFN:ABC-789 (Type: Customer Number)"
    
    # Check EXID attributes
    exid_attrs = [a for a in attrs if "EXID:" in a.get_value()]
    assert len(exid_attrs) == 2
    
    # Check first EXID with TYPE
    exid1 = [a for a in exid_attrs if "EXT-001" in a.get_value()][0]
    assert exid1.get_value() == "EXID:EXT-001 (Type: http://example.com/person)"
    
    # Check second EXID with TYPE
    exid2 = [a for a in exid_attrs if "SYS-9876" in a.get_value()][0]
    assert exid2.get_value() == "EXID:SYS-9876 (Type: http://other-system.org)"


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
    refn_attrs = [a for a in attrs if "REFN:" in a.get_value()]
    assert len(refn_attrs) == 1
    assert refn_attrs[0].get_value() == "REFN:USER-999"
    
    # Check EXID without TYPE
    exid_attrs = [a for a in attrs if "EXID:" in a.get_value()]
    assert len(exid_attrs) == 1
    assert exid_attrs[0].get_value() == "EXID:SIMPLE-ID"


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
    refn_attrs = [a for a in attrs if "REFN:" in a.get_value()]
    assert len(refn_attrs) == 1
    assert refn_attrs[0].get_value() == "REFN:FAM-001 (Type: Family Registry)"
    
    # Check EXID
    exid_attrs = [a for a in attrs if "EXID:" in a.get_value()]
    assert len(exid_attrs) == 1
    assert exid_attrs[0].get_value() == "EXID:FAM-EXT-123 (Type: http://family-db.com)"


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
    refn_attrs = [a for a in attrs if "REFN:" in a.get_value()]
    assert len(refn_attrs) == 1
    assert refn_attrs[0].get_value() == "REFN:DOC-001 (Type: Document Number)"
    
    # Check EXID
    exid_attrs = [a for a in attrs if "EXID:" in a.get_value()]
    assert len(exid_attrs) == 1
    assert exid_attrs[0].get_value() == "EXID:SOURCE-EXT-456 (Type: http://archives.gov)"


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
    refn_attrs = [a for a in attrs if "REFN:" in a.get_value()]
    assert len(refn_attrs) == 1
    assert refn_attrs[0].get_value() == "REFN:IMG-001 (Type: Photo Archive ID)"
    
    # Check EXID
    exid_attrs = [a for a in attrs if "EXID:" in a.get_value()]
    assert len(exid_attrs) == 1
    assert exid_attrs[0].get_value() == "EXID:MEDIA-789 (Type: http://media-library.org)"


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
    refn_attrs = [a for a in attrs if "REFN:" in a.get_value()]
    exid_attrs = [a for a in attrs if "EXID:" in a.get_value()]
    
    # Verify multiple instances preserved
    assert len(refn_attrs) == 2
    assert len(exid_attrs) == 2
    
    # Verify each has unique values
    refn_values = [a.get_value() for a in refn_attrs]
    assert "REFN:12345 (Type: Employee ID)" in refn_values
    assert "REFN:ABC-789 (Type: Customer Number)" in refn_values
    
    exid_values = [a.get_value() for a in exid_attrs]
    assert "EXID:EXT-001 (Type: http://example.com/person)" in exid_values
    assert "EXID:SYS-9876 (Type: http://other-system.org)" in exid_values