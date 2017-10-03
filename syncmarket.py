#!/usr/bin/env python3

import requests
import sqlite3
from concurrent.futures import ThreadPoolExecutor
import logging
import sde
from datetime import datetime
from esiauth import authedClient
import time

dbPath = './db/market.sqlite'

try:
    # tornado is bundled with pretty formatter - try using it
    from tornado.log import enable_pretty_logging
    enable_pretty_logging()
except Exception:
    print("Pretty logging disabled.")
    pass


def endlessGet(url):
    while True:
        res = requests.get(url)
        if res.ok:
            return res
        else:
            time.sleep(5)


def execSQL(sql, conn):
    logger.debug("Executing SQL:\n" + sql)
    c = conn.execute(sql)
    return c.rowcount


def initDB(pconn):
    # logger.debug("Connecting to '{}'...".format(dbPath))
    # conn = sqlite3.connect(dbPath)
    execSQL("DROP TABLE IF EXISTS buyOrdersInserting;", pconn)
    execSQL('\n'.join([
        "CREATE TABLE buyOrdersInserting (",
        "order_id INTEGER PRIMARY KEY,",
        "type_id INTEGER NOT NULL,",
        "location_id INTEGER NOT NULL,",
        "region_id INTEGER NOT NULL,",
        "volume_total INTEGER NOT NULL CHECK (volume_total > 0),",
        "volume_remain INTEGER NOT NULL CHECK (volume_remain > 0),",
        "min_volume INTEGER NOT NULL CHECK (min_volume > 0),",
        "price REAL NOT NULL CHECK (price > 0),",
        "range TEXT NOT NULL CHECK (range IN ('station', 'region', ",
        "'solarsystem', '1', '2', '3', '4', '5', '10', '20', '30', '40')),",
        "duration INTEGER NOT NULL CHECK (duration > 0),",
        "issued INTEGER NOT NULL);"]), pconn)
    execSQL("DROP TABLE IF EXISTS sellOrdersInserting;", pconn)
    execSQL('\n'.join([
        "CREATE TABLE sellOrdersInserting (",
        "order_id INTEGER PRIMARY KEY,",
        "type_id INTEGER NOT NULL,",
        "location_id INTEGER NOT NULL,",
        "region_id INTEGER NOT NULL,",
        "volume_total INTEGER NOT NULL CHECK (volume_total > 0),",
        "volume_remain INTEGER NOT NULL CHECK (volume_remain > 0),",
        "price REAL NOT NULL CHECK (price > 0),",
        "duration INTEGER NOT NULL CHECK (duration > 0),",
        # "volume_total INTEGER NOT NULL,",
        # "volume_remain INTEGER NOT NULL,",
        # "price REAL NOT NULL,",
        # "duration INTEGER NOT NULL,",
        "issued INTEGER NOT NULL);"]), pconn)
    execSQL("DROP TABLE IF EXISTS publicStructuresInserting;", pconn)
    execSQL('\n'.join([
        "CREATE TABLE publicStructuresInserting (",
        "structure_id INTEGER PRIMARY KEY,",
        "name TEXT NOT NULL,",
        "solar_system_id INTEGER NOT NULL);"]), pconn)
    pass

    # conn.commit()
    # conn.close()


def buyOrderTuple(order, reg):
    assert isinstance(reg, int)
    return (int(order['order_id']),
            int(order['type_id']),
            int(order['location_id']),
            reg,
            int(order['volume_total']),
            int(order['volume_remain']),
            int(order['min_volume']),
            order['price'],
            order['range'],
            int(order['duration']),
            int(datetime.strptime(order['issued'],
                                  '%Y-%m-%dT%H:%M:%SZ').timestamp())
            )


def sellOrderTuple(order, reg):
    assert isinstance(reg, int)
    return (int(order['order_id']),
            int(order['type_id']),
            int(order['location_id']),
            reg,
            int(order['volume_total']),
            int(order['volume_remain']),
            order['price'],
            int(order['duration']),
            int(datetime.strptime(order['issued'],
                                  '%Y-%m-%dT%H:%M:%SZ').timestamp())
            )


def fillOrderTupleLists(ordersList, buyTupleList, sellTupleList, reg):
    for order in ordersList:
        if order['is_buy_order']:
            buyTupleList.append(buyOrderTuple(order, reg))
        else:
            sellTupleList.append(sellOrderTuple(order, reg))


