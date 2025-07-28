"""Process GEDCOM 7 citation template extension data.

This module handles the gedcom-citations extension by Dave Thaler that provides
template-based citations following Evidence Explained standards, matching
GRAMPS' source template functionality.

Extension URI: https://github.com/dthaler/gedcom-citations
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gedcom7 import types as g7types
from gramps.gen.lib import Source, SrcAttribute, SrcAttributeType
from gramps.gen.lib.primaryobj import BasicPrimaryObject

from . import util
from .settings import ImportSettings

if TYPE_CHECKING:
    from gedcom7.types import GedcomStructure

# Extension tags
TAG_TMPLT = "_TMPLT"
TAG_FIEL = "_FIEL"
TAG_SOUR = "_SOUR"  # Under REPO
TAG_DATE = "_DATE"  # Under REPO._SOUR

# Extension URI
CITATION_TEMPLATES_URI = "https://github.com/dthaler/gedcom-citations"


def handle_source_with_template(
    structure: GedcomStructure,
    xref_handle_map: dict[str, str],
    settings: ImportSettings,
) -> tuple[Source, list[BasicPrimaryObject]]:
    """Handle a SOURCE structure that may contain citation templates.

    This enhances the standard source handling to support Dave Thaler's
    citation template extension.

    Args:
        structure: The GEDCOM structure containing the source data.
        xref_handle_map: A map of XREFs to GRAMPS handles.
        settings: Import settings.

    Returns:
        A tuple containing the GRAMPS Source object and a list of additional
        objects created during processing.
    """
    if not structure.xref:
        raise ValueError("SOUR structure must have an XREF")

    source = Source()
    source.handle = xref_handle_map.get(structure.xref, util.make_handle())
    objects = []

    # Track template information
    template_name = None
    template_fields = {}

    for child in structure.children:
        if child.tag == "TITL":
            # Source title
            assert isinstance(child.value, str), "Expected TITL value to be a string"
            source.set_title(child.value)
        
        elif child.tag == TAG_TMPLT:
            # Citation template name
            assert isinstance(child.value, str), "Expected _TMPLT value to be a string"
            template_name = child.value
            
            # Process template fields
            for tmplt_child in child.children:
                if tmplt_child.tag == TAG_FIEL:
                    field_name = tmplt_child.value
                    field_value = None
                    
                    # Get field value from TEXT substructure
                    for fiel_child in tmplt_child.children:
                        if fiel_child.tag == "TEXT" and isinstance(fiel_child.value, str):
                            field_value = fiel_child.value
                            break
                    
                    if field_name and field_value:
                        template_fields[str(field_name)] = field_value
        
        elif child.tag == "AUTH":
            # Author
            assert isinstance(child.value, str), "Expected AUTH value to be a string"
            source.set_author(child.value)
        
        elif child.tag == "PUBL":
            # Publication info
            assert isinstance(child.value, str), "Expected PUBL value to be a string"
            source.set_publication_info(child.value)
        
        elif child.tag == "ABBR":
            # Abbreviation
            assert isinstance(child.value, str), "Expected ABBR value to be a string"
            source.set_abbreviation(child.value)
        
        elif child.tag == "REPO":
            # Repository reference
            if child.pointer:
                try:
                    repo_handle = xref_handle_map[child.pointer]
                    # Create RepoRef
                    from gramps.gen.lib import RepoRef
                    repo_ref = RepoRef()
                    repo_ref.set_reference_handle(repo_handle)
                    
                    # Check for call number
                    for repo_child in child.children:
                        if repo_child.tag == "CALN" and isinstance(repo_child.value, str):
                            repo_ref.set_call_number(repo_child.value)
                    
                    source.add_repo_reference(repo_ref)
                except KeyError:
                    raise ValueError(f"Repository {child.pointer} not found")
        
        elif child.tag == "NOTE":
            # Notes
            source, note = util.add_note_to_object(child, source)
            objects.append(note)
        
        elif child.tag == "SNOTE" and child.pointer:
            # Shared notes
            try:
                note_handle = xref_handle_map[child.pointer]
                source.add_note(note_handle)
            except KeyError:
                raise ValueError(f"Shared note {child.pointer} not found")
        
        elif child.tag == "OBJE":
            # Media objects
            source = util.add_media_ref_to_object(child, source, xref_handle_map)
        
        elif child.tag == "UID":
            # Unique identifier
            util.add_uid_to_object(child, source)

    # If we have template information, store it as attributes
    if template_name:
        # Add template name as attribute
        attr = SrcAttribute()
        attr.set_type("Citation Template")
        attr.set_value(template_name)
        source.add_attribute(attr)
        
        # Add template fields as attributes
        for field_name, field_value in template_fields.items():
            attr = SrcAttribute()
            attr.set_type(f"Template Field: {field_name}")
            attr.set_value(field_value)
            source.add_attribute(attr)

    return source, objects


def format_citation_from_template(
    source: Source,
    page: str = "",
) -> str:
    """Format a citation string using template information.

    This attempts to reconstruct a formatted citation from the template
    data stored in source attributes.

    Args:
        source: The GRAMPS Source object.
        page: Optional page reference.

    Returns:
        A formatted citation string.
    """
    # Get template name and fields from attributes
    template_name = None
    template_fields = {}
    
    for attr in source.get_attribute_list():
        if attr.get_type() == "Citation Template":
            template_name = attr.get_value()
        elif attr.get_type().startswith("Template Field: "):
            field_name = attr.get_type()[16:]  # Remove "Template Field: "
            template_fields[field_name] = attr.get_value()
    
    if not template_name:
        # No template, use standard formatting
        return source.get_title() + (f", {page}" if page else "")
    
    # Format based on template type
    if template_name == "Census":
        # Example: "1850 U.S. Federal Census, Worcester County, Massachusetts"
        parts = []
        if "Year" in template_fields:
            parts.append(template_fields["Year"])
        parts.append("U.S. Federal Census")
        if "Jurisdiction" in template_fields:
            parts.append(template_fields["Jurisdiction"])
        
        citation = ", ".join(parts)
        if page:
            citation += f", {page}"
        return citation
    
    elif template_name == "Church Record":
        # Example: "St. Mary's Church, Winchester, Marriages, 1875"
        parts = []
        if "Church" in template_fields:
            parts.append(template_fields["Church"])
        if "Location" in template_fields:
            parts.append(template_fields["Location"])
        if "Record Type" in template_fields:
            parts.append(template_fields["Record Type"])
        if "Year" in template_fields:
            parts.append(template_fields["Year"])
        
        citation = ", ".join(parts)
        if page:
            citation += f", {page}"
        return citation
    
    elif template_name == "Newspaper":
        # Example: "Hampshire Chronicle, 15 May 1875, page 5"
        parts = []
        if "Paper" in template_fields:
            parts.append(template_fields["Paper"])
        if "Date" in template_fields:
            parts.append(template_fields["Date"])
        
        citation = ", ".join(parts)
        if page:
            citation += f", {page}"
        elif "Page" in template_fields:
            citation += f", page {template_fields['Page']}"
        return citation
    
    else:
        # Generic template formatting
        citation = f"{template_name}: {source.get_title()}"
        if template_fields:
            field_parts = [f"{k}: {v}" for k, v in template_fields.items()]
            citation += f" ({', '.join(field_parts)})"
        if page:
            citation += f", {page}"
        return citation


def get_template_fields(template_name: str) -> list[str]:
    """Get the expected fields for a given template.

    Args:
        template_name: The name of the citation template.

    Returns:
        A list of field names expected for this template.
    """
    # Define common templates and their fields
    templates = {
        "Census": [
            "Year",
            "Jurisdiction",
            "Enumeration District",
            "Page",
            "Line",
            "Repository",
            "Roll",
        ],
        "Church Record": [
            "Church",
            "Location",
            "Record Type",
            "Year",
            "Page",
            "Entry",
        ],
        "Civil Registration": [
            "Type",
            "Year",
            "Registry",
            "Volume",
            "Page",
            "Entry",
        ],
        "Newspaper": [
            "Paper",
            "Date",
            "Page",
            "Column",
            "Edition",
        ],
        "Online Database": [
            "Database Title",
            "Website",
            "URL",
            "Access Date",
            "Publisher",
        ],
        "Book": [
            "Author",
            "Title",
            "Publisher",
            "Place",
            "Year",
            "Page",
        ],
    }
    
    return templates.get(template_name, [])