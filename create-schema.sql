-- =====================================================
-- COUNTRY TABLE
-- =====================================================
   CREATE TABLE COUNTRY (CountryID INTEGER PRIMARY KEY, CountryCode TEXT NOT NULL UNIQUE, CountryName TEXT NOT NULL);

-- =====================================================
-- AIRPORT TABLE
-- =====================================================
   CREATE TABLE AIRPORT (
          AirportID INTEGER PRIMARY KEY,
          AirportCode TEXT NOT NULL UNIQUE,
          AirportName TEXT NOT NULL,
          CountryID INTEGER NOT NULL,
          FOREIGN KEY (CountryID) REFERENCES COUNTRY (CountryID)
          );

-- =====================================================
-- PILOT TABLE
-- =====================================================
   CREATE TABLE PILOT (
          PilotID INTEGER PRIMARY KEY,
          FullName TEXT NOT NULL,
          ContactNumber TEXT,
          LicenseNumber TEXT NOT NULL UNIQUE,
          -- This Check enforces that FlightHours is not a negative number.
          -- This field has a floating point (REAL datatype) to capture
          -- single short flights experience.
          FlightHours REAL NOT NULL CHECK (FlightHours >= 0.0)
          );

-- =====================================================
-- FLIGHT TABLE
-- =====================================================
   CREATE TABLE FLIGHT (
          FlightID INTEGER PRIMARY KEY,
          FlightNumber TEXT NOT NULL UNIQUE,
          -- This Check enforces that Status is always of one of:
          -- S -> Scheduled
          -- O -> Operational
          -- T -> Terminated
          Status TEXT NOT NULL CHECK (Status IN ('S', 'O', 'T')),
          Departure DATETIME NOT NULL,
          Arrival DATETIME NOT NULL,
          PilotID INTEGER,
          OriginID INTEGER NOT NULL,
          DestinationID INTEGER NOT NULL,
          FOREIGN KEY (PilotID) REFERENCES PILOT (PilotID),
          FOREIGN KEY (OriginID) REFERENCES AIRPORT (AirportID),
          FOREIGN KEY (DestinationID) REFERENCES AIRPORT (AirportID),
          -- This Check enforces that a operational flight (Status='O')
          -- or terminated flight (Status='T') must have a pilot assigned to it.
          CHECK (
          Status = 'S'
       OR PilotID IS NOT NULL
          )
          );