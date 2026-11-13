"""Write Gramps media objects as GEDCOM multimedia records."""

from __future__ import annotations

import mimetypes
import re
from typing import TYPE_CHECKING

from gedcom7 import const as g7const
from gedcom7 import gedzip as g7gedzip
from gedcom7 import grammar as g7grammar
from gedcom7 import types as g7types
from gramps.gen.lib import Media

from ..gedzip import archive_name, is_url, without_file_scheme
from ..report import GrampsObject
from . import util
from .citation import add_citations
from .note import add_notes
from .util import add

if TYPE_CHECKING:
    from .exporter import ExportContext

# A file must say what kind of file it is, and a media object whose type Gramps
# does not know still has to be written as something.
DEFAULT_MEDIA_TYPE = "application/octet-stream"

# The attribute the import parks a media reference's own title in.
TITLE_ATTRIBUTE = "OBJE:TITL"


def is_media_type(value: str) -> bool:
    """Say whether a value can be written as the payload of a FORM."""
    return re.fullmatch(g7grammar.mediatype, value) is not None


def media_type(media: Media) -> str:
    """Say what kind of file this is, guessing from its name if need be.

    Gramps stores the word "unknown", translated, where it could not tell the
    type of a file, so a stored type that is not a media type counts as none.
    """
    stored = media.get_mime_type()
    if stored and is_media_type(stored):
        return stored
    guessed, _ = mimetypes.guess_type(media.get_path() or "")
    return guessed or DEFAULT_MEDIA_TYPE


def file_payload(media: Media, context: ExportContext) -> str:
    """Say where a media file is: its path, or its name in a GEDZIP archive."""
    path = media.get_path() or ""
    if context.media_file is None or not path or is_url(path):
        return path
    path = without_file_scheme(path)
    owner = GrampsObject.of(media)
    name = archive_name(path)
    try:
        payload = g7gedzip.file_path(name) if name else None
    except ValueError:
        payload = None
    if payload is None:
        context.report.add(
            str(owner), f"path {path} not relative, file left out of the archive", owner
        )
        return path
    if payload not in context.files:
        source = context.media_file(media)
        if source is None:
            context.report.add(
                str(owner), f"file {path} not found, left out of the archive", owner
            )
        context.files[payload] = source
    return payload


def media_to_record(media: Media, context: ExportContext) -> g7types.GedcomStructure:
    """Write a media object as a multimedia record."""
    record = g7types.GedcomStructure(
        tag=g7const.OBJE, xref=context.xrefs.get(media.handle)
    )
    util.add_privacy(record, media.get_privacy())
    # A multimedia record is a file and what is known about it, so the file is
    # written even when Gramps has no path for it.
    file_structure = add(record, g7const.FILE)
    file_structure.text = file_payload(media, context)
    form = media_type(media)
    stored = media.get_mime_type()
    if stored and stored != form:
        owner = GrampsObject.of(media)
        context.report.add(
            str(owner),
            f"media type {stored!r} not a media type, written as {form}",
            owner,
        )
    add(file_structure, g7const.FORM, g7types.MediaType(form))
    if media.get_description():
        add(file_structure, g7const.TITL, media.get_description())

    util.add_attributes(record, media, context)
    add_notes(record, media, context)
    add_citations(record, media, context)
    util.add_change_date(record, media.change)
    return record


def add_media_refs(
    parent: g7types.GedcomStructure, obj: object, context: ExportContext
) -> None:
    """Point at the media an object shows, with any title it gives them."""
    if not util.allows(parent, g7const.OBJE):
        return
    for media_ref in obj.get_media_list():  # type: ignore[attr-defined]
        pointer = context.xref("media", media_ref.ref)
        if pointer is None:
            continue
        reference = add(parent, g7const.OBJE, pointer=pointer)
        for attribute in media_ref.get_attribute_list():
            attribute_type = attribute.get_type()
            if attribute_type.xml_str() == TITLE_ATTRIBUTE:
                add(reference, g7const.TITL, attribute.get_value())
