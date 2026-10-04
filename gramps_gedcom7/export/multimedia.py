"""Write Gramps media objects as GEDCOM multimedia records."""

from __future__ import annotations

import mimetypes
import re
from typing import TYPE_CHECKING

from gedcom7 import const as g7const
from gedcom7 import grammar as g7grammar
from gedcom7 import types as g7types
from gramps.gen.lib import Media

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


# A copy saved next to a file of the same name, e.g. "letter.pdf.1".
DUPLICATE_SUFFIX = re.compile(r"\.\d+$")


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
    path = media.get_path() or ""
    for name in (path, DUPLICATE_SUFFIX.sub("", path)):
        guessed, _ = mimetypes.guess_type(name)
        if guessed:
            return guessed
    return DEFAULT_MEDIA_TYPE


def media_to_record(media: Media, context: ExportContext) -> g7types.GedcomStructure:
    """Write a media object as a multimedia record."""
    record = g7types.GedcomStructure(
        tag=g7const.OBJE, xref=context.xrefs.get(media.handle)
    )
    util.add_privacy(record, media.get_privacy())
    # A multimedia record is a file and what is known about it, so the file is
    # written even when Gramps has no path for it.
    file_structure = add(record, g7const.FILE)
    file_structure.text = media.get_path() or ""
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
