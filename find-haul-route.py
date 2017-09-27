#!/usr/bin/env python3

import pickle
import localcache
import requests
from esiauth import authedClient

cargoVolumeLim = 640
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

def tradePairInfoStr(pair):
    return '\n'.join([ 'Item: \t\t{item_name}',
                        'Profit: \t{profit:,.2f} ISK',
                        'Margin: \t{margin:.2%}/{margin_actual:.2%}',
                        'Volume: \t{volume}',
                        'Cost: \t\t{cost:,.2f} ISK',
                        'Min. volume: \t{min_volume}',
                        'Min. cost: \t{min_cost:,.2f} ISK',
                        'Item size: \t{item_size:.2f} m3',
                        'Total size: \t{total_size:.2f} m3',
                        'From: \t\t{from_sec:.2f} {from_name}',
                        'To: \t\t{to_sec:.2f} {to_name}',
                        'Jumps: \t\t{jumps}',
                        'Profit/jump: \t{profit_per_jump:,.2f} ISK',
                        'Profit limit factor: {profit_limit_factor}.'
                    ]).format_map(pair)

def setDestination(dest):
    client.post('''https://esi.tech.ccp.is/latest\
/ui/autopilot/waypoint/?add_to_beginning=false&clear_other_waypoints=true&\
datasource=tranquility&destination_id=''' + str(dest))
    pass

def openMarketDetail(typeId):
    client.post('''https://esi.tech.ccp.is/latest\
/ui/openwindow/marketdetails/?datasource=tranquility&type_id=''' + str(typeId))

chaOnline = client.get('https://esi.tech.ccp.is/latest/characters/' + str(chaID) + '/online/?datasource=tranquility').json()
if chaOnline:
    print('Character online. triangulating...')
    locCurr = client.get('https://esi.tech.ccp.is/latest/characters/' + str(chaID) + '/location/?datasource=tranquility').json()['solar_system_id']
    print('Character found in system {}.'.format(systems.get(locCurr)['name']))
else:
    locCurr = None

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
                if locCurr is not None:
                    # Take jumps from current location into consideration
                    jumpsCurr = len(getRoute(locCurr, sysSell['system_id'])) - 1
                    if jumpsCurr == -1:
                        continue
                    jumps += jumpsCurr
                pass
            except Exception as errorMessage:
                print(errorMessage.args[0])
                continue
            legitPair = dict([
                ('type_id', int(typeId)),
                ('item_name', items.get(typeId)['name']),
                ('volume', availVolume),
                ('min_volume', minVolume),
                ('min_cost', minCost),
                ('item_size', itemVolume),
                ('total_size', itemVolume * availVolume),
                ('from_id', locSell), ('from_sec', secSell),
                ('from_name', getOrderLocationName(locSell)),
                ('to_id', locBuy), ('to_sec', secBuy),
                ('to_name', getOrderLocationName(locBuy)),
                ('cost', buyTotal),
                ('profit', profit),
                ('margin', margin),
                ('margin_actual', marginActual),
                ('jumps', jumps),
                ('profit_per_jump', profit / jumps),
                ('buy_orders', buyOrdersList),
                ('sell_orders', sellOrdersList),
                ('profit_limit_factor', profitLimFactor)
                ])
            tradePairs.append(legitPair)
            with open('./result.txt', 'a') as outputText:
                outputText.write(tradePairInfoStr(legitPair) + '\n\n')
                pass
            pass
        pass
    pass

command = 'dummy'
sortField = 'profit'
reverse = True
commandDict = { 'p': 'profit', 'm': 'margin', 'j': 'jumps' , 'u': 'profit_per_jump'}
while command.lower() != 'exit':
    tradePairs.sort(key=lambda pair: pair[sortField], reverse=reverse)
    for i in range(0, 3):
        print(tradePairInfoStr(tradePairs[i]), end='\n\n')
    command = input('''Please select 1~3.
'p' to sort by profit,
'm' to sort by margin(actual),
'j' to sort by jumps,
'u' to sort by profit per jump,
Capitalize ('P', 'M', 'J') to sort ascending.
'exit' to exit:''')
    if command in ['1', '2', '3']:
        idx = int(command) - 1
        command = input('"g" to go, "c" to clear this record.')
        if command == 'c':
            del tradePairs[idx]
        elif command == 'g':
            setDestination(tradePairs[idx]['from_id'])
            openMarketDetail(tradePairs[idx]['type_id'])
            input('Hit enter after reaching destination and bought the good.')
            input("*****DON'T FORGET TO LOAD YOUR CARGO!!!*****")
            setDestination(tradePairs[idx]['to_id'])
            del tradePairs[idx]
            pass
        pass
    elif command.lower() in list(commandDict.keys()):
        sortField = commandDict[command.lower()]
        reverse = command.islower()
        pass
    pass

with open('./cache/tradePairs.bin', 'wb') as output:
    print('Dumping trade pairs to file {}...'.format(output.name))
    pickle.dump(tradePairs, output, pickle.HIGHEST_PROTOCOL)
    print('Completed.')
    pass

