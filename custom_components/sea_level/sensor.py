import logging
from datetime import timedelta, datetime
import fmiopendata
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from fmiopendata.wfs import download_stored_query
from .const import DOMAIN

SCAN_INTERVAL = timedelta(minutes=10)


async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = SeaLevelDataUpdateCoordinator(hass, config_entry.data)
    await coordinator.async_config_entry_first_refresh()

    async_add_entities([SeaLevelSensor(coordinator)], True)


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
            # Fetch data from FMI open data platform
            return await self.hass.async_add_executor_job(self.fetch_sea_level)
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}")

    def fetch_sea_level(self):
        start_time = datetime(*datetime.now().timetuple()[:4])
        end_time = start_time + timedelta(hours=48)

        # Download the sea level data
        sealevel = download_stored_query(
            "fmi::forecast::sealevel::point::multipointcoverage",
            [
                f"latlon={self.latitude},{self.longitude}",
                f"starttime={datetime.isoformat(start_time)}",
                f"endtime={datetime.isoformat(end_time)}",
            ],
        )
        self.location = list(sealevel.location_metadata.keys())[0]
        self.forecast = [
            {
                "datetime": datetime.isoformat(key),
                "value": sealevel.data[key][self.location]["Water level"]["value"],
            }
            for key in sealevel.data
        ]


# >>> [f"{datetime.isoformat(key)} {sealevel.data[key]['Pihlava']['Water level']['value']}" for key in sealevel.data]
# ['2024-12-20T19:00:00 18.3', '2024-12-20T20:00:00 17.3', '2024-12-20T21:00:00 16.3', '2024-12-20T22:00:00 17.3', '2024-12-20T23:00:00 20.3', '2024-12-21T00:00:00 22.3', '2024-12-21T01:00:00
# 24.3', '2024-12-21T02:00:00 24.3', '2024-12-21T03:00:00 23.3', '2024-12-21T04:00:00 23.3', '2024-12-21T05:00:00 22.3', '2024-12-21T06:00:00 21.3', '2024-12-21T07:00:00 21.3']
# >>>


class SeaLevelSensor(SensorEntity):
    def __init__(self, coordinator):
        self.coordinator = coordinator

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

    async def async_update(self):
        await self.coordinator.async_request_refresh()
