from typing import List
from abc import ABC, abstractmethod
from db_operation import (
    InitializeAirlineSchemaDBOperation,
    SearchFlightsDBOperation,
    FindPilotByLicenseNumber,
)
from model import FlightSearch, FlightStatus
from utils import print_table, optional_input, print_sql_script
from datetime import date
import re


# Abstract representation of a menu option in the CLI.
class MenuOption(ABC):
    def __init__(self):
        super().__init__()
        self._name = ""

    # Public read-only property for the menu option name.
    @property
    def name(self) -> str:
        return self._name

    # Every menu option must define its own behavior.
    @abstractmethod
    def execute_option(self):
        pass


# Menu option that triggers flight searching.
class SearchFlightsMenuOption(MenuOption):

    def __init__(self):
        super().__init__()

        # Display text shown in the menu.
        self._name = "Search Flights"

    # Execute the associated database operation.
    def execute_option(self):
        print()
        search = self.__scan_flight_search()
        print()
        search_flights = SearchFlightsDBOperation(search)
        print("SQL Query:\n")
        print_sql_script(search_flights.query)
        print()
        search_flights.execute_transaction()
        if not search_flights.query_result:
            print("Empty flight search result.")
            return
        print_table(search_flights.query_result, search.get("projection", []))

    def __scan_flight_search(self) -> FlightSearch:
        search: FlightSearch = {}

        if optional_input("Filter flights? (y/n): ") == "y":
            print("Invalid or blank filter values will not be applied.")

            flight_id = optional_input("Flight ID (integer number): ")
            if flight_id:
                try:
                    search["flight_id"] = int(flight_id)
                except:
                    pass

            flight_number = optional_input("Flight number (F999999): ")
            if flight_number and re.fullmatch(r"F[0-9]{6}", flight_number):
                search["flight_number"] = flight_number[1:]

            print("Available statuses:")
            for status in FlightStatus:
                print(f"{status.value} - {status.label}")
            status_input = optional_input("Flight status: ")
            if status_input:
                try:
                    search["status"] = FlightStatus(status_input.upper())
                except:
                    pass

            departure_date = optional_input("Departure date (YYYY-MM-DD): ")
            if departure_date:
                try:
                    search["departure_date"] = date.fromisoformat(departure_date)
                except:
                    pass

            pilot_name = optional_input(
                "Pilot name (includes all names that contain the string): "
            )
            if pilot_name:
                search["includes_pilot_full_name"] = pilot_name

            pilot_license = optional_input("Pilot license number (LN9999): ")
            if pilot_license and re.fullmatch(r"LN[0-9]{4}", pilot_license):
                search["pilot_license_number"] = pilot_license[2:]

            flight_hours = optional_input("Minimum pilot flight hours (float number): ")
            if flight_hours:
                try:
                    search["from_pilot_flight_hours"] = float(flight_hours)
                except:
                    pass

            origin_airport = optional_input("Origin airport code: ")
            if origin_airport:
                search["origin_airport_code"] = origin_airport.upper()

            origin_country = optional_input("Origin country code: ")
            if origin_country:
                search["origin_country_code"] = origin_country.upper()

            destination_airport = optional_input("Destination airport code: ")
            if destination_airport:
                search["destination_airport_code"] = destination_airport.upper()

            destination_country = optional_input("Destination country code: ")
            if destination_country:
                search["destination_country_code"] = destination_country.upper()

        print("""
Flight column names:
  flight_id
  flight_number
  status
  departure
  arrival
  pilot_full_name
  pilot_license_number
  pilot_contact_number
  pilot_flight_hours
  origin_airport_code
  origin_airport_name
  origin_country
  destination_airport_code
  destination_airport_name
  destination_country

Type the columns, separated by spaces, to be displayed in the table.
Press Enter without inserting any input to displays all the columns.
    """)
        projection = optional_input("Column names: ")
        if projection:
            search["projection"] = re.split(r"\s+", projection)

        print("""
Type the + or - symbol followed by a column names, separated by spaces, to apply hierarchical ordering onto the search.
The symbol before the column name defines the order direction (+ for ascending, - for descending).
Press Enter without inserting any input to not apply any ordering.
    """)
        orders = optional_input("Orders: ")
        if orders:
            order_matchs = [
                (re.search(r"[+-]{1}", order), order)
                for order in re.split(r"\s+", orders)
            ]
            search["order"] = [
                (
                    (order[1:], "desc" if match.group() == "-" else "asc")
                    if match and match.span() == (0, 1)
                    else (order, "asc")
                )
                for match, order in order_matchs
            ]

        return search


