"""Write the header of an exported dataset."""

from __future__ import annotations

import datetime

from gedcom7 import const as g7const
from gedcom7 import types as g7types

from .util import GEDCOM_MONTHS, add

GEDCOM_VERSION = "7.0"

# What this writer calls itself in the header, so that a reader knows what wrote
# the file it is looking at.
PRODUCT_ID = "GRAMPS_GEDCOM7"
PRODUCT_NAME = "gramps-gedcom7"


def make_header(version: str | None = None) -> g7types.GedcomStructure:
    """Build the header pseudo-structure a dataset begins with."""
    head = g7types.GedcomStructure(tag=g7const.HEAD)

    gedc = add(head, g7const.GEDC)
    add(gedc, g7const.VERS, GEDCOM_VERSION)

    source = add(head, g7const.SOUR)
    source.text = PRODUCT_ID
    add(source, g7const.NAME, PRODUCT_NAME)
    if version:
        add(source, g7const.VERS, version)

    now = datetime.datetime.now(tz=datetime.timezone.utc)
    date = add(
        head,
        g7const.DATE,
        g7types.DateExact(
            day=now.day, month=GEDCOM_MONTHS[now.month - 1], year=now.year
        ),
    )
    add(
        date,
        g7const.TIME,
        g7types.Time(hour=now.hour, minute=now.minute, second=now.second, tz="Z"),
    )
    return head
