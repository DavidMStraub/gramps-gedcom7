"""Test the GEDCOM to XML conversion."""

import gzip
import os
import tempfile

import pytest
from click.testing import CliRunner

from gramps_gedcom7.gedcom2xml import main


@pytest.fixture
def gedcom_file():
    """Return the path to a test GEDCOM file."""
    return os.path.join(os.path.dirname(__file__), "data", "maximal70.ged")


def test_gedcom2xml_to_file(gedcom_file):
    """Test conversion from GEDCOM to XML file."""
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as temp_dir:
        output_file = os.path.join(temp_dir, "output.xml")
        result = runner.invoke(main, [gedcom_file, output_file])

        assert result.exit_code == 0
        assert os.path.exists(output_file)

        with gzip.open(output_file, "rt", encoding="utf-8") as f:
            content = f.read()
            assert content.startswith('<?xml version="1.0" encoding="UTF-8"?>')
            assert "<database" in content
            assert "</database>" in content


def test_gedcom2xml_to_stdout(gedcom_file):
    """Test conversion from GEDCOM to stdout (using dash as output file)."""
    runner = CliRunner()
    result = runner.invoke(main, [gedcom_file, "-"], catch_exceptions=False)

    assert result.exit_code == 0

    # When using "-", the output is not gzipped and goes directly to stdout as text
    content = result.stdout
    assert content.startswith('<?xml version="1.0" encoding="UTF-8"?>')
    assert "<database" in content
    assert "</database>" in content
