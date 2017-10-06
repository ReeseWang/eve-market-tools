#!/usr/bin/env python3

import sqlite3
import logging
# from syncmarket import dbPath as marketDBPath
import os
from tornado.log import LogFormatter


class Database:
    def execSQL(self, sql, data=None):
        if data:
            self.logger.debug("Executing SQL:\n" + sql +
                              "\nWith Data:\n" + repr(data))
            return self._conn.execute(sql, data)
        else:
            self.logger.debug("Executing SQL:\n" + sql)
            return self._conn.execute(sql)

    def execSQLScript(self, sql):
        self.logger.debug("Executing SQL:\n" + sql)
        return self._conn.executescript(sql)

    def _get(self, id, idcol, table, cols):
        assert isinstance(id, int)
        assert isinstance(idcol, str)
        assert isinstance(cols, str)
        assert isinstance(table, str)
        c = self.execSQL("SELECT {} FROM {} "
                         "WHERE {}=?".format(cols, table, idcol), (id,))
        assert c.arraysize == 1
        return c.fetchone()

    def cacheTableToMemory(self, table):
        c = self.execSQL("SELECT sql FROM hdd.sqlite_master "
                         "WHERE name = ? AND type = 'table';", (table,))
        sql = c.fetchone()[0]
        self.execSQLScript(
            sql +
            ";\nINSERT INTO main.{0} SELECT * FROM hdd.{0};".format(table))
        pass

    def _getStation(self, stationID, cols):
        return self._get(stationID,
                         idcol='stationID',
                         table='staStations',
                         cols=cols)

    def getStationSecurity(self, stationID):
        return self._getStation(stationID, cols='security')[0]

    def getStationSolarSystem(self, stationID):
        return self._getStation(stationID, cols='solarSystemID')[0]

    def getStationConstellation(self, stationID):
        return self._getStation(stationID, cols='constellationID')[0]

    def getStationRegion(self, stationID):
        return self._getStation(stationID, cols='regionID')[0]

    def _cacheItemsPackVols(self):
        res = self.execSQL(
            "SELECT typeID, volume FROM hdd.invVolumes;").fetchall()
        self.logger.info("Found {} item types "
                         "which has packaged volume.".format(len(res)))
        self.typesPackVol = {str(t[0]): t[1] for t in res}

    def _getType(self, typeID, cols):
        return self._get(typeID,
                         idcol='typeID',
                         table='invTypes',
                         cols=cols)
        pass

    def getTypeVolume(self, typeID):
        assert isinstance(typeID, int)
        vol = self.typesPackVol.get(str(typeID))
        if vol:
            return vol
        else:
            return self._getType(typeID,
                                 cols='volume')[0]

    def getTypeName(self, typeID):
        return self._getType(typeID,
                             cols='typeName')[0]

    def getItemName(self, itemID):
        return self._get(itemID,
                         idcol='itemID',
                         table='invNames',
                         cols='itemName')[0]

    def _getSolarSystem(self, solarSystemID, cols):
        return self._get(solarSystemID,
                         idcol='solarSystemID',
                         table='mapSolarSystems',
                         cols=cols)

    def getSolarSystemSecurity(self, solarSystemID):
        return self._getSolarSystem(solarSystemID,
                                    cols='security')[0]

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        self._conn = sqlite3.connect(':memory:')
        self.execSQL("ATTACH './db/sde.sqlite' AS hdd;")

        self.cacheTableToMemory('invTypes')
        self.cacheTableToMemory('invNames')
        self.cacheTableToMemory('staStations')
        self.cacheTableToMemory('mapSolarSystems')
        self._cacheItemsPackVols()

        self.execSQL("DETACH hdd;")

        marketDBPath = './db/market.sqlite'
        if os.path.exists(marketDBPath):
            self.execSQL("ATTACH '{}' AS hdd;".format(marketDBPath))

            self.cacheTableToMemory('buyOrders')
            self.cacheTableToMemory('sellOrders')
            self.cacheTableToMemory('publicStructures')

            self.execSQL("DETACH hdd;")
            pass


if __name__ == '__main__':
    channel = logging.StreamHandler()
    channel.setFormatter(LogFormatter())
    logging.basicConfig(handlers=[channel], level=logging.DEBUG)
    db = Database()
