#!/usr/bin/env python3

import pickle
import localcache
import requests
from esiauth import authedClient

cargoVolumeLim = 3045
budgetLim = 165e6
highsecRoute = False
minSecSta = 0
maxSecSta = 1
minMargin = 0.2
minProfit = 10e6

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

client = authedClient()
chaID = client.getCharacterID()
print('Getting structure list...')
structList = requests.get('https://esi.tech.ccp.is/latest/universe/structures/?datasource=tranquility').json()

items = localcache.Cache('item', 
        'https://esi.tech.ccp.is/latest/universe/types/',
        '/?datasource=tranquility&language=en-us')
systems = localcache.Cache('system', 
        'https://esi.tech.ccp.is/latest/universe/systems/',
        '/?datasource=tranquility&language=en-us')
stations = localcache.Cache('station',
        'https://esi.tech.ccp.is/latest/universe/stations/',
        '/?datasource=tranquility')
if highsecRoute:
    routes = localcache.Cache('routehigh',
            'https://esi.tech.ccp.is/latest/route/',
            '/?datasource=tranquility&flag=secure')
else:
    routes = localcache.Cache('route',
            'https://esi.tech.ccp.is/latest/route/',
            '/?datasource=tranquility&flag=shortest')
structures = localcache.Cache('structure',
        'https://esi.tech.ccp.is/latest/universe/structures/',
        '/?datasource=tranquility', getMethod = client.get)

def getOrderSolarSystem(location):
    if int(location) in structList:
        return systems.get(structures.get(location)['solar_system_id'])
    else:
        return systems.get(stations.get(location)['system_id'])

def getOrderLocationName(location):
    if int(location) in structList:
        return structures.get(location)['name']
    else:
        return stations.get(location)['name']

def totalVolume(ordersList):
    volume = 0
    for order in ordersList:
        volume += order['volume_remain']
        pass
    return volume

def totalISK(ordersList, volume):
    assert volume <= totalVolume(ordersList)
    # print('Calculating total amount... Volume: {}'.format(volume))
    amount = 0
    volumeRemain = volume
    for order in ordersList:
        if order['volume_remain'] > volumeRemain:
            amount += (volumeRemain * order['price'])
            # print('{:,.2f} ISK, \t{}({})'.format(order['price'], volumeRemain, order['volume_remain']))
            break
        else:
            amount += (order['volume_remain'] * order['price'])
            volumeRemain -= order['volume_remain']
            # print('{:,.2f} ISK, \t{}'.format(order['price'], order['volume_remain']))
            pass
        pass
    # print('Total amount: {:,.2f} ISK.'.format(amount))
    return amount

def getRoute(src, dst):
    if src == dst:
        return [src]
    if src < dst:
        routeId = str(src) + '/' + str(dst)
    else:
        routeId = str(dst) + '/' + str(src)
    try:
        route = routes.get(routeId)
    except Exception as errorMessage:
        print(errorMessage.args[0])
        return []

    if src < dst:
        return route
    else:
        return list(reversed(route))

