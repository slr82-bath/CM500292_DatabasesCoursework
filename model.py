from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional, TypedDict, NotRequired, List
from enum import Enum
import re


# FlightStatus enum -> Represents the status property of the flight
class FlightStatus(Enum):
    SCHEDULED = 'S'
    OPERATIONAL = 'O'
    TERMINATED = 'T'

    @property
    def label(self):

        # Return human-readable text in string format
        return {
            FlightStatus.SCHEDULED: 'Scheduled',
            FlightStatus.OPERATIONAL: 'Operational',
            FlightStatus.TERMINATED: 'Terminated'
        }[self]


# Airport class -> Ensures insertion of valid data
@dataclass(frozen=True)
class Airport:
    airport_code: str
    airport_name: str
    country_id: int

    def __post_init__(self):
        validations: List[str] = []

        # Validade if airport code is present
        if self.airport_code is None:
            validations.append("airport code must be a present")

        # Validade if airport code follows IATA standards
        if re.fullmatch(self.airport_code, r'[A-Z]{3}'):
            validations.append("airport code must be a IATA code")

        # Validade if airport name is present
        if self.airport_name is None or len(self.airport_name) < 1:
            validations.append("airport name must be a present")

        # Validade if country is present
        if self.country_id is None:
            validations.append("country must be a present")

        # Raise error with all validations that failed if the object is not valid
        if len(validations) > 0:
            raise ValueError('\n'.join(validations)) 


# Pilot class -> Ensures insertion of valid data
@dataclass(frozen=True)
class Pilot:
    full_name: str
    contact_number: Optional[str]
    license_number: str
    flight_hours: float

    def __post_init__(self):
        validations: List[str] = []

        # Validade if full name is present
        if self.full_name is None or len(self.full_name) < 1:
            validations.append("full name must be a present")

        # Validade if license number is present
        if self.license_number is None:
            validations.append("license number must be a present")

        # Validade if license number follows the common standards
        if re.fullmatch(self.license_number, r'[0-9]{4}'):
            validations.append("license number must have 4 numerical digits")

        # Validade if flight hours is present
        if self.flight_hours is None:
            validations.append("flight hours must be a present")

        # Enforce positive numerical values for flight hours
        if self.flight_hours < 0:
            validations.append("flight hours cannot be negative")

        # Raise error with all validations that failed if the object is not valid
        if len(validations) > 0:
            raise ValueError('\n'.join(validations)) 


# Flight class -> Ensures insertion of valid data
@dataclass(frozen=True)
class Flight:
    flight_number: str
    status: FlightStatus
    departure: datetime
    arrival: datetime
    pilot_id: Optional[int]
    origin_id: int
    destination_id: int

    def __post_init__(self):
        validations: List[str] = []

        # Validade if flight number is present
        if self.flight_number is None:
            validations.append("flight number must be a present")

        # Validade if flight number follows the common standards
        if re.fullmatch(self.flight_number, r'[0-9]{6}'):
            validations.append("flight number must have 6 numerical digits")

        # Validade if departure is present
        if self.departure is None:
            validations.append("departure must be a present")

        # Validade if arrival is present
        if self.arrival is None:
            validations.append("arrival must be a present")

        # Enforce logically accepted time interval between arrival and departure times
        if self.arrival <= self.departure:
            validations.append("arrival cannot be earlier than or equal to departure")

        # Validade if origin is present
        if self.origin_id is None:
            validations.append("origin must be a present")

        # Validade if destination is present
        if self.destination_id is None:
            validations.append("destination must be a present")

        # Validade if status is present
        if self.status is None:
            validations.append("status must be a present")

        # Validate if status was set as an invalid string
        try:
            FlightStatus(self.status)
        except:
            validations.append("status string value must be one of 'S', 'O', and 'T'")

        # Enforce pilot assignment when flight status is not scheduled
        if self.status in {FlightStatus.OPERATIONAL, FlightStatus.TERMINATED} and self.pilot_id is None:
            validations.append("operational or terminated flights must have a pilot assigned")
        
        # Raise error with all validations that failed if the object is not valid
        if len(validations) > 0:
            raise ValueError('\n'.join(validations)) 


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
        self.flight_number = flight_number
        self.status = None
        if status:
            self.status = FlightStatus(status).label
        self.departure = departure
        self.arrival = arrival
        self.pilot_full_name = pilot_full_name
        self.pilot_license_number = pilot_license_number
        self.pilot_contact_number = pilot_contact_number
        self.pilot_flight_hours = pilot_flight_hours
        self.origin_airport_code = origin_airport_code
        self.origin_airport_name = origin_airport_name
        self.origin_country = origin_country
        self.destination_airport_code = destination_airport_code
        self.destination_airport_name = destination_airport_name
        self.destination_country = destination_country


# FlightSearch class -> Configures the flight query
class FlightSearch(TypedDict):
    projection: NotRequired[List[str]]
    flight_id: NotRequired[int]
    flight_number: NotRequired[str]
    status: NotRequired[str]
    date_of_departure: NotRequired[date]
    includes_pilot_full_name: NotRequired[str]
    pilot_license_number: NotRequired[str]
    from_pilot_flight_hours: NotRequired[float]
    origin_airport_code: NotRequired[str]
    origin_country_code: NotRequired[str]
    destination_airport_code: NotRequired[str]
    destination_country_code: NotRequired[str]
