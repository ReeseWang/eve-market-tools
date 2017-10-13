import cmd
import logging
import sqlqueries
from prettytable import PrettyTable


class HaulToJita(cmd.Cmd):
    prompt = 'Haul To Jita > '

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

    def insertOrderPair(self, buy, sell, volume):
        assert buy['typeID'] == sell['typeID']
        self.db.execSQL(sqlqueries.insertOrderPairsQuery,
                        (buy['typeID'],
                         buy['orderID'],
                         sell['orderID'],
                         buy['price'],
                         sell['price'],
                         volume,
                         buy['regionID'],
                         sell['regionID']))
        pass

    def evalProfit(self, typeIDlocID):
        buyFrom = self.db.execSQL(sqlqueries.pickHaulToJitaTargetSellOrders(),
                                  (tuple(typeIDlocID))
                                  ).fetchall()
        sellTo = self.db.execSQL(sqlqueries.pickHaulToJitaTargetBuyOrders(),
                                 (typeIDlocID['typeID'],)).fetchall()
        buyIdx, sellIdx, buyConsumed, sellConsumed = 0, 0, 0, 0
        buyLen, sellLen = len(buyFrom), len(sellTo)
        sellMinVolAlert = True
        while True:
            if buyIdx == buyLen or sellIdx == sellLen:
                break
            if (buyFrom[buyIdx]['price'] >
               self.taxCoeff * sellTo[sellIdx]['price']):
                break
            sellRemain = sellTo[sellIdx]['volumeRemain'] - sellConsumed
            buyRemain = buyFrom[buyIdx]['volumeRemain'] - buyConsumed
            if sellRemain > buyRemain:
                if sellTo[sellIdx]['minVolume'] > buyRemain and sellMinVolAlert:
                    # Determining whether to consume this buy order is pretty
                    # hard. Skip it for now.
                    sellConsumed = 0
                    sellIdx += 1
                    sellMinVolAlert = True
                    # # Evaluting if we can meet minimum volume requirement
                    # # of this buy order (a sell action for us)
                    # income = self.taxCoeff * sellTo[sellIdx]['price']
                    # toConsume = sellTo['minVolume'] - buyRemain
                    # cost = buyRemain * buyFrom[buyIdx]['price']
                    # for buyIdxB in range(buyIdx+1, buyLen):
                    #     if buyFrom[buyIdxB]['price'] > sellPrice:
                    #         # We have to give up
                    #         sellMinVolAlert = True
                    #         sellIdx += 1
                    #         break
                    #     toConsume -= buyFrom[buyIdxB]['volumeRemain']
                    #     if toConsume <= 0:
                    #         sellMinVolAlert = False
                    #         break
                    #     if (buyIdxB == buyLen - 1) and toConsume > 0:
                    # else:  # We're good to go
                    #     sellMinVolAlert = False
                else:
                    self.insertOrderPair(buyFrom[buyIdx],
                                         sellTo[sellIdx],
                                         buyRemain)
                    sellConsumed += buyRemain
                    buyIdx += 1
                    buyConsumed = 0
            elif buyRemain > sellRemain:
                self.insertOrderPair(buyFrom[buyIdx],
                                     sellTo[sellIdx],
                                     sellRemain)
                buyConsumed += sellRemain
                sellIdx += 1
                sellMinVolAlert = True
                sellConsumed = 0
            else:
                self.insertOrderPair(buyFrom[buyIdx],
                                     sellTo[sellIdx],
                                     sellRemain)
                buyIdx += 1
                sellIdx += 1
                sellMinVolAlert = True
                buyConsumed, sellConsumed = 0, 0
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
                 minMargin=0.01):
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
        self.db.execSQLScript(sqlqueries.createOrderPairsTable())
        c = self.db.execSQL(sqlqueries.pickHaulToJitaItemLocationCombination())
        li = c.fetchall()
        # print(li)
        for pair in li:
            self.evalProfit(pair)
