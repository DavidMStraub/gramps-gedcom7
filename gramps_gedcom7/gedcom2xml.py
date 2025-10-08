"""Script to convert a GEDCOM file to a file in Gramps XML format."""

import click
import gi
from gramps_gedcom7.importer import import_gedcom
from gramps.gen.db.utils import make_database
from gramps.gen.db import DbWriteBase
from gramps.cli.user import User
from gramps.plugins.export.exportxml import export_data


gi.require_version("Gtk", "3.0")


@click.command()
@click.argument(
    "input_file", type=click.Path(exists=True, dir_okay=False, readable=True)
)
@click.argument(
    "output_file",
    type=click.Path(dir_okay=False, writable=True, resolve_path=True, allow_dash=True),
)
def main(input_file: str, output_file: str) -> None:
    """Convert a GEDCOM file to Gramps XML format.

    Args:
        input_file: Path to the input GEDCOM file.
        output_file: Path to the output XML file.
    """
    db: DbWriteBase = make_database("sqlite")
    db.load(":memory:", callback=None)
    user = User()
    import_gedcom(input_file=input_file, db=db)
    export_data(database=db, filename=output_file, user=user)


if __name__ == "__main__":
    main()
