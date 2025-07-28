#!/usr/bin/env python
"""Simple test of GEDCOM 7 extension parsing without full GRAMPS dependencies"""

import gedcom7
import json
from pathlib import Path

def test_parse_file(filepath):
    """Test parsing a GEDCOM 7 file and check for extensions"""
    print(f"\n{'='*60}")
    print(f"Testing: {filepath}")
    print(f"{'='*60}")
    
    # Parse the GEDCOM file
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    try:
        # Parse the file
        parsed = gedcom7.parser.parse_string(content)
        print(f"✓ Successfully parsed {filepath}")
        
        # Check for HEAD record
        head = None
        for record in parsed.records:
            if hasattr(record, 'tag') and record.tag == 'HEAD':
                head = record
                break
        
        if head:
            print("\nHEAD record found")
            
            # Look for SCHMA
            for child in head.children:
                if hasattr(child, 'tag') and child.tag == 'SCHMA':
                    print("\nSCHMA found - Extensions declared:")
                    for tag_decl in child.children:
                        if hasattr(tag_decl, 'tag') and tag_decl.tag == 'TAG':
                            ext_tag = tag_decl.xref  
                            url = tag_decl.value if hasattr(tag_decl, 'value') else 'Unknown'
                            print(f"  - {ext_tag} -> {url}")
        
        # Count extension usage
        ext_counts = {}
        for record in parsed.records:
            if hasattr(record, 'tag') and record.tag.startswith('_'):
                ext_counts[record.tag] = ext_counts.get(record.tag, 0) + 1
        
        if ext_counts:
            print("\nExtension usage counts:")
            for tag, count in sorted(ext_counts.items()):
                print(f"  - {tag}: {count} times")
        
        # Sample some extension records
        print("\nSample extension records:")
        count = 0
        for record in parsed.records:
            if hasattr(record, 'tag') and record.tag.startswith('_'):
                print(f"\n{record.tag} record:")
                print(f"  Level: {record.level}")
                if hasattr(record, 'xref'):
                    print(f"  ID: {record.xref}")
                if hasattr(record, 'value'):
                    print(f"  Value: {record.value[:50]}...")
                count += 1
                if count >= 3:
                    break
                    
    except Exception as e:
        print(f"✗ Error parsing {filepath}: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Test all GEDCOM files"""
    test_dir = Path("test-files")
    
    test_files = [
        "occurrence_test.ged",
        "evidence_test.ged", 
        "tag_test.ged",
        "citation_test.ged",
        "combined_test.ged"
    ]
    
    for test_file in test_files:
        filepath = test_dir / test_file
        if filepath.exists():
            test_parse_file(filepath)
        else:
            print(f"✗ File not found: {filepath}")

if __name__ == "__main__":
    main()