#!/usr/bin/env python3

import pickle
import math

with open('./cache/ordersAll.bin', 'rb') as input:
    print('Loading orders from file {} ...'.format(input.name))
    orders = pickle.load(input)
    print('Load complete.')
    pass

ordersTypeId = dict()
for regionId in orders:
    print(regionId)
    for order in orders[regionId]:
        typeId = str(order['type_id'])
        if ordersTypeId.get(typeId) is None:
            ordersTypeId[typeId] = dict([
                ('buy', dict()),
                ('sell', dict()),
                ('highest_buy', 0),
                ('lowest_sell', math.inf)])
            pass

        locationId = str(order['location_id'])
        if order['is_buy_order']:
            if ordersTypeId[typeId]['highest_buy'] < order['price']:
                ordersTypeId[typeId]['highest_buy'] = order['price']
            if ordersTypeId[typeId]['buy'].get(locationId) is None:
                ordersTypeId[typeId]['buy'][locationId] = []
            ordersTypeId[typeId]['buy'][locationId].append(order)
            pass
        else:
            if ordersTypeId[typeId]['lowest_sell'] > order['price']:
                ordersTypeId[typeId]['lowest_sell'] = order['price']
            if ordersTypeId[typeId]['sell'].get(locationId) is None:
                ordersTypeId[typeId]['sell'][locationId] = []
            ordersTypeId[typeId]['sell'][locationId].append(order)
            pass
        pass
    pass

for typeId in ordersTypeId:
    for locationId in ordersTypeId[typeId]['buy']:
        ordersTypeId[typeId]['buy'][locationId].\
            sort(key=lambda order: order['price'],
                 reverse=True)
        pass
    for locationId in ordersTypeId[typeId]['sell']:
        ordersTypeId[typeId]['sell'][locationId].\
            sort(key=lambda order: order['price'],
                 reverse=False)
        pass
    pass

with open('cache/ordersAllTypeIdSorted.bin', 'wb') as output:
    print('Dumping sorted order info to file {}...'.format(output.name))
    pickle.dump(ordersTypeId, output, pickle.HIGHEST_PROTOCOL)
    print('Completed.')
    pass
