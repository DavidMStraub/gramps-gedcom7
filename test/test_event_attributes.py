"""Test import of event attributes (AGNC, RELI, CAUS)."""

from gramps.gen.db import DbWriteBase
from gramps.gen.db.utils import make_database
from gramps.gen.lib import AttributeType, EventType
from gramps_gedcom7.importer import import_gedcom


def test_birth_event_attributes():
    """Test import of AGNC, RELI, CAUS on birth events."""
    gedcom_file = "test/data/event_attributes.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    
    # Get John Smith
    persons = list(db.iter_people())
    john = [p for p in persons if "John" in p.get_primary_name().get_first_name()][0]
    
    # Get birth event
    event_refs = john.get_event_ref_list()
    events = [db.get_event_from_handle(ref.ref) for ref in event_refs]
    birth_events = [e for e in events if e.get_type() == EventType.BIRTH]
    assert len(birth_events) == 1
    birth = birth_events[0]
    
    # Check attributes
    attrs = birth.get_attribute_list()
    assert len(attrs) == 3
    
    # Check AGNC (Agency)
    agency_attrs = [a for a in attrs if a.get_type() == AttributeType.AGENCY]
    assert len(agency_attrs) == 1
    assert agency_attrs[0].get_value() == "State Registry Office"
    
    # Check RELI (Religion) - stored as custom
    reli_attrs = [a for a in attrs if "Religion:" in a.get_value()]
    assert len(reli_attrs) == 1
    assert reli_attrs[0].get_value() == "Religion: Catholic"
    assert reli_attrs[0].get_type() == AttributeType.CUSTOM
    
    # Check CAUS (Cause)
    cause_attrs = [a for a in attrs if a.get_type() == AttributeType.CAUSE]
    assert len(cause_attrs) == 1
    assert cause_attrs[0].get_value() == "Natural birth"


def test_death_event_attributes():
    """Test import of AGNC, RELI, CAUS on death events."""
    gedcom_file = "test/data/event_attributes.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    
    # Get John Smith
    persons = list(db.iter_people())
    john = [p for p in persons if "John" in p.get_primary_name().get_first_name()][0]
    
    # Get death event
    event_refs = john.get_event_ref_list()
    events = [db.get_event_from_handle(ref.ref) for ref in event_refs]
    death_events = [e for e in events if e.get_type() == EventType.DEATH]
    assert len(death_events) == 1
    death = death_events[0]
    
    # Check attributes
    attrs = death.get_attribute_list()
    assert len(attrs) == 3
    
    # Check AGNC
    agency_attrs = [a for a in attrs if a.get_type() == AttributeType.AGENCY]
    assert len(agency_attrs) == 1
    assert agency_attrs[0].get_value() == "County Coroner"
    
    # Check RELI
    reli_attrs = [a for a in attrs if "Religion:" in a.get_value()]
    assert len(reli_attrs) == 1
    assert reli_attrs[0].get_value() == "Religion: Baptist"
    
    # Check CAUS
    cause_attrs = [a for a in attrs if a.get_type() == AttributeType.CAUSE]
    assert len(cause_attrs) == 1
    assert cause_attrs[0].get_value() == "Heart failure"


def test_baptism_event_attributes():
    """Test import of AGNC and RELI on baptism events."""
    gedcom_file = "test/data/event_attributes.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    
    # Get Jane Doe
    persons = list(db.iter_people())
    jane = [p for p in persons if "Jane" in p.get_primary_name().get_first_name()][0]
    
    # Get baptism event
    event_refs = jane.get_event_ref_list()
    events = [db.get_event_from_handle(ref.ref) for ref in event_refs]
    baptism_events = [e for e in events if e.get_type() == EventType.BAPTISM]
    assert len(baptism_events) == 1
    baptism = baptism_events[0]
    
    # Check attributes
    attrs = baptism.get_attribute_list()
    assert len(attrs) == 2
    
    # Check AGNC
    agency_attrs = [a for a in attrs if a.get_type() == AttributeType.AGENCY]
    assert len(agency_attrs) == 1
    assert agency_attrs[0].get_value() == "First Baptist Church"
    
    # Check RELI
    reli_attrs = [a for a in attrs if "Religion:" in a.get_value()]
    assert len(reli_attrs) == 1
    assert reli_attrs[0].get_value() == "Religion: Baptist"


