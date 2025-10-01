from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity, ExtraStoredData
from homeassistant.helpers.template import Template
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .connector import PgeTgeData, PgeTgeHourData, PgeTgeDayData
from .const import (
    DEFAULT_NAME,
    DOMAIN,
    CONF_STATE_TEMPLATE_FIXING_1_RATE,
    CONF_STATE_TEMPLATE_FIXING_1_VOLUME,
    PARAMETER_FIXING_1_RATE,
    PARAMETER_FIXING_1_VOLUME,
)
from .update_coordinator import PgeTgeUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass
class PgeTgeEntityStoredData(ExtraStoredData):
    cache: dict[datetime.date, PgeTgeDayData] | None = None

    def as_dict(self) -> dict[str, Any]:
        if self.cache is None:
            return {
                "cache": {}
            }
        return {
            "cache": {k.isoformat(): v.to_dict() for (k, v) in self.cache.items()}
        }

    def combined_hours(self) -> list[PgeTgeHourData]:
        values = []
        for v in self.cache.values():
            values.extend(v.hours)
        values.sort(key=lambda x: x.time)
        return values

    @staticmethod
    def from_dict(data: dict[str, Any]) -> PgeTgeEntityStoredData:
        _LOGGER.debug(f"PgeTgeEntityStoredData.from_dict: {data}")
        cache = data["cache"]
        parsed = {}
        for k, v in cache.items():
            date = datetime.date.fromisoformat(k)
            value = PgeTgeDayData.from_dict(v)
            parsed[date] = value
        return PgeTgeEntityStoredData(parsed)


class PgeTgeEntity(RestoreEntity, CoordinatorEntity):

    def __init__(self, coordinator: PgeTgeUpdateCoordinator, config_entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._stored_data: PgeTgeEntityStoredData = PgeTgeEntityStoredData({})
        self._calculated_data: PgeTgeEntityStoredData = PgeTgeEntityStoredData({})
        self.fixing_1_rate_template = config_entry.options.get(CONF_STATE_TEMPLATE_FIXING_1_RATE, "")
        self.fixing_1_volume_template = config_entry.options.get(CONF_STATE_TEMPLATE_FIXING_1_VOLUME, "")

    def get_data(self) -> PgeTgeEntityStoredData | None:
        return self._calculated_data

    @property
    def name(self) -> str:
        return self.base_name()

    def base_name(self) -> str:
        return DEFAULT_NAME

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}"

    @property
    def device_info(self) -> DeviceInfo:
        return {
            "identifiers": {(DOMAIN,)},
            "name": self.base_name(),
            "configuration_url": "https://www.gkpge.pl/dla-domu/oferta/dynamiczna-energia-z-pge",
        }

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {}

    @callback
    def _handle_coordinator_update(self) -> None:
        today = datetime.date.today()
        last_data: PgeTgeData | None = self.coordinator.data
        if last_data is None:
            return
        for day_data in last_data.data:
            self._stored_data.cache[day_data.date] = day_data
        _LOGGER.debug("cleaning up: {}", self._stored_data.cache)
        keys = [*self._stored_data.cache.keys()]
        for key in keys:
            if key < today:
                self._stored_data.cache.pop(key)

        self._calculated_data = self._calculate_stored_data(self._stored_data)
        self.async_write_ha_state()

    @property
    def extra_restore_state_data(self) -> PgeTgeEntityStoredData:
        return PgeTgeEntityStoredData.from_dict(self._stored_data.as_dict())

    async def async_added_to_hass(self) -> None:
        last_extra_data = await self.async_get_last_extra_data()
        _LOGGER.debug("Restored last data: {}", last_extra_data)
        if last_extra_data is None:
            self._stored_data = PgeTgeEntityStoredData({})
        else:
            self._stored_data = PgeTgeEntityStoredData.from_dict(last_extra_data.as_dict())
        self._calculated_data = self._calculate_stored_data(self._stored_data)
        await super().async_added_to_hass()

    def _calculate_stored_data(self, data: PgeTgeEntityStoredData) -> PgeTgeEntityStoredData:
        if data.cache is None:
            return PgeTgeEntityStoredData({})
        new_data = {}
        for date, date_data in data.cache.items():
            new_data[date] = self._calculate_all_templates(date_data)
        return PgeTgeEntityStoredData(new_data)

    def _calculate_all_templates(self, data: PgeTgeDayData) -> PgeTgeDayData:
        return PgeTgeDayData(data.date, list(map(lambda h: self._calculate_templates(h), data.hours)))

    def _calculate_templates(self, data: PgeTgeHourData) -> PgeTgeHourData:
        templated_fixing1_rate = self._calculate_template(data, self.fixing_1_rate_template, data.fixing1_rate)
        templated_fixing1_volume = self._calculate_template(data, self.fixing_1_volume_template, data.fixing1_volume)
        return PgeTgeHourData(data.time, templated_fixing1_rate, templated_fixing1_volume)

    def _calculate_template(self, data: PgeTgeHourData, template: str, default: float) -> float:
        if template == "":
            return default
        now_func = lambda: data.time
        return Template(template, self.hass).async_render(
            {
                PARAMETER_FIXING_1_RATE: data.fixing1_rate,
                PARAMETER_FIXING_1_VOLUME: data.fixing1_volume,
                "now": now_func
            }
        )
