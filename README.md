# gramps-gedcom7

A GEDCOM 7 import and export library for Gramps.

## Project Status

The library provides comprehensive GEDCOM 7 import functionality. The implementation covers the vast majority of features and has been successfully tested with real-world files. While suitable for production use, users should verify results as with any conversion tool.

Export is newer than import. Every test file survives a round trip unchanged, but the researcher recorded in the database is not yet written.

## Installation

To install the library, simply run:

```bash
python -m pip install gramps-gedcom7
```

Gramps 6.0 or newer is required, but is not installed automatically. Install it with
`python -m pip install "gramps>=6.0.0"`.

## Usage as command-line tool

The tool can be used to convert a GEDCOM 7 file to a Gramps XML file on the command line. The command is:

```bash
python -m gramps_gedcom7.gedcom2xml path/to/input.ged path/to/output.gramps
```

Instead of an output file name, you can also specify `-` to write the output to standard output.

## Usage as a library

```python
from gramps.gen.db.utils import make_database
from gramps_gedcom7 import import_gedcom, export_gedcom

db = make_database("sqlite")
db.load("/path/to/grampsdb/<id>")

import_gedcom("input.ged", db)
export_gedcom(db, "output.ged")
```

`db` is a Gramps database: `DbWriteBase` to import into, `DbReadBase` to export
from.

`export_gedcom` validates the dataset before writing and raises
`gedcom7.GedcomValidationError` if it does not conform; pass `validate=False` to
write anyway.

## Usage as Gramps plugin

The tool cannot be used as a Gramps plugin yet, since its interaction with the Gedcom 5 core plugin is not clarified. See [this thread](https://github.com/gramps-project/addons-source/pull/744) for the discussion.

## Web interface

A [Streamlit](https://streamlit.io/) web interface is available for interactive use at [gramps-gedcom7.streamlit.app](https://gramps-gedcom7.streamlit.app/).

You can also run it locally:

```bash
python -m gramps_gedcom7.web
```

This opens a web browser where you can upload GEDCOM 7 files and download the converted Gramps XML files.
