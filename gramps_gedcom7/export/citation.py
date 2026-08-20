"""Write Gramps citations as GEDCOM source citations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gedcom7 import const as g7const
from gedcom7 import types as g7types
from gramps.gen.lib import Citation

from . import util
from .note import add_notes
from .util import add

if TYPE_CHECKING:
    from .exporter import ExportContext

# The inverse of the map the import reads a quality with, so that a file read
# and written back says what it said. Gramps has one degree more than the
# specification, and its highest shares the highest of these.
CONFIDENCE_ENUMS = {
    Citation.CONF_VERY_LOW: "0",
    Citation.CONF_LOW: "1",
    Citation.CONF_NORMAL: "2",
    Citation.CONF_HIGH: "3",
    Citation.CONF_VERY_HIGH: "3",
}

# Attributes the import parks on a citation, written back where they came from.
EVENT_ATTRIBUTE = "EVEN"
EVENT_ROLE_ATTRIBUTE = "EVEN:ROLE"


def _attribute(citation: Citation, name: str) -> str | None:
    """Get the value of a citation attribute the import may have left."""
    for attribute in citation.get_attribute_list():
        attribute_type = attribute.get_type()
        if attribute_type.is_custom() and attribute_type.string == name:
            return attribute.get_value()
    return None


def add_citation(
    parent: g7types.GedcomStructure, citation: Citation, context: ExportContext
) -> g7types.GedcomStructure | None:
    """Write one citation under the structure that cites it.

    A citation is written where it is cited rather than as a record of its own,
    which is where the specification puts it. A Gramps citation cited from
    several places is therefore written several times.
    """
    if not util.allows(parent, g7const.SOUR):
        return None
    structure = add(
        parent, g7const.SOUR, pointer=context.xrefs.pointer(citation.source_handle)
    )
    if citation.get_page():
        add(structure, g7const.PAGE, citation.get_page())

    event_type = _attribute(citation, EVENT_ATTRIBUTE)
    if event_type:
        event = add(structure, g7const.EVEN, event_type)
        role = _attribute(citation, EVENT_ROLE_ATTRIBUTE)
        if role:
            add(event, g7const.ROLE, role)

    date = util.date_to_date_value(citation.get_date_object())
    if date is not None:
        data = add(structure, g7const.DATA)
        add(data, g7const.DATE, date)

    quality = CONFIDENCE_ENUMS.get(citation.get_confidence_level())
    if quality is not None:
        add(structure, g7const.QUAY, quality)

    add_notes(structure, citation, context)
    return structure


def add_citations(
    parent: g7types.GedcomStructure, obj: object, context: ExportContext
) -> None:
    """Write every citation an object cites."""
    for handle in obj.get_citation_list():  # type: ignore[attr-defined]
        citation = context.db.get_citation_from_handle(handle)
        if citation is not None:
            add_citation(parent, citation, context)
