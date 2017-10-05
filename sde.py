#!/usr/bin/env python3

import sqlite3
import logging
# from syncmarket import dbPath as marketDBPath
import os
import sqlqueries


try:
    # tornado is bundled with pretty formatter - try using it
    from tornado.log import enable_pretty_logging
    enable_pretty_logging()
except Exception:
    print("Pretty logging disabled.")
    pass

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


class Database:
    def _get(self, id, idcol, table, cols):
        assert isinstance(id, int)
        assert isinstance(idcol, str)
        assert isinstance(cols, str)
        assert isinstance(table, str)
        c = self._conn.execute("SELECT {} FROM {} "
                               "WHERE {}=?".format(cols, table, idcol), (id,))
        assert c.arraysize == 1
        return c.fetchone()

    def _gethdd(self, id, idcol, table, cols):
        assert isinstance(id, int)
        assert isinstance(idcol, str)
        assert isinstance(cols, str)
        assert isinstance(table, str)
        c = self._conn.execute("SELECT {} FROM hdd.{} "
                               "WHERE {}=?".format(cols, table, idcol), (id,))
        assert c.arraysize == 1
        return c.fetchone()

    def cacheTableToMemory(self, table):
        c = self._conn.execute("SELECT sql FROM hdd.sqlite_master "
                               "WHERE name = ? AND type = 'table';", (table,))
        sql = c.fetchone()[0]
        c.execute(sql)
        c.execute("INSERT INTO main.{0} SELECT * FROM hdd.{0};".format(table))
        c.close()
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
        c = self._conn.execute("SELECT typeID, volume FROM hdd.invVolumes;")
        res = c.fetchall()
        logger.info("Found {} item types "
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
        self._conn = sqlite3.connect(':memory:')
        self._conn.execute("ATTACH './db/sde.sqlite' AS hdd;")

        self.cacheTableToMemory('invTypes')
        self.cacheTableToMemory('invNames')
        self.cacheTableToMemory('staStations')
        self.cacheTableToMemory('mapSolarSystems')
        self._cacheItemsPackVols()

        self._conn.execute("DETACH hdd;")

        marketDBPath = './db/market.sqlite'
        if os.path.exists(marketDBPath):
            self._conn.execute("ATTACH '{}' AS hdd;".format(marketDBPath))

            self.cacheTableToMemory('buyOrders')
            self.cacheTableToMemory('sellOrders')
            self.cacheTableToMemory('publicStructures')

            self._conn.execute("DETACH hdd;")

            self._conn.execute(sqlqueries.hiSecMarketsView)
            pass
