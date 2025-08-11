"""Test import of contact fields (PHON, EMAIL, FAX, WWW)."""

from pathlib import Path
from gramps.gen.db import DbWriteBase
from gramps.gen.db.utils import make_database
from gramps.gen.lib import AttributeType, EventType, UrlType
from gramps_gedcom7.importer import import_gedcom


def test_contact_fields_repository():
    """Test import of PHON, FAX, EMAIL, WWW for repositories."""
    gedcom_file = "test/data/contact_fields.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    
    # Get repository
    repos = list(db.iter_repositories())
    assert len(repos) == 1
    repo = repos[0]
    assert repo.name == "Test Repository"
    
    # Check URLs (EMAIL and WWW)
    urls = repo.get_url_list()
    email_urls = [u for u in urls if u.get_type() == UrlType.EMAIL]
    assert len(email_urls) == 1
    assert email_urls[0].get_path() == "repo@example.com"
    
    web_urls = [u for u in urls if u.get_type() == UrlType.WEB_HOME]
    assert len(web_urls) == 1
    assert web_urls[0].get_path() == "https://example.com"
    
    # Check addresses (PHON and FAX stored in addresses)
    addresses = repo.get_address_list()
    assert len(addresses) == 2
    
    # Check phone in address
    phone_addrs = [a for a in addresses if a.get_phone() and "FAX" not in a.get_phone()]
    assert len(phone_addrs) == 1
    assert phone_addrs[0].get_phone() == "+1-555-0123"
    
    # Check fax in address
    fax_addrs = [a for a in addresses if a.get_phone() and "FAX" in a.get_phone()]
    assert len(fax_addrs) == 1
    assert fax_addrs[0].get_phone() == "FAX: +1-555-0124"


def test_contact_fields_individual():
    """Test import of PHON, FAX, EMAIL, WWW for individuals."""
    gedcom_file = "test/data/contact_fields.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    
    # Get first person (John Doe)
    persons = list(db.iter_people())
    john = [p for p in persons if "John" in p.get_primary_name().get_first_name()][0]
    
    # Check addresses (PHON and FAX stored in addresses)
    addresses = john.get_address_list()
    assert len(addresses) == 2
    
    # Check phone in address
    phone_addrs = [a for a in addresses if a.get_phone() and "FAX" not in a.get_phone()]
    assert len(phone_addrs) == 1
    assert phone_addrs[0].get_phone() == "+1-555-0125"
    
    # Check fax in address
    fax_addrs = [a for a in addresses if a.get_phone() and "FAX" in a.get_phone()]
    assert len(fax_addrs) == 1
    assert fax_addrs[0].get_phone() == "FAX: +1-555-0126"
    
    # Check URLs (EMAIL and WWW)
    urls = john.get_url_list()
    assert len(urls) == 2
    
    email_urls = [u for u in urls if u.get_type() == UrlType.EMAIL]
    assert len(email_urls) == 1
    assert email_urls[0].get_path() == "john@example.com"
    
    web_urls = [u for u in urls if u.get_type() == UrlType.WEB_HOME]
    assert len(web_urls) == 1
    assert web_urls[0].get_path() == "https://johndoe.com"


def test_contact_fields_event():
    """Test import of contact fields in events."""
    gedcom_file = "test/data/contact_fields.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    
    # Get Jane Doe
    persons = list(db.iter_people())
    jane = [p for p in persons if "Jane" in p.get_primary_name().get_first_name()][0]
    
    # Get birth event
    event_refs = jane.get_event_ref_list()
    events = [db.get_event_from_handle(ref.ref) for ref in event_refs]
    birth_events = [e for e in events if e.get_type() == EventType.BIRTH]
    assert len(birth_events) == 1
    birth = birth_events[0]
    
    # Check event attributes for contact fields
    attrs = birth.get_attribute_list()
    assert len(attrs) == 4  # PHON, EMAIL, FAX, WWW
    
    # Check phone attribute
    phone_attrs = [a for a in attrs if "Phone:" in a.get_value()]
    assert len(phone_attrs) == 1
    assert phone_attrs[0].get_value() == "Phone: +1-555-0127"
    
    # Check email attribute
    email_attrs = [a for a in attrs if "Email:" in a.get_value()]
    assert len(email_attrs) == 1
    assert email_attrs[0].get_value() == "Email: birth@hospital.com"
    
    # Check fax attribute
    fax_attrs = [a for a in attrs if "Fax:" in a.get_value()]
    assert len(fax_attrs) == 1
    assert fax_attrs[0].get_value() == "Fax: +1-555-0128"
    
    # Check website attribute
    www_attrs = [a for a in attrs if "Website:" in a.get_value()]
    assert len(www_attrs) == 1
    assert www_attrs[0].get_value() == "Website: https://hospital.com/births"


def test_multiple_contact_fields():
    """Test that multiple instances of the same contact field type are preserved."""
    # Create GEDCOM with multiple phone numbers
    gedcom_text = """0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 NAME Multi /Contact/
1 PHON +1-555-0001
1 PHON +1-555-0002
1 EMAIL first@example.com
1 EMAIL second@example.com
0 TRLR"""
    
    # Write test file
    test_file = Path(__file__).parent / "data" / "multi_contact.ged"
    test_file.write_text(gedcom_text)
    
    gedcom_file = str(test_file)
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    
    # Get person
    persons = list(db.iter_people())
    assert len(persons) == 1
    person = persons[0]
    
    # Check multiple phone numbers in addresses
    addresses = person.get_address_list()
    phones = [a.get_phone() for a in addresses if a.get_phone()]
    assert len(phones) == 2
    assert "+1-555-0001" in phones
    assert "+1-555-0002" in phones
    
    # Check multiple email addresses in URLs
    urls = person.get_url_list()
    email_urls = [u for u in urls if u.get_type() == UrlType.EMAIL]
    assert len(email_urls) == 2
    emails = [u.get_path() for u in email_urls]
    assert "first@example.com" in emails
    assert "second@example.com" in emails
    
    # Clean up test file
    test_file.unlink()