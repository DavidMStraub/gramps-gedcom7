from gedcom7 import types as g7types
from gramps.gen.lib import Date

from gramps_gedcom7.util import gedcom_date_value_to_gramps_date


def test_gedcom_date_value_to_gramps_date_date():
    """Test conversion of a valid GEDCOM date to a Gramps date."""
    date_value = g7types.Date(year=2023, month="OCT", day=15, calendar="GREGORIAN")
    gramps_date = gedcom_date_value_to_gramps_date(date_value)

    assert gramps_date.get_year() == 2023
    assert gramps_date.get_month() == 10
    assert gramps_date.get_day() == 15
    assert gramps_date.get_calendar() == Date.CAL_GREGORIAN


def test_gedcom_date_value_to_gramps_date_date_approx_est():
    """Test conversion of a GEDCOM approximate date to a Gramps date."""
    date_value = g7types.DateApprox(
        date=g7types.Date(year=2023, month="OCT", day=15, calendar="GREGORIAN"),
        approx="EST",
    )
    gramps_date = gedcom_date_value_to_gramps_date(date_value)

    assert gramps_date.get_year() == 2023
    assert gramps_date.get_month() == 10
    assert gramps_date.get_day() == 15
    assert gramps_date.get_calendar() == Date.CAL_GREGORIAN
    assert gramps_date.get_quality() == Date.QUAL_ESTIMATED
    assert gramps_date.get_modifier() == Date.MOD_NONE


def test_gedcom_date_value_to_gramps_date_date_approx_cal():
    """Test conversion of a GEDCOM approximate date with calendar to a Gramps date."""
    date_value = g7types.DateApprox(
        date=g7types.Date(year=2023, month="OCT", day=15, calendar="JULIAN"),
        approx="CAL",
    )
    gramps_date = gedcom_date_value_to_gramps_date(date_value)

    assert gramps_date.get_year() == 2023
    assert gramps_date.get_month() == 10
    assert gramps_date.get_day() == 15
    assert gramps_date.get_calendar() == Date.CAL_JULIAN
    assert gramps_date.get_quality() == Date.QUAL_CALCULATED
    assert gramps_date.get_modifier() == Date.MOD_NONE


def test_gedcom_date_value_to_gramps_date_approx_abt():
    """Test conversion of a GEDCOM approximate date with 'ABT' to a Gramps date."""
    date_value = g7types.DateApprox(
        date=g7types.Date(year=2023, month="OCT", day=15, calendar="GREGORIAN"),
        approx="ABT",
    )
    gramps_date = gedcom_date_value_to_gramps_date(date_value)

    assert gramps_date.get_year() == 2023
    assert gramps_date.get_month() == 10
    assert gramps_date.get_day() == 15
    assert gramps_date.get_calendar() == Date.CAL_GREGORIAN
    assert gramps_date.get_quality() == Date.QUAL_NONE
    assert gramps_date.get_modifier() == Date.MOD_ABOUT
