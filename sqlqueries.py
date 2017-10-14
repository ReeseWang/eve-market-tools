names = {
    # Public Structures table created by syncdyn
    'pubStruct': 'publicStructures',
    # Buy orders table created by syncdyn
    'buy': 'buyOrders',
    # Sell orders table created by syncdyn
    'sell': 'sellOrders',
    # View of all markets (stations and citadels)
    'market': 'markets',
    # View of markets (stations and citadels) which sit in solar systems
    # whose security status satisfies given constraints.
    'secMarket': 'secFilteredMarkets',
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
    'jitaHigh': 'jitaHighestBidPrices',
    # Table of selected buy-sell order pairs which can bring proit
    'orderPairs': 'orderPairsOfInterest',
    'orderPairsView': 'orderPairsOfInterestView'
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
    return ('''CREATE TEMP VIEW IF NOT EXISTS {market}
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
    staStations;
DROP VIEW IF EXISTS {secMarket};
CREATE TEMP VIEW IF NOT EXISTS {secMarket}
AS
SELECT * FROM {market}
WHERE
    security >= {minSec} AND security <= {maxSec};
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


insertOrderPairsQuery = (
    "INSERT INTO {orderPairs} VALUES (".format_map(names) +
    ','.join(3*'?') +
    ");"
)

summarizeRegionProfit = '''SELECT
    buyRegionName,
    SUM(buyPrice * volume) AS buyTotalISK,
    SUM((? * sellPrice - buyPrice) * volume) AS profit,
    SUM(sellPrice * volume) AS sellTotalISK,
    sellRegionName
FROM
    {orderPairsView}
GROUP BY
    buyRegionID, sellRegionID
ORDER BY
    profit DESC
;'''.format_map(names)

buyListInRegion = '''SELECT
    buyTypeID,
    buyTypeName,
    SUM(volume) AS volTotal,
    MIN(buyPrice) AS minBuy,
    MAX(sellPrice) AS maxSell,
    MIN(sellPrice) AS minSell,
    SUM((? * sellPrice - buyPrice) * volume) AS profit,
FROM
    {orderPairsView}
WHERE
    buyRegionID = ?
GROUP BY
    buyTypeID
ORDER BY
    profit DESC
;'''.format_map(names)

def createOrderPairsTable():
    # WARNING: From now on, 'buy' and 'sell' is from traders
    # perspective.
    return '''DROP TABLE IF EXISTS {orderPairs};
CREATE TABLE {orderPairs} (
    buyOrderID INTEGER NOT NULL,
    sellOrderID INTEGER NOT NULL,
    volume INTEGER NOT NULL,
    PRIMARY KEY (buyOrderID, sellOrderID)
);
'''.format_map(names)


def createOrderPairsView():
    return '''DROP VIEW IF EXISTS {orderPairsView};
CREATE TEMP VIEW {orderPairsView}
AS
SELECT
    {orderPairs}.volume AS volume,
    {orderPairs}.buyOrderID AS buyOrderID,
    {sell}.type_id AS buyTypeID,
    {sell}.price AS buyPrice,
    {sell}.location_id AS buyLocationID,
    {sell}.region_id AS buyRegionID,
    {sell}.volume_total AS buyVolumeTotal,
    {sell}.volume_remain AS buyVolumeRemain,
    {sell}.price AS buyPrice,
    {sell}.duration AS buyDuration,
    {sell}.issued AS buyIssued,
    {sell}.updated AS buyUpdated,
    {market}B.solarSystemID AS buySolarSystemID,
    {market}B.constellationID AS buyConstellationID,
    {market}B.security AS buySecurity,
    {market}B.stationName AS buyStationName,
    invTypesB.typeName AS buyTypeName,
    invNamesSSB.itemName AS buySolarSystemName,
    invNamesCB.itemName AS buyConstellationName,
    invNamesRB.itemName AS buyRegionName,
    {orderPairs}.sellOrderID AS sellOrderID,
    {buy}.type_id AS sellTypeID,
    {buy}.location_id AS sellLocationID,
    {buy}.region_id AS sellRegionID,
    {buy}.volume_total AS sellVolumeTotal,
    {buy}.volume_remain AS sellVolumeRemain,
    {buy}.min_volume AS sellMinVolume,
    {buy}.price AS sellPrice,
    {buy}.range AS sellRange,
    {buy}.duration AS sellDuration,
    {buy}.issued AS sellIssued,
    {buy}.updated AS sellUpdated,
    {market}S.solarSystemID AS sellSolarSystemID,
    {market}S.constellationID AS sellConstellationID,
    {market}S.security AS sellSecurity,
    {market}S.stationName AS sellStationName,
    invTypesS.typeName AS sellTypeName,
    invNamesSSS.itemName AS sellSolarSystemName,
    invNamesCS.itemName AS sellConstellationName,
    invNamesRS.itemName AS sellRegionName
FROM
    {orderPairs}
INNER JOIN {sell} ON
    {sell}.order_id = {orderPairs}.buyOrderID
INNER JOIN {buy} ON
    {buy}.order_id = {orderPairs}.sellOrderID
INNER JOIN {market} AS {market}S ON
    {market}S.stationID = sellLocationID
INNER JOIN {market} AS {market}B ON
    {market}B.stationID = buyLocationID
INNER JOIN invNames AS invNamesSSS ON
    invNamesSSS.itemID = sellSolarSystemID
INNER JOIN invNames AS invNamesCS ON
    invNamesCS.itemID = sellConstellationID
INNER JOIN invNames AS invNamesRS ON
    invNamesRS.itemID = sellRegionID
INNER JOIN invNames AS invNamesSSB ON
    invNamesSSB.itemID = buySolarSystemID
INNER JOIN invNames AS invNamesCB ON
    invNamesCB.itemID = buyConstellationID
INNER JOIN invNames AS invNamesRB ON
    invNamesRB.itemID = buyRegionID
INNER JOIN invTypes AS invTypesS ON
    invTypesS.typeID = sellTypeID
INNER JOIN invTypes AS invTypesB ON
    invTypesB.typeID = buyTypeID
;'''.format_map(names)


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
