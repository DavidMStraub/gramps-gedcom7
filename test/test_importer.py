"""Test gedcom 7 import into Gramps."""

from gramps.gen.db import DbWriteBase
from gramps.gen.db.utils import make_database
from gramps.gen.lib import (
    Attribute,
    ChildRef,
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
    PlaceName,
    RepoRef,
    Repository,
    Source,
    SrcAttribute,
    SrcAttributeType,
)
from gramps_gedcom7.importer import import_gedcom


def test_importer_minimal():
    """Test import of minimal gedcom."""
    gedcom_file = "test/data/minimal.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    assert db.get_number_of_families() == 0
    assert db.get_number_of_notes() == 0
    assert db.get_number_of_people() == 0


def test_importer_maximal70():
    """Test import of maximal (full featured) gedcom 7.0."""
    gedcom_file = "test/data/maximal70.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    assert db.get_number_of_families() == 2
    assert db.get_number_of_notes() == 11
    assert db.get_number_of_people() == 5
    assert db.get_number_of_sources() == 3
    assert db.get_number_of_repositories() == 3
    assert db.get_number_of_media() == 3
    # Events include contact fields from PR#3
    assert db.get_number_of_events() == 38

    # Families (line 86)
    families = list(db.iter_families())
    families.sort(key=lambda x: x.gramps_id)
    assert [f.gramps_id for f in families] == ["F1", "F2"]
    family: Family = families[0]
    assert family.gramps_id == "F1"
    assert family.private
    assert family.father_handle
    father = db.get_person_from_handle(family.father_handle)
    assert isinstance(father, Person)
    assert father.gramps_id == "I1"
    assert family.mother_handle
    mother = db.get_person_from_handle(family.mother_handle)
    assert isinstance(mother, Person)
    assert mother.gramps_id == "I2"
    children = [
        db.get_person_from_handle(r.ref) for r in family.get_child_ref_list()
    ]
    assert len(children) == 2
    assert children[0].gramps_id == "I4"
    # void pointer - no child in db
    assert children[1] is None
    # @VOID@ doesn't have a meaning/type, so it's just discarded
    assert len(family.get_child_ref_list()) == 1
    # family attributes
    assert len(family.attribute_list) == 2
    assert family.attribute_list[0].get_type() == "UID"
    assert (
        family.attribute_list[0].get_value() == "bbcc0025-34cb-4542-8cfb-45ba201c9c2c"
    )
    assert family.attribute_list[1].get_type() == "UID"
    assert (
        family.attribute_list[1].get_value() == "9ead4205-5bad-4c05-91c1-0aecd3f5127d"
    )
    # family events (line 96)
    assert len(family.event_ref_list) == 11
    # marriage (line 111)
    event = db.get_event_from_handle(family.event_ref_list[4].ref)
    assert isinstance(event, Event)
    assert event.get_type() == EventType.MARRIAGE
    assert event.get_date_object().get_year() == 1793
    assert event.private
    assert len(event.media_list) == 2
    marriage = event
    marriage_media1 = db.get_media_from_handle(marriage.media_list[0].ref)
    assert isinstance(marriage_media1, Media)
    marriage_media2 = db.get_media_from_handle(marriage.media_list[1].ref)
    assert isinstance(marriage_media2, Media)
    assert marriage_media1.gramps_id == "O1"
    assert marriage_media2.gramps_id == "O2"

    # event attributes: 8 contact fields (2 PHON, 2 EMAIL, 2 FAX, 2 WWW) + AGNC, RELI, CAUS + 2 UID = 13 total
    assert len(marriage.attribute_list) == 13
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
    assert event.get_type() == EventType.CUSTOM
    assert event.get_type().string == "marriage-like but not MARR"
    note = db.get_note_from_handle(event.note_list[0])
    assert isinstance(note, Note)
    assert note.type == NoteType.EVENT
    assert (
        note.text
        == "This is an event structure with an unrecognizable tag\nthat would, if the parser were less naive, be combined with the MARR.\n"
    )
    # relationship (F2)
    family = families[1]
    assert len(family.event_ref_list) == 1
    event = db.get_event_from_handle(family.event_ref_list[0].ref)
    assert isinstance(event, Event)
    assert event.get_type() == EventType.MARRIAGE
    assert event.get_date_object().get_year() == 1998
    children = [
        db.get_person_from_handle(r.ref) for r in family.get_child_ref_list()
    ]
    assert len(children) == 1
    assert children[0].gramps_id == "I1"

    # Person (line 3)
    persons = list(db.iter_people())
    persons.sort(key=lambda x: x.gramps_id)
    person: Person = persons[0]
    assert person.gramps_id == "I1"
    assert person.private
    # names (line 4)
    names = [person.primary_name] + person.alternate_names
    assert len(names) == 2
    name: Name = names[0]
    assert name.type == NameType.BIRTH
    assert name.get_nick_name() == "John"
    # name.lang is not present in 7.0 test file (no language encoding)
    assert name.get_first_name() == "Joseph"
    assert name.get_suffix() == "jr."
    assert name.get_title() == "Lt. Cmndr."
    assert name.private
    # media
    assert len(name.media_list) == 1
    name_media = db.get_media_from_handle(name.media_list[0].ref)
    assert isinstance(name_media, Media)
    assert name_media.gramps_id == "O1"
    # alternate name (line 22)
    name = names[1]
    assert name.type == NameType.MARRIED
    assert name.get_first_name() == "Joe"
    assert name.get_nick_name() == ""
    # sex (line 29)
    assert person.gender == Person.MALE
    # person attributes
    assert len(person.attribute_list) == 2
    assert person.attribute_list[0].get_type() == "UID"
    assert (
        person.attribute_list[0].get_value()
        == "bbcc0025-34cb-4542-8cfb-45ba201c9c2c"
    )
    assert person.attribute_list[1].get_type() == "UID"
    assert (
        person.attribute_list[1].get_value()
        == "9ead4205-5bad-4c05-91c1-0aecd3f5127d"
    )
    # person events (lines 30-47, 48-77, 153-164)
    assert len(person.event_ref_list) == 16
    # birth (line 30)
    event = db.get_event_from_handle(person.event_ref_list[0].ref)
    assert isinstance(event, Event)
    assert event.get_type() == EventType.BIRTH
    assert person.get_birth_ref() == person.event_ref_list[0]
    # ensure the date can be parsed
    assert event.get_date_object().get_year() == 1768
    assert event.get_date_object().get_month() == 3
    assert event.get_date_object().get_day() == 1
    assert event.get_date_object().get_text() == "1768-03-01T09:15"
    place = db.get_place_from_handle(event.place)
    assert isinstance(place, Place)
    assert place.get_name() == "place name"
    placename: PlaceName = place.get_all_names()[0]
    # ensure date can be parsed
    assert placename.get_date_object().get_year() == 1900
    # ASSO
    # TODO not yet implemented
    # OBJE
    assert len(event.media_list) == 2
    event_media1 = db.get_media_from_handle(event.media_list[0].ref)
    assert isinstance(event_media1, Media)
    event_media2 = db.get_media_from_handle(event.media_list[1].ref)
    assert isinstance(event_media2, Media)
    assert event_media1.gramps_id == "O1"
    assert event_media2.gramps_id == "O2"
    # SOUR
    # inline citations
    # TODO source notes not yet implemented
    assert len(event.citation_list) == 1
    inline_source = db.get_source_from_handle(event.source_list[0])
    assert isinstance(inline_source, Source)
    assert inline_source.title == "Source title"
    assert inline_source.abbrev == "The Abbreviation"
    assert inline_source.author == "Author"
    assert inline_source.pub_info == "Publisher"
    assert inline_source.get_note_list() == []
    inline_source_media = db.get_media_from_handle(inline_source.media_list[0].ref)
    assert isinstance(inline_source_media, Media)
    assert inline_source_media.gramps_id == "O1"
    # shared source citations
    source = db.get_source_from_handle(event.source_list[1])
    assert isinstance(source, Source)
    assert source.gramps_id == "S1"
    assert source.title == "A source"

    assert len(event.note_list) == 1
    note = db.get_note_from_handle(event.note_list[0])
    assert isinstance(note, Note)
    assert note.type == NoteType.EVENT
    # death (line 48)
    event = db.get_event_from_handle(person.event_ref_list[1].ref)
    assert isinstance(event, Event)
    assert event.get_type() == EventType.DEATH
    assert person.get_death_ref() == person.event_ref_list[1]
    # ensure the date can be parsed
    assert event.get_date_object().get_year() == 1768
    assert event.get_date_object().get_text() == "01 MAR 1768"
    place = db.get_place_from_handle(event.place)
    assert isinstance(place, Place)
    # ASSO
    # TODO not yet implemented
    assert event.private
    # OBJE
    assert len(event.media_list) == 2
    event_media1 = db.get_media_from_handle(event.media_list[0].ref)
    assert isinstance(event_media1, Media)
    event_media2 = db.get_media_from_handle(event.media_list[1].ref)
    assert isinstance(event_media2, Media)
    assert event_media1.gramps_id == "O1"
    assert event_media2.gramps_id == "O2"

    # person event attributes: 8 contact fields + AGNC, RELI, CAUS + 2 UID = 13 total
    assert len(event.attribute_list) == 13
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
    assert event.get_type() == EventType.EMIGRATION
    # IMMI - Immigration
    event = db.get_event_from_handle(person.event_ref_list[12].ref)
    assert isinstance(event, Event)
    assert event.get_type() == EventType.IMMIGRATION
    # NATU - Naturalization
    event = db.get_event_from_handle(person.event_ref_list[13].ref)
    assert isinstance(event, Event)
    assert event.get_type() == EventType.NATURALIZATION
    # PROB - Probate
    event = db.get_event_from_handle(person.event_ref_list[14].ref)
    assert isinstance(event, Event)
    assert event.get_type() == EventType.PROBATE
    # WILL - Will
    event = db.get_event_from_handle(person.event_ref_list[15].ref)
    assert isinstance(event, Event)
    assert event.get_type() == EventType.WILL

    # media and notes
    person = persons[1]
    assert person.gramps_id == "I2"
    assert len(person.media_list) == 2
    person_media1 = db.get_media_from_handle(person.media_list[0].ref)
    assert isinstance(person_media1, Media)
    assert person_media1.gramps_id == "O1"
    person_media2 = db.get_media_from_handle(person.media_list[1].ref)
    assert isinstance(person_media2, Media)
    assert person_media2.gramps_id == "O2"
    assert len(person.note_list) == 1
    person_note = db.get_note_from_handle(person.note_list[0])
    assert isinstance(person_note, Note)
    assert person_note.type == NoteType.PERSON
    assert person_note.gramps_id == "N1"
    assert person_note.text == "Test note."

    # Sources (lines 259, 264)
    sources = list(db.iter_sources())
    sources.sort(key=lambda x: x.gramps_id)
    source = sources[0]
    assert source.gramps_id == "S1"
    assert source.title == "A source"
    assert source.abbrev == "Short Source"
    assert source.author == "Author of source"
    assert source.pub_info == "Publisher of source"
    assert len(source.note_list) == 1
    source_note = db.get_note_from_handle(source.note_list[0])
    assert isinstance(source_note, Note)
    assert source_note.type == NoteType.SOURCE
    assert source_note.text == "Some note."
    assert len(source.reporef_list) == 1
    repo_ref: RepoRef = source.reporef_list[0]
    assert repo_ref.call_number == "Call number"
    assert len(repo_ref.note_list) == 1
    repo_ref_note = db.get_note_from_handle(repo_ref.note_list[0])
    assert isinstance(repo_ref_note, Note)
    assert repo_ref_note.type == NoteType.REPOREF
    assert repo_ref_note.text == "Repo reference note."
    assert len(source.media_list) == 1
    source_media = db.get_media_from_handle(source.media_list[0].ref)
    assert isinstance(source_media, Media)
    assert source_media.gramps_id == "O1"
    assert len(source.attribute_list) == 1
    source_attribute: SrcAttribute = source.attribute_list[0]
    assert source_attribute.get_type() == SrcAttributeType.CUSTOM
    assert source_attribute.get_type().string == "UID"
    assert source_attribute.get_value() == "9ead4205-5bad-4c05-91c1-0aecd3f5127d"

    source = sources[1]
    assert source.gramps_id == "S2"
    assert source.title == "Role"
    assert source.abbrev == ""
    assert source.author == ""
    assert source.pub_info == ""

    # objects (line 245)
    objes = list(db.iter_media())
    objes.sort(key=lambda x: x.gramps_id)
    assert [o.gramps_id for o in objes] == ["O1", "O2", "O3"]
    media = objes[0]
    assert media.gramps_id == "O1"
    assert media.desc == "A multimedia object"
    assert media.mime == "image/jpeg"
    assert media.path == "test.jpg"
    assert len(media.note_list) == 1
    media_note = db.get_note_from_handle(media.note_list[0])
    assert isinstance(media_note, Note)
    assert media_note.type == NoteType.MEDIA
    assert media_note.text == "Note about the multimedia object."
    # UID
    assert len(media.attribute_list) == 2
    assert media.attribute_list[0].get_type() == "UID"
    assert (
        media.attribute_list[0].get_value() == "bbcc0025-34cb-4542-8cfb-45ba201c9c2c"
    )
    assert media.attribute_list[1].get_type() == "UID"
    assert (
        media.attribute_list[1].get_value() == "9ead4205-5bad-4c05-91c1-0aecd3f5127d"
    )

    # repositories (line 275)
    repos = list(db.iter_repositories())
    repos.sort(key=lambda x: x.gramps_id)
    assert [r.gramps_id for r in repos] == ["R1", "R2", "R3"]
    repo: Repository = repos[0]
    assert repo.gramps_id == "R1"
    assert repo.name == "A repository"
    assert len(repo.note_list) == 1
    repo_note = db.get_note_from_handle(repo.note_list[0])
    assert isinstance(repo_note, Note)
    assert repo_note.type == NoteType.REPO
    assert repo_note.text == "Note about the repository."
    # UID
    # TODO not yet implemented


