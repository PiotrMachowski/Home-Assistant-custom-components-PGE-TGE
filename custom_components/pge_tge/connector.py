"""Connector for PGE TGE integration."""

from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass
from typing import Any

import requests

from .const import DATA_URL_TEMPLATE

_LOGGER = logging.getLogger(__name__)


@dataclass
class PgeTgeHourData:
    time: datetime.datetime
    fixing1_rate: float
    fixing1_volume: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "time": self.time.isoformat(),
            "fixing1_rate": self.fixing1_rate,
            "fixing1_volume": self.fixing1_volume,
        }

    @staticmethod
    def from_dict(value: dict[str, Any]) -> PgeTgeHourData:
        time = datetime.datetime.fromisoformat(value.get("time"))
        fixing1_rate = value.get("fixing1_rate")
        fixing1_volume = value.get("fixing1_volume")
        return PgeTgeHourData(time, fixing1_rate, fixing1_volume)


@dataclass
class PgeTgeDayData:
    date: datetime.date
    hours: list[PgeTgeHourData]

    @staticmethod
    def from_dict(value: dict[str, Any]) -> PgeTgeDayData:
        date = datetime.datetime.fromisoformat(value.get("date")).date()
        hours = [PgeTgeHourData.from_dict(h) for h in value.get("hours")]
        return PgeTgeDayData(date, hours)

    def to_dict(self):
        return {
            "date": self.date.isoformat(),
            "hours": [h.to_dict() for h in self.hours]
        }


@dataclass
class PgeTgeData:
    data: list[PgeTgeDayData]


@dataclass
class PgeTgeException(Exception):
    msg: str


class PgeTgeConnector:

    @staticmethod
    def get_data() -> PgeTgeData:
        all_data = PgeTgeConnector._get_all_data()
        data_for_today = PgeTgeConnector.get_data_for_date(all_data, datetime.date.today())
        data_for_tomorrow = PgeTgeConnector.get_data_for_date(all_data, datetime.date.today() + datetime.timedelta(days=1))
        data = [d for d in [data_for_today, data_for_tomorrow] if d is not None]
        return PgeTgeData(data)

    @staticmethod
    def get_data_for_date(all_data: list[PgeTgeHourData], date: datetime.date) -> PgeTgeDayData | None:
        data = list(filter(lambda d: d.time.date() == date, all_data))
        return PgeTgeDayData(date, data)

    @staticmethod
    def _get_all_data() -> list[PgeTgeHourData]:
        now = datetime.datetime.now()
        timezone = now.astimezone().tzinfo
        from_date = (now - datetime.timedelta(days=1)).strftime("%Y-%m-%d+00:00:00")
        to_date = (now + datetime.timedelta(days=0)).strftime("%Y-%m-%d+23:59:59")
        url = DATA_URL_TEMPLATE.format(from_date, to_date)
        response = requests.get(url, headers={"User-Agent": ""})
        if response.status_code != 200:
            _LOGGER.error("Failed to download PGE TGE data: {}", response.status_code)
            _LOGGER.debug("PGE TGE data: {}", response.text)
            raise PgeTgeException("Failed to download PGE TGE data")
        data = []
        for hourly_entry in response.json():
            time_str = PgeTgeConnector._get_entry_by_name(hourly_entry["attributes"], "quotationDate")
            price_str = PgeTgeConnector._get_entry_by_name(hourly_entry["attributes"], "price")
            volume_str = PgeTgeConnector._get_entry_by_name(hourly_entry["attributes"], "volume")
            time = datetime.datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S+00:00").replace(tzinfo=timezone)
            price = float(price_str)
            volume = float(volume_str)
            hour_data = PgeTgeHourData(time, price, volume)
            data.append(hour_data)
        return data


    @staticmethod
    def _get_entry_by_name(entry: dict[str, str], name: str) -> str | None:
        return next(map(lambda v: v["value"], filter(lambda a: a["name"] == name, entry)), None)


if __name__ == '__main__':
    data = PgeTgeConnector.get_data()
    print(data)
