import sqlite3
from typing import List, Optional
from abc import ABC, abstractmethod
from model import FlightView, FlightSearch, PilotView, Flight


# Abstract base class for database operations.
#
# Implements the Template Method pattern:
# - Connection and transaction management are centralized.
# - Subclasses only provide operation-specific logic via _execute().
class DBOperation(ABC):

    # Implement the operation-specific database logic.
    # This method is executed inside a managed transaction.
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
            raise e

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


# Database initialization operation.
#
# Creates the application schema and inserts seed data
# the first time the database is used.
class InitializeAirlineSchema(DBOperation):
    # Tables required for the application to be considered initialized.
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

    # Verify that every required application table exists.
    #
    # Returns:
    #     True if all required tables are present.
    #     False otherwise.
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


# Search operation for flights.
#
# Dynamically builds a SELECT query based on the supplied
# FlightSearch criteria, including:
# - projection (selected columns)
# - filtering
# - sorting
# - required table joins
#
# Results are returned as FlightView objects.
class SearchFlights(DBOperation):
    # Separator used when building comma-separated SQL fragments.
    __COMMA_SEP = ", "

    # Placeholder temporarily inserted into the query.
    # Later replaced with the JOIN clauses actually required.
    __PROJECTION_REPLACE_KEY = "==PROJECTION=="

    # Maps FlightSearch/View field names to their corresponding
    # SQL column references.
    #
    # This allows the search API to remain independent of the
    # underlying database schema.
    __COLUMN_NAME_MAP = {
        "flight_id": "f.FlightID",
        "flight_number": "f.FlightNumber",
        "status": "f.Status",
        "departure": "f.Departure",
        "arrival": "f.Arrival",
        "pilot_full_name": "p.FullName",
        "pilot_license_number": "p.LicenseNumber",
        "pilot_contact_number": "p.ContactNumber",
        "pilot_flight_hours": "p.FlightHours",
        "origin_airport_code": "o.AirportCode",
        "origin_airport_name": "o.AirportName",
        "origin_country": "co.CountryName",
        "destination_airport_code": "d.AirportCode",
        "destination_airport_name": "d.AirportName",
        "destination_country": "cd.CountryName",
    }

    __result: List[FlightView] = []

    def __init__(self, search: FlightSearch):
        super().__init__()

        # By default select every supported view column.
        # Projection can later be narrowed to requested fields only.
        projection = self.__COMMA_SEP.join(
            [f"{value} as {key}" for key, value in self.__COLUMN_NAME_MAP.items()]
        )
        # Restrict SELECT clause to explicitly requested columns.
        if "projection" in search and len(search["projection"]) > 0:
            projection = self.__COMMA_SEP.join(
                [f"{self.__COLUMN_NAME_MAP[p]} as {p}" for p in search["projection"]]
            )

        # Build the query incrementally.
        # JOIN clauses are inserted later once required tables
        # can be determined from the selected columns and filters.
        query = f"SELECT {projection} FROM FLIGHT AS f{self.__PROJECTION_REPLACE_KEY}"

        # Build WHERE conditions dynamically.
        # filter_clause tracks whether the next condition should
        # start with WHERE or be appended with AND.
        filter_clause = "WHERE"
        if "flight_id" in search and search["flight_id"] is not None:
            query = f"{query} {filter_clause} f.FlightID = {search["flight_id"]}"
            filter_clause = "AND"
        if "flight_number" in search and search["flight_number"] is not None:
            query = (
                f"{query} {filter_clause} f.FlightNumber = '{search["flight_number"]}'"
            )
            filter_clause = "AND"
        if "status" in search and search["status"] is not None:
            query = f"{query} {filter_clause} f.Status = '{search["status"].value}'"
            filter_clause = "AND"
        if "departure_date" in search and search["departure_date"] is not None:
            query = f"{query} {filter_clause} DATE(f.Departure) = DATE('{search["departure_date"]}')"
            filter_clause = "AND"
        if (
            "includes_pilot_full_name" in search
            and search["includes_pilot_full_name"] is not None
        ):
            query = f"{query} {filter_clause} p.FullName LIKE '%{search["includes_pilot_full_name"]}%'"
            filter_clause = "AND"
        if (
            "pilot_license_number" in search
            and search["pilot_license_number"] is not None
        ):
            query = f"{query} {filter_clause} p.LicenseNumber = '{search["pilot_license_number"]}'"
            filter_clause = "AND"
        if (
            "from_pilot_flight_hours" in search
            and search["from_pilot_flight_hours"] is not None
        ):
            query = f"{query} {filter_clause} p.FlightHours > {search["from_pilot_flight_hours"]}"
            filter_clause = "AND"
        if (
            "origin_airport_code" in search
            and search["origin_airport_code"] is not None
        ):
            query = f"{query} {filter_clause} o.AirportCode = '{search["origin_airport_code"]}'"
            filter_clause = "AND"
        if (
            "origin_country_code" in search
            and search["origin_country_code"] is not None
        ):
            query = f"{query} {filter_clause} co.CountryCode = '{search["origin_country_code"]}'"
            filter_clause = "AND"
        if (
            "destination_airport_code" in search
            and search["destination_airport_code"] is not None
        ):
            query = f"{query} {filter_clause} d.AirportCode = '{search["destination_airport_code"]}'"
            filter_clause = "AND"
        if (
            "destination_country_code" in search
            and search["destination_country_code"] is not None
        ):
            query = f"{query} {filter_clause} cd.CountryCode = '{search["destination_country_code"]}'"

        # Generate ORDER BY clause using the mapped database columns.
        if "order" in search and search["order"]:
            query_order = self.__COMMA_SEP.join(
                [
                    f"{self.__COLUMN_NAME_MAP[field]} {direction}"
                    for field, direction in search["order"]
                ]
            )
            query = f"{query} ORDER BY {query_order}"

        # Add only the joins actually required by the query.
        #
        # This keeps generated SQL simpler and avoids unnecessary
        # table joins when related data is not requested.
        join_tables = ""
        if "p." in query:
            join_tables = f"{join_tables} LEFT JOIN PILOT AS p ON f.PilotID = p.PilotID"
        if "o." in query:
            join_tables = f"{join_tables} JOIN AIRPORT AS o ON f.OriginID = o.AirportID"
        if "co." in query:
            join_tables = (
                f"{join_tables} JOIN COUNTRY AS co ON o.CountryID = co.CountryID"
            )
        if "d." in query:
            join_tables = (
                f"{join_tables} JOIN AIRPORT AS d ON f.DestinationID = d.AirportID"
            )
        if "cd." in query:
            join_tables = (
                f"{join_tables} JOIN COUNTRY AS cd ON d.CountryID = cd.CountryID"
            )

        # Replace the placeholder with the generated JOIN clauses.
        query = query.replace(self.__PROJECTION_REPLACE_KEY, join_tables, 1)

        self.__query = f"{query};"

    # Return the search results mapped as FlightView objects.
    @property
    def query_result(self) -> List[FlightView]:
        return self.__result

    # Return the SQL query
    @property
    def query(self) -> str:
        return self.__query

    # Execute the generated query and map each row to a FlightView.
    #
    # Column aliases are used so database rows can be unpacked
    # directly into the FlightView constructor.
    def _execute(self):
        self.__result = []

        self._cursor.execute(self.__query)

        columns = [col[0] for col in self._cursor.description]
        for row in self._cursor.fetchall():
            self.__result.append(FlightView(**dict(zip(columns, row))))


