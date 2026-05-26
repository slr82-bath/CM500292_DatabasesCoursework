from typing import List
from abc import ABC, abstractmethod
from db_operation import InitializeAirlineSchemaDBOperation, SearchFlightsDBOperation
from utils import print_table
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
    query_projection = None
    raw_input = input("Field names: ").strip()
    if raw_input:
      query_projection = re.split(r"\s+", raw_input)
    print()
    search_flights = SearchFlightsDBOperation(query_projection)
    print("SQL Query:\n")
    print(search_flights.query, "\n")
    search_flights.execute_transaction()
    print_table(search_flights.query_result, query_projection)


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


# Names of all required schema tables.
table_names = ["PILOT", "COUNTRY", "AIRPORT", "FLIGHT"]

# Create schema and seed database if needed.
InitializeAirlineSchemaDBOperation(table_names).execute_transaction()

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