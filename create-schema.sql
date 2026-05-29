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
          FlightHours REAL NOT NULL
          );

-- =====================================================
-- FLIGHT TABLE
-- =====================================================
   CREATE TABLE FLIGHT (
          FlightID INTEGER PRIMARY KEY,
          FlightNumber TEXT NOT NULL UNIQUE,
          Status TEXT NOT NULL,
          Departure DATETIME NOT NULL,
          Arrival DATETIME NOT NULL,
          PilotID INTEGER,
          OriginID INTEGER NOT NULL,
          DestinationID INTEGER NOT NULL,
          FOREIGN KEY (PilotID) REFERENCES PILOT (PilotID),
          FOREIGN KEY (OriginID) REFERENCES AIRPORT (AirportID),
          FOREIGN KEY (DestinationID) REFERENCES AIRPORT (AirportID)
          );