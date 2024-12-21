import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE

from .const import DOMAIN


class SeaLevelConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="Sea Level", data=user_input)

        # Get default home coordinates from Home Assistant configuration
        default_latitude = self.hass.config.latitude
        default_longitude = self.hass.config.longitude

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_LATITUDE, default=default_latitude): vol.Coerce(
                        float
                    ),
                    vol.Required(CONF_LONGITUDE, default=default_longitude): vol.Coerce(
                        float
                    ),
                }
            ),
        )

