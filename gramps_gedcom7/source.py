"""Handle GEDCOM source records and import them into the Gramps database."""

from typing import List

from gedcom7 import const as g7const
from gedcom7 import types as g7types
from gedcom7 import util as g7util
from gramps.gen.lib import (
    Note,
    NoteType,
    RepoRef,
    Source,
    SourceMediaType,
)
from gramps.gen.lib.primaryobj import BasicPrimaryObject

from . import util
from .settings import ImportSettings

MEDIA_TYPE_MAP = {
    "AUDIO": SourceMediaType.AUDIO,
    "BOOK": SourceMediaType.BOOK,
    "CARD": SourceMediaType.CARD,
    "ELECTRONIC": SourceMediaType.ELECTRONIC,
    "FICHE": SourceMediaType.FICHE,
    "FILM": SourceMediaType.FILM,
    "MAGAZINE": SourceMediaType.MAGAZINE,
    "MANUSCRIPT": SourceMediaType.MANUSCRIPT,
    "MAP": SourceMediaType.MAP,
    "NEWSPAPER": SourceMediaType.NEWSPAPER,
    "PHOTO": SourceMediaType.PHOTO,
    "TOMBSTONE": SourceMediaType.TOMBSTONE,
    "VIDEO": SourceMediaType.VIDEO,
    "OTHER": SourceMediaType.CUSTOM,
}


def handle_source(
    structure: g7types.GedcomStructure,
    xref_handle_map: dict[str, str],
    settings: ImportSettings,
) -> List[BasicPrimaryObject]:
    """Handle a source record and convert it to Gramps objects.

    Args:
        structure: The GEDCOM note structure to handle.
        xref_handle_map: A map of XREFs to Gramps handles.

    Returns:
        A list of Gramps objects created from the GEDCOM structure.
    """
    source = Source()
    objects = []
    for child in structure.children:
        # TODO handle event data
        if child.tag == g7const.TITL:
            # set source title
            if child.value is not None:
                assert isinstance(child.value, str), "Expected value to be a string"
                source.set_title(child.value)
        elif child.tag == g7const.AUTH:
            # set source author
            if child.value is not None:
                assert isinstance(child.value, str), "Expected value to be a string"
                source.set_author(child.value)
        elif child.tag == g7const.PUBL:
            # set source publisher
            if child.value is not None:
                assert isinstance(child.value, str), "Expected value to be a string"
                source.set_publication_info(child.value)
        elif child.tag == g7const.ABBR:
            # set source abbreviation
            if child.value is not None:
                assert isinstance(child.value, str), "Expected value to be a string"
                source.set_abbreviation(child.value)
        # add the note text as a source note
        elif child.tag == g7const.TEXT:
            note = Note()
            note.type = NoteType(NoteType.SOURCE_TEXT)
            if child.value is not None:
                assert isinstance(child.value, str), "Expected value to be a string"
                note.set(child.value)
            note.handle = util.make_handle()
            source.add_note(note.handle)
            objects.append(note)
        elif child.tag == g7const.REPO and child.pointer != g7const.VOIDPTR:
            repo_ref = RepoRef()
            if not child.pointer:
                raise ValueError("Repository reference without pointer")
            try:
                repo_handle = xref_handle_map[child.pointer]
            except KeyError:
                raise ValueError(f"Repository {child.pointer} not found")
            repo_ref.ref = repo_handle
            call_number = g7util.get_first_child_with_tag(child, g7const.CALN)
            if call_number:
                # A Gramps repository reference has one call number.
                repo_ref.set_call_number(call_number.value)
                media_type = g7util.get_first_child_with_tag(call_number, g7const.MEDI)
                if media_type:
                    repo_ref.set_media_type(medium_to_media_type(media_type))
            for reference_child in child.children:
                if reference_child.tag == g7const.NOTE:
                    repo_ref, note = util.add_note_to_object(reference_child, repo_ref)
                    objects.append(note)
                elif (
                    reference_child.tag == g7const.SNOTE
                    and reference_child.pointer
                    and reference_child.pointer != g7const.VOIDPTR
                ):
                    repo_ref.add_note(xref_handle_map[reference_child.pointer])
            source.add_repo_reference(repo_ref)
        elif child.tag == g7const.SNOTE and child.pointer != g7const.VOIDPTR:
            if not child.pointer:
                raise ValueError("Shared note reference without pointer")
            try:
                note_handle = xref_handle_map[child.pointer]
            except KeyError:
                raise ValueError(f"Shared note {child.pointer} not found")
            source.add_note(note_handle)
        elif child.tag == g7const.NOTE:
            source, note = util.add_note_to_object(child, source)
            objects.append(note)
        elif child.tag == g7const.OBJE:
            source = util.add_media_ref_to_object(child, source, xref_handle_map)
        elif child.tag == g7const.EXID:
            util.handle_external_id(child, source)
        elif child.tag == g7const.REFN:
            util.handle_external_id(child, source)
        elif child.tag == g7const.UID:
            util.add_uid_to_object(child, source)
    source = util.add_ids(source, structure=structure, xref_handle_map=xref_handle_map)
    util.set_change_date(structure=structure, obj=source)
    objects.append(source)
    return objects


def medium_to_media_type(structure: g7types.GedcomStructure) -> SourceMediaType:
    """Map a MEDI to a Gramps source media type, OTHER being named by its phrase."""
    assert isinstance(structure.value, str), "Expected MEDI to be a string"
    phrase = g7util.get_first_child_with_tag(structure, g7const.PHRASE)
    if phrase and phrase.value:
        assert isinstance(phrase.value, str), "Expected PHRASE to be a string"
        return SourceMediaType((SourceMediaType.CUSTOM, phrase.value))
    media_type = SourceMediaType(MEDIA_TYPE_MAP.get(structure.value, SourceMediaType.CUSTOM))
    if int(media_type) == SourceMediaType.CUSTOM:
        media_type.string = structure.value
    return media_type
