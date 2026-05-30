from typing import List, Optional
from abc import ABC, abstractmethod
from db_operation import (
    InitializeAirlineSchema,
    SearchFlights,
    FindPilotByLicenseNumber,
    CreateFlight,
    FindFlightByID,
    UpdateFlight,
)
from model import FlightSearch, FlightStatus, Flight
from utils import print_table, optional_input, print_sql_script
from datetime import date, datetime
import re


# Base class for all command-line menu actions.
#
# Each menu option exposes a display name and encapsulates
# the logic executed when the user selects that option.
class MenuOption(ABC):
    def __init__(self):
        super().__init__()
        self._name = ""

    # Public read-only property for the menu option name.
    @property
    def name(self) -> str:
        return self._name

    # Execute the menu action.
    # Concrete implementations define the user interaction
    # and business workflow for the option.
    @abstractmethod
    def execute_option(self):
        pass


# Interactive menu option that allows users to search
# flights using arbitrary combinations of filters,
# projections, and ordering rules.
class SearchFlightsMenuOption(MenuOption):

    def __init__(self):
        super().__init__()

        self._name = "Search Flights"

    # Gather search criteria, execute the search,
    # display the generated SQL, and present the results.
    def execute_option(self):
        print()
        search = self.__scan_flight_search()
        print()
        search_flights = SearchFlights(search)
        print("SQL Query:\n")
        print_sql_script(search_flights.query)
        print()
        search_flights.execute_transaction()
        if not search_flights.query_result:
            print("Empty flight search result.")
            return
        print_table(search_flights.query_result, search.get("projection", []))

    # Collect search criteria from user input.
    #
    # Invalid values are silently ignored so that users can
    # provide only the filters they care about.
    #
    # Returns:
    #     A FlightSearch dictionary containing the selected
    #     filters, projection, and ordering options.
    def __scan_flight_search(self) -> FlightSearch:
        # FlightSearch is built incrementally from the
        # user's optional filtering criteria.
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

        # Allow the user to limit which columns are returned.
        # An empty projection means "return all columns".
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

        # Allow multi-column sorting.
        #
        # Example:
        #   +departure -flight_number
        #
        # Means:
        #   departure ASC,
        #   flight_number DESC
        print("""
Type the + or - symbol followed by a column names, separated by spaces, to apply hierarchical ordering onto the search.
The symbol before the column name defines the order direction (+ for ascending, - for descending).
Press Enter without inserting any input to not apply any ordering.
    """)
        orders = optional_input("Orders: ")
        if orders:
            # Extract the optional ordering prefix (+ or -)
            # from each requested sort field.
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


# Displays all scheduled flights assigned to a pilot.
#
# The user provides a pilot license number and the system
# retrieves upcoming scheduled flights ordered by departure time.
class ViewPilotScheduleMenuOption(MenuOption):
    def __init__(self):
        super().__init__()
        self._name = "View Pilot Schedule"

    # Retrieve pilot details and display the pilot's
    # scheduled flights in chronological order.
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
        # Build a predefined search that returns only
        # scheduled flights for the selected pilot.
        search: FlightSearch = {}
        search["pilot_license_number"] = license_number
        search["status"] = FlightStatus.SCHEDULED
        # Display only schedule and destination related
        # information rather than the complete flight record.
        search["projection"] = [
            "departure",
            "arrival",
            "origin_airport_name",
            "origin_country",
            "destination_airport_name",
            "destination_country",
        ]
        # Sort flights chronologically.
        search["order"] = [("departure", "asc")]
        search_flights = SearchFlights(search)
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


# Creates a new flight from user-supplied information
# and persists it to the database.
class NewFlightMenuOption(MenuOption):
    def __init__(self):
        super().__init__()
        self._name = "Add a New Flight"

    # Collect flight information, validate it through the
    # Flight domain model, and save it if valid.
    def execute_option(self):
        flight = self.__create_flight_from_input()
        if flight:
            print()
            create_flight = CreateFlight(flight)
            create_flight.execute_transaction()
            print(
                f"Flight (ID: {create_flight.created_flight_id}) created successfully!"
            )

    # Convert user input into a Flight domain object.
    #
    # Domain validation is delegated to the Flight constructor.
    #
    # Returns:
    #     A valid Flight instance or None when validation fails.
    def __create_flight_from_input(self) -> Optional[Flight]:
        try:
            flight_number = optional_input("Flight number (F999999): ")
            print("Available statuses:")
            # Display valid flight status values to help
            # the user enter a valid status code.
            for status in FlightStatus:
                print(f"{status.value} - {status.label}")
            status_input = optional_input("Status: ")
            status = None
            if status_input:
                try:
                    status = FlightStatus(status_input.upper())
                except:
                    pass
            departure_input = optional_input("Departure datetime (YYYY-MM-DD HH:MM): ")
            arrival_input = optional_input("Arrival datetime (YYYY-MM-DD HH:MM): ")
            pilot_input = optional_input("Pilot ID (leave blank if none): ")
            origin_input = optional_input("Origin ID: ")
            destination_input = optional_input("Destination ID: ")

            # Convert textual input into strongly typed domain values.
            departure = (
                datetime.strptime(departure_input, "%Y-%m-%d %H:%M")
                if departure_input
                else None
            )
            arrival = (
                datetime.strptime(arrival_input, "%Y-%m-%d %H:%M")
                if arrival_input
                else None
            )
            pilot_id = int(pilot_input) if pilot_input else None
            origin_id = int(origin_input) if origin_input else None
            destination_id = int(destination_input) if destination_input else None

            # Construction triggers all domain-level validation rules.
            flight = Flight(
                flight_number=flight_number,
                status=status,
                departure=departure,
                arrival=arrival,
                pilot_id=pilot_id,
                origin_id=origin_id,
                destination_id=destination_id,
            )

            return flight

        except ValueError as e:
            print("\nValidation errors:")
            print(e)

        except Exception as e:
            print(f"\nUnexpected error: {e}")

        return None