# Lookup operation that retrieves a pilot by license number.
#
# Returns a PilotView projection or None when no matching
# pilot exists.
class FindPilotByLicenseNumber(DBOperation):
    def __init__(self, license_number: str):
        super().__init__()

        # Select only presentation-oriented pilot fields and
        # alias them to match PilotView constructor parameters.
        self.__query = f"""SELECT PilotID as pilot_id, 
            FullName as full_name,
            LicenseNumber as license_number,
            ContactNumber as contact_number,
            FlightHours as flight_hours  
            FROM PILOT WHERE LicenseNumber = '{license_number}';"""
        self.__result = None

    @property
    def query_result(self) -> Optional[PilotView]:
        return self.__result

    @property
    def query(self) -> str:
        return self.__query

    # Execute the lookup and convert the result row
    # into a PilotView object.
    def _execute(self):
        self.__result = None

        self._cursor.execute(self.__query)

        result = self._cursor.fetchone()

        if not result:
            return

        columns = [col[0] for col in self._cursor.description]
        self.__result = PilotView(**dict(zip(columns, result)))


# Lookup operation that retrieves a flight by its primary key.
#
# Returns a fully populated Flight domain entity or None
# if the flight does not exist.
class FindFlightByID(DBOperation):
    def __init__(self, flight_id: int):
        super().__init__()
        self.__query = f"""SELECT FlightID as flight_id,
        FlightNumber as flight_number,
        Status as status,
        Departure as departure,
        Arrival as arrival,
        PilotID as pilot_id,
        OriginID as origin_id,
        DestinationID as destination_id
        FROM FLIGHT WHERE FlightID = {flight_id};"""
        self.__result = None

    @property
    def query_result(self) -> Optional[Flight]:
        return self.__result

    # Convert the database record into a Flight domain object.
    #
    # Flight.from_db_fetch() handles transformation from
    # database-specific formats to domain types.
    def _execute(self):
        self.__result = None

        self._cursor.execute(self.__query)

        result = self._cursor.fetchone()

        if not result:
            return

        columns = [col[0] for col in self._cursor.description]
        self.__result = Flight.from_db_fetch(**dict(zip(columns, result)))


