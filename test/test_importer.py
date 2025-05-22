from gramps_gedcom7.importer import import_gedcom

def test_importer_maximal70():
    # Test the import_gedcom function with a maximal GEDCOM 7.0 file
    gedcom_file = "test/data/maximal70.ged"
    gedcom_data = import_gedcom(gedcom_file, None)
