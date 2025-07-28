"""Enhanced process module with GEDCOM 7 extension support.

This is a modified version of process.py that adds support for GEDCOM 7
extensions while maintaining backward compatibility.
"""

from __future__ import annotations

from typing import Any

from gedcom7 import const as g7const
from gedcom7 import types as g7types
from gramps.gen.db import DbTxn, DbWriteBase

# Import standard handlers
from .family import handle_family
from .header import handle_header
from .individual import handle_individual
from .multimedia import handle_multimedia
from .note import handle_shared_note
from .repository import handle_repository
from .settings import ImportSettings
from .source import handle_source
from .submitter import handle_submitter
from .util import make_handle

# Import extension handlers
from .citation_templates import handle_source_with_template
from .evidence import handle_evidence
from .occurrence import handle_occurrence

# Extension tags
EXTENSION_TAGS = {
    "_OCUR": handle_occurrence,
    "_EVID": handle_evidence,
}

# Extension URIs that we support
SUPPORTED_EXTENSIONS = {
    "https://github.com/glamberson/gedcom-occurrences",
    "https://github.com/glamberson/gedcom-evidence", 
    "https://github.com/dthaler/gedcom-citations",
}


def process_gedcom_structures(
    gedcom_structures: list[g7types.GedcomStructure],
    db: DbWriteBase,
    settings: ImportSettings,
):
    """Process GEDCOM structures and import them into the Gramps database.

    This enhanced version supports GEDCOM 7 extensions.

    Args:
        gedcom_structures: The GEDCOM structures to process.
        db: The Gramps database to import the GEDCOM structures into.
        settings: Import settings.
    """
    if len(gedcom_structures) < 2:
        raise ValueError("No GEDCOM structures to process.")
    
    first_structure = gedcom_structures[0]
    if first_structure.tag != g7const.HEAD:
        raise ValueError(
            f"First structure must be a HEAD structure, but got {first_structure.tag}"
        )
    
    # Note: gedcom7 library v0.4.0 doesn't include TRLR in the structures
    # So we skip this check for now
    # last_structure = gedcom_structures[-1]
    # if last_structure.tag != g7const.TRLR:
    #     raise ValueError(
    #         f"Last structure must be a TRLR structure, but got {last_structure.tag}"
    #     )

    # Process header and extract extension information
    registered_extensions = handle_header_with_extensions(
        first_structure, db, settings=settings
    )
    
    # Store registered extensions in settings for later use
    if not hasattr(settings, 'registered_extensions'):
        settings.registered_extensions = registered_extensions

    # Create a map of handles to XREFs
    xref_handle_map = {}
    for structure in gedcom_structures:
        if structure.xref and structure.xref not in xref_handle_map:
            xref_handle_map[structure.xref] = make_handle()

    # Handle the remaining structures (excluding header and trailer)
    objects = []
    for structure in gedcom_structures[1:-1]:
        result = handle_structure(
            structure, xref_handle_map=xref_handle_map, settings=settings
        )
        if result:
            objects.extend(result if isinstance(result, list) else [result])

    add_objects_to_database(objects, db)


def handle_header_with_extensions(
    structure: g7types.GedcomStructure,
    db: DbWriteBase,
    settings: ImportSettings,
) -> set[str]:
    """Handle header and extract registered extensions.

    Args:
        structure: The GEDCOM header structure.
        db: The Gramps database.
        settings: Import settings.

    Returns:
        A set of registered extension URIs.
    """
    # Call original header handler
    handle_header(structure, db, settings=settings)
    
    # Extract registered extensions from SCHMA
    registered_extensions = set()
    
    for child in structure.children:
        if child.tag == g7const.SCHMA:
            # Process schema declarations
            for schma_child in child.children:
                if schma_child.tag == "TAG":
                    # TAG structure contains extension definitions
                    tag_name = schma_child.value
                    if isinstance(tag_name, str) and tag_name.startswith("_"):
                        # This is an extension tag
                        # The URI should be in a substructure or attribute
                        for tag_child in schma_child.children:
                            if hasattr(tag_child, 'value') and isinstance(tag_child.value, str):
                                uri = tag_child.value
                                if uri in SUPPORTED_EXTENSIONS:
                                    registered_extensions.add(uri)
    
    return registered_extensions


