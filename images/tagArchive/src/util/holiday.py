import os
from datetime import date

from .https import HttpClient

API_KEY = os.getenv("INVERTEXTO_API_KEY")
STATE = os.getenv("INVERTEXTO_STATE")

http_client = HttpClient(
    base="https://api.invertexto.com/v1/",
    headers={ "Accept": "application/json" },
    raises_exception=True
)

_holidays_by_year = {}


def is_holiday(reference: date):
    holidays = get_holidays(reference.year)
    reference_date = reference.isoformat()

    return any(
        holiday_item.get("date") == reference_date
        and str(holiday_item.get("type", "")).lower() == "feriado"
        for holiday_item in holidays
        if isinstance(holiday_item, dict)
    )


def get_holidays(year: int):
    if year not in _holidays_by_year:
        if not API_KEY:
            raise ValueError("INVERTEXTO_API_KEY is required when holidays is set")

        params = {
            "token": API_KEY
        }

        if STATE:
            params["state"] = STATE

        res = http_client.get(
            endpoint=f"holidays/{year}",
            params=params
        )

        if not isinstance(res.data, list):
            raise ValueError(f"Unexpected Invertexto holidays response: {res.data}")

        _holidays_by_year[year] = res.data

    return _holidays_by_year[year]
