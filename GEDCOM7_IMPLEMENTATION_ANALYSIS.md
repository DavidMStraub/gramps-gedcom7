# GEDCOM 7 Implementation Analysis for GRAMPS
## David Straub's gramps-gedcom7 Library

### Executive Summary

David Straub has created a separate Python library (`gramps-gedcom7`) for GEDCOM 7 support rather than modifying the existing GEDCOM 5.5.1 import/export code in GRAMPS. The implementation is at v0.1.0 and is "almost complete" for import functionality, with 45 TODO items remaining.

### Current Status (as of August 2025)

- **Parser Library**: python-gedcom7 v0.4.0 (mature, last updated June 2025)
- **Import Library**: gramps-gedcom7 v0.1.0 (actively developed)
- **Export**: Not yet implemented
- **Production Ready**: No - still in active development
- **Test Coverage**: Has test suite but limited test files

### Architectural Approach

#### 1. Separate Library Architecture

David created a standalone library instead of modifying existing GEDCOM code because:

**Technical Reasons:**
- GEDCOM 7 is fundamentally different from GEDCOM 5.5.1 (JSON-LD schema, URI-based extensions, etc.)
- Clean separation allows independent development and testing
- Uses modern Python patterns (dataclasses, type hints)
- Dependency on specialized `gedcom7` parser library

**Existing GEDCOM Code Issues:**
- The existing `libgedcom.py` is ~12,000 lines of monolithic code
- Deeply embedded GEDCOM 5.5.1 assumptions
- Complex regex-based parsing vs structured schema approach
- Difficult to maintain backward compatibility while adding GEDCOM 7

#### 2. Two-Phase Processing

```python
# Phase 1: Parse GEDCOM 7 structures using python-gedcom7
gedcom_structures = gedcom7.loads(file_content)

# Phase 2: Map to GRAMPS objects
process_gedcom_structures(gedcom_structures, db, settings)
```

### Tag Mapping Implementation

#### Standard Tags Mapped

**Individual Tags:**
- ✅ SEX → Person.MALE/FEMALE/UNKNOWN/OTHER
- ✅ NAME → Name/Surname objects
- ✅ 19 event types (BIRT, DEAT, MARR, etc.)
- ✅ FAMC/FAMS → Family relationships
- ✅ NOTE/SNOTE → Note objects
- ✅ SOUR → Citation objects
- ✅ OBJE → Media references
- ✅ UID → Object UIDs

**Missing/TODO Items:**
- ❌ Attributes (RESI, OCCU, etc.)
- ❌ Associations (ASSO)
- ❌ Aliases (ALIA)
- ❌ Ancestral/Descendant interest (ANCI/DESI)
- ❌ External IDs (EXID/REFN)
- ❌ Phone/Email/Address structures
- ❌ Multiple media files per object
- ❌ PHRASE qualifiers
- ❌ Repository details

### Comparison with Existing GEDCOM Import

| Aspect | Existing (5.5.1) | David's (7.0) |
|--------|------------------|---------------|
| **Architecture** | Monolithic parser | Modular with external parser |
| **Code Size** | ~12,000 lines | ~2,000 lines |
| **Parsing** | Regex-based | Schema-based |
| **Type Safety** | Limited | Full type hints |
| **Extension Support** | Custom tags only | URI-based extensions possible |
| **Maintainability** | Complex | Clean separation |
| **Testing** | Embedded | Separate test suite |

### Suitability for Export

**Pros:**
- Clean object mapping already defined
- Reversible transformations for most data
- Type-safe structure definitions

**Cons:**
- Currently one-way only (import)
- No serialization code yet
- Missing mappings for some GRAMPS features
- Would need python-gedcom7 to add serialization

### Extension Development Implications

For your extension tag mapping work:

#### 1. Extension Detection Pattern
```python
# David's current approach - ignores extensions
if structure.tag == g7const.FAM:
    handle_family(...)
# No handler for tags starting with '_'
```

#### 2. Your Minimal PR #2 Approach
```python
# Preserve unknown extensions as Notes
if structure.tag.startswith('_'):
    note = Note()
    note.set_text(f"Extension: {structure.tag}")
    return note
```

#### 3. Recommended Extension Architecture
```python
# Extension registry pattern
EXTENSION_HANDLERS = {
    '_OCUR': handle_occurrence,
    '_EVID': handle_evidence,
    '_TAG': handle_tag,
}

def handle_structure(structure, ...):
    if structure.tag.startswith('_'):
        handler = EXTENSION_HANDLERS.get(structure.tag)
        if handler:
            return handler(structure, ...)
        else:
            return preserve_as_note(structure)
```

### Key Findings

1. **Complete Rewrite Justified**: GEDCOM 7's fundamental differences justify David's separate library approach

2. **Import Nearly Complete**: Core functionality works, missing features are mostly edge cases

3. **Export Not Started**: Would require significant additional work

4. **Extension-Ready Architecture**: Clean separation makes extension support straightforward

5. **Parser Maturity**: The underlying python-gedcom7 parser (v0.4.0) appears stable and well-maintained

### Recommendations for Extension Development

1. **Build on David's Architecture**: Use his clean handler pattern for extensions

2. **Registry-Based Extensions**: Implement a registration system for extension handlers

3. **Preserve Unknown Extensions**: Your Note-based approach is good for unknown extensions

4. **Consider Two-Phase Approach**:
   - Phase 1: Preserve all extensions as Notes (your PR #2)
   - Phase 2: Add specific handlers for known extensions

5. **Export Considerations**: Extension export will require:
   - Serialization support in python-gedcom7
   - Reverse mappings from GRAMPS to GEDCOM 7
   - Extension detection in GRAMPS objects

### Next Steps

1. **For Import**: Help complete the 45 TODO items in David's code
2. **For Extensions**: Implement registry-based handler system
3. **For Export**: Consider contributing serialization to python-gedcom7
4. **For Testing**: Add more comprehensive test files, especially with extensions

### Cleanup Notes

Found duplicate repositories at:
- `/home/greg/genealogy-ai/gedcom-tags/gramps-gedcom7-test` (can be deleted)
- `/home/greg/genealogy-ai/temp-gramps-analysis/gramps-gedcom7` (can be deleted)
- `/home/greg/genealogy-ai/gramps-gedcom7` (keep this one - it's the active fork)