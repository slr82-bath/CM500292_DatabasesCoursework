from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional, TypedDict, NotRequired, List, Literal
from enum import Enum
import re


# Flight status codes used by the persistence layer.
# The enum provides a type-safe representation within the domain model.
class FlightStatus(Enum):
    SCHEDULED = "S"
    OPERATIONAL = "O"
    TERMINATED = "T"

    @property
    def label(self):
        """
        Return a human-readable representation of the flight status.
        """
        return {
            FlightStatus.SCHEDULED: "Scheduled",
            FlightStatus.OPERATIONAL: "Operational",
            FlightStatus.TERMINATED: "Terminated",
        }[self]


class FlightValidationError(ValueError):
    """
    Raised when one or more flight business rules are violated.
    """

    pass


class Flight:
    # Flight numbers must follow the format:
    # F123456 (letter F followed by exactly six digits).
    FLIGHT_NUMBER_PATTERN = re.compile(r"^F\d{6}$")

    # Collects validation errors during object construction and state changes.
    _validations: List[str]

    def __init__(
        self,
        *,
        flight_id: Optional[int] = None,
        flight_number: Optional[str] = None,
        departure: Optional[datetime] = None,
        arrival: Optional[datetime] = None,
        origin_id: Optional[int] = None,
        destination_id: Optional[int] = None,
        status: Optional[FlightStatus] = None,
        pilot_id: Optional[int] = None,
    ):
        """
        Create a flight entity and validate all required business rules.

        A Flight instance is guaranteed to be in a valid state after
        construction. Any validation failures are accumulated and raised
        together as a FlightValidationError.
        """
        self._validations = []

        self._flight_id = flight_id
        self._validate_flight_number(flight_number)
        if flight_number:
            self._flight_number = flight_number
        self._validate_schedule(departure, arrival)
        if departure and arrival:
            self._departure = departure
            self._arrival = arrival
        self._validate_airports(origin_id, destination_id)
        if origin_id and destination_id:
            self._origin_id = origin_id
            self._destination_id = destination_id
        self._validate_status(status)
        if status:
            self._status = status
        self._pilot_id = pilot_id

        self._validate_status_and_pilot_id()

        self.validate()

    @classmethod
    def from_db_fetch(
        cls,
        *,
        flight_id: int,
        flight_number: str,
        departure: str,
        arrival: str,
        origin_id: int,
        destination_id: int,
        status: str,
        pilot_id: Optional[int],
    ):
        """
        Create a Flight entity from a database result row.

        Converts database-specific representations such as:
        - string timestamps -> datetime objects
        - status code strings -> FlightStatus enum values
        - numeric flight numbers -> domain flight number format
        """
        return cls(
            flight_id=flight_id,
            flight_number=f"F{flight_number}",
            departure=datetime.strptime(departure, "%Y-%m-%d %H:%M:%S"),
            arrival=datetime.strptime(arrival, "%Y-%m-%d %H:%M:%S"),
            origin_id=origin_id,
            destination_id=destination_id,
            status=FlightStatus(status),
            pilot_id=pilot_id if pilot_id else None,
        )

    @property
    def flight_id(self) -> Optional[int]:
        return self._flight_id

    @property
    def flight_number(self) -> str:
        return self._flight_number

    @property
    def departure(self) -> datetime:
        return self._departure

    @property
    def arrival(self) -> datetime:
        return self._arrival

    @property
    def origin_id(self) -> int:
        return self._origin_id

    @property
    def destination_id(self) -> int:
        return self._destination_id

    @property
    def status(self) -> FlightStatus:
        return self._status

    @property
    def pilot_id(self) -> Optional[int]:
        return self._pilot_id

    def validate(self) -> None:
        """
        Raise a FlightValidationError if any validation failures
        have been collected.

        Validation messages are aggregated so callers can see all
        violations at once instead of fixing them one by one.
        """
        if self._validations:
            raise FlightValidationError("\n".join(self._validations))
        self._validations = []

    def assign_pilot(self, pilot_id: Optional[int]) -> None:
        """
        Assign a pilot to the flight.

        The pilot identifier must be present and greater than zero.
        """
        if not pilot_id:
            self._validations.append("pilot_id must be present")
            self.validate()
            return

        if pilot_id <= 0:
            self._validations.append("pilot_id must be positive")

        self.validate()

        self._pilot_id = pilot_id

    def update_schedule(
        self,
        departure: Optional[datetime],
        arrival: Optional[datetime],
    ) -> None:
        """
        Update the flight schedule.

        Schedule changes are prohibited once a flight has been
        terminated.
        """
        self._validate_schedule(departure, arrival)

        if self._status == FlightStatus.TERMINATED:
            self._validations.append("Cannot modify terminated flight")

        self.validate()

        if departure and arrival:
            self._departure = departure
            self._arrival = arrival

    def start_operation(self) -> None:
        """
        Transition the flight from Scheduled to Operational.

        Business rules:
        - Only scheduled flights can start operation.
        - An operational flight must have an assigned pilot.
        """
        if self._status != FlightStatus.SCHEDULED:
            self._validations.append("Only scheduled flights can start operation")

        if self._pilot_id is None:
            self._validations.append("Operational flight requires a pilot")

        self.validate()

        self._status = FlightStatus.OPERATIONAL

    def terminate(self) -> None:
        """
        Transition the flight from Operational to Terminated.

        Business rule:
        - Only operational flights can be terminated.
        """
        if self._status != FlightStatus.OPERATIONAL:
            self._validations.append("Only operational flights can terminate")

        self.validate()

        self._status = FlightStatus.TERMINATED

    def _validate_flight_number(self, flight_number: Optional[str]) -> None:
        """
        Validate flight number presence and in correct format.
        """
        if not flight_number:
            self._validations.append("flight number must be present")
            return

        if not self.FLIGHT_NUMBER_PATTERN.fullmatch(flight_number):
            self._validations.append("flight number must follow F999999 pattern")

    def _validate_status(self, status: Optional[FlightStatus]) -> None:
        """
        Validate status presence.
        """
        if not status:
            self._validations.append("status must be present")

    def _validate_schedule(
        self,
        departure: Optional[datetime],
        arrival: Optional[datetime],
    ) -> None:
        """
        Validate that both schedule timestamps are present and that
        arrival occurs after departure.
        """
        if departure is None:
            self._validations.append("departure must be present")
            return

        if arrival is None:
            self._validations.append("arrival must be present")
            return

        if arrival <= departure:
            self._validations.append("arrival must be later than departure")

    def _validate_airports(
        self,
        origin_id: Optional[int],
        destination_id: Optional[int],
    ) -> None:
        """
        Validate airport assignments.

        Origin and destination airports must both exist and must
        not refer to the same airport.
        """
        if origin_id is None:
            self._validations.append("origin must be present")
            return

        if destination_id is None:
            self._validations.append("destination must be present")
            return

        if origin_id == destination_id:
            self._validations.append("origin and destination cannot be equal")

    def _validate_status_and_pilot_id(self) -> None:
        """
        Ensure flights in active or completed states have a pilot.

        Operational and terminated flights are expected to have been
        flown, therefore a pilot assignment is mandatory.
        """
        if (
            self._status
            in {
                FlightStatus.OPERATIONAL,
                FlightStatus.TERMINATED,
            }
            and self._pilot_id is None
        ):
            self._validations.append(
                "operational or terminated flights require a pilot"
            )


