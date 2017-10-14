#!/usr/bin/env python3

import logging
import sqlqueries
from evedatabase import Database
from tornado.log import LogFormatter
import cmd
import readline
import os
import atexit
import argparse
import tableprinter
from prettytable import PrettyTable


def saveHistory(prevHistoryLen, filePath):
    logger.debug('Entering saveHistory')
    newHistoryLen = readline.get_history_length()
    logger.debug('{} {}'.format(newHistoryLen, prevHistoryLen))
    readline.set_history_length(1000)
    readline.append_history_file(newHistoryLen - prevHistoryLen, filePath)


class EMT(cmd.Cmd):
    prompt = 'EVE Online Market > '

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
        print('\n', name, 'SELLER SUMMARY:\n')
        tableprinter.printSellOrdersTable(li)

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
        print('\n', name, 'BUYER SUMMARY:\n')
        tableprinter.printBuyOrdersTable(li)

    def do_haultojita(self, arg):
        from haultojita import HaulToJita
        subtool = HaulToJita(self.db)
        subtool.cmdloop()
        pass

    def do_test(self, arg):
        self.db.execSQLScript(
            sqlqueries.createCheapThanJitaTable(
                taxCoeff=self.taxCoeff,
                minProfitPerM3=self.minProfitPerM3,
                minMargin=self.minMargin)
        )
        c = self.db.execSQL(sqlqueries.pickHaulToJitaItemLocationCombination())
        rows = c.fetchall()
        table = PrettyTable()
        for row in rows:
            table.add_row(row)
        print(table)

    def do_sqltest(self, arg):
        try:
            c = self.db.execSQL(arg)
            rows = c.fetchall()
            table = PrettyTable()
            for row in rows:
                table.add_row(row)
            print(table)
        except Exception as e:
            print(str(e))

    def do_EOF(self, arg):
        print('Fly safe!')
        import sys
        sys.exit(0)

    def initConstants(self):
        self.minMargin = 0.1
        self.minProfitPerM3 = 500.0
        self.taxCoeff = 0.98

    def __init__(self, updateDynamic=True):
        super().__init__()
        self.typeID = None  # Avoiding some error
        self.logger = logging.getLogger(__name__)
        self.initConstants()
        self.db = Database(updateMarket=updateDynamic)
        self.db.execSQLScript(sqlqueries.createSecFilteredMarketsView(0.45, 1))
        self.db.execSQLScript(sqlqueries.createSecFilteredOrdersView())
        self.db.execSQLScript(sqlqueries.createItemPackagedVolumesView())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='EVE Market Tool')
    parser.add_argument('--debug-no-update-dynamic-data',
                        help="Don't update dynamic data "
                        "(market, player structures, etc.)",
                        action='store_true')
    parser.add_argument('--debug-verbose',
                        help='Set logger level to DEBUG.',
                        action='store_true')
    args = parser.parse_args()

    logger = logging.getLogger(__name__)
    channel = logging.StreamHandler()
    channel.setFormatter(LogFormatter())
    if args.debug_verbose:
        logging.basicConfig(handlers=[channel], level=logging.DEBUG)
    else:
        logging.basicConfig(handlers=[channel], level=logging.WARNING)

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

    tool = EMT(updateDynamic=not args.debug_no_update_dynamic_data)
    tool.cmdloop()
