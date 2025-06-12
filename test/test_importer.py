from gramps_gedcom7.importer import import_gedcom

from gramps.gen.db.utils import make_database

def test_importer_maximal70():
    # Test the import_gedcom function with a maximal GEDCOM 7.0 file
    gedcom_file = "test/data/maximal70.ged"
    db = make_database("sqlite")
    db.load(":memory:")
    import_gedcom(gedcom_file, db)
