"""Test MEDI PHRASE handling in SOURCE_REPOSITORY_CITATION."""

import io

from gramps.gen.db import DbWriteBase
from gramps.gen.db.utils import make_database
from gramps.gen.lib import SourceMediaType

from gramps_gedcom7.importer import import_gedcom


def test_medi_phrase_beside_a_standard_value_is_reported():
    """MEDI BOOK keeps BOOK; its phrase cannot replace it, Gramps having one value."""
    gedcom_file = "test/data/maximal70.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    report = import_gedcom(gedcom_file, db)

    source = db.get_source_from_gramps_id("S1")
    first = source.get_reporef_list()[0]
    assert first.get_media_type() == SourceMediaType.BOOK
    assert first.get_call_number() == "Call number"
    assert any("REPO > CALN > MEDI > PHRASE" in str(entry) for entry in report)


def test_medi_other_is_named_by_its_phrase():
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(
        io.StringIO(
            "0 HEAD\n1 GEDC\n2 VERS 7.0\n0 @R1@ REPO\n1 NAME Archive\n"
            "0 @S1@ SOUR\n1 REPO @R1@\n2 CALN 12\n3 MEDI OTHER\n4 PHRASE Booklet\n"
            "0 TRLR\n"
        ),
        db,
    )
    (reference,) = db.get_source_from_gramps_id("S1").get_reporef_list()
    media_type = reference.get_media_type()
    assert media_type == SourceMediaType.CUSTOM
    assert media_type.string == "Booklet"


def test_medi_without_phrase():
    """Test that MEDI without PHRASE uses the enumerated value."""
    gedcom_file = "test/data/maximal70.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)

    # Get the source
    source = db.get_source_from_gramps_id("S1")
    assert source is not None

    # Get repository references
    repo_refs = source.get_reporef_list()
    assert len(repo_refs) > 0

    # Find repo refs with standard media types (without PHRASE)
    # maximal70.ged has: AUDIO, ELECTRONIC, VIDEO, CARD, FICHE, FILM, etc.
    # Most important: check that standard enums work correctly
    found_standard = False
    for ref in repo_refs:
        mt = ref.get_media_type()
        # Any of these standard types proves the mapping works
        if mt in [
            SourceMediaType.VIDEO,
            SourceMediaType.AUDIO,
            SourceMediaType.ELECTRONIC,
            SourceMediaType.CARD,
        ]:
            found_standard = True
            break

    assert found_standard, "Should have at least one standard media type"
