# GEDCOM 7 Contact Fields Analysis and Implementation

## Executive Summary
Contact fields (PHON, EMAIL, FAX, WWW) in GEDCOM 7 have specific placement rules that must be strictly followed. Our initial implementation incorrectly added these fields to Individual records, which violates the GEDCOM 7 specification.

## GEDCOM 7 Specification Rules

### Where Contact Fields ARE Allowed

According to the GEDCOM 7 specification and the python-gedcom7 library validation:

1. **Repository Records** (`REPO`)
   - ✅ PHON - Phone numbers
   - ✅ EMAIL - Email addresses  
   - ✅ FAX - Fax numbers
   - ✅ WWW - Website URLs

2. **Submitter Records** (`SUBM`)
   - ✅ PHON - Phone numbers
   - ✅ EMAIL - Email addresses
   - ✅ FAX - Fax numbers  
   - ✅ WWW - Website URLs

3. **Corporate Entity** (`HEAD.SOUR.CORP`)
   - ✅ PHON - Phone numbers
   - ✅ EMAIL - Email addresses
   - ✅ FAX - Fax numbers
   - ✅ WWW - Website URLs

4. **ALL Event Structures** (Individual and Family)
   - ✅ PHON - Phone numbers
   - ✅ EMAIL - Email addresses
   - ✅ FAX - Fax numbers
   - ✅ WWW - Website URLs
   
   Including but not limited to:
   - Individual Events: BIRT, DEAT, BAPM, BURI, CHR, CREM, ADOP, BAPM, BARM, BASM, etc.
   - Family Events: MARR, DIV, ANUL, ENGA, MARB, MARC, MARL, MARS, etc.
   - Custom Events: EVEN with TYPE

### Where Contact Fields are NOT Allowed

1. **Individual Records** (`INDI`)
   - ❌ CANNOT have PHON/EMAIL/FAX/WWW directly under INDI
   - Must use events or associations to store contact information

2. **Family Records** (`FAM`)  
   - ❌ CANNOT have PHON/EMAIL/FAX/WWW directly under FAM
   - Must use family events to store contact information

3. **Source Records** (`SOUR`)
   - ❌ CANNOT have PHON/EMAIL/FAX/WWW directly
   - Use REPO reference or CORP for contact info

4. **Media Objects** (`OBJE`)
   - ❌ CANNOT have PHON/EMAIL/FAX/WWW

## Implementation in Gramps

### How Gramps Stores Contact Information

1. **Repository Objects**
   - EMAIL/WWW → stored as URL objects with appropriate UrlType
   - PHON/FAX → stored in Address objects (phone field)
   - Note: FAX prefixed with "FAX: " since Gramps lacks dedicated FAX field

2. **Event Objects**
   - ALL contact fields → stored as Attributes with custom type
   - Format: "Phone: {value}", "Email: {value}", etc.
   - Reason: Events don't support URL or Address objects directly

3. **Individual Objects**
   - NO direct storage of contact fields
   - Contact info must be in events attached to the individual

## Original TODO Items Analysis

### gramps_gedcom7/event.py:47
```python
# TODO handle PHON, EMAIL, FAX, WWW, AGNC, RELI, CAUS
```
- ✅ VALID - Events CAN have these fields per GEDCOM 7
- Implementation: Store as attributes with descriptive prefixes

### gramps_gedcom7/repository.py:54
```python  
# TODO handle PHON
# TODO handle address
```
- ✅ VALID - Repositories CAN have PHON (and FAX) per GEDCOM 7
- Implementation: Store in Address objects

### gramps_gedcom7/individual.py
- ❌ NO TODO for contact fields (correctly!)
- Individual records CANNOT have contact fields directly

## Test Data Issues

### Invalid GEDCOM 7 Structure (WRONG):
```gedcom
0 @I1@ INDI
1 NAME John /Doe/
1 PHON +1-555-0125      ❌ NOT ALLOWED
1 EMAIL john@example.com ❌ NOT ALLOWED
```

### Valid GEDCOM 7 Structure (CORRECT):
```gedcom
0 @I1@ INDI
1 NAME John /Doe/
1 BIRT
2 PHON +1-555-0125      ✅ ALLOWED in events
2 EMAIL john@example.com ✅ ALLOWED in events
```

## Errors in Our Implementation

### PR #3 (feat-contact-fields branch)
1. **Added handlers to individual.py** - WRONG
   - These fields are not valid under INDI records
   - Must be removed

2. **Test data with PHON/EMAIL under INDI** - WRONG
   - Invalid GEDCOM 7 structure
   - Parser correctly rejects this

3. **Repository implementation** - CORRECT
   - Properly handles contact fields as allowed

4. **Event implementation** - MISSING
   - Should be in separate PR or added here

## Correct Implementation Plan

### 1. Repository Contact Fields (repository.py)
```python
elif child.tag == g7const.PHON:
    address = Address()
    address.set_phone(child.value)
    repository.add_address(address)
elif child.tag == g7const.FAX:
    address = Address()
    address.set_phone(f"FAX: {child.value}")
    repository.add_address(address)
# EMAIL and WWW already implemented as URLs
```

### 2. Event Contact Fields (event.py)
```python
elif child.tag == g7const.PHON:
    attr = Attribute()
    attr.set_type(AttributeType.CUSTOM)
    attr.set_value(f"Phone: {child.value}")
    event.add_attribute(attr)
# Similar for EMAIL, FAX, WWW
```

### 3. Individual Contact Fields
- DO NOT IMPLEMENT
- Not allowed per GEDCOM 7 specification

## Validation Proof

Using python-gedcom7 library:
```python
from gedcom7 import const

# Check INDI cannot have PHON
'PHON' in const.substructures['https://gedcom.io/terms/v7/record-INDI']
# Result: False

# Check MARR event can have PHON  
'PHON' in const.substructures['https://gedcom.io/terms/v7/MARR']
# Result: True

# Check REPO can have PHON
'PHON' in const.substructures['https://gedcom.io/terms/v7/record-REPO']
# Result: True
```

## Summary of Required Changes

1. **Remove from individual.py**:
   - All PHON/EMAIL/FAX/WWW handlers
   - Related imports (Address, Url, UrlType)

2. **Keep in repository.py**:
   - Add PHON/FAX handlers (EMAIL/WWW exist)

3. **Add to event.py** (separate PR):
   - PHON/EMAIL/FAX/WWW as attributes

4. **Fix test data**:
   - Remove contact fields from INDI records
   - Keep them only in REPO and event structures

5. **Update test assertions**:
   - Remove tests for individual contact fields
   - Keep repository and event tests

## References
- GEDCOM 7.0 Specification: https://gedcom.io/specifications/FamilySearchGEDCOMv7.html
- python-gedcom7 validation: const.substructures dictionary
- maximal70.ged test file showing correct placement