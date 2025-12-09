"""Handle GEDCOM submitter records and import them into the Gramps database."""

from typing import List

from gedcom7 import const as g7const
from gedcom7 import grammar as g7grammar
from gedcom7 import types as g7types
from gedcom7 import util as g7util
from gramps.gen.lib import Address, Repository, RepositoryType, Researcher, Url, UrlType
from gramps.gen.lib.primaryobj import BasicPrimaryObject

from . import util
from .settings import ImportSettings


def _parse_address_structure(addr_structure: g7types.GedcomStructure) -> dict:
    """Parse a GEDCOM ADDRESS_STRUCTURE into address field components.
    
    Per GEDCOM spec: "If the substructures and ADDR payload disagree,
    the ADDR payload shall be taken as correct."
    
    This function prefers ADDR.value for street, only uses ADR1/2/3 if ADDR is empty.
    
    Args:
        addr_structure: The ADDR structure with potential substructures.
        
    Returns:
        Dict with keys: street, city, state, postal_code, country
        All values are strings (may be empty).
    """
    result = {
        "street": "",
        "city": "",
        "state": "",
        "postal_code": "",
        "country": ""
    }
    
    # Use ADDR.value if present
    if addr_structure.value is not None:
        assert isinstance(addr_structure.value, str), "Expected value to be a string"
        result["street"] = addr_structure.value
    
    # Process substructures
    street_lines = [result["street"]] if result["street"] else []
    
    for child in addr_structure.children:
        if child.tag == g7const.ADR1:
            # Only use ADR1 if ADDR.value was empty
            if not result["street"] and child.value:
                assert isinstance(child.value, str), "Expected value to be a string"
                result["street"] = child.value
        elif child.tag in (g7const.ADR2, g7const.ADR3):
            # Append to street if ADDR.value was empty
            if not addr_structure.value and child.value and isinstance(child.value, str):
                street_lines.append(child.value)
        elif child.tag == g7const.CITY:
            if child.value:
                assert isinstance(child.value, str), "Expected value to be a string"
                result["city"] = child.value
        elif child.tag == g7const.STAE:
            if child.value:
                assert isinstance(child.value, str), "Expected value to be a string"
                result["state"] = child.value
        elif child.tag == g7const.POST:
            if child.value:
                assert isinstance(child.value, str), "Expected value to be a string"
                result["postal_code"] = child.value
        elif child.tag == g7const.CTRY:
            if child.value:
                assert isinstance(child.value, str), "Expected value to be a string"
                result["country"] = child.value
    
    # Combine street lines with newlines
    if len(street_lines) > 1:
        result["street"] = "\n".join(street_lines)
    
    return result


def submitter_to_researcher(structure: g7types.GedcomStructure) -> Researcher:
    """Convert a GEDCOM SUBMITTER_RECORD to a Gramps Researcher.

    Args:
        structure: The GEDCOM submitter structure.

    Returns:
        A Researcher object.
    """
    researcher = Researcher()

    for child in structure.children:
        if child.tag == g7const.NAME:
            if child.value is not None:
                assert isinstance(child.value, str), "Expected value to be a string"
                researcher.set_name(child.value)
        elif child.tag == g7const.ADDR:
            # Parse ADDRESS_STRUCTURE using shared helper
            addr_data = _parse_address_structure(child)
            researcher.set_street(addr_data["street"])
            researcher.set_city(addr_data["city"])
            researcher.set_state(addr_data["state"])
            researcher.set_postal_code(addr_data["postal_code"])
            researcher.set_country(addr_data["country"])
        elif child.tag == g7const.PHON:
            if child.value is not None:
                assert isinstance(child.value, str), "Expected value to be a string"
                researcher.set_phone(child.value)
        elif child.tag == g7const.EMAIL:
            if child.value is not None:
                assert isinstance(child.value, str), "Expected value to be a string"
                researcher.set_email(child.value)
        # TODO: handle FAX, WWW, LANG, notes, media

    return researcher


