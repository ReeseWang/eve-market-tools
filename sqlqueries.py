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
    mapSolarSystems.constellationID AS constellationID,
    mapSolarSystems.security AS security
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
    solarSystemID,
    x,
    y,
    z,
    constellationID,
    security
FROM
    staStations
WHERE
    security > 0.45
;
'''
hiSecBuyOrdersView = '''
CREATE TEMP VIEW IF NOT EXISTS hiSecBuyOrders
AS
SELECT
    order_id,
    type_id,
    location_id,
    region_id,
    volume_total,
    volume_remain,
    min_volume,
    price,
    range,
    duration,
    issued,
    hiSecMarkets.stationName AS stationName,
    hiSecMarkets.solarSystemID AS solarSystemID,
    hiSecMarkets.constellationID AS constellationID,
    hiSecMarkets.security AS security
FROM
    buyOrders
INNER JOIN hiSecMarkets ON
    hiSecMarkets.stationID = buyOrders.location_id
;
'''
