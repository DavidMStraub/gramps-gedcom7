"""Test GEDCOM 7 attribute handling."""

from gramps.gen.db import DbWriteBase
from gramps.gen.db.utils import make_database
from gramps.gen.lib import AttributeType

from gramps_gedcom7.importer import import_gedcom


def test_individual_attributes():
    """Test that individual attributes are correctly imported."""
    gedcom_file = "test/data/maximal70.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    
    # Get the first person (should have attributes)
    people = list(db.iter_people())
    assert len(people) > 0
    
    person = people[0]
    attributes = person.get_attribute_list()
    
    # Should have at least some attributes
    assert len(attributes) > 0
    
    # Check specific attribute types exist
    attr_types = {attr.get_type().value for attr in attributes}
    
    # CAST maps to CASTE
    assert AttributeType.CASTE in attr_types or any(
        attr.get_type().xml_str() == "Caste" for attr in attributes
    )
    
    # OCCU maps to OCCUPATION
    assert AttributeType.OCCUPATION in attr_types or any(
        attr.get_type().xml_str() == "Occupation" for attr in attributes
    )
    
    # NCHI maps to NUM_CHILD
    assert AttributeType.NUM_CHILD in attr_types or any(
        attr.get_type().xml_str() == "Number of Children" for attr in attributes
    )


def test_family_attributes():
    """Test that family attributes are correctly imported."""
    gedcom_file = "test/data/maximal70.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    
    # Get families
    families = list(db.iter_families())
    assert len(families) > 0
    
    family = families[0]
    attributes = family.get_attribute_list()
    
    # Should have at least NCHI attribute
    assert len(attributes) > 0
    
    # Check for NUM_CHILD attribute
    attr_types = {attr.get_type().value for attr in attributes}
    assert AttributeType.NUM_CHILD in attr_types or any(
        attr.get_type().xml_str() == "Number of Children" for attr in attributes
    )
    
    # Verify the value
    nchi_attrs = [
        attr for attr in attributes
        if attr.get_type().value == AttributeType.NUM_CHILD
        or attr.get_type().xml_str() == "Number of Children"
    ]
    assert len(nchi_attrs) > 0
    assert nchi_attrs[0].get_value() == "2"


def test_custom_attributes():
    """Test that custom attributes (EDUC, RELI, etc.) are imported."""
    gedcom_file = "test/data/maximal70.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    
    # Get the first person
    people = list(db.iter_people())
    person = people[0]
    attributes = person.get_attribute_list()
    
    # Check for custom attributes
    custom_attrs = [
        attr for attr in attributes
        if attr.get_type().value == AttributeType.CUSTOM
    ]
    
    # Should have some custom attributes (EDUC, RELI, PROP, etc.)
    assert len(custom_attrs) > 0
    
    # Check that custom attribute names are preserved
    custom_names = {attr.get_type().xml_str() for attr in custom_attrs}
    
    # Education, Religion, Property should be there
    assert any("Education" in name for name in custom_names)
    assert any("Religion" in name or "reli" in name for name in custom_names)


def test_attribute_with_type():
    """Test that attributes with TYPE substructure are handled correctly.
    
    For FACT and IDNO, TYPE defines the attribute type.
    For others, TYPE provides additional context but we keep the standard type.
    """
    gedcom_file = "test/data/maximal70.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    
    # Get the first person
    people = list(db.iter_people())
    person = people[0]
    attributes = person.get_attribute_list()
    
    # IDNO with TYPE should be a custom attribute with the TYPE value as the name
    idno_attrs = [
        attr for attr in attributes
        if attr.get_type().value == AttributeType.CUSTOM
        and "ID number type" in attr.get_type().xml_str()
    ]
    assert len(idno_attrs) > 0
    assert idno_attrs[0].get_value() == "ID number"
    
    # Standard attributes like CAST should keep their standard type
    # even when TYPE substructure is present
    cast_attrs = [
        attr for attr in attributes
        if attr.get_type().value == AttributeType.CASTE
    ]
    assert len(cast_attrs) > 0
    assert cast_attrs[0].get_value() == "Caste"
