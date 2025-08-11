"""Test import of contact fields (PHON, EMAIL, FAX, WWW)."""

from gramps.gen.db import DbWriteBase
from gramps.gen.db.utils import make_database
from gramps.gen.lib import EventType, UrlType
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
    phone_attrs = [a for a in attrs if a.get_type().string == "Phone"]
    assert len(phone_attrs) == 1
    assert phone_attrs[0].get_value() == "+1-555-0127"
    
    # Check email attribute
    email_attrs = [a for a in attrs if a.get_type().string == "Email"]
    assert len(email_attrs) == 1
    assert email_attrs[0].get_value() == "birth@hospital.com"
    
    # Check fax attribute
    fax_attrs = [a for a in attrs if a.get_type().string == "Fax"]
    assert len(fax_attrs) == 1
    assert fax_attrs[0].get_value() == "+1-555-0128"
    
    # Check website attribute
    www_attrs = [a for a in attrs if a.get_type().string == "Website"]
    assert len(www_attrs) == 1
    assert www_attrs[0].get_value() == "https://hospital.com/births"