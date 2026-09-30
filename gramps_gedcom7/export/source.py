"""Write Gramps sources and repositories as GEDCOM records."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gedcom7 import const as g7const
from gedcom7 import types as g7types
from gramps.gen.lib import (
    NoteType,
    Repository,
    RepositoryType,
    Source,
    SourceMediaType,
    UrlType,
)

from . import util
from .multimedia import add_media_refs
from .note import add_note, add_notes
from .util import add

if TYPE_CHECKING:
    from .exporter import ExportContext

# The inverse of the map the import reads a call number's medium with.
MEDIA_TYPE_ENUMS = {
    SourceMediaType.AUDIO: "AUDIO",
    SourceMediaType.BOOK: "BOOK",
    SourceMediaType.CARD: "CARD",
    SourceMediaType.ELECTRONIC: "ELECTRONIC",
    SourceMediaType.FICHE: "FICHE",
    SourceMediaType.FILM: "FILM",
    SourceMediaType.MAGAZINE: "MAGAZINE",
    SourceMediaType.MANUSCRIPT: "MANUSCRIPT",
    SourceMediaType.MAP: "MAP",
    SourceMediaType.NEWSPAPER: "NEWSPAPER",
    SourceMediaType.PHOTO: "PHOTO",
    SourceMediaType.TOMBSTONE: "TOMBSTONE",
    SourceMediaType.VIDEO: "VIDEO",
}

# What the import turns a repository's contact details into, and what each one
# is written back as.
URL_TAGS = {
    UrlType.EMAIL: g7const.EMAIL,
    UrlType.WEB_HOME: g7const.WWW,
}

# The import has nowhere but an address to keep a repository's fax number, and
# marks it so that it can be told from a telephone number again.
FAX_PREFIX = "FAX: "

# A GEDCOM submitter has no counterpart in Gramps, so the import keeps one as a
# repository marked with this type and name, and these read the marks back off.
SUBMITTER_TYPE = "GEDCOM data"
SUBMITTER_PREFIX = "Submitter: "


def source_to_record(source: Source, context: ExportContext) -> g7types.GedcomStructure:
    """Write a source as a source record."""
    record = g7types.GedcomStructure(
        tag=g7const.SOUR, xref=context.xrefs.get(source.handle)
    )
    if source.get_author():
        add(record, g7const.AUTH, source.get_author())
    if source.get_title():
        add(record, g7const.TITL, source.get_title())
    if source.get_abbreviation():
        add(record, g7const.ABBR, source.get_abbreviation())
    if source.get_publication_info():
        add(record, g7const.PUBL, source.get_publication_info())

    for repo_ref in source.get_reporef_list():
        pointer = context.xrefs.get(repo_ref.ref)
        if pointer is None:
            continue
        reference = add(record, g7const.REPO, pointer=pointer)
        if repo_ref.get_call_number():
            call_number = add(reference, g7const.CALN, repo_ref.get_call_number())
            _add_medium(call_number, repo_ref.get_media_type())

    util.add_attributes(record, source, context)
    _add_source_text(record, source, context)
    add_notes(record, source, context)
    add_media_refs(record, source, context)
    util.add_change_date(record, source.change)
    return record


def _add_source_text(
    record: g7types.GedcomStructure, source: Source, context: ExportContext
) -> None:
    """Write the text a source itself carries, which the import keeps as a note."""
    for handle in source.get_note_list():
        note = context.db.get_note_from_handle(handle)
        if note is None or int(note.get_type()) != NoteType.SOURCE_TEXT:
            continue
        if context.note_backlinks.get(handle, 0) <= 1:
            add(record, g7const.TEXT).text = note.get()
            context.written_notes.add(handle)


def _add_medium(parent: g7types.GedcomStructure, media_type) -> None:
    """Say what a call number leads to, naming it where it has no enumeration."""
    if media_type is None:
        return
    if media_type.is_custom():
        if not media_type.string:
            return
        medium = add(parent, g7const.MEDI, "OTHER")
        add(medium, g7const.PHRASE, media_type.string)
        return
    enum = MEDIA_TYPE_ENUMS.get(int(media_type))
    if enum is not None:
        add(parent, g7const.MEDI, enum)


def _is_submitter(repository: Repository) -> bool:
    """Say whether this repository is a submitter the import had to park here."""
    repository_type = repository.get_type()
    return repository_type.is_custom() and repository_type.string == SUBMITTER_TYPE


def repository_to_record(
    repository: Repository, context: ExportContext
) -> g7types.GedcomStructure:
    """Write a repository as a repository record, or as the submitter it was."""
    submitter = _is_submitter(repository)
    record = g7types.GedcomStructure(
        tag=g7const.SUBM if submitter else g7const.REPO,
        xref=context.xrefs.get(repository.handle),
    )
    name = repository.get_name()
    if submitter:
        name = name.removeprefix(SUBMITTER_PREFIX)
    # The record must say what it is called, so one with no name is written with
    # an empty one rather than left without the structure.
    add(record, g7const.NAME).text = name

    for address in repository.get_address_list():
        _add_address(record, address)

    for url in repository.get_url_list():
        tag = URL_TAGS.get(int(url.get_type()))
        if tag is not None and url.get_path():
            add(record, tag, url.get_path())

    add_notes(record, repository, context)
    util.add_change_date(record, repository.change)
    return record


def _add_address(parent: g7types.GedcomStructure, address) -> None:
    """Write one of a repository's addresses, and the numbers kept with it.

    The payload carries the street alone. The specification says a reader should
    prefer it where it disagrees with the parts beneath, and the import reads the
    whole of it as the street, so putting the rest of the address there too would
    come back as a street of several lines.
    """
    parts = (
        (g7const.CITY, address.get_city()),
        (g7const.STAE, address.get_state()),
        (g7const.POST, address.get_postal_code()),
        (g7const.CTRY, address.get_country()),
    )
    if address.get_street() or any(value for _, value in parts):
        structure = add(parent, g7const.ADDR)
        structure.text = address.get_street()
        for tag, value in parts:
            if value:
                add(structure, tag, value)
    phone = address.get_phone()
    if phone.startswith(FAX_PREFIX):
        add(parent, g7const.FAX, phone[len(FAX_PREFIX) :])
    elif phone:
        add(parent, g7const.PHON, phone)
