#!/usr/bin/env python3

import requests
import sqlite3
from concurrent.futures import ThreadPoolExecutor
import logging
from sde import Database
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

logger = logging.getLogger()


class BuyOrder:

    def __init__(self, dictOrder, regionID):
        self.orderID = dictOrder['order_id']
        self.typeID = dictOrder['type_id']
        self.locationID = dictOrder['location_id']
        self.regionID = regionID
        self.volumeTotal = dictOrder['volume_total']
        self.volumeRemain = dictOrder['volume_remain']
        self.minVolume = dictOrder['min_volume']
        self.price = dictOrder['price']
        self.buyRange = dictOrder['range']
        self.duration = dictOrder['duration']
        self.issuedTime = datetime.strptime(dictOrder['issued'],
                                            '%Y-%m-%dT%H:%M:%SZ')

    # A failure. I thought adapter can be used to insert multi column
    def __conform__(self, protocol):
        if protocol is sqlite3.PrepareProtocol:
            return (self.orderID, self.typeID,
                    self.locationID, self.regionID,
                    self.volumeTotal, self.volumeRemain,
                    self.minVolume, self.price,
                    self.buyRange, self.duration,
                    self.issuedTime.timestamp())
        pass


class EVESyncWorker:

    def endlessGet(self, url):
        while True:
            res = requests.get(url)
            if res.ok:
                return res
            else:
                time.sleep(5)

    def execSQL(self, sql):
        logger.debug("Executing SQL:\n" + sql)
        c = self.conn.execute(sql)
        return c.rowcount

    def initDB(self):
        # logger.debug("Connecting to '{}'...".format(dbPath))
        # conn = sqlite3.connect(dbPath)
        self.execSQL("DROP TABLE IF EXISTS buyOrdersInserting;")
        self.execSQL('\n'.join([
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
            "issued INTEGER NOT NULL);"]))
        self.execSQL("DROP TABLE IF EXISTS sellOrdersInserting;")
        self.execSQL('\n'.join([
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
            "issued INTEGER NOT NULL);"]))
        self.execSQL("DROP TABLE IF EXISTS publicStructuresInserting;")
        self.execSQL('\n'.join([
            "CREATE TABLE publicStructuresInserting (",
            "structure_id INTEGER PRIMARY KEY,",
            "name TEXT NOT NULL,",
            "solar_system_id INTEGER NOT NULL,",
            "type_id INTEGER NOT NULL,",
            "x REAL NOT NULL,",
            "y REAL NOT NULL,",
            "z REAL NOT NULL",
            ");"]))
        pass

        # conn.commit()
        # conn.close()

    def buyOrderTuple(self, order, reg):
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

    def sellOrderTuple(self, order, reg):
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

    def fillOrderTupleLists(self, pordersList, preg):
        for order in pordersList:
            if order['is_buy_order']:
                self.buyTuplesList.append(self.buyOrderTuple(order, preg))
            else:
                self.sellTuplesList.append(self.sellOrderTuple(order, preg))

    def execSQLMany(self, sql, data):
        logger.debug("Executing SQL:\n" + sql)
        c = self.conn.executemany(sql, data)
        return c.rowcount

    def insertDB(self):
        rows = 0
        if(self.buyTuplesList):
            rows += self.execSQLMany("INSERT OR IGNORE INTO "
                                     "buyOrdersInserting VALUES "
                                     "({});".format(','.join(11*'?')),
                                     self.buyTuplesList)
        if(self.sellTuplesList):
            rows += self.execSQLMany("INSERT OR IGNORE INTO "
                                     "sellOrdersInserting VALUES "
                                     "({});".format(','.join(9*'?')),
                                     self.sellTuplesList)
        return rows

    def getOrders(self, preg, ppage):
        req = self.client.get('https://esi.tech.ccp.is/latest/markets/' +
                              preg + '/orders/?datasource=tranquility' +
                              '&order_type=all&page=' + str(ppage))
        assert req.status_code == 200
        self.fillOrderTupleLists(req.json(), int(preg))
        # insertDB(req.json(), int(reg))
        logger.info('Region {} Page {} received.'.format(self.regionNames[preg],
                                                         ppage))
        pass

    def getFirstPage(self, preg):
        res = self.client.get('https://esi.tech.ccp.is/latest/markets/' +
                              preg + '/orders/?datasource=tranquility' +
                              '&order_type=all&page=1')
        assert res.status_code == 200
        # return req.json(), int(req.headers['x-pages'])
        self.fillOrderTupleLists(res.json(), int(preg))
        self.pageCounts[preg] = int(res.headers['x-pages'])
        logger.info('Got the first page of orders in {0}. {0} has {1} '
                    'pages of orders. Last modified '
                    'at {2}.'.format(self.regionNames[preg],
                                     self.pageCounts[preg],
                                     res.headers['last-modified']))
        # insertDB(req.json(), int(reg))

    def getRegionsList(self):
        logger.info('Getting region list...')
        res = self.client.get('https://esi.tech.ccp.is/'
                              'latest/universe/regions/?datasource=tranquility')
        assert res.status_code == 200
        self.regionsInt = res.json()
        # You definitely don't want to touch region SOLITUDE
        self.regionsInt.remove(10000044)
        # For test
        # self.regionsInt = self.regionsInt[0:3]
        self.regionsStr = []
        for reg in self.regionsInt:
            self.regionsStr.append(str(reg))
            pass
        self.regionNames = dict.fromkeys(self.regionsStr, None)

        for reg in self.regionsInt:
            self.regionNames[str(reg)] = sde.getItemName(reg)

    def getStructuresList(self):
        logger.info('Getting structures list...')
        res = self.client.get('https://esi.tech.ccp.is/'
                              'latest/universe/structures/?'
                              'datasource=tranquility')
        assert res.status_code == 200
        res = res.json()
        logger.info("There are {} public structures.".format(len(res)))
        self.structuresInt = res
        # For test
        # self.structuresInt = self.structuresInt[0:10]

    def fetchMarketData(self):
        self.pageCounts = dict.fromkeys(self.regionsStr, 0)
        with ThreadPoolExecutor(max_workers=20) as executor:
            for reg in self.regionsStr:
                # Single thread test
                # self.getFirstPage(reg)
                executor.submit(self.getFirstPage, reg)
                pass

        with ThreadPoolExecutor(max_workers=20) as executor:
            for reg in self.regionsStr:
                try:
                    assert self.pageCounts[reg] >= 1
                except AssertionError:
                    import sys
                    sys.exit("{}, {}".format(reg, self.pageCounts[reg]))
                for page in range(1, self.pageCounts[reg]):
                    # Single thread test
                    # self.getOrders(reg, page+1)
                    executor.submit(self.getOrders, reg, page+1)
                    pass
                pass
            pass

    def replaceTable(self):
        sql = """
    DROP TABLE IF EXISTS buyOrders;
    ALTER TABLE buyOrdersInserting RENAME TO buyOrders;
    DROP TABLE IF EXISTS sellOrders;
    ALTER TABLE sellOrdersInserting RENAME TO sellOrders;
    DROP TABLE IF EXISTS publicStructures;
    ALTER TABLE publicStructuresInserting RENAME TO publicStructures;
"""
        logger.debug("Executing SQL:\n" + sql)
        self.conn.executescript(sql)

    def insertStructuresDB(self):
        rows = self.execSQLMany("INSERT OR IGNORE INTO "
                                "publicStructuresInserting VALUES "
                                "(?,?,?,?,?,?,?);", self.structTuplesList)
        logger.debug('Structures: {} rows inserted.'.format(rows))
        structuresCount = len(self.structTuplesList)
        if rows != structuresCount:
            logger.warning('{} structures not inserted into the '
                           'database'.format(structuresCount - rows))

    def filterOrders(self):
        rows = self.execSQL('\n'.join([
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
            ");"]))
        if rows != 0:
            logger.info(
                "{} buy orders deleted because of not located in a public "
                "structure.".format(rows))
        rows = self.execSQL('\n'.join([
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
            ");"]))
        if rows != 0:
            logger.info(
                "{} sell orders deleted because of not located in a public "
                "structure.".format(rows))

    def dumpToDatabse(self):
        logger.debug("Connecting to '{}'...".format(dbPath))
        self.conn = sqlite3.connect(dbPath)
        self.initDB()
        self.insertStructuresDB()
        ordersCount = len(self.buyTuplesList) + len(self.sellTuplesList)
        logger.info('Inserting {} orders into '
                    'database'.format(ordersCount))
        rows = self.insertDB()
        logger.debug('{} orders inserted.'.format(rows))
        if ordersCount != rows:
            logger.warning(
                '{} order(s) not inserted into the'
                ' database.'.format(ordersCount - rows))
            pass
        self.filterOrders()
        self.replaceTable()
        self.conn.commit()
        self.conn.close()
        pass

    def getStructureInfo(self, pID):
        res = self.client.get(
            'https://esi.tech.ccp.is/latest/universe/structures/' +
            str(pID) +
            '/?datasource=tranquility').json()
        logger.info('Structure {} info received, its name is '
                    '{}.'.format(pID, res['name']))
        self.structTuplesList.append((
            pID, res['name'], res['solar_system_id'], res['type_id'],
            res['position']['x'],
            res['position']['y'],
            res['position']['z'],
        ))

    def fetchStructuresInfo(self):
        # You don't want to refresh token in multithread.
        self.client.getToken('refresh')
        with ThreadPoolExecutor(max_workers=100) as executor:
            for ID in self.structuresInt:
                # Single thread test
                # getStructureInfo(pstructs, ID, client)
                executor.submit(self.getStructureInfo, ID)
                pass

        if len(self.structTuplesList) != len(self.structuresInt):
            logger.warning("Info of {} strutures not retrieved "
                           "successfully".format(
                                len(self.structuresInt) -
                                len(self.structTuplesList)))

    def __init__(self):
        self.buyTuplesList = []
        self.sellTuplesList = []
        self.structTuplesList = []
        self.client = authedClient()

    def main(self):
        try:
            while True:
                self.getRegionsList()
                self.getStructuresList()

                self.fetchStructuresInfo()
                self.fetchMarketData()
                self.dumpToDatabse()
                pass
        except KeyboardInterrupt:
            logger.debug('KeyboardInterrupt caught, exiting gracefully...')


if __name__ == '__main__':
    logger.setLevel(logging.DEBUG)
    sde = Database()
    worker = EVESyncWorker()
    worker.main()