def test_marriage_event_attributes():
    """Test import of AGNC, RELI, CAUS on family events."""
    gedcom_file = "test/data/event_attributes.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    
    # Get family
    families = list(db.iter_families())
    family = families[0]
    
    # Get marriage event
    event_refs = family.get_event_ref_list()
    events = [db.get_event_from_handle(ref.ref) for ref in event_refs]
    marriage_events = [e for e in events if e.get_type() == EventType.MARRIAGE]
    assert len(marriage_events) == 1
    marriage = marriage_events[0]
    
    # Check attributes
    attrs = marriage.get_attribute_list()
    assert len(attrs) == 3
    
    # Check AGNC
    agency_attrs = [a for a in attrs if a.get_type() == AttributeType.AGENCY]
    assert len(agency_attrs) == 1
    assert agency_attrs[0].get_value() == "City Clerk Office"
    
    # Check RELI
    reli_attrs = [a for a in attrs if "Religion:" in a.get_value()]
    assert len(reli_attrs) == 1
    assert reli_attrs[0].get_value() == "Religion: Civil Ceremony"
    
    # Check CAUS
    cause_attrs = [a for a in attrs if a.get_type() == AttributeType.CAUSE]
    assert len(cause_attrs) == 1
    assert cause_attrs[0].get_value() == "Love"


def test_divorce_event_attributes():
    """Test import of AGNC and CAUS on divorce events."""
    gedcom_file = "test/data/event_attributes.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    
    # Get family
    families = list(db.iter_families())
    family = families[0]
    
    # Get divorce event
    event_refs = family.get_event_ref_list()
    events = [db.get_event_from_handle(ref.ref) for ref in event_refs]
    divorce_events = [e for e in events if e.get_type() == EventType.DIVORCE]
    assert len(divorce_events) == 1
    divorce = divorce_events[0]
    
    # Check attributes
    attrs = divorce.get_attribute_list()
    assert len(attrs) == 2
    
    # Check AGNC
    agency_attrs = [a for a in attrs if a.get_type() == AttributeType.AGENCY]
    assert len(agency_attrs) == 1
    assert agency_attrs[0].get_value() == "District Court"
    
    # Check CAUS
    cause_attrs = [a for a in attrs if a.get_type() == AttributeType.CAUSE]
    assert len(cause_attrs) == 1
    assert cause_attrs[0].get_value() == "Irreconcilable differences"


def test_custom_event_attributes():
    """Test import of AGNC and RELI on custom events."""
    gedcom_file = "test/data/event_attributes.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    
    # Get Test Person
    persons = list(db.iter_people())
    test_person = [p for p in persons if "Test" in p.get_primary_name().get_first_name()][0]
    
    # Get custom event (with TYPE "Graduation")
    event_refs = test_person.get_event_ref_list()
    events = [db.get_event_from_handle(ref.ref) for ref in event_refs]
    # Custom events with a TYPE substructure have their type set to that value
    graduation_events = [e for e in events if e.get_type().string == "Graduation"]
    assert len(graduation_events) == 1
    custom = graduation_events[0]
    
    # Check attributes
    attrs = custom.get_attribute_list()
    assert len(attrs) == 2
    
    # Check AGNC
    agency_attrs = [a for a in attrs if a.get_type() == AttributeType.AGENCY]
    assert len(agency_attrs) == 1
    assert agency_attrs[0].get_value() == "University of Example"
    
    # Check RELI
    reli_attrs = [a for a in attrs if "Religion:" in a.get_value()]
    assert len(reli_attrs) == 1
    assert reli_attrs[0].get_value() == "Religion: Non-denominational"