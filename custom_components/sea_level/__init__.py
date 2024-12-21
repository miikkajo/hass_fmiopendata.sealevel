from homeassistant.core import HomeAssistant


async def async_setup(hass: HomeAssistant, config: dict):
    return True


async def async_setup_entry(hass: HomeAssistant, entry):
    # Setup the integration using the config entry data
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry):
    # Unload the integration
    await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    return True

