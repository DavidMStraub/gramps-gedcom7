"""Test MEDI PHRASE handling in SOURCE_REPOSITORY_CITATION."""

from gramps.gen.db import DbWriteBase
from gramps.gen.db.utils import make_database
from gramps.gen.lib import SourceMediaType

from gramps_gedcom7.importer import import_gedcom


def test_medi_with_phrase():
    """Test that MEDI with PHRASE uses the phrase as custom media type."""
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

    # Find the repo ref with MEDI BOOK and PHRASE "Booklet"
    # This should be stored as CUSTOM with string "Booklet"
    booklet_ref = None
    for repo_ref in repo_refs:
        media_type = repo_ref.get_media_type()
        if media_type == SourceMediaType.CUSTOM and media_type.string == "Booklet":
            booklet_ref = repo_ref
            break

    assert booklet_ref is not None, "Should find repo ref with PHRASE 'Booklet'"
    assert booklet_ref.get_call_number() == "Call number"


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
