#!/usr/bin/env python3

import requests
import sqlite3
from concurrent.futures import ThreadPoolExecutor
import logging
from tornado.log import LogFormatter
from sde import Database
from datetime import datetime
from esiauth import AuthedClient
import time

dbPath = './db/market.sqlite'


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
        self.logger.debug("Executing SQL:\n" + sql)
        c = self.conn.execute(sql)
        return c.rowcount

    def initDB(self):
        # self.logger.debug("Connecting to '{}'...".format(dbPath))
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
            "issued timestamp NOT NULL,",
            "updated timestamp NOT NULL);"]))
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
            "issued timestamp NOT NULL,",
            # "volume_total INTEGER NOT NULL,",
            # "volume_remain INTEGER NOT NULL,",
            # "price REAL NOT NULL,",
            # "duration INTEGER NOT NULL,",
            "updated timestamp NOT NULL);"]))
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

    def buyOrderTuple(self, order, reg, updateTime):
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
                datetime.strptime(order['issued'],
                                  '%Y-%m-%dT%H:%M:%SZ'),
                updateTime
                )

    def sellOrderTuple(self, order, reg, updateTime):
        assert isinstance(reg, int)
        return (int(order['order_id']),
                int(order['type_id']),
                int(order['location_id']),
                reg,
                int(order['volume_total']),
                int(order['volume_remain']),
                order['price'],
                int(order['duration']),
                datetime.strptime(order['issued'],
                                  '%Y-%m-%dT%H:%M:%SZ'),
                updateTime
                )

    def fillOrderTupleLists(self, pordersList, preg, updateTime):
        for order in pordersList:
            if order['is_buy_order']:
                self.buyTuplesList.append(self.buyOrderTuple(order,
                                                             preg,
                                                             updateTime))
            else:
                self.sellTuplesList.append(self.sellOrderTuple(order,
                                                               preg,
                                                               updateTime))

    def execSQLMany(self, sql, data):
        self.logger.debug("Executing SQL:\n" + sql)
        c = self.conn.executemany(sql, data)
        return c.rowcount

    def insertDB(self):
        rows = 0
        if(self.buyTuplesList):
            rows += self.execSQLMany("INSERT OR IGNORE INTO "
                                     "buyOrdersInserting VALUES "
                                     "({});".format(','.join(12*'?')),
                                     self.buyTuplesList)
        if(self.sellTuplesList):
            rows += self.execSQLMany("INSERT OR IGNORE INTO "
                                     "sellOrdersInserting VALUES "
                                     "({});".format(','.join(10*'?')),
                                     self.sellTuplesList)
        return rows

    def getPageOfOrder(self, preg, ppage):
        res = self.client.get('https://esi.tech.ccp.is/latest/markets/' +
                              preg + '/orders/?datasource=tranquility' +
                              '&order_type=all&page=' + str(ppage))
        assert res.status_code == 200
        expires = datetime.strptime(res.headers['expires'],
                                    self.headerTimeFormat)
        if self.expireTime > expires:  # Update the expire time if earlier
            self.expireTime = expires
        lastMod = datetime.strptime(res.headers['last-modified'],
                                    self.headerTimeFormat)
        modDelta = datetime.utcnow() - lastMod
        self.fillOrderTupleLists(res.json(), int(preg), lastMod)
        self.logger.info('Got page {0}/{1} of orders in {2}. '
                         'Last modified {3} second(s) '
                         'ago.'.format(ppage,
                                       self.pageCounts[preg],
                                       self.regionNames[preg],
                                       round(modDelta.total_seconds())))
        if ppage == 1:
            return int(res.headers['x-pages'])

    def getFirstPage(self, preg):
        self.pageCounts[preg] = self.getPageOfOrder(preg, 1)
        # insertDB(req.json(), int(reg))

    def getRegionsList(self):
        self.logger.info('Getting region list...')
        res = self.client.get('https://esi.tech.ccp.is/'
                              'latest/universe/regions/?datasource=tranquility')
        assert res.status_code == 200
        self.regionsInt = res.json()
        # You definitely don't want to touch region SOLITUDE
        self.regionsInt.remove(10000044)
        # For test
        if self.debug:
            self.regionsInt = self.regionsInt[0:2]
        self.regionsStr = []
        for reg in self.regionsInt:
            self.regionsStr.append(str(reg))
            pass
        self.regionNames = dict.fromkeys(self.regionsStr, None)

        for reg in self.regionsInt:
            self.regionNames[str(reg)] = sde.getItemName(reg)

    def getStructuresList(self):
        self.logger.info('Getting structures list...')
        res = self.client.get('https://esi.tech.ccp.is/'
                              'latest/universe/structures/?'
                              'datasource=tranquility')
        assert res.status_code == 200
        res = res.json()
        self.logger.debug("There are {} public structures.".format(len(res)))
        self.structuresInt = res
        # For test
        if self.debug:
            self.structuresInt = self.structuresInt[0:10]

    def fetchMarketData(self):
        self.pageCounts = dict.fromkeys(self.regionsStr, 0)
        with ThreadPoolExecutor(max_workers=20) as executor:
            for reg in self.regionsStr:
                # Single thread test
                if self.singleThread:
                    self.getFirstPage(reg)
                else:
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
                    if self.singleThread:
                        self.getPageOfOrder(reg, page+1)
                    else:
                        executor.submit(self.getPageOfOrder, reg, page+1)
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
        self.logger.debug("Executing SQL:\n" + sql)
        self.conn.executescript(sql)

    def insertStructuresDB(self):
        rows = self.execSQLMany("INSERT OR IGNORE INTO "
                                "publicStructuresInserting VALUES "
                                "(?,?,?,?,?,?,?);", self.structTuplesList)
        self.logger.debug('Structures: {} rows inserted.'.format(rows))
        structuresCount = len(self.structTuplesList)
        if rows != structuresCount:
            self.logger.warning('{} structures not inserted into the '
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
            self.logger.info(
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
            self.logger.info(
                "{} sell orders deleted because of not located in a public "
                "structure.".format(rows))

    def dumpToDatabse(self):
        self.logger.debug("Connecting to '{}'...".format(dbPath))
        self.conn = sqlite3.connect(dbPath)
        self.initDB()
        self.insertStructuresDB()
        ordersCount = len(self.buyTuplesList) + len(self.sellTuplesList)
        self.logger.info('Inserting {} orders into '
                         'database'.format(ordersCount))
        rows = self.insertDB()
        self.logger.debug('{} orders inserted.'.format(rows))
        if ordersCount != rows:
            self.logger.warning(
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
        self.logger.info('Structure {} info received, its name is '
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
            self.logger.warning("Info of {} strutures not retrieved "
                                "successfully".format(
                                    len(self.structuresInt) -
                                    len(self.structTuplesList)))

    def __init__(self, debug=False, singleThread=False):
        self.logger = logging.getLogger(__name__)
        self.debug = debug
        self.singleThread = singleThread

        self.expireTime = datetime.utcnow().max
        self.headerTimeFormat = '%a, %d %b %Y %H:%M:%S GMT'
        self.buyTuplesList = []
        self.sellTuplesList = []
        self.structTuplesList = []
        self.client = AuthedClient()

    def sleepUntilFirstExpire(self):
        sleepSec = (self.expireTime - datetime.utcnow()).total_seconds()
        if sleepSec < 0:
            sleepSec = 0
        self.logger.debug('Work done, according to data expire time '
                          'provided by server, I will rest for {} '
                          'seconds...'.format(round(sleepSec)))
        time.sleep(sleepSec)
        self.expireTime = datetime.utcnow().max
        pass

    def resetDataCache(self):
        self.buyTuplesList = []
        self.sellTuplesList = []
        self.structTuplesList = []

    def main(self):
        try:
            while True:
                self.getRegionsList()
                self.getStructuresList()

                self.fetchStructuresInfo()
                self.fetchMarketData()
                self.dumpToDatabse()
                self.resetDataCache()
                self.sleepUntilFirstExpire()
                pass
        except KeyboardInterrupt:
            self.logger.debug('KeyboardInterrupt caught, exiting gracefully...')
            import sys
            sys.exit(0)


if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    channel = logging.StreamHandler()
    channel.setFormatter(LogFormatter())
    logging.basicConfig(handlers=[channel], level=logging.DEBUG)

    sde = Database()
    worker = EVESyncWorker(debug=False)
    worker.main()