def handle_submitter(
    structure: g7types.GedcomStructure,
    xref_handle_map: dict[str, str],
    settings: ImportSettings,
) -> List[BasicPrimaryObject]:
    """Handle a submitter record and convert it to a Gramps Repository.

    Following libgedcom pattern, submitters are converted to Repository objects
    with type 'GEDCOM data'. The submitter referenced in HEAD will be separately
    converted to a Researcher object.

    Args:
        structure: The GEDCOM submitter structure to handle.
        xref_handle_map: A map of XREFs to Gramps handles.
        settings: Import settings.

    Returns:
        A list containing a Repository object.
    """
    repo = Repository()
    objects = []

    # Get submitter name for repository name
    name_struct = g7util.get_first_child_with_tag(structure, g7const.NAME)
    if name_struct and name_struct.value:
        repo_name = f"Submitter: {name_struct.value}"
    else:
        repo_name = f"Submitter {structure.xref or 'Unknown'}"
    repo.set_name(repo_name)

    # Set repository type to custom "GEDCOM data"
    rtype = RepositoryType()
    rtype.set((RepositoryType.CUSTOM, "GEDCOM data"))
    repo.set_type(rtype)

    # Handle address and contact information
    for child in structure.children:
        if child.tag == g7const.ADDR:
            # Parse ADDRESS_STRUCTURE using shared helper
            addr_data = _parse_address_structure(child)
            addr = Address()
            addr.set_street(addr_data["street"])
            addr.set_city(addr_data["city"])
            addr.set_state(addr_data["state"])
            addr.set_postal_code(addr_data["postal_code"])
            addr.set_country(addr_data["country"])
            repo.add_address(addr)
        elif child.tag == g7const.PHON:
            if child.value is not None:
                assert isinstance(child.value, str), "Expected value to be a string"
                url = Url()
                url.set_path(child.value)
                url.set_type(UrlType.CUSTOM)
                url.set_description("Phone")
                repo.add_url(url)
        elif child.tag == g7const.EMAIL:
            if child.value is not None:
                assert isinstance(child.value, str), "Expected value to be a string"
                url = Url()
                url.set_path(child.value)
                url.set_type(UrlType.EMAIL)
                repo.add_url(url)
        elif child.tag == g7const.FAX:
            if child.value is not None:
                assert isinstance(child.value, str), "Expected value to be a string"
                url = Url()
                url.set_path(child.value)
                url.set_type(UrlType.CUSTOM)
                url.set_description("Fax")
                repo.add_url(url)
        elif child.tag == g7const.WWW:
            if child.value is not None:
                assert isinstance(child.value, str), "Expected value to be a string"
                url = Url()
                url.set_path(child.value)
                url.set_type(UrlType.WEB_HOME)
                repo.add_url(url)
        elif child.tag == g7const.SNOTE:
            if child.pointer != g7grammar.voidptr:
                try:
                    note_handle = xref_handle_map[child.pointer]
                    repo.add_note(note_handle)
                except KeyError:
                    raise ValueError(f"Shared note {child.pointer} not found")
        elif child.tag == g7const.NOTE:
            repo, note = util.add_note_to_object(child, repo)
            objects.append(note)
        elif child.tag == g7const.OBJE:
            # Repository doesn't support media references in Gramps, skip
            pass
        elif child.tag == g7const.EXID:
            # Repository doesn't support attributes in Gramps, skip
            pass
        elif child.tag == g7const.REFN:
            # Repository doesn't support attributes in Gramps, skip
            pass
        elif child.tag == g7const.UID:
            # Repository doesn't support attributes in Gramps, skip
            pass
        # TODO: handle LANG

    repo = util.add_ids(repo, structure=structure, xref_handle_map=xref_handle_map)
    util.set_change_date(structure=structure, obj=repo)
    objects.append(repo)
    return objects
