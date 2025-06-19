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