class ViewPilotScheduleMenuOption(MenuOption):
    def __init__(self):
        super().__init__()
        self._name = "View Pilot Schedule"

    def execute_option(self):
        print()
        print("An invalid or blank input will be ignored.")
        license_number = optional_input("Pilot license number (LN9999): ")
        if not license_number or not re.fullmatch(r"LN[0-9]{4}", license_number):
            return
        print()
        license_number = license_number[2:]
        pilot_search = FindPilotByLicenseNumber(license_number)
        print("SQL Query:\n")
        print_sql_script(pilot_search.query)
        print()
        pilot_search.execute_transaction()
        pilot = pilot_search.query_result
        if not pilot:
            print(f"There is not a pilot with the license number LN{license_number}.")
            return
        search: FlightSearch = {}
        search["pilot_license_number"] = license_number
        search["status"] = FlightStatus.SCHEDULED
        search["projection"] = [
            "departure",
            "arrival",
            "origin_airport_code",
            "origin_country",
            "destination_airport_code",
            "destination_country",
        ]
        search["order"] = [("departure", "asc")]
        search_flights = SearchFlightsDBOperation(search)
        print("SQL Query:\n")
        print_sql_script(search_flights.query)
        print()
        search_flights.execute_transaction()
        print(f"""Pilot: {pilot.full_name} ({pilot.license_number})
Contact number: {pilot.contact_number if pilot.contact_number else "Not provided"}
Experience (total flight hours): {pilot.flight_hours}
        """)
        if not search_flights.query_result:
            print(f"The pilot does not have any scheduled flights.")
            return
        print_table(search_flights.query_result, search.get("projection", []))


# Menu option that exits the application.
class ExitMenuOption(MenuOption):
    def __init__(self):
        super().__init__()
        self._name = "Exit"

    # Terminates the program immediately.
    def execute_option(self):
        exit(0)


# Represents the command-line interface menu.
class Menu:
    def __init__(self):

        # Stores all available menu options.
        self.__menu_options: List[MenuOption] = []

    # Adds a new option to the menu.
    def add_option(self, menu_option: MenuOption):
        self.__menu_options.append(menu_option)

    # Displays all menu options to the user.
    def display_options(self):
        print("\nMenu:")

        # enumerate() generates:
        # (index, menu_option)
        for i, menu_option in enumerate(self.__menu_options):
            print(f"{i + 1}. {menu_option.name}")

    # Executes the selected menu option.
    def choose_option(self, i: int):

        # Convert user-friendly numbering (1-based)
        # into list indexing (0-based).
        i -= 1

        # Validate user selection.
        if i not in range(len(self.__menu_options)):
            print("Invalid Choice")
            return

        # Retrieve selected menu option.
        menu_option: MenuOption = self.__menu_options[i]

        # Execute selected action.
        menu_option.execute_option()


# Create schema and seed database if needed.
InitializeAirlineSchemaDBOperation().execute_transaction()

# Create the command-line menu.
menu = Menu()

# Register menu options.
menu.add_option(SearchFlightsMenuOption())
menu.add_option(ViewPilotScheduleMenuOption())
menu.add_option(ExitMenuOption())


# Main application loop.
while True:

    # Display available actions.
    menu.display_options()

    # Read and execute user choice.
    menu.choose_option(int(input("Enter your choice: ")))