def test_importer_all_events():
    """Test import of all standard events."""
    gedcom_file = "test/data/all_events.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    assert db.get_number_of_families() == 1
    assert db.get_number_of_people() == 3
    assert db.get_number_of_events() == 53

    # Person events
    persons = list(db.iter_people())
    persons.sort(key=lambda x: x.gramps_id)
    person = persons[0]
    assert person.gramps_id == "I1"
    # get sorted list of event descriptions to check
    event_refs = person.get_event_ref_list()
    events = [db.get_event_from_handle(ref.ref) for ref in event_refs]
    event_types = [e.get_type() for e in events]
    event_type_strings = [e.get_type().string for e in events]
    # birth and death
    assert EventType.BIRTH in event_types
    assert EventType.DEATH in event_types
    # Adoption, Adult Christening, Bar Mitzvah, Bat Mitzvah
    assert EventType.ADULT_CHRISTEN in event_types
    assert EventType.ADOPT in event_types
    assert EventType.BAR_MITZVAH in event_types
    assert EventType.BAS_MITZVAH in event_types
    # Baptism, Burial, Census, Christening, Confirmation
    assert EventType.BAPTISM in event_types
    assert EventType.BURIAL in event_types
    assert EventType.CENSUS in event_types
    assert EventType.CHRISTEN in event_types
    assert EventType.CONFIRMATION in event_types
    # Cremation, Emigration, First Communion, Graduation, Immigration
    assert EventType.CREMATION in event_types
    assert EventType.EMIGRATION in event_types
    assert EventType.FIRST_COMMUN in event_types
    assert EventType.GRADUATION in event_types
    assert EventType.IMMIGRATION in event_types
    # Naturalization, Ordination, Probate, Retirement, Will
    assert EventType.NATURALIZATION in event_types
    assert EventType.ORDINATION in event_types
    assert EventType.PROBATE in event_types
    assert EventType.RETIREMENT in event_types
    assert EventType.WILL in event_types
    # Custom - Education, Military, Occupation, Property
    assert "Education" in event_type_strings
    assert "Emigration" in event_type_strings  # EMIG maps to EMIGRATION
    assert "Immigration" in event_type_strings  # IMMI maps to IMMIGRATION
    assert "Military Service" in event_type_strings
    assert "Naturalization" in event_type_strings  # NATU maps to NATURALIZATION
    assert "Occupation" in event_type_strings
    assert "Property" in event_type_strings
    assert "Residence" in event_type_strings

    # Family events
    families = list(db.iter_families())
    family = families[0]
    assert family.gramps_id == "F1"
    # get sorted list of event descriptions to check
    event_refs = family.get_event_ref_list()
    events = [db.get_event_from_handle(ref.ref) for ref in event_refs]
    event_types = [e.get_type() for e in events]
    event_type_strings = [e.get_type().string for e in events]
    # Annulment, Census, Divorce, Divorce Filed, Engagement
    assert EventType.ANNULMENT in event_types
    assert EventType.CENSUS in event_types
    assert EventType.DIVORCE in event_types
    assert EventType.DIV_FILING in event_types
    assert EventType.ENGAGEMENT in event_types
    # Marriage, Marriage Settlement, Marriage License, Marriage Contract
    assert EventType.MARRIAGE in event_types
    assert EventType.MARR_SETTL in event_types
    assert EventType.MARR_LIC in event_types
    assert EventType.MARR_CONTR in event_types
    # Marriage Banns
    assert EventType.MARR_BANNS in event_types

    # Custom family event
    assert "Residence" in event_type_strings


