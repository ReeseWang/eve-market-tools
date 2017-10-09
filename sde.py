#!/usr/bin/env python3

import sqlite3
import logging


try:
    # tornado is bundled with pretty formatter - try using it
    from tornado.options import enable_pretty_logging
    enable_pretty_logging()
except Exception:
    pass

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


def _get(id, idcol, table, cols):
    assert isinstance(id, int)
    assert isinstance(idcol, str)
    assert isinstance(cols, str)
    assert isinstance(table, str)
    c = _conn.cursor()
    c.execute("SELECT {} FROM {} "
              "WHERE {}=?".format(cols, table, idcol), (id,))
    assert c.arraysize == 1
    return c.fetchone()


def _gethdd(id, idcol, table, cols):
    assert isinstance(id, int)
    assert isinstance(idcol, str)
    assert isinstance(cols, str)
    assert isinstance(table, str)
    c = _conn.cursor()
    c.execute("SELECT {} FROM hdd.{} "
              "WHERE {}=?".format(cols, table, idcol), (id,))
    assert c.arraysize == 1
    return c.fetchone()


def cacheTableToMemory(table):
    c = _conn.cursor()
    c.execute("SELECT sql FROM hdd.sqlite_master "
              "WHERE name = ? AND type = 'table';", (table,))
    sql = c.fetchone()[0]
    c.execute(sql)
    c.execute("INSERT INTO main.{0} SELECT * FROM hdd.{0};".format(table))
    c.close()
    pass


def _getStation(stationID, cols):
    return _get(stationID,
                idcol='stationID',
                table='staStations',
                cols=cols)


def getStationSecurity(stationID):
    res = _getStation(stationID, cols='security')
    if res:
        return res[0]


def getStationSolarSystem(stationID):
    return _getStation(stationID, cols='solarSystemID')[0]


def getStationConstellation(stationID):
    return _getStation(stationID, cols='constellationID')[0]


def getStationRegion(stationID):
    return _getStation(stationID, cols='regionID')[0]


def _cacheItemsPackVols():
    c = _conn.cursor()
    c.execute("SELECT typeID, volume FROM hdd.invVolumes;")
    res = c.fetchall()
    logger.info("Found {} item types "
                "which has packaged volume.".format(len(res)))
    dict = {str(t[0]): t[1] for t in res}
    return dict


def _getType(typeID, cols):
    return _get(typeID,
                idcol='typeID',
                table='invTypes',
                cols=cols)
    pass


def getTypeVolume(typeID):
    assert isinstance(typeID, int)
    vol = typesPackVol.get(str(typeID))
    if vol:
        return vol
    else:
        return _getType(typeID,
                        cols='volume')[0]


def getTypeName(typeID):
    return _getType(typeID,
                    cols='typeName')[0]


def getItemName(itemID):
    return _get(itemID,
                idcol='itemID',
                table='invNames',
                cols='itemName')[0]


def _getSolarSystem(solarSystemID, cols):
    return _get(solarSystemID,
                idcol='solarSystemID',
                table='mapSolarSystems',
                cols=cols)


def getSolarSystemSecurity(solarSystemID):
    return _getSolarSystem(solarSystemID,
                           cols='security')[0]


_conn = sqlite3.connect(':memory:')
_conn.execute("ATTACH './db/sde.sqlite' AS hdd;")

cacheTableToMemory('invTypes')
cacheTableToMemory('invNames')
cacheTableToMemory('staStations')
cacheTableToMemory('mapSolarSystems')
typesPackVol = _cacheItemsPackVols()
