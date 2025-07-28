# GEDCOM 7 Extensions Support for GRAMPS

This document describes the implementation of GEDCOM 7 extension support in the gramps-gedcom7 importer, enabling full compatibility with GRAMPS' advanced data model.

## Overview

This enhancement adds support for three complementary GEDCOM 7 extensions that address long-standing incompatibilities between GRAMPS and GEDCOM:

1. **gedcom-citations** (by Dave Thaler) - Template-based source citations
2. **gedcom-occurrences** (by Greg Lamberson) - Independent event records  
3. **gedcom-evidence** (by Greg Lamberson) - Evidence container support

Together, these extensions enable lossless GEDCOM 7 exchange for GRAMPS users while maintaining backward compatibility.

## Implementation Details

### Architecture

The implementation follows the existing gramps-gedcom7 architecture:
- Each extension has its own handler module
- Extension detection via SCHMA declarations
- Graceful fallback for unsupported extensions
- Full type safety with Python type hints

### New Modules

1. **occurrence.py** - Handles `_OCUR` occurrence records and `_OCREF` references
2. **evidence.py** - Handles `_EVID` evidence containers
3. **citation_templates.py** - Handles `_TMPLT` citation templates
4. **process_enhanced.py** - Enhanced processor with extension support
5. **individual_enhanced.py** - Enhanced individual handler for `_OCREF` and `_EVID`
6. **note_enhanced.py** - Enhanced note handler for GEDCOM 7 HTML formatting

### Key Features

#### 1. Shared Events (Occurrences)

GRAMPS treats events as first-class objects that multiple people can participate in. The occurrence extension maps perfectly:

```gedcom
0 @O1@ _OCUR              # GRAMPS Event object
1 TYPE Census
1 DATE 1850
1 PLAC Boston
1 _PART @I1@             # Participant
2 ROLE Head

0 @I1@ INDI
1 _OCREF @O1@            # EventRef in GRAMPS
2 ROLE Head
```

#### 2. Evidence Management

GRAMPS supports evidence/conclusion separation. The evidence extension provides:

```gedcom
0 @E1@ _EVID             # Evidence container
1 _FIND "John Smith, age 40"
1 SOUR @S1@

0 @I1@ INDI
1 NAME John /Smith/
2 _EVID @E1@            # Link to evidence
3 _CONF Medium          # Confidence level
```

#### 3. Citation Templates

GRAMPS uses source templates. Dave Thaler's extension provides:

```gedcom
0 @S1@ SOUR
1 _TMPLT Census         # Template type
2 _FIEL Year
3 TEXT 1850
2 _FIEL Jurisdiction
3 TEXT Massachusetts
```

#### 4. HTML Formatting

GEDCOM 7 supports HTML subset in notes. We convert to GRAMPS StyledText:

```gedcom
0 @N1@ SNOTE This is <b>bold</b> and <i>italic</i> text.
1 MIME text/html
```

### Extension Interoperability

While GEDCOM 7 doesn't allow extensions to formally modify each other, we implement informal coordination:

1. **Shared Confidence Levels**: Both evidence and occurrences use compatible confidence scales
2. **Consistent Role Types**: Occurrence roles map to GRAMPS EventRoleType
3. **Unified Citation Approach**: Evidence containers reference sources using citation templates

This demonstrates best practices for extension coordination within GEDCOM 7's constraints.

## Testing

Comprehensive tests are included in `test/test_extensions.py`:
- Occurrence creation and linking
- Evidence container mapping
- Citation template processing
- HTML formatting conversion
- Extension interoperability

## Usage

The extension support is automatic when extensions are declared in SCHMA:

```python
from gedcom7 import parse
from gramps_gedcom7.process_enhanced import process_gedcom_structures

# Parse GEDCOM file
structures = parse(gedcom_text)

# Process with extension support
process_gedcom_structures(structures, db, settings)
```

## Benefits for GRAMPS Users

1. **No More Data Loss**: Shared events, evidence, and templates preserve GRAMPS constructs
2. **Professional Genealogy**: Full support for research-based methodology
3. **Rich Text Preservation**: HTML formatting maintained in notes
4. **Backward Compatible**: Falls back gracefully for standard GEDCOM 7

## Future Enhancements

1. **Export Support**: Currently import-only; export could be added
2. **Additional Extensions**: Support for gedcom-relationships, gedcom-research-process
3. **Extension Registry**: Automatic discovery of new extensions
4. **Custom Mappings**: User-configurable extension tag mappings

## Contributing

To add support for new extensions:

1. Create a handler module following the pattern of `occurrence.py`
2. Add the extension URI to `SUPPORTED_EXTENSIONS`
3. Map extension tags in `EXTENSION_TAGS`
4. Add tests to `test_extensions.py`

## References

- [GEDCOM 7 Specification](https://gedcom.io/)
- [GRAMPS Bug #12226](https://gramps-project.org/bugs/view.php?id=12226)
- [FamilySearch/GEDCOM Issue #663](https://github.com/FamilySearch/GEDCOM/issues/663)
- Extension Repositories:
  - [gedcom-citations](https://github.com/dthaler/gedcom-citations)
  - [gedcom-occurrences](https://github.com/glamberson/gedcom-occurrences)
  - [gedcom-evidence](https://github.com/glamberson/gedcom-evidence)