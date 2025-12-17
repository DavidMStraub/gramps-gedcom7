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
        elif child.tag == g7const.REPO:
            repo_ref = RepoRef()
            try:
                repo_handle = xref_handle_map[child.pointer]
            except KeyError:
                raise ValueError(f"Repository {child.pointer} not found")
            repo_ref.ref = repo_handle
            call_number = g7util.get_first_child_with_tag(child, g7const.CALN)
            # TODO handle reporef notes
            if call_number:
                # TODO handle multiple call numbers in a single REPO
                repo_ref.set_call_number(call_number.value)
                media_type = g7util.get_first_child_with_tag(call_number, g7const.MEDI)
                if media_type:
                    assert isinstance(
                        media_type.value, str
                    ), "Expected value to be a string"

                    # Check for MEDI PHRASE substructure
                    phrase_structure = g7util.get_first_child_with_tag(
                        media_type, g7const.PHRASE
                    )

                    if phrase_structure and phrase_structure.value:
                        # Use PHRASE as custom media type
                        assert isinstance(
                            phrase_structure.value, str
                        ), "Expected PHRASE to be a string"
                        gramps_media_type = SourceMediaType(SourceMediaType.CUSTOM)
                        gramps_media_type.string = phrase_structure.value
                    else:
                        # Use enumerated MEDI value
                        gramps_source_media_type = MEDIA_TYPE_MAP.get(
                            media_type.value, SourceMediaType.CUSTOM
                        )
                        gramps_media_type = SourceMediaType(gramps_source_media_type)
                        if gramps_source_media_type == SourceMediaType.CUSTOM:
                            gramps_media_type.string = media_type.value

                    repo_ref.set_media_type(gramps_media_type)
            source.add_repo_reference(repo_ref)
        elif child.tag == g7const.SNOTE:
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
