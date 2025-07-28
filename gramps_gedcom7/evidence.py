"""Process GEDCOM 7 evidence extension data.

This module handles the gedcom-evidence extension that provides containers
for evidence and supports the separation of evidence from conclusions,
matching GRAMPS' research and evidence management capabilities.

Extension URI: https://github.com/glamberson/gedcom-evidence
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gedcom7 import types as g7types
from gramps.gen.lib import (
    Attribute,
    AttributeType,
    Note,
    NoteType,
    Person,
    Tag,
)
from gramps.gen.lib.primaryobj import BasicPrimaryObject

from . import util
from .citation import handle_citation
from .settings import ImportSettings

if TYPE_CHECKING:
    from gedcom7.types import GedcomStructure

# Extension tags
TAG_EVID = "_EVID"
TAG_FIND = "_FIND"
TAG_ID = "_ID"
TAG_CONF = "_CONF"
TAG_CONC = "_CONC"
TAG_RACT = "_RACT"
TAG_RDOC = "_RDOC"

# Extension URI
EVIDENCE_EXTENSION_URI = "https://github.com/glamberson/gedcom-evidence"

# Confidence levels
CONFIDENCE_LEVELS = {
    "Low": 1,
    "Medium": 2,
    "High": 3,
    "Hypothesis": 0,
}


def handle_evidence(
    structure: GedcomStructure,
    xref_handle_map: dict[str, str],
    settings: ImportSettings,
) -> tuple[Note, list[BasicPrimaryObject]]:
    """Convert an _EVID evidence structure to GRAMPS objects.

    Since GRAMPS doesn't have a direct evidence container type, we map
    evidence to a Note with special formatting and tags to identify it
    as evidence.

    Args:
        structure: The GEDCOM structure containing the evidence data.
        xref_handle_map: A map of XREFs to GRAMPS handles.
        settings: Import settings.

    Returns:
        A tuple containing the GRAMPS Note object representing the evidence
        and a list of additional objects created during processing.
    """
    if not structure.xref:
        raise ValueError("_EVID structure must have an XREF")

    # Create a Note to represent the evidence container
    evidence_note = Note()
    evidence_note.handle = xref_handle_map.get(structure.xref, util.make_handle())
    evidence_note.set_type(NoteType.RESEARCH)
    
    # Tag it as evidence
    evidence_tag = Tag()
    evidence_tag.set_name("Evidence")
    evidence_tag.set_color("#0000FF")  # Blue for evidence
    
    objects = [evidence_tag]
    
    # Build the evidence content
    content_parts = ["=== EVIDENCE CONTAINER ===\n"]
    
    # Track metadata
    evidence_id = None
    findings = []
    conclusions = []
    confidence = None
    research_docs = []

    for child in structure.children:
        if child.tag == TAG_ID:
            # Evidence identifier
            assert isinstance(child.value, str), "Expected _ID value to be a string"
            evidence_id = child.value
            content_parts.append(f"Evidence ID: {evidence_id}\n")
        
        elif child.tag == TAG_FIND:
            # What was found in the source
            assert isinstance(child.value, str), "Expected _FIND value to be a string"
            findings.append(child.value)
        
        elif child.tag == TAG_CONC:
            # Conclusion drawn from evidence
            for conc_child in child.children:
                if conc_child.tag == "TEXT" and isinstance(conc_child.value, str):
                    conclusions.append(conc_child.value)
                elif conc_child.tag == TAG_CONF and isinstance(conc_child.value, str):
                    confidence = conc_child.value
        
        elif child.tag == "SOUR":
            # Source citation for this evidence
            content_parts.append("\n--- SOURCE ---\n")
            citation, other_objects = handle_citation(
                child,
                xref_handle_map=xref_handle_map,
                settings=settings,
            )
            objects.extend(other_objects)
            evidence_note.add_citation(citation.handle)
            objects.append(citation)
            
            # Add source info to content
            if hasattr(citation, 'get_page'):
                page = citation.get_page()
                if page:
                    content_parts.append(f"Page: {page}\n")
        
        elif child.tag == TAG_RACT:
            # Research activity
            content_parts.append("\n--- RESEARCH ACTIVITY ---\n")
            for ract_child in child.children:
                if ract_child.tag == "DATE" and ract_child.value:
                    content_parts.append(f"Date: {ract_child.value}\n")
                elif ract_child.tag == "NOTE" and isinstance(ract_child.value, str):
                    content_parts.append(f"Activity: {ract_child.value}\n")
        
        elif child.tag == TAG_RDOC:
            # Research document reference
            if child.pointer:
                research_docs.append(child.pointer)
        
        elif child.tag == "NOTE":
            # Additional notes
            _, note = util.add_note_to_object(child, None)
            if note:
                evidence_note.add_note(note.handle)
                objects.append(note)
        
        elif child.tag == "OBJE":
            # Media objects (documents, images)
            evidence_note = util.add_media_ref_to_object(
                child, evidence_note, xref_handle_map
            )

    # Build the formatted content
    if findings:
        content_parts.append("\n--- FINDINGS ---\n")
        for i, finding in enumerate(findings, 1):
            content_parts.append(f"{i}. {finding}\n")
    
    if conclusions:
        content_parts.append("\n--- CONCLUSIONS ---\n")
        for i, conclusion in enumerate(conclusions, 1):
            content_parts.append(f"{i}. {conclusion}\n")
        if confidence:
            content_parts.append(f"Confidence: {confidence}\n")
    
    if research_docs:
        content_parts.append("\n--- RESEARCH DOCUMENTS ---\n")
        for doc in research_docs:
            content_parts.append(f"- Document: {doc}\n")

    # Set the formatted content
    evidence_note.set("".join(content_parts))
    
    # Add the evidence tag
    evidence_note.add_tag(evidence_tag.handle)

    return evidence_note, objects


def handle_evidence_reference(
    structure: GedcomStructure,
    obj,  # Any GRAMPS object that can have attributes
    xref_handle_map: dict[str, str],
    settings: ImportSettings,
) -> None:
    """Handle an _EVID reference and add it to an object.

    Args:
        structure: The GEDCOM structure containing the _EVID reference.
        obj: The GRAMPS object to add the evidence reference to.
        xref_handle_map: A map of XREFs to GRAMPS handles.
        settings: Import settings.
    """
    if not structure.pointer:
        # This is an inline evidence association, not a reference
        return

    try:
        evidence_handle = xref_handle_map[structure.pointer]
    except KeyError:
        raise ValueError(f"Evidence {structure.pointer} not found")

    # Add as a note reference
    if hasattr(obj, 'add_note'):
        obj.add_note(evidence_handle)

    # Also add an attribute to track the evidence association
    if hasattr(obj, 'add_attribute'):
        attr = Attribute()
        attr.set_type(AttributeType.CUSTOM)
        attr.set_value(f"Evidence: {structure.pointer}")
        
        # Check for confidence level
        for child in structure.children:
            if child.tag == TAG_CONF and isinstance(child.value, str):
                confidence_value = CONFIDENCE_LEVELS.get(child.value, 2)
                attr.set_value(
                    f"Evidence: {structure.pointer} (Confidence: {child.value})"
                )
                break
        
        obj.add_attribute(attr)


def create_evidence_tag(db) -> Tag:
    """Create or retrieve the Evidence tag for marking evidence notes.

    Args:
        db: The GRAMPS database.

    Returns:
        The Evidence tag.
    """
    # Check if tag already exists
    for tag_handle in db.get_tag_handles():
        tag = db.get_tag_from_handle(tag_handle)
        if tag.get_name() == "Evidence":
            return tag
    
    # Create new tag
    tag = Tag()
    tag.set_name("Evidence")
    tag.set_color("#0000FF")  # Blue
    tag.set_priority(1)
    
    return tag