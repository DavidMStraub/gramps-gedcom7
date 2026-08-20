"""Write Gramps media objects as GEDCOM multimedia records."""

from __future__ import annotations

import mimetypes
from typing import TYPE_CHECKING

from gedcom7 import const as g7const
from gedcom7 import types as g7types
from gramps.gen.lib import Media

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


def media_type(media: Media) -> str:
    """Say what kind of file this is, guessing from its name if need be."""
    if media.get_mime_type():
        return media.get_mime_type()
    guessed, _ = mimetypes.guess_type(media.get_path() or "")
    return guessed or DEFAULT_MEDIA_TYPE


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
    add(file_structure, g7const.FORM, g7types.MediaType(media_type(media)))
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
        pointer = context.xrefs.get(media_ref.ref)
        if pointer is None:
            continue
        reference = add(parent, g7const.OBJE, pointer=pointer)
        for attribute in media_ref.get_attribute_list():
            attribute_type = attribute.get_type()
            if attribute_type.is_custom() and attribute_type.string == TITLE_ATTRIBUTE:
                add(reference, g7const.TITL, attribute.get_value())
