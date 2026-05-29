from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional, TypedDict, NotRequired, List, Literal
from enum import Enum
import re


# FlightStatus enum -> Represents the status property of the flight
class FlightStatus(Enum):
    SCHEDULED = "S"
    OPERATIONAL = "O"
    TERMINATED = "T"

    @property
    def label(self):

        # Return human-readable text in string format
        return {
            FlightStatus.SCHEDULED: "Scheduled",
            FlightStatus.OPERATIONAL: "Operational",
            FlightStatus.TERMINATED: "Terminated",
        }[self]


class FlightValidationError(ValueError):
    pass


class Flight:
    FLIGHT_NUMBER_PATTERN = re.compile(r"^F\d{6}$")
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
        if self._validations:
            raise FlightValidationError("\n".join(self._validations))
        self._validations = []

    def assign_pilot(self, pilot_id: Optional[int]) -> None:
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
        self._validate_schedule(departure, arrival)

        if self._status == FlightStatus.TERMINATED:
            self._validations.append("Cannot modify terminated flight")

        self.validate()

        if departure and arrival:
            self._departure = departure
            self._arrival = arrival

    def start_operation(self) -> None:
        if self._status != FlightStatus.SCHEDULED:
            self._validations.append("Only scheduled flights can start operation")

        if self._pilot_id is None:
            self._validations.append("Operational flight requires a pilot")

        self.validate()

        self._status = FlightStatus.OPERATIONAL

    def terminate(self) -> None:
        if self._status != FlightStatus.OPERATIONAL:
            self._validations.append("Only operational flights can terminate")

        self.validate()

        self._status = FlightStatus.TERMINATED

    def _validate_flight_number(self, flight_number: Optional[str]) -> None:
        if not flight_number:
            self._validations.append("flight number must be present")
            return

        if not self.FLIGHT_NUMBER_PATTERN.fullmatch(flight_number):
            self._validations.append("flight number must follow F999999 pattern")

    def _validate_status(self, status: Optional[FlightStatus]) -> None:
        if not status:
            self._validations.append("status must be present")

    def _validate_schedule(
        self,
        departure: Optional[datetime],
        arrival: Optional[datetime],
    ) -> None:
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
        if origin_id is None:
            self._validations.append("origin must be present")
            return

        if destination_id is None:
            self._validations.append("destination must be present")
            return

        if origin_id == destination_id:
            self._validations.append("origin and destination cannot be equal")

    def _validate_status_and_pilot_id(self) -> None:
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


# FlightView class -> Embodies all flight related data for viewing
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


# PilotView class -> Embodies all pilot related data for viewing
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


# FlightSearch class -> Configures the flight query
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
