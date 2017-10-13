import cmd
import logging
import sqlqueries


class HaulToJita(cmd.Cmd):
    prompt = 'Haul To Jita > '

    def evalProfit(self, pair):
        c = self.db.execSQL(sqlqueries.pickHaulToJitaTargetSellOrders(), pair)
        sell = c.fetchall()
        c = self.db.execSQL(sqlqueries.pickHaulToJitaTargetBuyOrders(), pair[0])
        buy = c.fetchall()
        pass

    def postcmd(self, stop, line):
        return stop

    def do_exit(self, arg):
        print('Bye!')
        return True

    def do_EOF(self, arg):
        print('Bye!')
        return True

    def __init__(self,
                 db,
                 taxCoeff=0.98,
                 minProfitPerM3=500.0,
                 minMargin=0.001):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.db = db
        self.taxCoeff = taxCoeff
        self.minProfitPerM3 = minProfitPerM3
        self.minMargin = minMargin
        print('Looking for cheap stuff...')
        self.db.execSQLScript(
            sqlqueries.createCheapThanJitaTable(
                taxCoeff=self.taxCoeff,
                minProfitPerM3=self.minProfitPerM3,
                minMargin=self.minMargin)
        )
        print('Summarizing item and location...')
        c = self.db.execSQL(sqlqueries.pickHaulToJitaItemLocationCombination())
        li = c.fetchall()
        # print(li)
        for pair in li:
            self.evalProfit(pair)
