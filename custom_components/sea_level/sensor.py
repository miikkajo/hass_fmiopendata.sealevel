import logging
from datetime import timedelta, datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from fmiopendata.wfs import download_stored_query

from .const import DOMAIN

SCAN_INTERVAL = timedelta(minutes=10)

SEA_LEVEL_QUERY = "fmi::forecast::sealevel::point::multipointcoverage"
WEATHER_QUERY = "fmi::forecast::edited::weather::scandinavia::point::multipointcoverage"
WIND_PARAMETERS = "WindSpeedMS,WindDirection,HourlyMaximumGust"


async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = SeaLevelDataUpdateCoordinator(hass, config_entry.data)
    await coordinator.async_config_entry_first_refresh()

    async_add_entities(
        [
            SeaLevelSensor(coordinator, config_entry.entry_id),
            WindSpeedSensor(coordinator, config_entry.entry_id),
            WindDirectionSensor(coordinator, config_entry.entry_id),
            WindGustSensor(coordinator, config_entry.entry_id),
        ],
        True,
    )


class SeaLevelDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, config):
        self.latitude = config[CONF_LATITUDE]
        self.longitude = config[CONF_LONGITUDE]
        super().__init__(
            hass,
            logging.getLogger(__name__),
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )

    async def _async_update_data(self):
        try:
            return await self.hass.async_add_executor_job(self.fetch_data)
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}")

    def fetch_data(self):
        start_time = datetime(*datetime.now().timetuple()[:4])
        end_time = start_time + timedelta(hours=48)
        time_args = [
            f"starttime={datetime.isoformat(start_time)}",
            f"endtime={datetime.isoformat(end_time)}",
        ]

        # Fetch sea level forecast
        sealevel = download_stored_query(
            SEA_LEVEL_QUERY,
            [f"latlon={self.latitude},{self.longitude}"] + time_args,
        )
        self.location = list(sealevel.location_metadata.keys())[0]
        self.forecast = self._build_forecast(sealevel, self.location, "Water level")

        # Fetch wind forecast for the same location
        weather = download_stored_query(
            WEATHER_QUERY,
            [f"latlon={self.latitude},{self.longitude}"]
            + time_args
            + [f"parameters={WIND_PARAMETERS}"],
        )
        self.weather_location = list(weather.location_metadata.keys())[0]
        self.wind_speed_forecast = self._build_forecast(
            weather, self.weather_location, "Wind speed"
        )
        self.wind_direction_forecast = self._build_forecast(
            weather, self.weather_location, "Wind direction"
        )
        self.wind_gust_forecast = self._build_forecast(
            weather, self.weather_location, "Hourly maximum wind gust"
        )

    @staticmethod
    def _build_forecast(data, location, parameter):
        return [
            {
                "datetime": datetime.isoformat(key),
                "value": float(data[key][location][parameter]["value"]),
            }
            for key in data
        ]


class SeaLevelSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_sea_level"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def name(self):
        return "Sea Level"

    @property
    def state(self):
        return self.coordinator.forecast[0]["value"]

    @property
    def extra_state_attributes(self):
        return {
            "forecast": self.coordinator.forecast,
            "location": self.coordinator.location,
            "latitude": self.coordinator.latitude,
            "longitude": self.coordinator.longitude,
        }


class WindSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_wind_{self.forecast_attr}"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def forecast_attr(self):
        raise NotImplementedError

    @property
    def forecast(self):
        return getattr(self.coordinator, self.forecast_attr)

    @property
    def state(self):
        return self.forecast[0]["value"]

    @property
    def extra_state_attributes(self):
        return {
            "forecast": self.forecast,
            "location": self.coordinator.weather_location,
            "latitude": self.coordinator.latitude,
            "longitude": self.coordinator.longitude,
        }


class WindSpeedSensor(WindSensor):
    @property
    def name(self):
        return "Wind Speed"

    @property
    def forecast_attr(self):
        return "wind_speed_forecast"

    @property
    def unit_of_measurement(self):
        return "m/s"

    @property
    def device_class(self):
        return SensorDeviceClass.WIND_SPEED


class WindDirectionSensor(WindSensor):
    @property
    def name(self):
        return "Wind Direction"

    @property
    def forecast_attr(self):
        return "wind_direction_forecast"

    @property
    def unit_of_measurement(self):
        return "°"


class WindGustSensor(WindSensor):
    @property
    def name(self):
        return "Wind Gust"

    @property
    def forecast_attr(self):
        return "wind_gust_forecast"

    @property
    def unit_of_measurement(self):
        return "m/s"

    @property
    def device_class(self):
        return SensorDeviceClass.WIND_SPEED
