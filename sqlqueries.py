hiSecMarketsView = '''
CREATE TEMP VIEW IF NOT EXISTS hiSecMarkets
AS
SELECT
  structure_id AS stationID,
  publicStructures.name AS stationName,
  solar_system_id as solarSystemId,
  publicStructures.x AS x,
  publicStructures.y AS y,
  publicStructures.z AS z,
  mapSolarSystems.constellationID AS constellationID
FROM
  publicStructures
INNER JOIN mapSolarSystems ON
  mapSolarSystems.solarSystemId = publicStructures.solar_system_id
WHERE
  mapSolarSystems.security > 0.45
UNION ALL
SELECT
  stationID,
  stationName,
  solarSystemId,
  x,
  y,
  z,
  constellationID
FROM
  staStations
WHERE
  security > 0.45
;
'''
