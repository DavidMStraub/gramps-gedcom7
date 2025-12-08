"""Tests for GEDCOM citation handling."""

import pytest
from gedcom7 import const as g7const
from gedcom7 import types as g7types
from gramps.gen.db import DbWriteBase
from gramps.gen.lib import Citation, Person, Source

from util import import_to_memory


def test_citation_even_without_role():
    """Test that EVEN tag in citation is stored as SrcAttribute."""
    # Create a person with a birth event citation that has EVEN
    sour_struct = g7types.GedcomStructure(
        tag=g7const.SOUR,
        pointer="@S1@",
        text="",
        xref="",
        children=[
            g7types.GedcomStructure(
                tag=g7const.PAGE,
                pointer="",
                text="Page 42",
                xref="",
                children=[]
            ),
            g7types.GedcomStructure(
                tag=g7const.EVEN,
                pointer="",
                text="BIRT",
                xref="",
                children=[]
            ),
        ]
    )
    
    indi = g7types.GedcomStructure(
        tag=g7const.INDI,
        pointer="",
        text="",
        xref="@I1@",
        children=[sour_struct]
    )
    
    source = g7types.GedcomStructure(
        tag=g7const.SOUR,
        pointer="",
        text="",
        xref="@S1@",
        children=[
            g7types.GedcomStructure(
                tag=g7const.TITL,
                pointer="",
                text="Birth Register",
                xref="",
                children=[]
            )
        ]
    )
    
    db: DbWriteBase = import_to_memory([indi, source])
    
    # Check citation was created with EVEN attribute
    assert db.get_number_of_citations() == 1
    citations = list(db.iter_citations())
    citation = citations[0]
    assert isinstance(citation, Citation)
    
    # Check page was set
    assert citation.get_page() == "Page 42"
    
    # Check EVEN attribute
    attrs = citation.get_attribute_list()
    assert len(attrs) == 1
    even_attr = attrs[0]
    assert even_attr.get_type() == "EVEN"
    assert even_attr.get_value() == "BIRT"


def test_citation_even_with_role():
    """Test that EVEN tag with ROLE substructure stores both as SrcAttributes."""
    # Create citation with EVEN BIRT and ROLE MOTH
    sour_struct = g7types.GedcomStructure(
        tag=g7const.SOUR,
        pointer="@S1@",
        text="",
        xref="",
        children=[
            g7types.GedcomStructure(
                tag=g7const.PAGE,
                pointer="",
                text="Page 42",
                xref="",
                children=[]
            ),
            g7types.GedcomStructure(
                tag=g7const.EVEN,
                pointer="",
                text="BIRT",
                xref="",
                children=[
                    g7types.GedcomStructure(
                        tag=g7const.ROLE,
                        pointer="",
                        text="MOTH",
                        xref="",
                        children=[]
                    )
                ]
            ),
        ]
    )
    
    indi = g7types.GedcomStructure(
        tag=g7const.INDI,
        pointer="",
        text="",
        xref="@I1@",
        children=[sour_struct]
    )
    
    source = g7types.GedcomStructure(
        tag=g7const.SOUR,
        pointer="",
        text="",
        xref="@S1@",
        children=[
            g7types.GedcomStructure(
                tag=g7const.TITL,
                pointer="",
                text="Birth Certificate",
                xref="",
                children=[]
            )
        ]
    )
    
    db: DbWriteBase = import_to_memory([indi, source])
    
    # Check citation attributes
    citations = list(db.iter_citations())
    citation = citations[0]
    
    attrs = citation.get_attribute_list()
    assert len(attrs) == 2
    
    # Check EVEN attribute
    even_attrs = [a for a in attrs if a.get_type() == "EVEN"]
    assert len(even_attrs) == 1
    assert even_attrs[0].get_value() == "BIRT"
    
    # Check ROLE attribute
    role_attrs = [a for a in attrs if a.get_type() == "EVEN:ROLE"]
    assert len(role_attrs) == 1
    assert role_attrs[0].get_value() == "MOTH"


def test_citation_even_multiple_roles():
    """Test that multiple ROLE substructures are all stored."""
    # Create citation with EVEN and multiple roles (edge case but valid)
    role1 = g7types.GedcomStructure(
        tag=g7const.ROLE,
        pointer="",
        text="WITN",
        xref="",
        children=[]
    )
    role2 = g7types.GedcomStructure(
        tag=g7const.ROLE,
        pointer="",
        text="GODP",
        xref="",
        children=[]
    )
    
    sour_struct = g7types.GedcomStructure(
        tag=g7const.SOUR,
        pointer="@S1@",
        text="",
        xref="",
        children=[
            g7types.GedcomStructure(
                tag=g7const.EVEN,
                pointer="",
                text="BAPM",
                xref="",
                children=[role1, role2]
            ),
        ]
    )
    
    indi = g7types.GedcomStructure(
        tag=g7const.INDI,
        pointer="",
        text="",
        xref="@I1@",
        children=[sour_struct]
    )
    
    source = g7types.GedcomStructure(
        tag=g7const.SOUR,
        pointer="",
        text="",
        xref="@S1@",
        children=[]
    )
    
    db: DbWriteBase = import_to_memory([indi, source])
    
    citations = list(db.iter_citations())
    citation = citations[0]
    
    attrs = citation.get_attribute_list()
    
    # Should have 1 EVEN and 2 ROLE attributes
    even_attrs = [a for a in attrs if a.get_type() == "EVEN"]
    role_attrs = [a for a in attrs if a.get_type() == "EVEN:ROLE"]
    
    assert len(even_attrs) == 1
    assert even_attrs[0].get_value() == "BAPM"
    
    assert len(role_attrs) == 2
    role_values = [a.get_value() for a in role_attrs]
    assert "WITN" in role_values
    assert "GODP" in role_values
