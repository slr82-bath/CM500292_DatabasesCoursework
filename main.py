import sqlite3
from typing import List
from abc import ABC, abstractmethod


# Abstract base class that defines the common structure
# for all database operations.
class DBOperation(ABC):

  # Each subclass must implement its own database logic.
  @abstractmethod
  def _execute(self):
    pass

  # Handles the complete transaction lifecycle:
  # - Open connection
  # - Begin transaction
  # - Execute operation
  # - Commit or rollback on failure
  # - Close connection
  def execute_transaction(self):
    try:
      self.__get_connection()

      # Enable SQLite foreign key constraints.
      # SQLite disables them by default.
      self._cursor.execute("PRAGMA foreign_keys = ON;")

      # Start a database transaction manually.
      self._cursor.execute("BEGIN")

      # Execute the subclass-specific operation.
      self._execute()

      # Save all changes if execution succeeds.
      self.__connection.commit()

    except Exception as e:
      # Undo all changes if an error occurs.
      self.__connection.rollback()
      print(e)

    finally:
      # Always close the database connection, if present.
      if self.__connection:
        self.__connection.close()

  # Establishes a connection to the SQLite database
  # and creates a cursor for executing SQL statements.
  def __get_connection(self):
    try:
      self.__connection = sqlite3.connect("AirlineDB.db")
      self._cursor = self.__connection.cursor()

    except Exception as e:
      print("Error: failed to connect to the database")
      raise e


# Database operation responsible for:
# - Creating the schema
# - Populating initial data
class InitializeAirlineSchemaDBOperation(DBOperation):
  def __init__(self, tables: List[str]):
    super().__init__()

    # List of expected tables used to verify initialization.
    self.__tables = tables

  # Executes schema initialization only if the
  # database has not already been initialized.
  def _execute(self):
    if not self.__is_initialized():
      self.__open_sql_scripts()
      self.__initialize_schema()
      self.__generate_initial_data()

  # Checks whether all required tables already exist.
  def __is_initialized(self):

    # Query sqlite_schema to count matching tables.
    self._cursor.execute(f"""
      SELECT (
                SELECT SUM(1)
                  FROM sqlite_schema
                  WHERE type = 'table'
                    AND name IN {tuple(self.__tables)}
              ) = {len(self.__tables)};
    """)

    # Returns True if all expected tables exist.
    return self._cursor.fetchone()[0]

  # Reads SQL scripts from external files.
  def __open_sql_scripts(self):
    try:
      # SQL script for creating schema tables.
      with open("./create-schema.sql", "r", encoding="utf-8") as sql_file:
        self.__create_schema_sql = sql_file.read()

      # SQL script for inserting sample data.
      with open("./generate-data.sql", "r", encoding="utf-8") as sql_file:
        self.__generate_data_sql = sql_file.read()

    except Exception as e:
      print("Error: failed to read SQL scripts")
      raise e

  # Executes the schema creation script.
  def __initialize_schema(self):
    try:
      self._cursor.executescript(self.__create_schema_sql)

    except Exception as e:
      print("Error: failed to create tables")
      raise e

  # Executes the script that inserts initial data.
  def __generate_initial_data(self):
    try:
      self._cursor.executescript(self.__generate_data_sql)

    except Exception as e:
      print("Error: failed to insert initial data")
      raise e


# Database operation that retrieves all flights.
class SearchFlightsDBOperation(DBOperation):

  def _execute(self):

    # Retrieve all rows from the FLIGHT table.
    self._cursor.execute("SELECT * FROM FLIGHT")

    # Print each flight record.
    for row in self._cursor.fetchall():
      print(row)


# Abstract representation of a menu option in the CLI.
class MenuOption(ABC):
  def __init__(self):
    super().__init__()
    self._name = ''
  
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
    SearchFlightsDBOperation().execute_transaction()


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
table_names = ['PILOT', 'COUNTRY', 'AIRPORT', 'FLIGHT']

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