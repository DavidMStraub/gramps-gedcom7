"""Test import of event contact fields (PHON, EMAIL, FAX, WWW)."""

from gramps.gen.db import DbWriteBase
from gramps.gen.db.utils import make_database
from gramps.gen.lib import EventType
from gramps_gedcom7.importer import import_gedcom


def test_birth_event_contact_fields():
    """Test import of contact fields on birth events."""
    gedcom_file = "test/data/event_contact_fields.ged"
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
    assert len(attrs) == 4
    
    # Check contact fields stored as attributes
    phone_attrs = [a for a in attrs if "Phone:" in a.get_value()]
    assert len(phone_attrs) == 1
    assert phone_attrs[0].get_value() == "Phone: +1-555-0100"
    
    email_attrs = [a for a in attrs if "Email:" in a.get_value()]
    assert len(email_attrs) == 1
    assert email_attrs[0].get_value() == "Email: birth.registry@hospital.org"
    
    fax_attrs = [a for a in attrs if "Fax:" in a.get_value()]
    assert len(fax_attrs) == 1
    assert fax_attrs[0].get_value() == "Fax: +1-555-0101"
    
    www_attrs = [a for a in attrs if "Website:" in a.get_value()]
    assert len(www_attrs) == 1
    assert www_attrs[0].get_value() == "Website: http://hospital.org/birth-records"


def test_death_event_multiple_contact_fields():
    """Test import of multiple contact fields on death events."""
    gedcom_file = "test/data/event_contact_fields.ged"
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
    
    # Check attributes (2 PHON, 2 EMAIL, 2 FAX, 2 WWW = 8 total)
    attrs = death.get_attribute_list()
    assert len(attrs) == 8
    
    # Check multiple instances preserved
    phone_attrs = [a for a in attrs if "Phone:" in a.get_value()]
    assert len(phone_attrs) == 2
    phone_values = [a.get_value() for a in phone_attrs]
    assert "Phone: +1-555-0200" in phone_values
    assert "Phone: +1-555-0201" in phone_values
    
    email_attrs = [a for a in attrs if "Email:" in a.get_value()]
    assert len(email_attrs) == 2
    email_values = [a.get_value() for a in email_attrs]
    assert "Email: coroner@county.gov" in email_values
    assert "Email: admin@hospital.org" in email_values
    
    fax_attrs = [a for a in attrs if "Fax:" in a.get_value()]
    assert len(fax_attrs) == 2
    
    www_attrs = [a for a in attrs if "Website:" in a.get_value()]
    assert len(www_attrs) == 2


def test_baptism_event_contact_fields():
    """Test import of contact fields on baptism events."""
    gedcom_file = "test/data/event_contact_fields.ged"
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
    assert len(attrs) == 2  # Only PHON and EMAIL
    
    phone_attrs = [a for a in attrs if "Phone:" in a.get_value()]
    assert len(phone_attrs) == 1
    assert phone_attrs[0].get_value() == "Phone: +1-555-0300"
    
    email_attrs = [a for a in attrs if "Email:" in a.get_value()]
    assert len(email_attrs) == 1
    assert email_attrs[0].get_value() == "Email: church@firstbaptist.org"


def test_marriage_event_contact_fields():
    """Test import of contact fields on family events."""
    gedcom_file = "test/data/event_contact_fields.ged"
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
    assert len(attrs) == 4
    
    phone_attrs = [a for a in attrs if "Phone:" in a.get_value()]
    assert len(phone_attrs) == 1
    assert phone_attrs[0].get_value() == "Phone: +1-555-0400"
    
    email_attrs = [a for a in attrs if "Email:" in a.get_value()]
    assert len(email_attrs) == 1
    assert email_attrs[0].get_value() == "Email: clerk@city.gov"
    
    fax_attrs = [a for a in attrs if "Fax:" in a.get_value()]
    assert len(fax_attrs) == 1
    assert fax_attrs[0].get_value() == "Fax: +1-555-0401"
    
    www_attrs = [a for a in attrs if "Website:" in a.get_value()]
    assert len(www_attrs) == 1
    assert www_attrs[0].get_value() == "Website: http://city.gov/marriages"


def test_divorce_event_contact_fields():
    """Test import of partial contact fields on divorce events."""
    gedcom_file = "test/data/event_contact_fields.ged"
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
    
    # Check attributes (only PHON and EMAIL, no FAX or WWW)
    attrs = divorce.get_attribute_list()
    assert len(attrs) == 2
    
    phone_attrs = [a for a in attrs if "Phone:" in a.get_value()]
    assert len(phone_attrs) == 1
    assert phone_attrs[0].get_value() == "Phone: +1-555-0500"
    
    email_attrs = [a for a in attrs if "Email:" in a.get_value()]
    assert len(email_attrs) == 1
    assert email_attrs[0].get_value() == "Email: court@district.gov"


def test_custom_event_contact_fields():
    """Test import of contact fields on custom events."""
    gedcom_file = "test/data/event_contact_fields.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    
    # Get Test Person
    persons = list(db.iter_people())
    test_person = [p for p in persons if "Test" in p.get_primary_name().get_first_name()][0]
    
    # Get custom event
    event_refs = test_person.get_event_ref_list()
    events = [db.get_event_from_handle(ref.ref) for ref in event_refs]
    graduation_events = [e for e in events if e.get_type().string == "Graduation"]
    assert len(graduation_events) == 1
    graduation = graduation_events[0]
    
    # Check all four contact fields
    attrs = graduation.get_attribute_list()
    assert len(attrs) == 4
    
    phone_attrs = [a for a in attrs if "Phone:" in a.get_value()]
    assert len(phone_attrs) == 1
    assert phone_attrs[0].get_value() == "Phone: +1-555-0600"
    
    email_attrs = [a for a in attrs if "Email:" in a.get_value()]
    assert len(email_attrs) == 1
    assert email_attrs[0].get_value() == "Email: registrar@university.edu"
    
    fax_attrs = [a for a in attrs if "Fax:" in a.get_value()]
    assert len(fax_attrs) == 1
    assert fax_attrs[0].get_value() == "Fax: +1-555-0601"
    
    www_attrs = [a for a in attrs if "Website:" in a.get_value()]
    assert len(www_attrs) == 1
    assert www_attrs[0].get_value() == "Website: http://university.edu/graduation"