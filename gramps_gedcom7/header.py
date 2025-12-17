"""Handle GEDCOM header records and import them into the Gramps database."""

from gedcom7 import const as g7const
from gedcom7 import util as g7util
from gramps.gen.db import DbWriteBase
from gedcom7 import types as g7types
from .settings import ImportSettings


def handle_header(
    structure: g7types.GedcomStructure, db: DbWriteBase, settings: ImportSettings
) -> str | None:
    """Handle a header record and import it into the Gramps database.

    Args:
        structure: The GEDCOM header structure to handle.
        db: The Gramps database to import into.
        settings: Import settings.

    Returns:
        The XREF of the submitter referenced in HEAD.SUBM, or None.
    """
    # Extract HEAD.PLAC.FORM if present
    plac_struct = g7util.get_first_child_with_tag(structure, g7const.PLAC)
    if plac_struct:
        form_struct = g7util.get_first_child_with_tag(plac_struct, g7const.FORM)
        if form_struct and form_struct.value:
            assert isinstance(form_struct.value, list), "Expected FORM value to be a list"
            settings.head_plac_form = form_struct.value
    
    # Extract SUBM reference from header
    subm_struct = g7util.get_first_child_with_tag(structure, g7const.SUBM)
    if subm_struct and subm_struct.pointer:
        return subm_struct.pointer
    return None
