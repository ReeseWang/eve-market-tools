publicStructuresTableName = 'publicStructures'
buyOrdersTableName = 'buyOrders'
sellOrdersTableName = 'sellOrders'
secFilteredMarketsViewName = 'secMarkets'
secFilteredBuyOrdersViewName = 'secBuyOrders'
secFilteredSellOrdersViewName = 'secSellOrders'
whatIsCheaperThanJitaViewName = 'cheaperThanJita'
itemPackagedSizesViewName = 'packSizes'
jitaHighestBidViewName = 'jitaHigh'

test = '''SELECT
    *
FROM
    {table}
ORDER BY
    maxMargin DESC
LIMIT 30;
'''.format(table=whatIsCheaperThanJitaViewName)


def getWhatInWhereHasCheaperThanJita(groupby='region_id'):
    return '''SELECT
    type_id,
    {groupby}
FROM
    {table}
WHERE
    maxMargin > ? AND maxProfitPerM3 > ?
GROUP BY
    type_id,
    {groupby};
'''.format(table=whatIsCheaperThanJitaViewName,
           groupby=goupby)


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
'''.format(secBuy=secFilteredBuyOrdersViewName,
           buy=buyOrdersTableName,
           secSell=secFilteredSellOrdersViewName,
           sell=sellOrdersTableName,
           secMarket=secFilteredMarketsViewName)


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
    solarSystemName,
    stationName,
    volume_remain,
    price,
    min_volume,
    range,
    updated,
    issued
FROM
    {table}
WHERE
    type_id = ?
ORDER BY
    price DESC
LIMIT 20;
'''.format(table=secFilteredBuyOrdersViewName)


def createItemPackagedVolumesView():
    return '''CREATE TEMP VIEW IF NOT EXISTS {view}
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
'''.format(view=itemPackagedSizesViewName)


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
    region_id,
FROM
    {cheap}
'''.format(cheap=whatIsCheaperThanJitaViewName)


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
    priceCoeff = taxCoeff / (1 + minMargin)
    buyLocationConstraint = jitaBelongTo[jitaRange]
    return '''DROP VIEW IF EXISTS {jitaHigh};
CREATE TEMP VIEW {jitaHigh}
AS
SELECT
    type_id,
    MAX(price) as maxBid
FROM
    {secBuy}
WHERE
    {buyLocationConstraint}
GROUP BY
    type_id;
DROP VIEW IF EXISTS {cheap};
CREATE TEMP VIEW {cheap}
AS
SELECT
    order_id,
    volume_remain,
    {size}.volume AS size,
    {secSell}.type_id AS type_id,
    location_id,
    region_id,
    constellationID,
    solarSystemID
FROM {secSell}
INNER JOIN {jitaHigh} ON
    jitaHigh.type_id = {secSell}.type_id
INNER JOIN {size} ON
    {size}.typeID = {secSell}.type_id
WHERE
    {secSell}.price < jitaHigh.maxBid * {priceCoeff}
    AND
    jitaHigh.maxBid * {taxCoeff} - {secSell}.price >
    {minProfitPerM3} * {size}.volume;
'''.format(cheap=whatIsCheaperThanJitaViewName,
           size=itemPackagedSizesViewName,
           secBuy=secFilteredBuyOrdersViewName,
           secSell=secFilteredSellOrdersViewName,
           priceCoeff=priceCoeff,
           taxCoeff=taxCoeff,
           minProfitPerM3=minProfitPerM3,
           buyLocationConstraint=buyLocationConstraint,
           jitaHigh=jitaHighestBidViewName
           )
