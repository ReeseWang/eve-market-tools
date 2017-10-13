names = {
    # Public Structures table created by syncdyn
    'pubStruct': 'publicStructures',
    # Buy orders table created by syncdyn
    'buy': 'buyOrders',
    # Sell orders table created by syncdyn
    'sell': 'sellOrders',
    # View of markets (stations and citadels) which sit in solar systems
    # whose security status satisfies given constraints.
    'secMarket': 'secFilteredMarket',
    # View of buy orders which sits in said markets.
    'secBuy': 'secFilteredBuyOrders',
    # View of sell orders which sits in said markets.
    'secSell': 'secFilteredSellOrders',
    # View of item sizes, packaged size if it has this property.
    'packSize': 'itemPackagedSizes',
    # View of buy orders in Jita,
    # can be expanded to be in same system/constellation/region with Jita
    # according to given parameter.
    # Security filtered.
    'jitaBuyOrders': 'jitaBuyOrders',
    # Table of sell orders which is cheaper than Jita highest bid price
    # and satisfies some constraints.
    'cheap': 'secFilteredSellCheaperThanJita',
    # View of highest bid prices of each type of items in Jita
    'jitaHigh': 'jitaHighestBidPrices'
}

test = '''SELECT
    *
FROM
    {cheap}
ORDER BY
    maxMargin DESC
LIMIT 30;
'''.format_map(names)


def createSecFilteredMarketsView(minSec=-1, maxSec=1):
    names['minSec'] = minSec
    names['maxSec'] = maxSec
    return ('''DROP VIEW IF EXISTS {secMarket};
CREATE TEMP VIEW IF NOT EXISTS {secMarket}
AS
SELECT
    structure_id AS stationID,
    {pubStruct}.name AS stationName,
    solar_system_id as solarSystemId,
    {pubStruct}.x AS x,
    {pubStruct}.y AS y,
    {pubStruct}.z AS z,
    mapSolarSystems.constellationID AS constellationID,
    mapSolarSystems.security AS security
FROM
    {pubStruct}
INNER JOIN mapSolarSystems ON
    mapSolarSystems.solarSystemId = {pubStruct}.solar_system_id
WHERE
    {minSec} <= mapSolarSystems.security
    AND
    mapSolarSystems.security <= {maxSec}
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
    {minSec} <= security AND security <= {maxSec}
;
''').format_map(names)


def createSecFilteredOrdersView():
    return '''CREATE TEMP VIEW IF NOT EXISTS {secBuy}
AS
SELECT
    order_id AS orderID,
    type_id AS typeID,
    location_id AS locationID,
    region_id AS regionID,
    volume_total AS volumeTotal,
    volume_remain AS volumeRemain,
    min_volume AS minVolume,
    price,
    range,
    duration,
    issued,
    updated,
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
    order_id AS orderID,
    type_id AS typeID,
    location_id AS locationID,
    region_id AS regionID,
    volume_total AS volumeTotal,
    volume_remain AS volumeRemain,
    price,
    duration,
    issued,
    updated,
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
'''.format_map(names)


def listSellOrders():
    return '''SELECT
    security,
    regionName,
    solarSystemName,
    stationName,
    volumeRemain,
    price,
    updated,
    issued
FROM
    {secSell}
WHERE
    typeID = ?
ORDER BY
    price ASC
LIMIT 20;
'''.format_map(names)


def listBuyOrders():
    return '''SELECT
    security,
    regionName,
    solarSystemName,
    stationName,
    volumeRemain,
    price,
    minVolume,
    range,
    updated,
    issued
FROM
    {secBuy}
WHERE
    typeID = ?
ORDER BY
    price DESC
LIMIT 20;
'''.format_map(names)


def createItemPackagedVolumesView():
    return '''CREATE TEMP VIEW IF NOT EXISTS {packSize}
AS
SELECT
    typeID,
    volume
FROM
    invVolumes
UNION ALL
SELECT
    typeID,
    volume
FROM
    invTypes
WHERE
    typeID NOT IN (SELECT typeID FROM invVolumes);
'''.format_map(names)


def pickHaulToJitaTargetBuyOrders():
    return '''SELECT
    orderID,
    locationID,
    volumeRemain,
    minVolume,
    price
FROM
    {jitaBuyOrders}
WHERE
    typeID = ?
ORDER BY
    price DESC;
'''.format_map(names)


def pickHaulToJitaTargetSellOrders():
    return '''SELECT
    orderID,
    locationID,
    volumeRemain,
    price
FROM
    {cheap}
WHERE
    typeID = ?
    AND
    regionID = ?
ORDER BY
    price ASC;
'''.format_map(names)


def pickHaulToJitaItemLocationCombination():
    return '''SELECT
    typeID,
    regionID
FROM
    {cheap}
GROUP BY
    typeID,
    regionID;
'''.format_map(names)


jitaBelongTo = {
    'region': 'regionID = 10000002',
    'constellation': 'constellationID = 20000020',
    'solarsystem': 'solarSystemID = 30000142',
    'station': 'locationID = 50003760'
}


def createCheapThanJitaTable(taxCoeff=0.98,
                             minProfitPerM3=500.0,
                             minMargin=0.1,
                             jitaRange='constellation'):
    assert 0 < taxCoeff < 1
    names['priceCoeff'] = taxCoeff / (1 + minMargin)
    names['buyLocConstraint'] = jitaBelongTo[jitaRange]
    names['minProfitPerM3'] = minProfitPerM3
    names['taxCoeff'] = taxCoeff
    return '''DROP VIEW IF EXISTS {jitaBuyOrders};
CREATE TEMP VIEW {jitaBuyOrders}
AS
SELECT
    *
FROM
    {secBuy}
WHERE
    {buyLocConstraint};
DROP VIEW IF EXISTS {jitaHigh};
CREATE TEMP VIEW {jitaHigh}
AS
SELECT
    typeID,
    MAX(price) AS maxBid
FROM
    {jitaBuyOrders}
GROUP BY
    typeID;
DROP TABLE IF EXISTS {cheap};
CREATE TABLE {cheap}
AS
SELECT
    orderID,
    {secSell}.price AS price,
    volumeRemain,
    {secSell}.typeID AS typeID,
    locationID,
    regionID,
    constellationID,
    solarSystemID
FROM {secSell}
INNER JOIN {jitaHigh} ON
    {jitaHigh}.typeID = {secSell}.typeID
INNER JOIN {packSize} ON
    {packSize}.typeID = {secSell}.typeID
WHERE
    {secSell}.price < {jitaHigh}.maxBid * {priceCoeff}
    AND
    {jitaHigh}.maxBid * {taxCoeff} - {secSell}.price >
    {minProfitPerM3} * {packSize}.volume;
'''.format_map(names)
