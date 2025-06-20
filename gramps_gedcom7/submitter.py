"""Handle GEDCOM submitter records and import them into the Gramps database."""

from typing import List
from gramps.gen.lib.primaryobj import BasicPrimaryObject
from gedcom7 import types as g7types

from .settings import ImportSettings


def handle_submitter(
    structure: g7types.GedcomStructure,
    xref_handle_map: dict[str, str],
    settings: ImportSettings,
) -> List[BasicPrimaryObject]:
    """Handle a submitter record and convert it to Gramps objects.

    Args:
        structure: The GEDCOM submitter structure to handle.
        xref_handle_map: A map of XREFs to Gramps handles.
        settings: Import settings.

    Returns:
        A list of Gramps objects created from the GEDCOM structure.
    """
    # TODO: Implement submitter import
    return []
