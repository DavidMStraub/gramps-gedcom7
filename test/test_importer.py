from gramps.gen.db import DbWriteBase
from gramps.gen.db.utils import make_database
from gramps.gen.lib import (
    Citation,
    Event,
    EventType,
    Family,
    Media,
    Name,
    NameType,
    Note,
    NoteType,
    Person,
    Place,
    Repository,
    Source,
    Surname,
    UrlType,
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

    # event notes
    assert len(marriage.note_list) == 1
    marriage_note = db.get_note_from_handle(marriage.note_list[0])
    assert isinstance(marriage_note, Note)
    assert marriage_note.gramps_id == "N1"

    # event source citations
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

    # event media
    assert len(marriage.media_list) == 2
    marriage_media1 = db.get_media_from_handle(marriage.media_list[0].ref)
    assert isinstance(marriage_media1, Media)
    marriage_media2 = db.get_media_from_handle(marriage.media_list[1].ref)
    assert isinstance(marriage_media2, Media)
    assert marriage_media1.gramps_id == "O1"
    assert marriage_media2.gramps_id == "O2"

    # event UID + contact fields (8 contact fields: 2 PHON, 2 EMAIL, 2 FAX, 2 WWW) + AGNC, RELI, CAUS
    assert len(marriage.attribute_list) == 13  # 8 contact fields + 3 event attrs + 2 UID
    # Check contact fields by type string
    phone_attrs = [a for a in marriage.attribute_list if a.get_type().string == "Phone"]
    assert len(phone_attrs) == 2
    email_attrs = [a for a in marriage.attribute_list if a.get_type().string == "Email"]
    assert len(email_attrs) == 2
    fax_attrs = [a for a in marriage.attribute_list if a.get_type().string == "Fax"]
    assert len(fax_attrs) == 2
    www_attrs = [a for a in marriage.attribute_list if a.get_type().string == "Website"]
    assert len(www_attrs) == 2
    # Check UIDs
    uid_attrs = [a for a in marriage.attribute_list if a.get_type() == "UID"]
    assert len(uid_attrs) == 2
    uid_values = [a.get_value() for a in uid_attrs]
    assert "bbcc0025-34cb-4542-8cfb-45ba201c9c2c" in uid_values
    assert "9ead4205-5bad-4c05-91c1-0aecd3f5127d" in uid_values
    # Check AGNC, RELI, CAUS attributes
    agency_attrs = [a for a in marriage.attribute_list if a.get_type() == "Agency"]
    assert len(agency_attrs) == 1
    reli_attrs = [a for a in marriage.attribute_list if a.get_type().string == "Religion"]
    assert len(reli_attrs) == 1
    cause_attrs = [a for a in marriage.attribute_list if a.get_type() == "Cause"]
    assert len(cause_attrs) == 1

    # custom event (line 123)
    event = db.get_event_from_handle(family.event_ref_list[10].ref)
    assert isinstance(event, Event)
    assert event.get_type().value == EventType.CUSTOM
    assert event.get_type().string == "Event type"

    # husband
    father = db.get_person_from_handle(family.father_handle)
    assert isinstance(father, Person)
    assert father.gramps_id == "I1"

    # wife
    mother = db.get_person_from_handle(family.mother_handle)
    assert isinstance(mother, Person)
    assert mother.gramps_id == "I2"

    # children
    assert len(family.child_ref_list) == 1
    child1 = db.get_person_from_handle(family.child_ref_list[0].ref)
    assert isinstance(child1, Person)
    assert child1.gramps_id == "I4"

    # family UID
    assert len(family.attribute_list) == 2
    assert family.attribute_list[0].get_type() == "UID"
    assert (
        family.attribute_list[0].get_value() == "bbcc0025-34cb-4542-8cfb-45ba201c9c2c"
    )
    assert family.attribute_list[1].get_type() == "UID"
    assert (
        family.attribute_list[1].get_value() == "9ead4205-5bad-4c05-91c1-0aecd3f5127d"
    )

    # family note
    assert len(family.note_list) == 2
    family_note1 = db.get_note_from_handle(family.note_list[0])
    assert isinstance(family_note1, Note)
    assert family_note1.text.string == "Note text"
    family_note2 = db.get_note_from_handle(family.note_list[1])
    assert isinstance(family_note2, Note)
    assert family_note2.gramps_id == "N1"

    # family source citations (line 209ff)
    assert len(family.citation_list) == 2

    family_citation1 = db.get_citation_from_handle(family.citation_list[0])
    assert isinstance(family_citation1, Citation)
    family_source1 = db.get_source_from_handle(family_citation1.source_handle)
    assert isinstance(family_source1, Source)
    assert family_source1.gramps_id == "S1"
    assert family_citation1.page == "1"
    assert family_citation1.confidence == 1

    family_citation2 = db.get_citation_from_handle(family.citation_list[1])
    assert isinstance(family_citation2, Citation)
    family_source2 = db.get_source_from_handle(family_citation2.source_handle)
    assert isinstance(family_source2, Source)
    assert family_source2.gramps_id == "S2"
    assert family_citation2.page == "2"
    assert family_citation2.confidence == 2

    # family media
    assert len(family.media_list) == 2
    family_media1 = db.get_media_from_handle(family.media_list[0].ref)
    assert isinstance(family_media1, Media)
    family_media2 = db.get_media_from_handle(family.media_list[1].ref)
    assert isinstance(family_media2, Media)
    assert family_media1.gramps_id == "O1"
    assert family_media2.gramps_id == "O2"

    # second family (line 227ff)
    family = db.get_family_from_gramps_id("F2")
    assert isinstance(family, Family)
    assert not family.get_privacy()
    assert len(family.event_ref_list) == 1
    marriage = db.get_event_from_handle(family.event_ref_list[0].ref)
    assert isinstance(marriage, Event)
    assert marriage.get_type().value == EventType.MARRIAGE
    assert marriage.date.dateval == (0, 0, 1998, False)
    assert len(family.child_ref_list) == 1
    person = db.get_person_from_handle(family.child_ref_list[0].ref)
    assert isinstance(person, Person)
    assert person.gramps_id == "I1"

    # first individual (line 231-510)
    assert person.get_privacy()

    # primary name
    name: Name = person.get_primary_name()
    assert name.type.value == NameType.CUSTOM
    assert name.title == "Lt. Cmndr."
    assert name.first_name == "Joseph"
    assert name.nick == "John"
    assert name.suffix == "jr."
    assert len(name.surname_list) == 1
    surname: Surname = name.surname_list[0]
    assert surname.prefix == "de"
    assert surname.surname == "Allen"

    # alternate names
    assert len(person.alternate_names) == 3
    alt_name1: Name = person.alternate_names[0]
    assert alt_name1.type.value == NameType.BIRTH
    assert alt_name1.first_name == "John"
    assert alt_name1.surname_list[0].surname == "Doe"

    alt_name2: Name = person.alternate_names[1]
    assert alt_name2.type.value == NameType.AKA
    assert alt_name2.first_name == "Aka"
    assert len(alt_name2.surname_list) == 0

    alt_name3: Name = person.alternate_names[2]
    assert alt_name3.type.value == NameType.CUSTOM
    assert alt_name3.type.string == "IMMIGRANT"
    assert alt_name3.first_name == "Immigrant Name"
    assert len(alt_name2.surname_list) == 0

    # gender
    assert person.gender == Person.MALE

    # TODO individual attributes (lines 265-294)

    # person events
    assert len(person.event_ref_list) == 26

    # BAPM - Baptism
    event = db.get_event_from_handle(person.event_ref_list[0].ref)
    assert isinstance(event, Event)
    assert event.get_type().value == EventType.BAPTISM

    # BAPM - Baptism
    event = db.get_event_from_handle(person.event_ref_list[1].ref)
    assert isinstance(event, Event)
    assert event.get_type().value == EventType.BAPTISM

    # BARM - Bar Mitzvah
    event = db.get_event_from_handle(person.event_ref_list[2].ref)
    assert isinstance(event, Event)
    assert event.get_type().value == EventType.BAR_MITZVAH

    # BASM - Bas Mitzvah
    event = db.get_event_from_handle(person.event_ref_list[3].ref)
    assert isinstance(event, Event)
    assert event.get_type().value == EventType.BAS_MITZVAH

    # BLES - Blessing
    event = db.get_event_from_handle(person.event_ref_list[4].ref)
    assert isinstance(event, Event)
    assert event.get_type().value == EventType.BLESS

    # BURI - Burial
    event = db.get_event_from_handle(person.event_ref_list[5].ref)
    assert isinstance(event, Event)
    assert event.get_type().value == EventType.BURIAL
    assert event.date.dateval == (30, 3, 2022, False)

    # CENS - Census
    event = db.get_event_from_handle(person.event_ref_list[6].ref)
    assert isinstance(event, Event)
    assert event.get_type().value == EventType.CENSUS

    # CHRA - Adult Christening
    event = db.get_event_from_handle(person.event_ref_list[7].ref)
    assert isinstance(event, Event)
    assert event.get_type().value == EventType.ADULT_CHRISTEN

    # CONF - Confirmation
    event = db.get_event_from_handle(person.event_ref_list[8].ref)
    assert isinstance(event, Event)
    assert event.get_type().value == EventType.CONFIRMATION

    # CREM - Cremation
    event = db.get_event_from_handle(person.event_ref_list[9].ref)
    assert isinstance(event, Event)
    assert event.get_type().value == EventType.CREMATION

    # DEAT - Death (line 315)
    event = db.get_event_from_handle(person.event_ref_list[10].ref)
    assert isinstance(event, Event)
    assert event.get_type().value == EventType.DEATH
    assert event.date.dateval == (28, 3, 2022, False)
    place = db.get_place_from_handle(event.place)
    assert isinstance(place, Place)
    assert place.name.value == "Somewhere"
    assert event.get_privacy()

    # TODO associations (lines 335-338)

    # person event notes
    assert len(event.note_list) == 2
    event_note1 = db.get_note_from_handle(event.note_list[0])
    assert isinstance(event_note1, Note)
    assert event_note1.text.string == "Note text"

    event_note2 = db.get_note_from_handle(event.note_list[1])
    assert isinstance(event_note2, Note)
    assert event_note2.gramps_id == "N1"

    # person event source citations
    assert len(event.citation_list) == 2
    event_citation1 = db.get_citation_from_handle(event.citation_list[0])
    assert isinstance(event_citation1, Citation)
    event_source1 = db.get_source_from_handle(event_citation1.source_handle)
    assert isinstance(event_source1, Source)
    assert event_source1.gramps_id == "S1"
    assert event_citation1.page == "1"
    event_citation2 = db.get_citation_from_handle(event.citation_list[1])
    assert isinstance(event_citation2, Citation)
    event_source2 = db.get_source_from_handle(event_citation2.source_handle)
    assert isinstance(event_source2, Source)
    assert event_source2.gramps_id == "S2"
    assert event_citation2.page == "2"

    # person event media
    assert len(event.media_list) == 2
    event_media1 = db.get_media_from_handle(event.media_list[0].ref)
    assert isinstance(event_media1, Media)
    event_media2 = db.get_media_from_handle(event.media_list[1].ref)
    assert isinstance(event_media2, Media)
    assert event_media1.gramps_id == "O1"
    assert event_media2.gramps_id == "O2"

    # person event UID + contact fields (DEAT event has contact fields too) + AGNC, RELI, CAUS
    assert len(event.attribute_list) == 13  # 8 contact fields + 3 event attrs + 2 UID
    # Check contact fields and UIDs
    phone_attrs = [a for a in event.attribute_list if a.get_type().string == "Phone"]
    assert len(phone_attrs) == 2
    uid_attrs = [a for a in event.attribute_list if a.get_type() == "UID"]
    assert len(uid_attrs) == 2
    uid_values = [a.get_value() for a in uid_attrs]
    assert "bbcc0025-34cb-4542-8cfb-45ba201c9c2c" in uid_values
    assert "9ead4205-5bad-4c05-91c1-0aecd3f5127d" in uid_values
    # Check AGNC, RELI, CAUS attributes
    agency_attrs = [a for a in event.attribute_list if a.get_type() == "Agency"]
    assert len(agency_attrs) == 1
    reli_attrs = [a for a in event.attribute_list if a.get_type().string == "Religion"]
    assert len(reli_attrs) == 1
    cause_attrs = [a for a in event.attribute_list if a.get_type() == "Cause"]
    assert len(cause_attrs) == 1

    # EMIG - Emigration
    event = db.get_event_from_handle(person.event_ref_list[11].ref)
    assert isinstance(event, Event)
    assert event.get_type().value == EventType.EMIGRATION

    # FCOM - First Communion
    event = db.get_event_from_handle(person.event_ref_list[12].ref)
    assert isinstance(event, Event)
    assert event.get_type().value == EventType.FIRST_COMMUN

    # GRAD - Graduation
    event = db.get_event_from_handle(person.event_ref_list[13].ref)
    assert isinstance(event, Event)
    assert event.get_type().value == EventType.GRADUATION

    # IMMI - Immigration
    event = db.get_event_from_handle(person.event_ref_list[14].ref)
    assert isinstance(event, Event)
    assert event.get_type().value == EventType.IMMIGRATION

    # NATU - Naturalization
    event = db.get_event_from_handle(person.event_ref_list[15].ref)
    assert isinstance(event, Event)
    assert event.get_type().value == EventType.NATURALIZATION

    # ORDN - Ordination
    event = db.get_event_from_handle(person.event_ref_list[16].ref)
    assert isinstance(event, Event)
    assert event.get_type().value == EventType.ORDINATION

    # PROB - Probate
    event = db.get_event_from_handle(person.event_ref_list[17].ref)
    assert isinstance(event, Event)
    assert event.get_type().value == EventType.PROBATE

    # RETI - Retirement
    event = db.get_event_from_handle(person.event_ref_list[18].ref)
    assert isinstance(event, Event)
    assert event.get_type().value == EventType.RETIREMENT

    # WILL - Will
    event = db.get_event_from_handle(person.event_ref_list[19].ref)
    assert isinstance(event, Event)
    assert event.get_type().value == EventType.WILL

    # ADOP - Adoption
    event = db.get_event_from_handle(person.event_ref_list[20].ref)
    assert isinstance(event, Event)
    assert event.get_type().value == EventType.ADOPT

    # TODO FAMC & ADOP structure of ADOP event (lines 368-371)

    # BIRTH - Birth
    event = db.get_event_from_handle(person.event_ref_list[23].ref)
    assert isinstance(event, Event)
    assert event.get_type().value == EventType.BIRTH
    assert event.date.dateval == (1, 1, 2000, False)

    # CHR - Christening
    event = db.get_event_from_handle(person.event_ref_list[24].ref)
    assert isinstance(event, Event)
    assert event.get_type().value == EventType.CHRISTEN
    assert event.date.dateval == (9, 1, 2000, False)

    # EVEN - Custom event
    event = db.get_event_from_handle(person.event_ref_list[25].ref)
    assert isinstance(event, Event)
    assert event.get_type().value == EventType.CUSTOM
    assert event.get_type().string == "Event type"

    # family relations
    assert len(person.parent_family_list) == 1
    parent_family = db.get_family_from_handle(person.parent_family_list[0])
    assert isinstance(parent_family, Family)
    assert parent_family.gramps_id == "F2"
    assert person.handle in [cref.ref for cref in parent_family.child_ref_list]

    assert len(person.family_list) == 1
    family = db.get_family_from_handle(person.family_list[0])
    assert isinstance(family, Family)
    assert family.gramps_id == "F1"
    assert family.father_handle == person.handle

    # TODO associations (lines 459-476)

    # person UIDs
    assert len(person.attribute_list) == 2
    assert person.attribute_list[0].get_type() == "UID"
    assert (
        person.attribute_list[0].get_value() == "bbcc0025-34cb-4542-8cfb-45ba201c9c2c"
    )
    assert person.attribute_list[1].get_type() == "UID"
    assert (
        person.attribute_list[1].get_value() == "9ead4205-5bad-4c05-91c1-0aecd3f5127d"
    )

    # person notes
    assert len(person.note_list) == 2
    person_note1 = db.get_note_from_handle(person.note_list[0])
    assert isinstance(person_note1, Note)
    assert person_note1.text.string == "Note text"
    person_note2 = db.get_note_from_handle(person.note_list[1])
    assert isinstance(person_note2, Note)
    assert person_note2.gramps_id == "N1"

    # peron source citations
    assert len(person.citation_list) == 2
    person_citation1 = db.get_citation_from_handle(person.citation_list[0])
    assert isinstance(person_citation1, Citation)
    person_source1 = db.get_source_from_handle(person_citation1.source_handle)
    assert isinstance(person_source1, Source)
    assert person_source1.gramps_id == "S1"
    assert person_citation1.page == "1"
    assert person_citation1.confidence == Citation.CONF_HIGH
    person_citation2 = db.get_citation_from_handle(person.citation_list[1])
    assert isinstance(person_citation2, Citation)
    person_source2 = db.get_source_from_handle(person_citation2.source_handle)
    assert isinstance(person_source2, Source)
    assert person_source2.gramps_id == "S2"

    # person media objects
    assert len(person.media_list) == 2
    person_media1 = db.get_media_from_handle(person.media_list[0].ref)
    assert isinstance(person_media1, Media)
    person_media2 = db.get_media_from_handle(person.media_list[1].ref)
    assert isinstance(person_media2, Media)
    assert person_media1.gramps_id == "O1"
    assert person_media2.gramps_id == "O2"

    # other individuals (lines 511-524)
    person = db.get_person_from_gramps_id("I2")
    assert isinstance(person, Person)

    # names
    name: Name = person.get_primary_name()
    assert name.first_name == "Maiden Name"
    assert name.type.value == NameType.CUSTOM
    assert name.type.string == "MAIDEN"

    assert len(person.alternate_names) == 2

    name: Name = person.alternate_names[0]
    assert name.first_name == "Married Name"
    assert name.type.value == NameType.CUSTOM
    assert name.type.string == "MARRIED"

    name: Name = person.alternate_names[1]
    assert name.first_name == "Professional Name"
    assert name.type.value == NameType.CUSTOM
    assert name.type.string == "PROFESSIONAL"

    assert person.gender == Person.FEMALE

    # family
    assert len(person.family_list) == 1
    family = db.get_family_from_handle(person.family_list[0])
    assert isinstance(family, Family)
    assert family.gramps_id == "F1"
    assert family.mother_handle == person.handle

    person = db.get_person_from_gramps_id("I3")
    assert isinstance(person, Person)
    assert person.gender == Person.OTHER

    person = db.get_person_from_gramps_id("I4")
    assert isinstance(person, Person)
    assert person.gender == Person.UNKNOWN
    assert len(person.parent_family_list) == 1
    parent_family = db.get_family_from_handle(person.parent_family_list[0])
    assert isinstance(parent_family, Family)
    assert parent_family.gramps_id == "F1"
    assert person.handle in [cref.ref for cref in parent_family.child_ref_list]

    # media objects
    media = db.get_media_from_gramps_id("O1")
    assert isinstance(media, Media)
    assert media.get_privacy()
    assert media.path == "/path/to/file1"
    assert media.mime == "text/plain"
    # TODO handle other files

    # media UID
    assert len(media.attribute_list) == 2
    assert media.attribute_list[0].get_type() == "UID"
    assert media.attribute_list[0].get_value() == "bbcc0025-34cb-4542-8cfb-45ba201c9c2c"
    assert media.attribute_list[1].get_type() == "UID"
    assert media.attribute_list[1].get_value() == "9ead4205-5bad-4c05-91c1-0aecd3f5127d"

    # media notes
    assert len(media.note_list) == 2
    media_note1 = db.get_note_from_handle(media.note_list[0])
    assert isinstance(media_note1, Note)
    # original text with translation appended
    assert media_note1.text.string == "American English\n\nBritish English"

    # media source citations
    assert len(media.citation_list) == 2
    media_citation1 = db.get_citation_from_handle(media.citation_list[0])
    assert isinstance(media_citation1, Citation)
    media_source1 = db.get_source_from_handle(media_citation1.source_handle)
    assert isinstance(media_source1, Source)
    assert media_source1.gramps_id == "S1"
    assert media_citation1.page == "1"
    # TODO DATA
    assert media_citation1.confidence == Citation.CONF_VERY_LOW

    # media source citation media
    assert len(media_citation1.media_list) == 2
    media_citation_media1 = db.get_media_from_handle(media_citation1.media_list[0].ref)
    assert isinstance(media_citation_media1, Media)
    media_citation_media2 = db.get_media_from_handle(media_citation1.media_list[1].ref)
    assert isinstance(media_citation_media2, Media)
    assert media_citation_media1.gramps_id == "O1"
    # TODO CROP

    # media source citation note
    assert len(media_citation1.note_list) == 2
    media_citation_note = db.get_note_from_handle(media_citation1.note_list[0])
    assert isinstance(media_citation_note, Note)
    assert media_citation_note.text.string == "American English\n\nBritish English"
    media_citation_note2 = db.get_note_from_handle(media_citation1.note_list[1])
    assert isinstance(media_citation_note2, Note)
    assert media_citation_note2.gramps_id == "N1"

    # media source citation
    media_citation2 = db.get_citation_from_handle(media.citation_list[1])
    assert isinstance(media_citation2, Citation)
    media_source2 = db.get_source_from_handle(media_citation2.source_handle)
    assert isinstance(media_source2, Source)
    assert media_source2.gramps_id == "S1"
    assert media_citation2.page == "2"

    # other media object
    media = db.get_media_from_gramps_id("O2")
    assert media.get_privacy()
    assert media.path == "http://host.example.com/path/to/file2"
    assert media.mime == "text/plain"

    # repositories
    repository = db.get_repository_from_gramps_id("R1")
    assert isinstance(repository, Repository)
    assert repository.name == "Repository 1"
    # TODO repository address
    assert len(repository.urls) == 4
    assert repository.urls[0].path == "GEDCOM@FamilySearch.org"
    assert repository.urls[0].type.value == UrlType.EMAIL
    assert repository.urls[1].path == "GEDCOM@example.com"
    assert repository.urls[1].type.value == UrlType.EMAIL
    assert repository.urls[2].path == "http://gedcom.io"
    assert repository.urls[2].type.value == UrlType.WEB_HOME
    assert repository.urls[3].path == "http://gedcom.info"
    assert repository.urls[3].type.value == UrlType.WEB_HOME

    # repository notes
    assert len(repository.note_list) == 2
    repository_note1 = db.get_note_from_handle(repository.note_list[0])
    assert isinstance(repository_note1, Note)
    assert repository_note1.text.string == "Note text"
    repository_note2 = db.get_note_from_handle(repository.note_list[1])
    assert isinstance(repository_note2, Note)
    assert repository_note2.gramps_id == "N1"

    # other repository
    repository = db.get_repository_from_gramps_id("R2")
    assert isinstance(repository, Repository)
    assert repository.name == "Repository 2"

    # shared notes
    note = db.get_note_from_gramps_id("N1")
    assert isinstance(note, Note)
    assert note.text.string == "Shared note 1\n\nShared note 1\n\nShared note 1"

    note = db.get_note_from_gramps_id("N2")
    assert isinstance(note, Note)
    assert note.text.string == "Shared note 2"

    # sources
    source = db.get_source_from_gramps_id("S1")
    assert isinstance(source, Source)
    # TODO DATA
    assert source.author == "Author"
    assert source.title == "Title"
    assert source.abbrev == "Abbreviation"
    assert source.pubinfo == "Publication info"

    # soure text as note
    assert len(source.note_list) == 3
    source_note = db.get_note_from_handle(source.note_list[0])
    assert isinstance(source_note, Note)
    assert source_note.text.string == "Source text"
    assert source_note.type.value == NoteType.SOURCE_TEXT

    assert len(source.reporef_list) == 2
    reporef1 = source.reporef_list[0]
    reporef1_repository = db.get_repository_from_handle(reporef1.ref)
    assert isinstance(reporef1_repository, Repository)
    assert reporef1_repository.gramps_id == "R1"
    assert reporef1.call_number == "Call number"
    # TODO reporef notes
    # assert len(reporef1.note_list) == 2
    # reporef1_note = db.get_note_from_handle(reporef1.note_list[0])
    # assert isinstance(reporef1_note, Note)
    # assert reporef1_note.text.string == "Note text"
    # reporef1_note2 = db.get_note_from_handle(reporef1.note_list[1])
    # assert isinstance(reporef1_note2, Note)
    # assert reporef1_note2.gramps_id == "N1"
    reporef2 = source.reporef_list[1]
    reporef2_repository = db.get_repository_from_handle(reporef2.ref)
    assert isinstance(reporef2_repository, Repository)
    assert reporef2_repository.gramps_id == "R2"
    assert reporef2.call_number == "Call number"

    source_note2 = db.get_note_from_handle(source.note_list[1])
    assert isinstance(source_note2, Note)
    assert source_note2.text.string == "Note text"

    source_note3 = db.get_note_from_handle(source.note_list[2])
    assert isinstance(source_note3, Note)
    assert source_note3.gramps_id == "N1"

    # second source
    source = db.get_source_from_gramps_id("S2")
    assert isinstance(source, Source)
    assert source.title == "Source Two"

    # TODO submitter (researcher)
