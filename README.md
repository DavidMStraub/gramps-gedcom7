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

## Usage as Gramps plugin

TODO

## Usage as command-line tool

The tool can be used to convert a GEDCOM 7 file to a Gramps XML file on the command line. The command is:

```bash
python -m gramps-gedcom7.gedcom2xml <input.ged> <output.gramps.xml>
```

Instead of an output file name, you can also specify `-` to write the output to standard output.
