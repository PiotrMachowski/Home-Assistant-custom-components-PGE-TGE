import datetime
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .connector import PgeTgeHourData
from .const import (
    DOMAIN,
    ATTRIBUTE_PRICES,
    ATTRIBUTE_TODAY_SUFFIX,
    ATTRIBUTE_TOMORROW_SUFFIX,
    ATTRIBUTE_PARAMETER_PRICE,
    ATTRIBUTE_PARAMETER_VOLUME,
    ATTRIBUTE_VOLUMES,
    CONF_UNIT,
    UNIT_ZL_MWH,
    UNIT_GR_KWH,
    UNIT_ZL_KWH,
    PARAMETER_FIXING_1_RATE,
    PARAMETER_FIXING_1_VOLUME,
)
from .entity import PgeTgeEntity
from .update_coordinator import PgeTgeUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    coordinator: PgeTgeUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        PgeTgeFixing1RateSensor(coordinator, entry),
        PgeTgeFixing1VolumeSensor(coordinator, entry),
    ]
    async_add_entities(entities)


class PgeTgeSensor(PgeTgeEntity, SensorEntity):
    _data_parameter_name: str
    _state_attribute_name: str
    _state_attribute_parameter_name: str

    def __init__(self, coordinator: PgeTgeUpdateCoordinator, config_entry: ConfigEntry) -> None:
        super().__init__(coordinator, config_entry)

    def get_parameter_value(self, data: PgeTgeHourData) -> float:
        value = getattr(data, self._data_parameter_name)
        if self.native_unit_of_measurement == UNIT_GR_KWH:
            value = round(value / 10, 3)
        elif self.native_unit_of_measurement == UNIT_ZL_KWH:
            value = round(value / 1000, 5)
        return value

    @property
    def native_value(self) -> float | None:
        data = self.get_data()
        if data is None:
            return None
        today = datetime.date.today()
        if today not in data.cache:
            return None
        today_data = data.cache[today]
        now_hour = datetime.datetime.now().hour
        hour_data = list(filter(lambda h: h.time.hour == now_hour, today_data.hours))
        if len(hour_data) > 0:
            return self.get_parameter_value(hour_data[0])
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        output = super().extra_state_attributes
        data = self.get_data()
        if data is not None:
            values = list(
                map(lambda d: {
                    "time": d.time,
                    self._state_attribute_parameter_name: self.get_parameter_value(d)
                }, data.combined_hours()))

            today = datetime.date.today()
            tomorrow = today + datetime.timedelta(days=1)
            values_today = list(filter(lambda d: d["time"].date() == today, values))
            values_tomorrow = list(filter(lambda d: d["time"].date() == tomorrow, values))
            output[f"{self._state_attribute_name}{ATTRIBUTE_TODAY_SUFFIX}"] = values_today
            output[f"{self._state_attribute_name}{ATTRIBUTE_TOMORROW_SUFFIX}"] = values_tomorrow
            output[self._state_attribute_name] = values
        return output

    @property
    def available(self) -> bool:
        return super().available and self.get_data() is not None

    @property
    def unique_id(self) -> str:
        return f"{super().unique_id}_sensor_{self._data_parameter_name}"

    @property
    def state_class(self) -> SensorStateClass:
        return SensorStateClass.MEASUREMENT


class PgeTgeFixing1RateSensor(PgeTgeSensor):

    def __init__(self, coordinator: PgeTgeUpdateCoordinator, config_entry: ConfigEntry) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_suggested_display_precision = 2
        if self.native_unit_of_measurement == UNIT_GR_KWH:
            self._attr_suggested_display_precision = 3
        elif self.native_unit_of_measurement == UNIT_ZL_KWH:
            self._attr_suggested_display_precision = 5
        self._data_parameter_name = PARAMETER_FIXING_1_RATE
        self._state_attribute_name = ATTRIBUTE_PRICES
        self._state_attribute_parameter_name = ATTRIBUTE_PARAMETER_PRICE

    @property
    def icon(self) -> str:
        return "mdi:cash"

    @property
    def name(self) -> str:
        return f"{self.base_name()} Fixing 1 Rate"

    @property
    def native_unit_of_measurement(self) -> str:
        return self._config_entry.options.get(CONF_UNIT, UNIT_ZL_MWH)


class PgeTgeFixing1VolumeSensor(PgeTgeSensor):

    def __init__(self, coordinator: PgeTgeUpdateCoordinator, config_entry: ConfigEntry) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_entity_registry_enabled_default = False
        self._data_parameter_name = PARAMETER_FIXING_1_VOLUME
        self._state_attribute_name = ATTRIBUTE_VOLUMES
        self._state_attribute_parameter_name = ATTRIBUTE_PARAMETER_VOLUME

    @property
    def icon(self) -> str:
        return "mdi:meter-electric"

    @property
    def name(self) -> str:
        return f"{self.base_name()} Fixing 1 Volume"

    @property
    def native_unit_of_measurement(self) -> str:
        return UnitOfEnergy.MEGA_WATT_HOUR
