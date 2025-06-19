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


def test_gedcom_date_value_to_gramps_date_range_full():
    """Test conversion of a GEDCOM date range with start and end to a Gramps date."""
    date_value = g7types.DateRange(
        start=g7types.Date(year=2020, month="JAN", day=1),
        end=g7types.Date(year=2023, month="DEC", day=31),
    )
    gramps_date = gedcom_date_value_to_gramps_date(date_value)

    assert gramps_date.get_modifier() == Date.MOD_RANGE
    start_day, start_month, start_year, _ = gramps_date.get_start_date()
    assert start_year == 2020
    assert start_month == 1
    assert start_day == 1
    stop_day, stop_month, stop_year, _ = gramps_date.get_stop_date()
    assert stop_year == 2023
    assert stop_month == 12
    assert stop_day == 31


def test_gedcom_date_value_to_gramps_date_range_after():
    """Test conversion of a GEDCOM date range with only start to a Gramps date."""
    date_value = g7types.DateRange(
        start=g7types.Date(year=2020, month="JAN", day=1),
        end=None,
    )
    gramps_date = gedcom_date_value_to_gramps_date(date_value)

    assert gramps_date.get_modifier() == Date.MOD_AFTER
    day, month, year, _ = gramps_date.get_start_date()
    assert year == 2020
    assert month == 1
    assert day == 1


def test_gedcom_date_value_to_gramps_date_range_before():
    """Test conversion of a GEDCOM date range with only end to a Gramps date."""
    date_value = g7types.DateRange(
        start=None,
        end=g7types.Date(year=2023, month="DEC", day=31),
    )
    gramps_date = gedcom_date_value_to_gramps_date(date_value)

    assert gramps_date.get_modifier() == Date.MOD_BEFORE
    day, month, year, _ = gramps_date.get_start_date()
    assert year == 2023
    assert month == 12
    assert day == 31


def test_gedcom_date_value_to_gramps_date_period_span():
    """Test conversion of a GEDCOM date period with from and to to a Gramps date."""
    date_value = g7types.DatePeriod(
        from_=g7types.Date(year=2020, month="JAN", day=1),
        to=g7types.Date(year=2023, month="DEC", day=31),
    )
    gramps_date = gedcom_date_value_to_gramps_date(date_value)

    assert gramps_date.get_modifier() == Date.MOD_SPAN
    start_day, start_month, start_year, _ = gramps_date.get_start_date()
    assert start_year == 2020
    assert start_month == 1
    assert start_day == 1
    stop_day, stop_month, stop_year, _ = gramps_date.get_stop_date()
    assert stop_year == 2023
    assert stop_month == 12
    assert stop_day == 31


def test_gedcom_date_value_to_gramps_date_period_from():
    """Test conversion of a GEDCOM date period with only from to a Gramps date."""
    date_value = g7types.DatePeriod(
        from_=g7types.Date(year=2020, month="JAN", day=1),
        to=None,
    )
    gramps_date = gedcom_date_value_to_gramps_date(date_value)

    assert gramps_date.get_modifier() == Date.MOD_FROM
    day, month, year, _ = gramps_date.get_start_date()
    assert year == 2020
    assert month == 1
    assert day == 1


def test_gedcom_date_value_to_gramps_date_period_to():
    """Test conversion of a GEDCOM date period with only to to a Gramps date."""
    date_value = g7types.DatePeriod(
        from_=None,
        to=g7types.Date(year=2023, month="DEC", day=31),
    )
    gramps_date = gedcom_date_value_to_gramps_date(date_value)

    assert gramps_date.get_modifier() == Date.MOD_TO
    day, month, year, _ = gramps_date.get_start_date()
    assert year == 2023
    assert month == 12
    assert day == 31


def test_gedcom_date_value_to_gramps_date_range_with_julian():
    """Test conversion of a GEDCOM date range with Julian calendar to a Gramps date."""
    date_value = g7types.DateRange(
        start=g7types.Date(year=1752, month="FEB", day=15, calendar="JULIAN"),
        end=g7types.Date(year=1752, month="MAR", day=25, calendar="JULIAN"),
    )
    gramps_date = gedcom_date_value_to_gramps_date(date_value)

    assert gramps_date.get_modifier() == Date.MOD_RANGE
    assert gramps_date.get_calendar() == Date.CAL_JULIAN
    start_day, start_month, start_year, _ = gramps_date.get_start_date()
    assert start_year == 1752
    assert start_month == 2
    assert start_day == 15
    stop_day, stop_month, stop_year, _ = gramps_date.get_stop_date()
    assert stop_year == 1752
    assert stop_month == 3
    assert stop_day == 25


def test_gedcom_date_value_to_gramps_date_period_with_julian():
    """Test conversion of a GEDCOM date period with Julian calendar to a Gramps date."""
    date_value = g7types.DatePeriod(
        from_=g7types.Date(year=1600, month="APR", day=10, calendar="JULIAN"),
        to=g7types.Date(year=1600, month="JUN", day=15, calendar="JULIAN"),
    )
    gramps_date = gedcom_date_value_to_gramps_date(date_value)

    assert gramps_date.get_modifier() == Date.MOD_SPAN
    assert gramps_date.get_calendar() == Date.CAL_JULIAN
    start_day, start_month, start_year, _ = gramps_date.get_start_date()
    assert start_year == 1600
    assert start_month == 4
    assert start_day == 10
    stop_day, stop_month, stop_year, _ = gramps_date.get_stop_date()
    assert stop_year == 1600
    assert stop_month == 6
    assert stop_day == 15


def test_gedcom_date_value_to_gramps_date_range_after_with_julian():
    """Test conversion of a GEDCOM date range with only start in Julian calendar to a Gramps date."""
    date_value = g7types.DateRange(
        start=g7types.Date(year=1700, month="SEP", day=14, calendar="JULIAN"),
        end=None,
    )
    gramps_date = gedcom_date_value_to_gramps_date(date_value)

    assert gramps_date.get_modifier() == Date.MOD_AFTER
    assert gramps_date.get_calendar() == Date.CAL_JULIAN
    day, month, year, _ = gramps_date.get_start_date()
    assert year == 1700
    assert month == 9
    assert day == 14


def test_gedcom_date_value_to_gramps_date_period_from_with_julian():
    """Test conversion of a GEDCOM date period with only from in Julian calendar to a Gramps date."""
    date_value = g7types.DatePeriod(
        from_=g7types.Date(year=1500, month="NOV", day=5, calendar="JULIAN"),
        to=None,
    )
    gramps_date = gedcom_date_value_to_gramps_date(date_value)

    assert gramps_date.get_modifier() == Date.MOD_FROM
    assert gramps_date.get_calendar() == Date.CAL_JULIAN
    day, month, year, _ = gramps_date.get_start_date()
    assert year == 1500
    assert month == 11
    assert day == 5
