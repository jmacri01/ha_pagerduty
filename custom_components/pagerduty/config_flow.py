import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import CONF_API_TOKEN, DOMAIN
from pdpyras import APISession, PDClientError

_LOGGER = logging.getLogger(__name__)


class PagerDutyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def validate_input(self, hass, token):
        """Validate the user input allows us to connect."""

        def validate():
            session = APISession(token)
            try:
                # Perform a test API call
                session.rget("abilities")
                return True
            except PDClientError as e:
                _LOGGER.debug("Failed to validate PagerDuty token: %s", e)
                return False

        _LOGGER.debug("Validating PagerDuty API token")
        return await hass.async_add_executor_job(validate)

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            _LOGGER.debug("Received user input: %s", user_input)
            valid = await self.validate_input(self.hass, user_input[CONF_API_TOKEN])
            if not valid:
                errors["base"] = "invalid_auth"
                _LOGGER.debug("Validation failed: invalid_auth")
            if not errors:
                _LOGGER.debug("Validation successful, creating entry")
                return self.async_create_entry(title="PagerDuty", data=user_input)

        data_schema = vol.Schema(
            {
                vol.Required(CONF_API_TOKEN): str,
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return PagerDutyOptionsFlowHandler(config_entry)


class PagerDutyOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle PagerDuty options."""

    def __init__(self, config_entry):
        """Initialize PagerDuty options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the PagerDuty options."""
        _LOGGER.debug("Initializing PagerDuty options flow")
        # Implement options flow if needed
        return self.async_show_form(
            step_id="init"
            # Define options schema here if needed
        )
