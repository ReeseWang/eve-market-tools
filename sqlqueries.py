publicStructuresTableName = 'publicStructures'
buyOrdersTableName = 'buyOrders'
sellOrdersTableName = 'sellOrders'
secFilteredMarketsViewName = 'secMarkets'
secFilteredBuyOrdersViewName = 'secBuyOrders'
secFilteredSellOrdersViewName = 'secSellOrders'


def createSecFilteredMarketsView(minSec=-1, maxSec=1):
    return ('''DROP VIEW IF EXISTS {0};
CREATE TEMP VIEW IF NOT EXISTS {0}
AS'''.format(secFilteredMarketsViewName) + '''
SELECT
    structure_id AS stationID,
    {0}.name AS stationName,
    solar_system_id as solarSystemId,
    {0}.x AS x,
    {0}.y AS y,
    {0}.z AS z,
    mapSolarSystems.constellationID AS constellationID,
    mapSolarSystems.security AS security
FROM
    {0}
INNER JOIN mapSolarSystems ON
    mapSolarSystems.solarSystemId = {0}.solar_system_id
WHERE'''.format(publicStructuresTableName) + '''
    {minSec} < mapSolarSystems.security AND mapSolarSystems.security < {maxSec}
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
    {minSec} < security AND security < {maxSec}
;
''').format(minSec=minSec, maxSec=maxSec)


def createSecFilteredOrdersView():
    return '''CREATE TEMP VIEW IF NOT EXISTS {secBuy}
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
    {secMarket}.stationName AS stationName,
    {secMarket}.solarSystemID AS solarSystemID,
    {secMarket}.constellationID AS constellationID,
    {secMarket}.security AS security,
    invNamesSS.itemName AS solarSystemName,
    invNamesC.itemName AS constellationName,
    invNamesR.itemName AS regionName
FROM
    {buy}
INNER JOIN {secMarket} ON
    {secMarket}.stationID = {buy}.location_id
INNER JOIN invNames AS invNamesSS ON
    invNamesSS.itemID = {secMarket}.solarSystemID
INNER JOIN invNames AS invNamesC ON
    invNamesC.itemID = {secMarket}.constellationID
INNER JOIN invNames AS invNamesR ON
    invNamesR.itemID = region_id
;
CREATE TEMP VIEW IF NOT EXISTS {secSell}
AS
SELECT
    order_id,
    type_id,
    location_id,
    region_id,
    volume_total,
    volume_remain,
    price,
    duration,
    issued,
    {secMarket}.stationName AS stationName,
    {secMarket}.solarSystemID AS solarSystemID,
    {secMarket}.constellationID AS constellationID,
    {secMarket}.security AS security,
    invNamesSS.itemName AS solarSystemName,
    invNamesC.itemName AS constellationName,
    invNamesR.itemName AS regionName
FROM
    {sell}
INNER JOIN {secMarket} ON
    {secMarket}.stationID = {sell}.location_id
INNER JOIN invNames AS invNamesSS ON
    invNamesSS.itemID = {secMarket}.solarSystemID
INNER JOIN invNames AS invNamesC ON
    invNamesC.itemID = {secMarket}.constellationID
INNER JOIN invNames AS invNamesR ON
    invNamesR.itemID = region_id
;
'''.format(secBuy=secFilteredBuyOrdersViewName,
           buy=buyOrdersTableName,
           secSell=secFilteredSellOrdersViewName,
           sell=sellOrdersTableName,
           secMarket=secFilteredMarketsViewName)


def listSellOrders():
    return '''SELECT
    security,
    regionName,
    constellationName,
    stationName,
    volume_remain,
    price
FROM
    {table}
WHERE
    type_id = ?
ORDER BY
    price ASC
LIMIT 20;
'''.format(table=secFilteredSellOrdersViewName)


def listBuyOrders():
    return '''SELECT
    security,
    regionName,
    constellationName,
    stationName,
    volume_remain,
    price,
    min_volume,
    range
FROM
    {table}
WHERE
    type_id = ?
ORDER BY
    price DESC
LIMIT 20;
'''.format(table=secFilteredBuyOrdersViewName)