# Read-only projection used for displaying flight information.
# This class combines flight, pilot, and airport data into a format
# suitable for tables, reports, or UI presentation.
class FlightView:
    def __init__(
        self,
        flight_id: Optional[int] = None,
        flight_number: Optional[str] = None,
        status: Optional[str] = None,
        departure: Optional[str] = None,
        arrival: Optional[str] = None,
        pilot_full_name: Optional[str] = None,
        pilot_license_number: Optional[str] = None,
        pilot_contact_number: Optional[str] = None,
        pilot_flight_hours: Optional[str] = None,
        origin_airport_code: Optional[str] = None,
        origin_airport_name: Optional[str] = None,
        origin_country: Optional[str] = None,
        destination_airport_code: Optional[str] = None,
        destination_airport_name: Optional[str] = None,
        destination_country: Optional[str] = None,
    ):
        self.flight_id = None
        if flight_id:
            self.flight_id = str(flight_id)
        self.flight_number = None
        if flight_number:
            self.flight_number = f"F{flight_number}"
        self.status = None
        if status:
            self.status = FlightStatus(status).label
        self.departure = departure
        self.arrival = arrival
        pilot_view = PilotView(
            full_name=pilot_full_name,
            license_number=pilot_license_number,
            contact_number=pilot_contact_number,
            flight_hours=pilot_flight_hours,
        )
        self.pilot_full_name = pilot_view.full_name
        self.pilot_license_number = pilot_view.license_number
        self.pilot_contact_number = pilot_view.contact_number
        self.pilot_flight_hours = pilot_view.flight_hours
        self.origin_airport_code = origin_airport_code
        self.origin_airport_name = origin_airport_name
        self.origin_country = origin_country
        self.destination_airport_code = destination_airport_code
        self.destination_airport_name = destination_airport_name
        self.destination_country = destination_country


# Read-only projection used for displaying pilot information.
# Formats identifiers for presentation purposes.
class PilotView:
    def __init__(
        self,
        pilot_id: Optional[int] = None,
        full_name: Optional[str] = None,
        license_number: Optional[str] = None,
        contact_number: Optional[str] = None,
        flight_hours: Optional[str] = None,
    ):
        self.pilot_id = None
        if pilot_id:
            self.pilot_id = str(pilot_id)
        self.full_name = full_name
        self.license_number = None
        if license_number:
            self.license_number = f"LN{license_number}"
        self.contact_number = contact_number
        self.flight_hours = flight_hours


# Defines the supported search criteria for querying flights.
#
# Notes:
# - All fields are optional.
# - projection controls which fields are returned.
# - order specifies sorting instructions in the form:
#   ("field_name", "asc" | "desc")
class FlightSearch(TypedDict):
    projection: NotRequired[List[str]]
    flight_id: NotRequired[int]
    flight_number: NotRequired[str]
    status: NotRequired[FlightStatus]
    departure_date: NotRequired[date]
    includes_pilot_full_name: NotRequired[str]
    pilot_license_number: NotRequired[str]
    from_pilot_flight_hours: NotRequired[float]
    origin_airport_code: NotRequired[str]
    origin_country_code: NotRequired[str]
    destination_airport_code: NotRequired[str]
    destination_country_code: NotRequired[str]
    order: NotRequired[List[tuple[str, Literal["asc", "desc"]]]]