# Persists a new flight record.
#
# After successful insertion, the generated database
# identifier is available through created_flight_id.
class CreateFlight(DBOperation):
    def __init__(self, flight: Flight):
        super().__init__()

        # Parameterized INSERT statement.
        #
        # Parameter binding protects against SQL injection and
        # delegates value formatting to the SQLite driver.
        self.__sql_script = """INSERT INTO FLIGHT 
        (FlightNumber, Status, Departure, Arrival, PilotID, OriginID, DestinationID)
        VALUES (?, ?, ?, ?, ?, ?, ?)"""
        self.__flight = flight
        self.__created_flight_id = None

    # Database-generated identifier of the newly created flight.
    @property
    def created_flight_id(self) -> Optional[int]:
        return self.__created_flight_id

    # Insert the flight and capture the generated primary key.
    def _execute(self):
        self._cursor.execute(
            self.__sql_script,
            (
                self.__flight.flight_number[1:],
                self.__flight.status.value,
                self.__flight.departure,
                self.__flight.arrival,
                self.__flight.pilot_id,
                self.__flight.origin_id,
                self.__flight.destination_id,
            ),
        )

        self.__created_flight_id = self._cursor.lastrowid


# Updates an existing flight record using the current
# state of a Flight domain entity.
class UpdateFlight(DBOperation):
    def __init__(self, flight: Flight) -> None:
        super().__init__()

        # Parameterized UPDATE statement used to synchronize
        # domain entity changes back to the database.
        self.__sql_script = """UPDATE FLIGHT SET 
        FlightNumber = ?, Status = ?, Departure = ?, Arrival = ?, PilotID = ?, OriginID = ?, DestinationID = ?
        WHERE FlightID = ?"""
        self.__flight = flight

    # Persist all mutable flight properties to the database.
    def _execute(self):
        self._cursor.execute(
            self.__sql_script,
            (
                self.__flight.flight_number[1:],
                self.__flight.status.value,
                self.__flight.departure,
                self.__flight.arrival,
                self.__flight.pilot_id,
                self.__flight.origin_id,
                self.__flight.destination_id,
                self.__flight.flight_id,
            ),
        )
