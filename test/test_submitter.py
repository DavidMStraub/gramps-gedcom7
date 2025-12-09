"""Test GEDCOM submitter handling."""

from gramps.gen.db import DbWriteBase
from gramps.gen.db.utils import make_database
from gramps_gedcom7.importer import import_gedcom


def test_submitter_to_researcher():
    """Test that HEAD.SUBM becomes the database Researcher."""
    gedcom_file = "test/data/submitter.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    
    # Check that researcher was set
    researcher = db.get_researcher()
    assert researcher.get_name() == "John Doe"
    assert researcher.get_email() == "john@example.com"
    assert researcher.get_phone() == "+1-555-1234"
    assert researcher.get_street() == "123 Main Street"
    assert researcher.get_city() == "Springfield"
    assert researcher.get_state() == "IL"
    assert researcher.get_postal_code() == "62701"
    assert researcher.get_country() == "USA"


def test_submitter_to_repository():
    """Test that non-HEAD submitters become Repositories."""
    gedcom_file = "test/data/submitter.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    
    # Should have repositories for submitters
    repos = list(db.iter_repositories())
    assert len(repos) == 2  # SUBM1 (also researcher) and SUBM2
    
    # Find the second submitter repository
    subm2_repo = None
    for repo in repos:
        if "Jane Smith" in repo.get_name():
            subm2_repo = repo
            break
    
    assert subm2_repo is not None
    assert subm2_repo.get_type().string == "GEDCOM data"
    
    # Check address
    addresses = subm2_repo.get_address_list()
    assert len(addresses) == 0  # SUBM2 has no address in test data
    
    # Check contact info stored as URLs
    urls = subm2_repo.get_url_list()
    email_urls = [u for u in urls if u.get_type().value == 1]  # EMAIL
    assert len(email_urls) == 1
    assert email_urls[0].get_path() == "jane@example.com"
    
    www_urls = [u for u in urls if u.get_type().value == 2]  # WEB_HOME
    assert len(www_urls) == 1
    assert www_urls[0].get_path() == "https://janesmith.example.com"
