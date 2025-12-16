# gramps-gedcom7

A GEDCOM 7 import library for Gramps.

## Project Status

The project is currently in active development. The implementation of GEDCOM 7 import is almost complete. You can search for the `TODO` comments in the code to see what is still missing.

**The library is not yet ready for production use, but testing and feedback is welcome!**

## Installation

To install the library, simply run:

```bash
python -m pip install gramps-gedcom7
```

Note that this will also install Gramps with `pip`, if it is not installed in your environment yet.

## Usage as command-line tool

The tool can be used to convert a GEDCOM 7 file to a Gramps XML file on the command line. The command is:

```bash
python -m gramps_gedcom7.gedcom2xml path/to/input.ged path/to/output.gramps
```

Instead of an output file name, you can also specify `-` to write the output to standard output.

## Usage as Gramps plugin

The tool cannot be used as a Gramps plugin yet, since its interaction with the Gedcom 5 core plugin is not clarified. See [this thread](https://github.com/gramps-project/addons-source/pull/744) for the discussion.

## Web interface

A [Streamlit](https://streamlit.io/) web interface is available for interactive use at [gramps-gedcom7.streamlit.app](https://gramps-gedcom7.streamlit.app/).

You can also run it locally:

```bash
python -m gramps_gedcom7.web
```

This opens a web browser where you can upload GEDCOM 7 files and download the converted Gramps XML files.