def execSQLMany(sql, conn, data):
    logger.debug("Executing SQL:\n" + sql)
    c = conn.executemany(sql, data)
    return c.rowcount


def insertDB(ordersList, conn, reg):
    rows = 0
    if(ordersList):
        buyTupleList = []
        sellTupleList = []
        fillOrderTupleLists(ordersList,
                            buyTupleList,
                            sellTupleList,
                            reg)
        if(buyTupleList):
            rows += execSQLMany("INSERT OR IGNORE INTO buyOrdersInserting VALUES "
                                "({});".format(','.join(11*'?')),
                                conn, buyTupleList)
        if(sellTupleList):
            rows += execSQLMany("INSERT OR IGNORE INTO sellOrdersInserting VALUES "
                                "({});".format(','.join(9*'?')),
                                conn, sellTupleList)
        # for order in ordersList:
        #     if order['is_buy_order']:
        #         execSQL("INSERT INTO buyOrdersInserting VALUES "
        #                 "({});".format(','.join(11*'?')),
        #                 conn, data=buyOrderTuple(order, reg))
        #     else:
        #         execSQL("INSERT INTO sellOrdersInserting VALUES "
        #                 "({});".format(','.join(10*'?')),
        #                 conn, data=sellOrderTuple(order, reg))
        #     pass
        pass
    return rows


def getOrders(pordersList, pregionNames, preg, ppage):
    req = endlessGet('https://esi.tech.ccp.is/latest/markets/' +
                       str(preg) + '/orders/?datasource=tranquility' +
                       '&order_type=all&page=' + str(ppage))
    assert req.status_code == 200
    pordersList.extend(req.json())
    # insertDB(req.json(), int(reg))
    logger.info('Region {} Page {} received.'.format(pregionNames[preg], ppage))
    pass


def getFirstPage(porders, ppageCounts, pregionNames, preg):
    req = endlessGet('https://esi.tech.ccp.is/latest/markets/' +
                       preg + '/orders/?datasource=tranquility' +
                       '&order_type=all&page=1')
    assert req.status_code == 200
    # return req.json(), int(req.headers['x-pages'])
    porders[preg] = req.json()
    ppageCounts[preg] = int(req.headers['x-pages'])
    logger.info('Got the first page of orders in {0}. {0} has {1} '
                'pages of orders. Last modified '
                'at {2}.'.format(pregionNames[preg], ppageCounts[preg], req.headers['last-modified']))
    # insertDB(req.json(), int(reg))


def getRegionsList():
    logger.info('Getting region list...')
    req = endlessGet('https://esi.tech.ccp.is/'
                       'latest/universe/regions/?datasource=tranquility')
    assert req.status_code == 200
    return req.json()


def getStructuresList():
    logger.info('Getting structures list...')
    req = endlessGet('https://esi.tech.ccp.is/'
                       'latest/universe/structures/?datasource=tranquility')
    assert req.status_code == 200
    res = req.json()
    logger.info("There are {} public structures.".format(len(res)))
    return res


def fetchMarketData(porders, pregionsStr, pregionNames):
    pageCounts = dict.fromkeys(pregionsStr, 0)
    with ThreadPoolExecutor(max_workers=20) as executor:
        for reg in pregionsStr:
            executor.submit(getFirstPage, porders, pageCounts, pregionNames, reg)
            pass

    with ThreadPoolExecutor(max_workers=20) as executor:
        for reg in pregionsStr:
            try:
                assert pageCounts[reg] >= 1
            except AssertionError:
                import sys
                sys.exit("{}, {}".format(reg, pageCounts[reg]))
            for page in range(1, pageCounts[reg]):
                executor.submit(getOrders, porders[reg], pregionNames, reg, page+1)
                pass
            pass
        pass


def replaceTable(pconn):
    sql = """DROP TABLE IF EXISTS buyOrders;
ALTER TABLE buyOrdersInserting RENAME TO buyOrders;
DROP TABLE IF EXISTS sellOrders;
ALTER TABLE sellOrdersInserting RENAME TO sellOrders;
DROP TABLE IF EXISTS publicStructures;
ALTER TABLE publicStructuresInserting RENAME TO publicStructures;"""
    logger.debug("Executing SQL:\n" + sql)
    pconn.executescript(sql)