def test_importer_all_event_attributes():
    """Test import of all standard attributes on events."""
    gedcom_file = "test/data/all_event_attributes.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    assert db.get_number_of_families() == 1
    assert db.get_number_of_people() == 2
    assert db.get_number_of_events() == 2

    # Check person birth event has age attribute
    persons = list(db.iter_people())
    person = [p for p in persons if p.gramps_id == "I1"][0]
    event_refs = person.get_event_ref_list()
    events = [db.get_event_from_handle(ref.ref) for ref in event_refs]
    birth_events = [e for e in events if e.get_type() == EventType.BIRTH]
    assert len(birth_events) == 1
    birth = birth_events[0]
    # Check that the event has attributes
    attrs = birth.get_attribute_list()
    # Check age attribute
    age_attrs = [a for a in attrs if a.get_type() == "Age"]
    assert len(age_attrs) == 1
    assert age_attrs[0].get_value() == "0"

    # Check family marriage event has husband age
    families = list(db.iter_families())
    family = families[0]
    event_refs = family.get_event_ref_list()
    events = [db.get_event_from_handle(ref.ref) for ref in event_refs]
    marriage_events = [e for e in events if e.get_type() == EventType.MARRIAGE]
    assert len(marriage_events) == 1
    marriage = marriage_events[0]
    # Check that the event has attributes
    attrs = marriage.get_attribute_list()
    # Check age attributes (husband and wife ages)
    age_attrs = [a for a in attrs if a.get_type() == "Age"]
    assert len(age_attrs) == 2
    # Check that we have both ages
    ages = [a.get_value() for a in age_attrs]
    assert "25" in ages  # husband age
    assert "23" in ages  # wife age


