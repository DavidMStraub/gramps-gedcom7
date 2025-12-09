"""Test import of repository addresses."""

from gramps.gen.db import DbWriteBase
from gramps.gen.db.utils import make_database
from gramps_gedcom7.importer import import_gedcom


def test_repository_full_address():
    """Test import of full ADDRESS_STRUCTURE for repositories."""
    gedcom_file = "test/data/repository_address.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    
    # Get repository
    repos = list(db.iter_repositories())
    assert len(repos) == 1
    repo = repos[0]
    assert repo.get_name() == "National Archives"
    
    # Check full address
    addresses = repo.get_address_list()
    assert len(addresses) == 1
    addr = addresses[0]
    
    assert addr.get_street() == "700 Pennsylvania Avenue NW"
    assert addr.get_city() == "Washington"
    assert addr.get_state() == "DC"
    assert addr.get_postal_code() == "20408"
    assert addr.get_country() == "USA"


def test_repository_address_with_adr123():
    """Test ADDRESS_STRUCTURE with deprecated ADR1/2/3 fields."""
    gedcom_file = "test/data/repository_address_adr123.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    
    repos = list(db.iter_repositories())
    assert len(repos) == 1
    repo = repos[0]
    
    addresses = repo.get_address_list()
    assert len(addresses) == 1
    addr = addresses[0]
    
    # When ADDR is empty, ADR1/2/3 should be concatenated
    assert addr.get_street() == "123 Main Street\nSuite 100\nFloor 2"
    assert addr.get_city() == "Springfield"
