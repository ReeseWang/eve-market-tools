#!/usr/bin/env python3

import requests
import sqlite3
from concurrent.futures import ThreadPoolExecutor
import logging
import sde
from datetime import datetime

dbPath = './db/market.sqlite'

try:
    # tornado is bundled with pretty formatter - try using it
    from tornado.log import enable_pretty_logging
    enable_pretty_logging()
except Exception:
    print("Pretty logging disabled.")
    pass


def execSQL(sql, conn):
    logger.debug("Executing SQL:\n" + sql)
    conn.execute(sql)


def initDB():
    logger.debug("Connecting to '{}'...".format(dbPath))
    conn = sqlite3.connect(dbPath)
    execSQL("DROP TABLE IF EXISTS buyOrderInserting;", conn)
    execSQL('\n'.join([
        "CREATE TABLE buyOrderInserting (",
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
        "issued INTEGER NOT NULL);"]), conn)
    execSQL("DROP TABLE IF EXISTS sellOrderInserting;", conn)
    execSQL('\n'.join([
        "CREATE TABLE sellOrderInserting (",
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
        "issued INTEGER NOT NULL);"]), conn)
    conn.commit()
    conn.close()


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
    conn.executemany(sql, data)


def insertDB(ordersList, conn, reg):
    if(ordersList):
        buyTupleList = []
        sellTupleList = []
        fillOrderTupleLists(ordersList,
                            buyTupleList,
                            sellTupleList,
                            reg)
        if(buyTupleList):
            execSQLMany("INSERT OR IGNORE INTO buyOrderInserting VALUES "
                        "({});".format(','.join(11*'?')),
                        conn, buyTupleList)
        if(sellTupleList):
            execSQLMany("INSERT OR IGNORE INTO sellOrderInserting VALUES "
                        "({});".format(','.join(9*'?')),
                        conn, sellTupleList)
        # for order in ordersList:
        #     if order['is_buy_order']:
        #         execSQL("INSERT INTO buyOrderInserting VALUES "
        #                 "({});".format(','.join(11*'?')),
        #                 conn, data=buyOrderTuple(order, reg))
        #     else:
        #         execSQL("INSERT INTO sellOrderInserting VALUES "
        #                 "({});".format(','.join(10*'?')),
        #                 conn, data=sellOrderTuple(order, reg))
        #     pass
        pass
    pass


def getOrders(ordersList, reg, page):
    req = requests.get('https://esi.tech.ccp.is/latest/markets/' +
                       str(reg) + '/orders/?datasource=tranquility' +
                       '&order_type=all&page=' + str(page))
    assert req.status_code == 200
    ordersList.extend(req.json())
    # insertDB(req.json(), int(reg))
    logger.info('Region {} Page {} received.'.format(regionNames[reg], page))
    pass


def getFirstPage(ordersDict, pageCountsDict, reg):
    logger.info('Getting the first page of orders '
                'in region {}'.format(regionNames[reg]))
    req = requests.get('https://esi.tech.ccp.is/latest/markets/' +
                       reg + '/orders/?datasource=tranquility' +
                       '&order_type=all&page=1')
    assert req.status_code == 200
    # return req.json(), int(req.headers['x-pages'])
    ordersDict[reg] = req.json()
    pageCountsDict[reg] = int(req.headers['x-pages'])
    logger.info('Region {} has {} '
                'pages'.format(regionNames[reg], pageCountsDict[reg]))
    # insertDB(req.json(), int(reg))


def getRegionList():
    logger.info('Getting region list...')
    req = requests.get('https://esi.tech.ccp.is/'
                       'latest/universe/regions/?datasource=tranquility')
    assert req.status_code == 200
    return req.json()


def fetchMarketData():
    with ThreadPoolExecutor(max_workers=10) as executor:
        for reg in regionsStr:
            executor.submit(getFirstPage, orders, pageCounts, reg)
            pass

    with ThreadPoolExecutor(max_workers=10) as executor:
        for reg in regionsStr:
            try:
                assert pageCounts[reg] >= 1
            except AssertionError:
                import sys
                sys.exit("{}, {}".format(reg, pageCounts[reg]))
            for page in range(1, pageCounts[reg]):
                executor.submit(getOrders, orders[reg], reg, page+1)
                pass
            pass
        pass


def dumpToDatabse():
    logger.debug("Connecting to '{}'...".format(dbPath))
    conn = sqlite3.connect(dbPath)
    for reg in regionsStr:
        logger.info('Region {} has {} '
                    'orders, inserting into '
                    'database'.format(regionNames[reg], len(orders[reg])))
        insertDB(orders[reg], conn, int(reg))
        pass
    conn.commit()
    conn.close()


logger = logging.getLogger()
if __name__ == '__main__':
    logger.setLevel(logging.DEBUG)

initDB()

if __name__ == '__main__':
    regionsInt = getRegionList()

    regionsStr = []
    for reg in regionsInt:
        regionsStr.append(str(reg))
        pass
    orders = dict.fromkeys(regionsStr, [])
    pageCounts = dict.fromkeys(regionsStr, 0)
    regionNames = dict.fromkeys(regionsStr, None)

    for reg in regionsInt:
        regionNames[str(reg)] = sde.getItemName(reg)

    fetchMarketData()
    dumpToDatabse()
