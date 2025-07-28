#!/usr/bin/env python3
"""Verify that our GEDCOM 7 extensions are being properly processed"""

import gedcom7
from pathlib import Path
import xml.etree.ElementTree as ET

def check_gedcom_extensions(gedcom_file):
    """Check which extensions are declared and used in a GEDCOM file"""
    print(f"\n{'='*60}")
    print(f"Checking: {gedcom_file}")
    print(f"{'='*60}")
    
    with open(gedcom_file, 'r') as f:
        data = f.read()
    
    structures = list(gedcom7.loads(data))
    
    # Find SCHMA declarations
    extensions_declared = {}
    head = structures[0]
    for child in head.children:
        if child.tag == 'SCHMA':
            for tag_decl in child.children:
                if tag_decl.tag == 'TAG':
                    ext_tag = tag_decl.xref if hasattr(tag_decl, 'xref') else tag_decl.payload[0]
                    ext_url = tag_decl.payload[0] if hasattr(tag_decl, 'payload') else tag_decl.value
                    extensions_declared[ext_tag] = ext_url
                    print(f"Declared: {ext_tag} -> {ext_url}")
    
    # Count extension usage
    extensions_used = {}
    for struct in structures:
        if struct.tag.startswith('http'):
            extensions_used[struct.tag] = extensions_used.get(struct.tag, 0) + 1
    
    print("\nExtension usage:")
    for url, count in extensions_used.items():
        print(f"  {url}: {count} times")
    
    return extensions_declared, extensions_used

def check_gramps_output(gramps_file):
    """Check if GRAMPS XML contains our extension data"""
    print(f"\nChecking GRAMPS output: {gramps_file}")
    
    if not Path(gramps_file).exists():
        print("  File not found!")
        return
    
    # Check file size
    size = Path(gramps_file).stat().st_size
    print(f"  File size: {size} bytes")
    
    # Parse compressed XML
    import gzip
    try:
        with gzip.open(gramps_file, 'rb') as f:
            tree = ET.parse(f)
            root = tree.getroot()
    except:
        # Try uncompressed
        tree = ET.parse(gramps_file)
        root = tree.getroot()
    
    # Count elements
    counts = {}
    for elem in root.iter():
        tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        counts[tag] = counts.get(tag, 0) + 1
    
    print("  Element counts:")
    for tag, count in sorted(counts.items()):
        if count > 0:
            print(f"    {tag}: {count}")
    
    # Look for extension-specific data
    # Check for events (occurrences)
    events = root.findall('.//event')
    print(f"\n  Events found: {len(events)}")
    
    # Check for notes (evidence)  
    notes = root.findall('.//note')
    print(f"  Notes found: {len(notes)}")
    
    # Check for tags
    tags = root.findall('.//tag')
    print(f"  Tags found: {len(tags)}")

def main():
    """Test all extension files"""
    test_files = [
        ("test-files/occurrence_test.ged", "test-files/occurrence_test_output.gramps"),
        ("test-files/evidence_test.ged", "test-files/evidence_test_output.gramps"),
        ("test-files/citation_test.ged", "test-files/citation_test_output.gramps"),
        ("test-files/tag_test.ged", "test-files/tag_test_output.gramps"),
        ("test-files/combined_test.ged", "test-files/combined_test_output.gramps"),
    ]
    
    for ged_file, gramps_file in test_files:
        check_gedcom_extensions(ged_file)
        check_gramps_output(gramps_file)

if __name__ == "__main__":
    main()