"""Test media reference TITL handling."""

from gramps.gen.db import DbWriteBase
from gramps.gen.db.utils import make_database
from gramps_gedcom7.importer import import_gedcom


def test_media_ref_title():
    """Test that OBJE.TITL is stored as an attribute on the media reference."""
    gedcom_file = "test/data/media_ref_title.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    
    person = db.get_person_from_gramps_id("I1")
    assert person is not None
    assert len(person.media_list) == 3
    
    # First media ref has a title
    media_ref1 = person.media_list[0]
    assert len(media_ref1.attribute_list) == 1
    attr = media_ref1.attribute_list[0]
    assert attr.get_type().string == "OBJE:TITL"
    assert attr.get_value() == "Custom Title for This Reference"
    
    # Second media ref has no title
    media_ref2 = person.media_list[1]
    assert len(media_ref2.attribute_list) == 0
    
    # Third media ref points to same media as first but has different title
    media_ref3 = person.media_list[2]
    assert media_ref3.ref == media_ref1.ref  # Same media object
    assert len(media_ref3.attribute_list) == 1
    assert media_ref3.attribute_list[0].get_value() == "Same Photo, Different Context"
