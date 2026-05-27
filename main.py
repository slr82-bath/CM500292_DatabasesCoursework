from typing import List
from abc import ABC, abstractmethod
from db_operation import InitializeAirlineSchemaDBOperation, SearchFlightsDBOperation
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
        print_table(search_flights.query_result, search.get("projection", []))

    def __scan_flight_search(self) -> FlightSearch:
        search: FlightSearch = {}

        if optional_input("Filter flights? (y/n): ") == "y":
            print("Invalid or blank filter values will not be applied.")

            flight_id = optional_input("Flight ID: ")
            if flight_id:
                try:
                    search["flight_id"] = int(flight_id)
                except:
                    pass

            flight_number = optional_input("Flight Number: ")
            if flight_number:
                search["flight_number"] = flight_number

            print("Available statuses:")
            for status in FlightStatus:
                print(f"{status.value} - {status.label}")
            status_input = optional_input("Flight Status: ")
            if status_input:
                search["status"] = status_input.upper()

            departure_date = optional_input("Date of Departure (YYYY-MM-DD): ")
            if departure_date:
                try:
                    search["date_of_departure"] = date.fromisoformat(departure_date)
                except:
                    pass

            pilot_name = optional_input("Pilot Full Name: ")
            if pilot_name:
                search["includes_pilot_full_name"] = pilot_name

            pilot_license = optional_input("Pilot License Number: ")
            if pilot_license:
                search["pilot_license_number"] = pilot_license

            flight_hours = optional_input("Minimum Pilot Flight Hours: ")
            if flight_hours:
                try:
                    search["from_pilot_flight_hours"] = float(flight_hours)
                except:
                    pass

            origin_airport = optional_input("Origin Airport Code: ")
            if origin_airport:
                search["origin_airport_code"] = origin_airport.upper()

            origin_country = optional_input("Origin Country Code: ")
            if origin_country:
                search["origin_country_code"] = origin_country.upper()

            destination_airport = optional_input("Destination Airport Code: ")
            if destination_airport:
                search["destination_airport_code"] = destination_airport.upper()

            destination_country = optional_input("Destination Country Code: ")
            if destination_country:
                search["destination_country_code"] = destination_country.upper()

        print("""
Flight View field names:
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

Type the fields, separated by spaces, to be displayed in the table.
Pressing Enter without inserting any input displays all the fields.
    """)
        projection = optional_input("Field names: ")
        if projection:
            search["projection"] = re.split(r"\s+", projection)

        return search


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
menu.add_option(ExitMenuOption())


# Main application loop.
while True:

    # Display available actions.
    menu.display_options()

    # Read and execute user choice.
    menu.choose_option(int(input("Enter your choice: ")))
