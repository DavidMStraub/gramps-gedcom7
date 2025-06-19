from gramps.gen.db import DbWriteBase
from gramps.gen.db.utils import make_database
from gramps.gen.lib import (
    Citation,
    Event,
    EventType,
    Family,
    Media,
    Note,
    Person,
    Place,
    Repository,
    Source,
)

from gramps_gedcom7.importer import import_gedcom


def test_importer_maximal70():
    """Test the import_gedcom function with a maximal GEDCOM 7.0 file."""
    gedcom_file = "test/data/maximal70.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)

    family = db.get_family_from_gramps_id("F1")
    assert isinstance(family, Family)
    assert family.get_privacy()
    # TODO attributes (lines 48-72)

    # events
    assert len(family.event_ref_list) == 11
    anulment = db.get_event_from_handle(family.event_ref_list[0].ref)
    assert isinstance(anulment, Event)
    assert anulment.get_type().value == EventType.ANNULMENT

    census = db.get_event_from_handle(family.event_ref_list[1].ref)
    assert isinstance(census, Event)
    assert census.get_type().value == EventType.CENSUS

    divorce = db.get_event_from_handle(family.event_ref_list[2].ref)
    assert isinstance(divorce, Event)
    assert divorce.get_type().value == EventType.DIVORCE

    divorce_filing = db.get_event_from_handle(family.event_ref_list[3].ref)
    assert isinstance(divorce_filing, Event)
    assert divorce_filing.get_type().value == EventType.DIV_FILING

    engagement = db.get_event_from_handle(family.event_ref_list[4].ref)
    assert isinstance(engagement, Event)
    assert engagement.get_type().value == EventType.ENGAGEMENT

    marriage_banns = db.get_event_from_handle(family.event_ref_list[5].ref)
    assert isinstance(marriage_banns, Event)
    assert marriage_banns.get_type().value == EventType.MARR_BANNS

    marriage_contract = db.get_event_from_handle(family.event_ref_list[6].ref)
    assert isinstance(marriage_contract, Event)
    assert marriage_contract.get_type().value == EventType.MARR_CONTR

    marriage_license = db.get_event_from_handle(family.event_ref_list[7].ref)
    assert isinstance(marriage_license, Event)
    assert marriage_license.get_type().value == EventType.MARR_LIC

    marriage_settlement = db.get_event_from_handle(family.event_ref_list[8].ref)
    assert isinstance(marriage_settlement, Event)
    assert marriage_settlement.get_type().value == EventType.MARR_SETTL

    marriage = db.get_event_from_handle(family.event_ref_list[9].ref)
    assert isinstance(marriage, Event)
    assert marriage.get_type().value == EventType.MARRIAGE
    # TODO AGE
    assert marriage.date.dateval == (27, 3, 2022, False)
    # TODO PHRASE
    marriage_place = db.get_place_from_handle(marriage.place)
    assert isinstance(marriage_place, Place)
    assert marriage_place.name.value == "Place"
    assert marriage.get_privacy()
    assert len(marriage.note_list) == 1
    marriage_note = db.get_note_from_handle(marriage.note_list[0])
    assert isinstance(marriage_note, Note)
    assert marriage_note.gramps_id == "N1"
    assert len(marriage.citation_list) == 2
    marriage_citation1 = db.get_citation_from_handle(marriage.citation_list[0])
    assert isinstance(marriage_citation1, Citation)
    marriage_citation2 = db.get_citation_from_handle(marriage.citation_list[1])
    assert isinstance(marriage_citation2, Citation)
    marriage_source = db.get_source_from_handle(marriage_citation1.source_handle)
    assert isinstance(marriage_source, Source)
    assert marriage_citation1.source_handle == marriage_source.handle
    assert marriage_citation2.source_handle == marriage_source.handle
    assert marriage_source.gramps_id == "S1"
    assert marriage_citation1.page == "1"
    assert marriage_citation2.page == "2"
    assert len(marriage.media_list) == 2
    marriage_media1 = db.get_media_from_handle(marriage.media_list[0].ref)
    assert isinstance(marriage_media1, Media)
    marriage_media2 = db.get_media_from_handle(marriage.media_list[1].ref)
    assert isinstance(marriage_media2, Media)
    assert marriage_media1.gramps_id == "O1"
    assert marriage_media2.gramps_id == "O2"