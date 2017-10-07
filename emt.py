#!/usr/bin/env python3

import logging
import sqlqueries
from sde import Database
from tornado.log import LogFormatter
from tabulate import tabulate
import cmd
import readline
import os
import atexit
from datetime import datetime


def timefmt(timestamp, level=3):
    time = datetime.strptime(
        timestamp,
        '%Y-%m-%d %H:%M:%S'
    )
    secs = int((datetime.utcnow() -
                time).total_seconds())
    d, h, m, s = '', '', '', ''
    if secs >= 86400 and level >= 3:
        d = '{}D '.format(secs // 86400)
        secs %= 86400
        h, m = '00:', '00'
        pass
    if secs > 3600 and level >= 2:
        h = '{:02d}:'.format(secs // 3600)
        secs %= 3600
        m = '00'
        pass
    if secs > 60 and level >= 1:
        m = '{:02d}'.format(secs // 60)
        secs %= 60
        pass
    s = ':{:02d}'.format(secs)
    return (d + h + m + s)


def saveHistory(prevHistoryLen, filePath):
    logger.debug('Entering saveHistory')
    newHistoryLen = readline.get_history_length()
    logger.debug('{} {}'.format(newHistoryLen, prevHistoryLen))
    readline.set_history_length(1000)
    readline.append_history_file(newHistoryLen - prevHistoryLen, filePath)


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


class EMT(cmd.Cmd):
    prompt = 'EVE Online Market>'

    def do_sellerlist(self, arg):
        if arg:
            try:
                self.typeID = int(arg)
            except ValueError:
                print('Please provide a legal type ID.')
                return
        else:
            if not self.typeID:
                print("Please give me an item's type ID before querying.")
                return
        name = self.db.getTypeName(self.typeID)
        if not name:
            print("I didn't find an item with this type ID.")
            return
        c = self.db.execSQL(sqlqueries.listSellOrders(), data=(self.typeID,))
        li = c.fetchall()
        if not li:  # No orders found
            print('No orders found for {}.'.format(name))
            return
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
                    e[4]*e[5],  # Sum
                    timefmt(e[6], 2),  # Updated
                    timefmt(e[7], 3)  # Issued
                ] for e in li
            ],
            self.sellListHeaders,
            tablefmt='pipe',
            numalign='right',
            floatfmt=('', ',.0f', ',.2f', ',.2f')
        ))

    def do_buyerlist(self, arg):
        if arg:
            try:
                self.typeID = int(arg)
            except ValueError:
                print('Please provide a legal type ID.')
                return
        else:
            if not self.typeID:
                print("Please give me an item's type ID before querying.")
                return
        name = self.db.getTypeName(self.typeID)
        if not name:
            print("I didn't find an item with this type ID.")
            return
        c = self.db.execSQL(sqlqueries.listBuyOrders(), data=(self.typeID,))
        li = c.fetchall()
        if not li:  # No orders found
            print('No orders found for {}.'.format(name))
            return
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
                    e[4]*e[5],  # Sum
                    timefmt(e[8], 2),  # Updated
                    timefmt(e[9], 3)  # Issued
                ] for e in li
            ],
            self.buyListHeaders,
            tablefmt='pipe',
            numalign='right',
            floatfmt=('', '', ',.0f', ',.0f', ',.2f', ',.2f')
        ))

    def do_test(self, arg):
        print(arg)

    def do_EOF(self, arg):
        print('Fly safe!')
        import sys
        sys.exit(0)

    def __init__(self):
        super().__init__()
        self.typeID = None  # Avoiding some error
        self.logger = logging.getLogger(__name__)
        self.sellListHeaders = [
            'Location',
            'Remaining',
            'Ask price / ISK',
            'Sum / ISK',
            'Updated ago',
            'Issued ago'
        ]
        self.buyListHeaders = [
            'Location',
            'Range',
            'Remaining',
            'Min volume',
            'Bid price / ISK',
            'Sum / ISK',
            'Updated ago',
            'Issued ago'
        ]
        self.db = Database()
        self.db.execSQLScript(sqlqueries.createSecFilteredMarketsView(0.45, 1))
        self.db.execSQLScript(sqlqueries.createSecFilteredOrdersView())


if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    channel = logging.StreamHandler()
    channel.setFormatter(LogFormatter())
    logging.basicConfig(handlers=[channel], level=logging.DEBUG)

    historyFilePath = os.path.join(os.path.expanduser("~"), '.emt_history')

    try:
        readline.read_history_file(historyFilePath)
        hlen = readline.get_history_length()
        logger.debug('Got {} lines of command history.'.format(hlen))
    except FileNotFoundError:
        open(historyFilePath, 'wb').close()
        logger.debug('Command history file not found, created a new file.')
        hlen = 0

    atexit.register(saveHistory, hlen, historyFilePath)

    tool = EMT()
    tool.cmdloop()
