# Add GEDCOM 7 Extensions Support for GRAMPS Compatibility

## Summary

This PR adds support for three GEDCOM 7 extensions that enable full compatibility with GRAMPS' advanced data model, addressing the long-standing issue of data loss when exchanging GEDCOM files with GRAMPS.

## Motivation

GRAMPS has a richer data model than standard GEDCOM supports, leading to data loss during import/export. This PR implements support for GEDCOM 7 extensions that preserve:
- Shared events (multiple people at one census/burial/etc.)
- Evidence containers (separation of sources from conclusions)
- Template-based citations (following Evidence Explained standards)
- Rich text formatting in notes

## Changes

### New Modules
- `occurrence.py` - Handles shared event records (`_OCUR`/`_OCREF`)
- `evidence.py` - Handles evidence containers (`_EVID`) 
- `citation_templates.py` - Handles citation templates (`_TMPLT`)
- `process_enhanced.py` - Enhanced processor with extension detection
- `individual_enhanced.py` - Enhanced individual handler
- `note_enhanced.py` - HTML subset to StyledText conversion

### Key Features
1. **Extension Detection**: Reads SCHMA declarations to identify registered extensions
2. **Shared Events**: Maps `_OCUR` records to GRAMPS Event objects
3. **Evidence Management**: Maps `_EVID` to GRAMPS research notes
4. **Citation Templates**: Preserves template structure in source attributes
5. **HTML Formatting**: Converts GEDCOM 7 HTML subset to GRAMPS StyledText

### Testing
- Comprehensive test suite in `test/test_extensions.py`
- Example GEDCOM files demonstrating each extension
- Tests for extension interoperability

## Example

```gedcom
# Shared census event
0 @O1@ _OCUR
1 TYPE Census
1 DATE 1850
1 _PART @I1@
2 ROLE Head

# Person references the event
0 @I1@ INDI
1 NAME John /Smith/
1 _OCREF @O1@
```

## Compatibility

- Fully backward compatible - unknown extensions are ignored
- Follows GEDCOM 7 specification for extension handling
- Maintains existing behavior for standard GEDCOM files

## Related Issues

- Addresses GRAMPS Bug [#12226](https://gramps-project.org/bugs/view.php?id=12226)
- Implements extensions from [FamilySearch/GEDCOM#663](https://github.com/FamilySearch/GEDCOM/issues/663)
- Supports extensions registered in [PR #173](https://github.com/FamilySearch/GEDCOM-registries/pull/173)

## Documentation

- See `GEDCOM7_EXTENSIONS_SUPPORT.md` for detailed documentation
- Extension specifications:
  - [gedcom-occurrences](https://github.com/glamberson/gedcom-occurrences)
  - [gedcom-evidence](https://github.com/glamberson/gedcom-evidence)
  - [gedcom-citations](https://github.com/dthaler/gedcom-citations)

## Future Work

- Add export support (currently import-only)
- Support additional extensions as they become available
- Add user configuration for extension handling

## Testing Instructions

1. Install dependencies: `pip install -r requirements-dev.txt`
2. Run tests: `pytest test/test_extensions.py`
3. Test with example files in `test/data/`

This PR represents a significant step forward in GEDCOM 7 adoption by demonstrating how extensions can solve real compatibility issues between genealogy applications.