tradePairs = []
for typeId in orders:
#     if len(orders[typeId][sell]) == 0:
#         continue
# 
#     if len(orders[typeId][buy]) == 0:
#         continue
# 
    if orders[typeId]['lowest_sell'] > orders[typeId]['highest_buy']:
        continue

    for locSell in orders[typeId][sell]:
        for locBuy in orders[typeId][buy]:
            sellOrdersList = orders[typeId][sell][locSell]
            buyOrdersList = orders[typeId][buy][locBuy]
            if ( len(sellOrdersList) == 0 ) or ( len(buyOrdersList) == 0 ):
                continue
            if sellOrdersList[0][price] > buyOrdersList[0][price]:
                continue
            profitLimFactor = 'Market'

            availVolume = min(totalVolume(sellOrdersList), totalVolume(buyOrdersList))
            sellTotal = totalISK(sellOrdersList, availVolume)
            buyTotal = totalISK(buyOrdersList, availVolume)
            profit = buyTotal - sellTotal
            margin = buyOrdersList[0][price] / sellOrdersList[0][price] - 1
            if margin < minMargin:
                # print('Margin = {:.2%} < {:.2%}, too low.'.format(margin, minMargin))
                continue
            if profit < minProfit:
                # print('Profit = {:,.2f} ISK < {:,.2f} ISK, too low.'.format(profit, minProfit))
                continue
            buyerMinVolumes = [order['min_volume'] for order in buyOrdersList]
            minVolume = min(buyerMinVolumes)
            if minVolume > totalVolume(sellOrdersList):
                continue
            minCost = totalISK(sellOrdersList, minVolume)
            if minCost > budgetLim:
                # print('Min. cost = {:,.2f} ISK > {:,.2f} ISK, too high.'.\
                #         format(minCost, budgetLim))
                continue
            try:
                if cargoVolumeLim != 0:
                    itemVolume = items.get(typeId)['volume']
                    if itemVolume > cargoVolumeLim:
                        # print('Item volume = {}m3 > {}m3, too big.'.format(itemVolume, cargoVolumeLim))
                        continue
                    if availVolume > (cargoVolumeLim // itemVolume):
                        profitLimFactor = 'Cargo space'
                        availVolume = (cargoVolumeLim // itemVolume)
                        # Now that volume is recalculated.
                        sellTotal = totalISK(sellOrdersList, availVolume)
                        buyTotal = totalISK(buyOrdersList, availVolume)
                        profit = buyTotal - sellTotal
                    pass
                if budgetLim != 0:
                    if totalISK(buyOrdersList, availVolume) > budgetLim:
                        profitLimFactor = 'Budget'
                        availVolume -= 1
                        while(totalISK(buyOrdersList, availVolume) > budgetLim):
                            availVolume -= 1
                            pass
                        sellTotal = totalISK(sellOrdersList, availVolume)
                        buyTotal = totalISK(buyOrdersList, availVolume)
                        profit = buyTotal - sellTotal
                        pass
                    pass

                # Check updated profit
                if profit < minProfit:
                    # print('Profit = {:,.2f} ISK < {:,.2f} ISK, too low.'.format(profit, minProfit))
                    continue
                # Actual margin, can only be lower.
                marginActual = buyTotal / sellTotal - 1
                sysBuy = getOrderSolarSystem(locBuy)
                secBuy = sysBuy[security]
                if not ( minSecSta < secBuy < maxSecSta ):
                    # print('Buyer location security status does not meet requirements.')
                    continue
                sysSell = getOrderSolarSystem(locSell)
                secSell = sysSell[security]
                if not ( minSecSta < secSell < maxSecSta ):
                    # print('Seller location security status does not meet requirements.')
                    continue
                jumps = len(getRoute(sysSell['system_id'], sysBuy['system_id'])) - 1
                if jumps == -1:
                    continue
                pass
            except Exception as errorMessage:
                print(errorMessage.args[0])
                continue
            legitPair = dict([
                ('volume', availVolume),
                ('min_volume', minVolume),
                ('profit', profit),
                ('margin', margin),
                ('margin_actual', marginActual),
                ('jumps', jumps),
                ('buy', buyOrdersList),
                ('sell', sellOrdersList)
                ])
            tradePairs.append(legitPair)
            with open('./result.txt', 'a') as outputText:
                outputText.write('Item: \t\t{} {} \nProfit: \t{:,.2f} ISK \nMargin: \t{:.2%}/{:.2%} \n'.
                        format(typeId, items.get(typeId)['name'], profit, margin, marginActual) + 
                        'Volume: \t{} \nCost: \t\t{:,.2f} ISK \n'.format(availVolume, sellTotal) + 
                        'Min. volume: \t{} \n'.format(minVolume) +
                        'Min. cost: \t{:,.2f} ISK \n'.format(minCost) +
                        'Item size: \t{:.2f} m3 \n'.format(itemVolume) +
                        'Total size: \t{:.2f} m3 \n'.format(itemVolume * availVolume) +
                        'From: \t\t{} {:.2f} {} \n'.format(locSell, secSell, getOrderLocationName(locSell)) + 
                        'To: \t\t{} {:.2f} {} \n'.format(locBuy, secBuy, getOrderLocationName(locBuy)) + 
                        'Jumps: \t\t{} \n'.format(jumps) + 
                        'Profit/jump: \t{:,.2f} ISK \n'.format(profit / jumps) + 
                        'Profit limit factor: {}.\n'.format(profitLimFactor) + '\n')
                pass
            pass
        pass
    pass

with open('./cache/tradePairs.bin', 'wb') as output:
    print('Dumping trade pairs to file {}...'.format(output.name))
    pickle.dump(tradePairs, output, pickle.HIGHEST_PROTOCOL)
    print('Completed.')
    pass