def fillStructuresTupleList(pstructs, ptuplelist):
    for key, struct in pstructs.items():
        ptuplelist.append((int(key), struct['name'], struct['solar_system_id']))
        pass
    pass


def insertStructuresDB(pstructs, pconn):
    structuresTupleList = []
    fillStructuresTupleList(pstructs, structuresTupleList)
    rows = execSQLMany("INSERT OR IGNORE INTO publicStructuresInserting VALUES "
                       "(?,?,?);", pconn, structuresTupleList)
    logger.debug('Structures: {} rows inserted.'.format(rows))
    structuresCount = len(pstructs)
    if rows != structuresCount:
        logger.warning('{} structures not inserted into the '
                       'database'.format(structuresCount - rows))


def filterOrders(pconn):
    rows = execSQL('\n'.join([
        "DELETE",
        "FROM",
        "buyOrdersInserting",
        "WHERE (",
        "   (location_id > 100000000) AND (",
        "       location_id NOT IN (",
        "           SELECT",
        "           structure_id",
        "           FROM",
        "           publicStructuresInserting",
        "       )",
        "   )",
        ");"]), pconn)
    if rows != 0:
        logger.info("{} buy orders deleted because of not located in a public "
                    "structure.".format(rows))
    rows = execSQL('\n'.join([
        "DELETE",
        "FROM",
        "sellOrdersInserting",
        "WHERE (",
        "   (location_id > 100000000) AND (",
        "       location_id NOT IN (",
        "           SELECT",
        "           structure_id",
        "           FROM",
        "           publicStructuresInserting",
        "       )",
        "   )",
        ");"]), pconn)
    if rows != 0:
        logger.info("{} sell orders deleted because of not located in a public "
                    "structure.".format(rows))

def dumpToDatabse(porders, pstructs, pregionsStr, pregionNames):
    logger.debug("Connecting to '{}'...".format(dbPath))
    conn = sqlite3.connect(dbPath)
    initDB(conn)
    insertStructuresDB(pstructs, conn)
    for reg in pregionsStr:
        ordersCount = len(porders[reg])
        if ordersCount != 0:
            logger.info('Region {} has {} '
                        'orders, inserting into '
                        'database'.format(pregionNames[reg], ordersCount))
            rows = insertDB(porders[reg], conn, int(reg))
            logger.debug('Region {}: {} inserted.'.format(pregionNames[reg],
                                                        rows))
            if ordersCount != rows:
                logger.warning('Region {} has {} order(s) not inserted into the '
                            'database.'.format(pregionNames[reg],
                                                ordersCount - rows))
                pass
            pass
        pass
    filterOrders(conn)
    replaceTable(conn)
    conn.commit()
    conn.close()
    pass


def getStructureInfo(pstructs, pID, client):
    pstructs[pID] =\
        client.get('https://esi.tech.ccp.is/latest/universe/structures/' +
                pID + '/?datasource=tranquility').json()
    logger.info('Structure {} info received, its name is '
                '{}.'.format(pID, pstructs[pID]['name']))


def fetchStructuresInfo(pstructs, pIDList):
    client = authedClient()
    client.getCharacterID()
    with ThreadPoolExecutor(max_workers=100) as executor:
        for ID in pIDList:
            # Single thread test
            # getStructureInfo(pstructs, ID, client)
            executor.submit(getStructureInfo, pstructs, ID, client)
            pass


def main():
    regionsInt = getRegionsList()
    structuresInt = getStructuresList()

    # structuresInt = structuresInt[0:100]

    regionsStr = []
    for reg in regionsInt:
        regionsStr.append(str(reg))
        pass
    structuresStr = []
    for struct in structuresInt:
        structuresStr.append(str(struct))
        pass

    orders = dict.fromkeys(regionsStr, [])
    structures = dict.fromkeys(structuresStr, None)

    regionNames = dict.fromkeys(regionsStr, None)

    for reg in regionsInt:
        regionNames[str(reg)] = sde.getItemName(reg)

    fetchStructuresInfo(structures, structuresStr)
    if len(structures) != len(structuresStr):
        logger.warning("Info of {} strutures not retrieved "
                       "successfully".format(
                           len(structuresStr) - len(structures)))
    fetchMarketData(orders, regionsStr, regionNames)
    dumpToDatabse(orders, structures, regionsStr, regionNames)


logger = logging.getLogger()
if __name__ == '__main__':
    logger.setLevel(logging.DEBUG)
    main()
