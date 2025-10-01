"""Update coordinator for PGE TGE integration."""
import datetime
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .connector import PgeTgeConnector, PgeTgeData
from .const import DOMAIN, DEFAULT_UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class PgeTgeUpdateCoordinator(DataUpdateCoordinator[PgeTgeData]):

    def __init__(self, hass: HomeAssistant):
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=DEFAULT_UPDATE_INTERVAL,
                         update_method=self.update_method)
        self.connector = PgeTgeConnector()
        self._last_update_hour: datetime.date | None = None
        self._last_data: PgeTgeData | None = None

    async def update_method(self) -> PgeTgeData | None:
        return await self.hass.async_add_executor_job(self._update)

    def _update(self) -> PgeTgeData:
        now = datetime.datetime.now()
        if self._should_update(now):
            _LOGGER.debug("Updating PGE TGE data")
            self._last_update_hour = now.hour
            self._last_data = self.connector.get_data()
        else:
            _LOGGER.debug("Using cached PGE TGE data")
        return self._last_data

    def _should_update(self, now: datetime.datetime) -> bool:
        return (
                self._last_update_hour is None
                or now.hour != self._last_update_hour
                or self._last_data is None
        )