def test_importer_indi_preferred_parent_family():
    """Test import of preferred parent relationships."""
    gedcom_file = "test/data/preferred_parent.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    assert db.get_number_of_families() == 3
    assert db.get_number_of_people() == 5

    # Get the child
    persons = list(db.iter_people())
    child = [p for p in persons if p.gramps_id == "I1"][0]

    # Check that child has 3 parent families
    parent_family_list = child.get_parent_family_handle_list()
    assert len(parent_family_list) == 3

    # The first family in the list should be the preferred (main) one (F1)
    main_family = db.get_family_from_handle(parent_family_list[0])
    assert main_family.gramps_id == "F1"

    # Check that F2 and F3 are also present in the list
    family_gramps_ids = [
        db.get_family_from_handle(h).gramps_id for h in parent_family_list
    ]
    assert "F2" in family_gramps_ids
    assert "F3" in family_gramps_ids


def test_importer_orphan_note():
    """Test orphan note support (note not linked to any record)."""
    gedcom_file = "test/data/orphan_note.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)
    assert db.get_number_of_notes() == 2

    # Get notes
    notes = list(db.iter_notes())
    notes.sort(key=lambda x: x.gramps_id)
    assert notes[0].gramps_id == "N1"
    assert notes[0].text == "This is an orphan note not linked to any record"
    assert notes[1].gramps_id == "N2"
    assert notes[1].text == "This is a note that is referenced"

    # Check that person references N2
    persons = list(db.iter_people())
    assert len(persons) == 1
    person = persons[0]
    assert len(person.note_list) == 1
    person_note = db.get_note_from_handle(person.note_list[0])
    assert person_note.gramps_id == "N2"


def test_importer_aliased_events():
    """Test that aliased event types work properly."""
    gedcom_file = "test/data/aliased_events.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)

    persons = list(db.iter_people())
    person = persons[0]

    # Get events
    event_refs = person.get_event_ref_list()
    events = [db.get_event_from_handle(ref.ref) for ref in event_refs]

    # Check that aliased event types are properly mapped
    event_types = [e.get_type() for e in events]
    assert EventType.CHRISTEN in event_types  # CHR maps to CHRISTEN
    assert EventType.BURIAL in event_types  # BURI maps to BURIAL


def test_importer_source_repository():
    """Test source-repository link with CALN."""
    gedcom_file = "test/data/source_repository.ged"
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    import_gedcom(gedcom_file, db)

    # Get source
    sources = list(db.iter_sources())
    assert len(sources) == 1
    source = sources[0]

    # Check repository reference
    assert len(source.reporef_list) == 1
    repo_ref = source.reporef_list[0]
    assert repo_ref.call_number == "CALL-123"

    # Check that repo exists
    repo = db.get_repository_from_handle(repo_ref.ref)
    assert repo.gramps_id == "R1"
    assert repo.name == "Sample Repository"