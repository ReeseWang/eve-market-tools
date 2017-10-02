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


def execSQL(sql, conn, data=None):
    logger.debug("Executing SQL:\n" + sql)
    conn.execute(sql)


def initDB():
    logger.info("Connecting to '{}'...".format(dbPath))
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
        "min_volume INTEGER NOT NULL CHECK (min_volume > 0),",
        "price REAL NOT NULL CHECK (price > 0),",
        "duration INTEGER NOT NULL CHECK (duration > 0),",
        "issued INTEGER NOT NULL);"]), conn)


def buyOrderTuple(order, reg):
    return (order['order_id'],
            order['type_id'],
            order['location_id'],
            reg,
            order['volume_total'],
            order['volume_remain'],
            order['min_volume'],
            order['price'],
            order['range'],
            order['duration'],
            int(datetime.strptime(order['issued'],
                                  '%Y-%m-%dT%H:%M:%SZ').timestamp())
            )


def sellOrderTuple(order, reg):
    return (order['order_id'],
            order['type_id'],
            order['location_id'],
            reg,
            order['volume_total'],
            order['volume_remain'],
            order['min_volume'],
            order['price'],
            order['duration'],
            int(datetime.strptime(order['issued'],
                                  '%Y-%m-%dT%H:%M:%SZ').timestamp())
            )


def insertDB(ordersList, reg):
    assert isinstance(reg, int)
    conn = sqlite3.connect(dbPath)
    for order in ordersList:
        if order['is_buy_order']:
            execSQL("INSERT INTO buyOrderInserting VALUES "
                    "({});".format(','.join(11*'?')),
                    conn, data=buyOrderTuple(order, reg))
        else:
            execSQL("INSERT INTO buyOrderInserting VALUES "
                    "({});".format(','.join(11*'?')),
                    conn, data=sellOrderTuple(order, reg))
        pass
    pass


def getOrders(ordersList, reg, page):
    req = requests.get('https://esi.tech.ccp.is/latest/markets/' +
                       str(reg) + '/orders/?datasource=tranquility' +
                       '&order_type=all&page=' + str(page))
    assert req.status_code == 200
    # ordersList.extend(req.json())
    insertDB(req.json(), int(reg))
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
    # ordersDict[reg] = req.json()
    pageCountsDict[reg] = int(req.headers['x-pages'])
    insertDB(req.json(), int(reg))


def getRegionList():
    logger.info('Getting region list...')
    req = requests.get('https://esi.tech.ccp.is/'
                       'latest/universe/regions/?datasource=tranquility')
    logger.debug('Sent GET request to ' + req.url)
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

    for reg in regionsStr:
        logger.info('Region {} has {} '
                    'orders'.format(regionNames[reg], len(orders[reg])))
        pass


if __name__ == '__main__':
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    initDB()

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
