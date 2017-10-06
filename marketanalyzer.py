#!/usr/bin/env python3

import logging
import sqlqueries
from sde import Database
from tornado.log import LogFormatter
from tabulate import tabulate


def rangeString(r):
    assert isinstance(r, str)
    if r.isdigit():
        if int(r) == 1:
            return '1 jump'
        else:
            return (r + ' jumps')
    else:
        if r == 'solarsystem':
            return 'System'
        else:
            return r.capitalize()


class MarketAnalyzer:
    def printSellerList(self, typeID):
        assert isinstance(typeID, int)
        name = self.db.getTypeName(typeID)
        c = self.db.execSQL(sqlqueries.listSellOrders(), data=(typeID,))
        print(name.upper(), 'SELLER SUMMARY:\n')
        print(tabulate(
            [
                [
                    '{:.1f} '.format(e[0]) +
                    ' - '.join(
                        [
                            e[1],  # Region name
                            # e[2],  # Constellation name
                            e[3][0:50]  # Station name, solar system name inc.
                        ]
                    ),
                    float(e[4]),  # Volume remain
                    e[5],  # Price
                    e[4]*e[5]  # Sum
                ] for e in c.fetchall()
            ],
            self.sellListHeaders,
            tablefmt='pipe',
            numalign='right',
            floatfmt=('', ',.0f', ',.2f', ',.2f')
        ))

    def printBuyerList(self, typeID):
        assert isinstance(typeID, int)
        name = self.db.getTypeName(typeID)
        c = self.db.execSQL(sqlqueries.listBuyOrders(), data=(typeID,))
        print(name.upper(), 'BUYER SUMMARY:\n')
        print(tabulate(
            [
                [
                    '{:.1f} '.format(e[0]) +
                    ' - '.join(
                        [
                            e[1],  # Region name
                            # e[2],4 # Constellation name
                            e[3][0:40]  # Station name, solar system name inc.
                        ]
                    ),
                    rangeString(e[7]),  # Range
                    float(e[4]),  # Volume remain
                    float(e[6]),  # Min volume
                    e[5],  # Price
                    e[4]*e[5]  # Sum
                ] for e in c.fetchall()
            ],
            self.buyListHeaders,
            tablefmt='pipe',
            numalign='right',
            floatfmt=('', '', ',.0f', ',.0f', ',.2f', ',.2f')
        ))

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.sellListHeaders = [
            'Location',
            'Remaining',
            'Ask price / ISK',
            'Sum / ISK'
        ]
        self.buyListHeaders = [
            'Location',
            'Range',
            'Remaining',
            'Min volume',
            'Bid price / ISK',
            'Sum / ISK'
        ]
        self.db = Database()
        self.db.execSQLScript(sqlqueries.createSecFilteredMarketsView(0.45, 1))
        self.db.execSQLScript(sqlqueries.createSecFilteredOrdersView())


if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    channel = logging.StreamHandler()
    channel.setFormatter(LogFormatter())
    logging.basicConfig(handlers=[channel], level=logging.WARNING)

    analyzer = MarketAnalyzer()
    analyzer.printSellerList(6677)
    analyzer.printBuyerList(34)
