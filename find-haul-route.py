#!/usr/bin/env python

import pickle

# cargoVolumeLim = 0
# budgetLim = 0
minMargin = 0.5
minProfit = 1e6

name = 'name'
price = 'price'
ask = 'sell'
sell = 'sell'
bid = 'buy'
buy = 'buy'
security = 'security_status'
volume = 'volume_remain'

print('Loading orders...')
with open('./cache/ordersAllTypeIdSorted.bin', 'rb') as inputFile:
    print("Opened '{}'".format(inputFile.name))
    orders = pickle.load(inputFile)
    pass

print('Loading systems info...')
with open('./cache/systemsInfo.bin', 'rb') as inputFile:
    print("Opened '{}'".format(inputFile.name))
    systems = pickle.load(inputFile)
    pass

# print('Loading items info...')
# with open('./cache/itemsInfo.bin', 'rb') as inputFile:
#     print("Opened '{}'".format(inputFile.name))
#     items = pickle.load(inputFile)
#     pass

# try:
#     print('Loading space stations info...')
#     with open('./cache/stationsInfo.bin', 'rb') as inputFile:
#         print("Opened '{}'".format(inputFile.name))
#         stations = pickle.load(inputFile)
#         pass
#     pass
# except IOError:
#     print('File not found, will create a new file.')
#     stations = dict()

tradePairs = []
for typeId in orders:
    if len(orders[typeId][sell]) == 0:
        continue

    if len(orders[typeId][buy]) == 0:
        continue

    if orders[typeId][sell][0][price] > orders[typeId][buy][0][price]:
        continue

    for sellOrder in orders[typeId][sell]:
        for buyOrder in orders[typeId][buy]:
            if sellOrder[price] > buyOrder[price]:
                continue
            
            availVolume = min(sellOrder[volume], buyOrder[volume])
            profit = availVolume * (buyOrder[price] - sellOrder[price])
            margin = buyOrder[price] / sellOrder[price] - 1
            legitPair = dict([
                ('volume', availVolume),
                ('profit', profit),
                ('margin', margin),
                ('buy', buyOrder),
                ('sell', sellOrder)
                ])
            if margin < minMargin:
                continue
            if profit < minProfit:
                continue
            tradePairs.append(legitPair)
            print('TypeID: {}, Profit: {}, Margin: {}.'.
                    format(typeId, profit, margin))
            pass
        pass
    pass

with open('./cache/tradePairs.bin', 'wb') as output:
    print('Dumping trade pairs to file {}...'.format(output.name))
    pickle.dump(tradePairs, output, pickle.HIGHEST_PROTOCOL)
    print('Completed.')
    pass

