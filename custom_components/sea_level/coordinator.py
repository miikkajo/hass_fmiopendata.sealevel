import logging
from datetime import timedelta, datetime

from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from fmiopendata.wfs import download_stored_query

from .const import DOMAIN

SCAN_INTERVAL = timedelta(minutes=10)

SEA_LEVEL_QUERY = "fmi::forecast::sealevel::point::multipointcoverage"
WEATHER_QUERY = "fmi::forecast::edited::weather::scandinavia::point::multipointcoverage"
WIND_PARAMETERS = "WindSpeedMS,WindDirection,HourlyMaximumGust"


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

        # Attach wind direction to wind speed and gust forecasts
        direction_by_time = {
            entry["datetime"]: entry["value"]
            for entry in self.wind_direction_forecast
        }
        for entry in self.wind_speed_forecast + self.wind_gust_forecast:
            direction = direction_by_time.get(entry["datetime"])
            entry["wind_direction"] = direction
            entry["wind_direction_text"] = (
                self._degrees_to_compass(direction) if direction is not None else None
            )

    @staticmethod
    def _build_forecast(data, location, parameter):
        return [
            {
                "datetime": datetime.isoformat(key),
                "value": float(data.data[key][location][parameter]["value"]),
            }
            for key in data.data
        ]

    @staticmethod
    def _degrees_to_compass(degrees):
        compass_points = [
            "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
        ]
        index = round(degrees / 22.5) % 16
        return compass_points[index]
