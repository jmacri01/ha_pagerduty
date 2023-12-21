import logging
import datetime
from pdpyras import APISession, PDClientError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import asyncio
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class PagerDutyDataCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the PagerDuty API."""

    def __init__(self, hass, api_token, update_interval):
        """Initialize the data coordinator."""
        _LOGGER.debug("Initializing PagerDuty Data Coordinator")
        self.session = APISession(api_token)
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=update_interval)

    async def _async_update_data(self):
        """Fetch data from the PagerDuty API."""

        async def fetch_user_teams():
            try:
                _LOGGER.debug("Fetching PagerDuty user teams")
                user_info = await self.hass.async_add_executor_job(
                    self.session.rget, "users/me", params={"include[]": "teams"}
                )
                return [team["id"] for team in user_info["teams"]]
            except PDClientError as e:
                _LOGGER.error("Error fetching user teams from PagerDuty: %s", e)
                raise UpdateFailed(f"Error fetching user teams from PagerDuty: {e}")

        async def fetch_on_call_data():
            try:
                _LOGGER.debug("Fetching PagerDuty on-call data")
                on_calls = await self.hass.async_add_executor_job(
                    self.session.list_all, "oncalls", params={"user_ids[]": "me"}
                )
                on_call_data = []
                for on_call in on_calls:
                    start = datetime.datetime.fromisoformat(on_call["start"])
                    end = datetime.datetime.fromisoformat(on_call["end"])
                    on_call_data.append(
                        {
                            "schedule_id": on_call["schedule"]["id"],
                            "schedule_name": on_call["schedule"]["summary"],
                            "start": start,
                            "end": end,
                            "escalation_level": on_call["escalation_level"],
                        }
                    )
                return on_call_data
            except PDClientError as e:
                _LOGGER.error("Error fetching on-call data from PagerDuty: %s", e)
                raise UpdateFailed(f"Error fetching on-call data from PagerDuty: {e}")

        # Run both functions concurrently
        user_teams, on_call_data = await asyncio.gather(
            fetch_user_teams(), fetch_on_call_data()
        )

        # Process and return the combined data
        parsed_data = {}
        for team_id in user_teams:
            _LOGGER.debug("Fetching PagerDuty services for team ID: %s", team_id)
            params = {"team_ids[]": team_id}
            services = await self.hass.async_add_executor_job(
                self.session.list_all, "services", params=params
            )

            for service in services:
                service_id = service["id"]
                service_name = service["name"]
                incidents_params = {
                    "service_ids[]": service_id,
                    "statuses[]": ["triggered", "acknowledged"],
                }
                incidents = await self.hass.async_add_executor_job(
                    self.session.list_all, "incidents", params=incidents_params
                )

                incident_count = sum(1 for incident in incidents)
                high_urgency_count = sum(
                    1 for incident in incidents if incident["urgency"] == "high"
                )
                low_urgency_count = sum(
                    1 for incident in incidents if incident["urgency"] == "low"
                )

                triggered_count = sum(
                    1 for incident in incidents if incident["status"] == "triggered"
                )
                acknowledged_count = sum(
                    1 for incident in incidents if incident["status"] == "acknowledged"
                )

                parsed_data[service_id] = {
                    "team_id": team_id,
                    "service_name": service_name,
                    "triggered_count": triggered_count,
                    "acknowledged_count": acknowledged_count,
                    "high_urgency_count": high_urgency_count,
                    "low_urgency_count": low_urgency_count,
                    "incident_count": incident_count,
                    "on_call_data": on_call_data,
                }

        return parsed_data