from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    async_add_entities(
        [
            SeaLevelSensor(coordinator, config_entry.entry_id),
            WindSpeedSensor(coordinator, config_entry.entry_id),
            WindDirectionSensor(coordinator, config_entry.entry_id),
            WindGustSensor(coordinator, config_entry.entry_id),
        ],
        True,
    )


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