def handle_structure(
    structure: g7types.GedcomStructure,
    xref_handle_map: dict[str, str],
    settings: ImportSettings,
) -> list | None:
    """Handle a single GEDCOM structure.

    This enhanced version checks for extension tags before falling back
    to standard handlers.

    Args:
        structure: The GEDCOM structure to handle.
        xref_handle_map: A map of XREFs to Gramps handles.
        settings: Import settings.

    Returns:
        A list of created objects or None.
    """
    # Check if this is an extension tag
    # Use original_tag if available (from our patch), otherwise check tag URI
    tag_to_check = getattr(structure, 'original_tag', structure.tag)
    if tag_to_check.startswith("_") or structure.tag.startswith("http"):
        return handle_extension_structure(
            structure, xref_handle_map=xref_handle_map, settings=settings
        )
    
    # Handle standard GEDCOM 7 tags
    if structure.tag == g7const.FAM:
        return handle_family(
            structure, xref_handle_map=xref_handle_map, settings=settings
        )
    elif structure.tag == g7const.INDI:
        return handle_individual(
            structure, xref_handle_map=xref_handle_map, settings=settings
        )
    elif structure.tag == g7const.OBJE:
        return handle_multimedia(
            structure, xref_handle_map=xref_handle_map, settings=settings
        )
    elif structure.tag == g7const.REPO:
        return handle_repository(
            structure, xref_handle_map=xref_handle_map, settings=settings
        )
    elif structure.tag == g7const.SNOTE:
        return handle_shared_note(
            structure, xref_handle_map=xref_handle_map, settings=settings
        )
    elif structure.tag == g7const.SOUR:
        # Check if source uses citation templates
        has_template = any(child.tag == "_TMPLT" for child in structure.children)
        if has_template:
            return handle_source_with_template(
                structure, xref_handle_map=xref_handle_map, settings=settings
            )
        else:
            return handle_source(
                structure, xref_handle_map=xref_handle_map, settings=settings
            )
    elif structure.tag == g7const.SUBM:
        return handle_submitter(
            structure, xref_handle_map=xref_handle_map, settings=settings
        )
    
    return None


def handle_extension_structure(
    structure: g7types.GedcomStructure,
    xref_handle_map: dict[str, str],
    settings: ImportSettings,
) -> list | None:
    """Handle a GEDCOM 7 extension structure.

    Args:
        structure: The GEDCOM extension structure to handle.
        xref_handle_map: A map of XREFs to Gramps handles.
        settings: Import settings.

    Returns:
        A list of created objects or None.
    """
    # Get the original tag name if available (from our patch)
    tag_name = getattr(structure, 'original_tag', structure.tag)
    
    # Check if we have a handler for this extension tag
    handler = EXTENSION_TAGS.get(tag_name)
    if handler:
        # Check if extension is registered (if strict mode)
        if hasattr(settings, 'strict_extensions') and settings.strict_extensions:
            if not hasattr(settings, 'registered_extensions'):
                # No extensions registered
                return None
            # For now, assume extension is registered if we support it
            # In a full implementation, we'd check the SCHMA declarations
        
        # Call the extension handler
        result = handler(
            structure, xref_handle_map=xref_handle_map, settings=settings
        )
        
        # Ensure we return a list
        if result is None:
            return None
        elif isinstance(result, tuple):
            # Handler returned (main_object, additional_objects)
            main_obj, additional = result
            return [main_obj] + additional
        elif isinstance(result, list):
            return result
        else:
            return [result]
    
    # Unknown extension tag
    if hasattr(settings, 'warn_unknown_extensions') and settings.warn_unknown_extensions:
        print(f"Warning: Unknown extension tag {structure.tag}")
    
    return None


def add_objects_to_database(objects: list[Any], db: DbWriteBase):
    """Add objects to the Gramps database.

    Args:
        objects: List of Gramps objects to add.
        db: The Gramps database.
    """
    with DbTxn("Import GEDCOM 7 with extensions", db) as transaction:
        for obj in objects:
            if obj.__class__.__name__ == "Person":
                db.add_person(obj, transaction)
            elif obj.__class__.__name__ == "Family":
                db.add_family(obj, transaction)
            elif obj.__class__.__name__ == "Event":
                db.add_event(obj, transaction)
            elif obj.__class__.__name__ == "Citation":
                db.add_citation(obj, transaction)
            elif obj.__class__.__name__ == "Source":
                db.add_source(obj, transaction)
            elif obj.__class__.__name__ == "Note":
                db.add_note(obj, transaction)
            elif obj.__class__.__name__ == "Media":
                db.add_media(obj, transaction)
            elif obj.__class__.__name__ == "Place":
                db.add_place(obj, transaction)
            elif obj.__class__.__name__ == "Repository":
                db.add_repository(obj, transaction)
            elif obj.__class__.__name__ == "Tag":
                db.add_tag(obj, transaction)