# Allows users to modify the departure and arrival times
# of an existing flight.
class UpdateFlightScheduleMenuOption(MenuOption):
    def __init__(self):
        super().__init__()
        self._name = "Update Flight Schedule"

    # Load an existing flight, display its current schedule,
    # collect updated values, and persist the changes.
    def execute_option(self):
        flight_id_input = optional_input("Flight ID: ")

        if not flight_id_input:
            return

        flight_id = None

        try:
            flight_id = int(flight_id_input)

        except:
            pass

        if not flight_id:
            return

        print()

        # Retrieve the current flight state before applying updates.
        find_flight_by_id = FindFlightByID(flight_id)
        find_flight_by_id.execute_transaction()
        flight = find_flight_by_id.query_result

        if not flight:
            print(f"The flight (ID: {flight_id}) does not exist.")
            return

        print(f"Flight Number: {flight.flight_number}")
        print(f"Departure: {flight.departure.strftime("%Y-%m-%d %H:%M")}")
        print(f"Arrival: {flight.arrival.strftime("%Y-%m-%d %H:%M")}")

        try:
            departure_input = optional_input("Departure (YYYY-MM-DD HH:MM): ")
            arrival_input = optional_input("Arrival (YYYY-MM-DD HH:MM): ")

            departure = (
                datetime.strptime(departure_input, "%Y-%m-%d %H:%M")
                if departure_input
                else None
            )
            arrival = (
                datetime.strptime(arrival_input, "%Y-%m-%d %H:%M")
                if arrival_input
                else None
            )

            print()

            # Apply domain validation before saving changes.
            #
            # The Flight entity enforces business rules such as:
            # - arrival must be after departure
            # - terminated flights cannot be modified
            flight.update_schedule(departure, arrival)

            update_flight = UpdateFlight(flight)
            update_flight.execute_transaction()
            print("Flight schedule updated successfully!")

        except ValueError as e:
            print("\nValidation errors:")
            print(e)

        except Exception as e:
            print(f"\nUnexpected error: {e}")


# Assigns a pilot to an existing flight.
#
# Validation is performed by the Flight domain model
# before changes are persisted.
class AssignPilotToFlightMenuOption(MenuOption):
    def __init__(self):
        super().__init__()
        self._name = "Assign Pilot to Flight"

    # Load the flight, collect the pilot identifier,
    # validate the assignment, and save the updated flight.
    def execute_option(self):
        flight_id_input = optional_input("Flight ID: ")

        if not flight_id_input:
            return

        flight_id = None

        try:
            flight_id = int(flight_id_input)

        except:
            pass

        if not flight_id:
            return

        print()

        find_flight_by_id = FindFlightByID(flight_id)
        find_flight_by_id.execute_transaction()
        flight = find_flight_by_id.query_result

        if not flight:
            print(f"The flight (ID: {flight_id}) does not exist.")
            return

        print(f"Flight Number: {flight.flight_number}")
        print(f"Pilot ID: {flight.pilot_id if flight.pilot_id else "Not assigned"}")

        try:
            pilot_input = optional_input("Pilot ID: ")
            pilot_id = int(pilot_input) if pilot_input else None

            print()

            # Delegate assignment rules to the Flight entity.
            #
            # Example rules:
            # - pilot must exist
            # - pilot identifier must be positive
            flight.assign_pilot(pilot_id)

            update_flight = UpdateFlight(flight)
            update_flight.execute_transaction()
            print("Pilot assigned to flight successfully!")

        except ValueError as e:
            print("\nValidation errors:")
            print(e)

        except Exception as e:
            print(f"\nUnexpected error: {e}")


# Terminates the application immediately.
#
# No additional cleanup is required because all database
# operations manage their own connections and transactions.
class ExitMenuOption(MenuOption):
    def __init__(self):
        super().__init__()
        self._name = "Exit"

    # Terminates the program immediately.
    def execute_option(self):
        exit(0)


# Manages registration, display, and execution
# of command-line menu options.
class Menu:
    def __init__(self):

        # Registered menu actions displayed to the user.
        self.__menu_options: List[MenuOption] = []

    # Adds a new option to the menu.
    def add_option(self, menu_option: MenuOption):
        self.__menu_options.append(menu_option)

    # Displays all menu options to the user.
    def display_options(self):
        print("\nMenu:")

        # # Display menu options using 1-based numbering.
        for i, menu_option in enumerate(self.__menu_options):
            print(f"{i + 1}. {menu_option.name}")

    # Execute the selected menu option after validating
    # that the supplied menu number exists.
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


# Ensure the database schema and seed data exist before
# the interactive application becomes available.
InitializeAirlineSchema().execute_transaction()

# Create the command-line menu.
menu = Menu()

# Register available application workflows.
#
# The order of registration determines the order shown
# in the menu presented to the user.
menu.add_option(NewFlightMenuOption())
menu.add_option(SearchFlightsMenuOption())
menu.add_option(UpdateFlightScheduleMenuOption())
menu.add_option(ViewPilotScheduleMenuOption())
menu.add_option(AssignPilotToFlightMenuOption())
menu.add_option(ExitMenuOption())


# Main application loop.
#
# Continuously display the menu and execute the selected
# action until the user chooses to exit.
while True:

    # Display available actions.
    menu.display_options()

    # Read the selected menu number and dispatch
    # execution to the corresponding menu option.
    menu.choose_option(int(input("Enter your choice: ")))
