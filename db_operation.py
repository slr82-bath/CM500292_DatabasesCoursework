import sqlite3
from typing import List
from abc import ABC, abstractmethod
from model import FlightView, FlightSearch


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
  # Names of all required schema tables.
  __table_names = ["PILOT", "COUNTRY", "AIRPORT", "FLIGHT"]
  
  def __init__(self):
    super().__init__()

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
                    AND name IN {tuple(self.__table_names)}
              ) = {len(self.__table_names)};
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
  __COMMA_SEP = ", "
  __PROJECTION_REPLACE_KEY = "==PROJECTION=="
  __FIELD_NAME_MAP = {
    "flight_id": "f.FlightID as flight_id",
    "flight_number": "f.FlightNumber as flight_number",
    "status": "f.Status as status",
    "departure": "f.Departure as departure",
    "arrival": "f.Arrival as arrival",
    "pilot_full_name": "p.FullName as pilot_full_name",
    "pilot_license_number": "p.LicenseNumber as pilot_license_number",
    "pilot_contact_number": "p.ContactNumber as pilot_contact_number",
    "pilot_flight_hours": "p.FlightHours as pilot_flight_hours",
    "origin_airport_code": "o.AirportCode as origin_airport_code",
    "origin_airport_name": "o.AirportName as origin_airport_name",
    "origin_country": "co.CountryName as origin_country",
    "destination_airport_code": "d.AirportCode as destination_airport_code",
    "destination_airport_name": "d.AirportName as destination_airport_name",
    "destination_country": "cd.CountryName as destination_country"
  }

  __result: List[FlightView] = []

  def __init__(self, search: FlightSearch):
    super().__init__()

    projection = self.__COMMA_SEP.join(list(self.__FIELD_NAME_MAP.values()))
    if "projection" in search and len(search["projection"]) > 0:
      projection = self.__COMMA_SEP.join([self.__FIELD_NAME_MAP[p] for p in search["projection"]])

    query = f"SELECT {projection} FROM FLIGHT AS f{self.__PROJECTION_REPLACE_KEY}"

    if "flight_id" in search and search["flight_id"] is not None:
      query = f"{query} WHERE f.FlightID = {search["flight_id"]}"
    if "flight_number" in search and search["flight_number"]:
      query = f"{query} WHERE f.FlightNumber = '{search["flight_number"]}'"
    if "status" in search and search["status"] is not None:
      query = f"{query} WHERE f.Status = '{search["status"].value}'"
    if "date_of_departure" in search and search["date_of_departure"] is not None:
      query = f"{query} WHERE DATE(f.Departure) = DATE('{search["date_of_departure"]}')"    
    if "includes_pilot_full_name" in search and search["includes_pilot_full_name"]:
      query = f"{query} WHERE p.FullName LIKE '%{search["includes_pilot_full_name"]}%'"
    if "pilot_license_number" in search and search["pilot_license_number"]:
      query = f"{query} WHERE p.LicenseNumber = '{search["pilot_license_number"]}'"
    if "from_pilot_flight_hours" in search and search["from_pilot_flight_hours"]:
      query = f"{query} WHERE p.FlightHours > {search["from_pilot_flight_hours"]}"
    if "origin_airport_code" in search and search["origin_airport_code"]:
      query = f"{query} WHERE o.AirportCode = '{search["origin_airport_code"]}'"
    if "origin_country_code" in search and search["origin_country_code"]:
      query = f"{query} WHERE co.CountryCode = '{search["origin_country_code"]}'"
    if "destination_airport_code" in search and search["destination_airport_code"]:
      query = f"{query} WHERE d.AirportCode = '{search["destination_airport_code"]}'"
    if "destination_country_code" in search and search["destination_country_code"]:
      query = f"{query} WHERE cd.CountryCode = '{search["destination_country_code"]}'"
    
    join_tables = ""
    if "p." in query:
      join_tables = f"{join_tables} LEFT JOIN PILOT AS p ON f.PilotID = p.PilotID"
    if "o." in query:
      join_tables = f"{join_tables} JOIN AIRPORT AS o ON f.OriginID = o.AirportID"
    if "co." in query:
      join_tables = f"{join_tables} JOIN COUNTRY AS co ON o.CountryID = co.CountryID"
    if "d." in query:
      join_tables = f"{join_tables} JOIN AIRPORT AS d ON f.DestinationID = d.AirportID"
    if "cd." in query:
      join_tables = f"{join_tables} JOIN COUNTRY AS cd ON d.CountryID = cd.CountryID"

    query = query.replace(self.__PROJECTION_REPLACE_KEY, join_tables, 1)

    self.__query = f"{query};"

  # Return the fetched list of fights
  @property
  def query_result(self) -> List[FlightView]:
    return self.__result

  # Return the SQL query
  @property
  def query(self) -> str:
    return self.__query

  def _execute(self):
    self.__result = []

    self._cursor.execute(self.__query)

    columns = [col[0] for col in self._cursor.description]
    for row in self._cursor.fetchall():
      self.__result.append(FlightView(**dict(zip(columns, row))))
