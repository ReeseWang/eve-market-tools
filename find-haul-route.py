#!/usr/bin/env python3

import pickle
import localcache

cargoVolumeLim = 400
budgetLim = 15e6
highsecOnly = True
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

items = localcache.Cache('item', 
        'https://esi.tech.ccp.is/latest/universe/types/',
        '/?datasource=tranquility&language=en-us')
systems = localcache.Cache('system', 
        'https://esi.tech.ccp.is/latest/universe/systems/',
        '/?datasource=tranquility&language=en-us')
stations = localcache.Cache('station',
        'https://esi.tech.ccp.is/latest/universe/stations/',
        '/?datasource=tranquility')
# print('Loading systems info...')
# with open('./cache/systemsInfo.bin', 'rb') as inputFile:
#     print("Opened '{}'".format(inputFile.name))
#     systems = pickle.load(inputFile)
#     pass

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
            if margin < minMargin:
                continue
            if profit < minProfit:
                continue
            if buyOrder[price] > budgetLim:
                continue
            try:
                if cargoVolumeLim != 0:
                    itemVolume = items.get(typeId)['volume']
                    if itemVolume > cargoVolumeLim:
                        continue
                    availVolume = min(availVolume, cargoVolumeLim // itemVolume)
                    profit = availVolume * (buyOrder[price] - sellOrder[price])
                    if profit < minProfit:
                        continue
                    pass
                if highsecOnly:
                    if systems.get(
                            stations.get(buyOrder['location_id'])['system_id']
                            )[security] < 0.5:
                        continue
                    if systems.get(
                            stations.get(sellOrder['location_id'])['system_id']
                            )[security] < 0.5:
                        continue
                    pass
                pass
            except Exception as errorMessage:
                print(errorMessage.args[0])
                continue
            legitPair = dict([
                ('volume', availVolume),
                ('profit', profit),
                ('margin', margin),
                ('buy', buyOrder),
                ('sell', sellOrder)
                ])
            tradePairs.append(legitPair)
            with open('./result.txt', 'a') as outputText:
                outputText.write('Item: {}, Profit: {:,.2f}ISK, Margin: {:.2%}, From: {}, To: {}.\n'.
                        format(items.get(typeId)['name'], profit, margin,
                            stations.get(sellOrder['location_id'])['name'],
                            stations.get(buyOrder['location_id'])['name']
                            ))
                pass
            pass
        pass
    pass

with open('./cache/tradePairs.bin', 'wb') as output:
    print('Dumping trade pairs to file {}...'.format(output.name))
    pickle.dump(tradePairs, output, pickle.HIGHEST_PROTOCOL)
    print('Completed.')
    pass

