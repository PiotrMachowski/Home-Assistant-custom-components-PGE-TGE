from datetime import timedelta
from typing import Final

from homeassistant.const import Platform, UnitOfEnergy

DOMAIN: Final = "pge_tge"
DEFAULT_NAME: Final = "PGE TGE"
DEFAULT_UPDATE_INTERVAL: Final = timedelta(minutes=1)
DATA_URL_TEMPLATE: Final = 'https://datahub.gkpge.pl/api/tge/quote?date_from={}&date_to={}&source=TGE&contract=Fix_1&limit=100&page=1'

ATTRIBUTE_TODAY_SUFFIX: Final = "_today"
ATTRIBUTE_TOMORROW_SUFFIX: Final = "_tomorrow"
ATTRIBUTE_PRICES: Final = "prices"
ATTRIBUTE_VOLUMES: Final = "volumes"
ATTRIBUTE_PARAMETER_PRICE: Final = "price"
ATTRIBUTE_PARAMETER_VOLUME: Final = "volume"

PARAMETER_FIXING_1_RATE = "fixing1_rate"
PARAMETER_FIXING_1_VOLUME = "fixing1_volume"

UNIT_CURRENCY_Zl: Final = "zł"
UNIT_CURRENCY_GR: Final = "gr"

UNIT_ZL_MWH = f"{UNIT_CURRENCY_Zl}/{UnitOfEnergy.MEGA_WATT_HOUR}"
UNIT_GR_KWH = f"{UNIT_CURRENCY_GR}/{UnitOfEnergy.KILO_WATT_HOUR}"
UNIT_ZL_KWH = f"{UNIT_CURRENCY_Zl}/{UnitOfEnergy.KILO_WATT_HOUR}"

PLATFORMS = [
    Platform.SENSOR
]

CONF_UNIT: Final = "unit"
CONF_USE_STATE_TEMPLATES: Final = "use_state_templates"
CONF_STATE_TEMPLATE_FIXING_1_RATE: Final = "state_template_" + PARAMETER_FIXING_1_RATE
CONF_STATE_TEMPLATE_FIXING_1_VOLUME: Final = "state_template_" + PARAMETER_FIXING_1_VOLUME
