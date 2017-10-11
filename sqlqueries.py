publicStructuresTableName = 'publicStructures'
buyOrdersTableName = 'buyOrders'
sellOrdersTableName = 'sellOrders'
secFilteredMarketsViewName = 'secMarkets'
secFilteredBuyOrdersViewName = 'secBuyOrders'
secFilteredSellOrdersViewName = 'secSellOrders'
whatIsCheaperThanJitaViewName = 'cheaperThanJita'
itemPackagedSizesViewName = 'packSizes'
jitaHighestBidViewName = 'jitaHigh'

names = {
    'pubStruct' : 'publicStructures',
    'buy' : 'buyOrders',
    'sell' : 'sellOrders',
    'secMarket' : 'secFilteredMarket',
    'secBuy' : 'secFilteredBuyOrders',
    'secSell' : 'secFilteredSellOrders',
    'packSize' : 'itemPackagedSizes',
    'cheap' : 'secFilteredSellCheaperThanJita',
    'jitaHigh' : 'jitaHighestBidPrices'
}

test = '''SELECT
    *
FROM
    {cheap}
ORDER BY
    maxMargin DESC
LIMIT 30;
'''.format_map(names)


def getWhatInWhereHasCheaperThanJita(groupby='region_id'):
    names['groupby']=groupby
    return '''SELECT
    type_id,
    {groupby}
FROM
    {cheap}
WHERE
    maxMargin > ? AND maxProfitPerM3 > ?
GROUP BY
    type_id,
    {groupby};
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
''').format_map(names)


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
    order_id,
    type_id,
    location_id,
    region_id,
    volume_total,
    volume_remain,
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
    volume_remain,
    price,
    updated,
    issued
FROM
    {secSell}
WHERE
    type_id = ?
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
    volume_remain,
    price,
    min_volume,
    range,
    updated,
    issued
FROM
    {secBuy}
WHERE
    type_id = ?
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


def pickHaulToJitaTargetSellOrders():
    return '''SELECT
    order_id,
    location_id,
    volume_remain,
    price
FROM
    {secSell}
WHERE
    {secSell}.type_id = ?
    AND
    region_id = ?
'''


def pickHaulToJitaItemLocationCombination():
    return '''SELECT
    {cheap}.type_id,
    region_id
FROM
    {cheap}
'''.format_map(names)


jitaBelongTo = {
    'region': 'region_id = 10000002',
    'constellation': 'constellationID = 20000020',
    'solarsystem': 'solarSystemID = 30000142',
    'station': 'location_id = 50003760'
}

def createWhatWhereCheaperThanJitaView(taxCoeff=0.98,
                                       minProfitPerM3=500.0,
                                       minMargin=0.1,
                                       jitaRange='constellation'):
    assert 0 < taxCoeff < 1
    names['priceCoeff'] = taxCoeff / (1 + minMargin)
    names['buyLocConstraint'] = jitaBelongTo[jitaRange]
    names['minProfitPerM3'] = minProfitPerM3
    names['taxCoeff'] = taxCoeff
    return '''DROP VIEW IF EXISTS {jitaHigh};
CREATE TEMP VIEW {jitaHigh}
AS
SELECT
    type_id,
    MAX(price) AS maxBid
FROM
    {secBuy}
WHERE
    {buyLocConstraint}
GROUP BY
    type_id;
DROP VIEW IF EXISTS {cheap};
CREATE TEMP VIEW {cheap}
AS
SELECT
    order_id,
    volume_remain,
    {packSize}.volume AS size,
    {secSell}.type_id AS type_id,
    location_id,
    region_id,
    constellationID,
    solarSystemID
FROM {secSell}
INNER JOIN {jitaHigh} ON
    {jitaHigh}.type_id = {secSell}.type_id
INNER JOIN {packSize} ON
    {packSize}.typeID = {secSell}.type_id
WHERE
    {secSell}.price < {jitaHigh}.maxBid * {priceCoeff}
    AND
    {jitaHigh}.maxBid * {taxCoeff} - {secSell}.price >
    {minProfitPerM3} * {packSize}.volume;
'''.format_map(names)
