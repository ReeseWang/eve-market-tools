#!/usr/bin/env python3

import json
import requests
import pickle

with open('./cache/ordersAll.bin', 'rb') as input:
    print('Loading orders from file {} ...'.format(input.name))
    orders = pickle.load(input)
    print('Load complete.')
    pass

ordersTypeId = dict()
for regionId in orders:
    for order in orders[regionId]:
        typeId = str(order['type_id'])
        if ordersTypeId.get(typeId) == None:
            ordersTypeId[typeId] = dict([('buy', []), ('sell', [])])
            pass

        if order['is_buy_order']:
            ordersTypeId[typeId]['buy'].append(order)
            pass
        else:
            ordersTypeId[typeId]['sell'].append(order)
            pass
        pass
    pass

for typeId in ordersTypeId:
    ordersTypeId[typeId]['buy'].sort(key=lambda order: order['price'], \
            reverse=True)
    ordersTypeId[typeId]['sell'].sort(key=lambda order: order['price'], \
            reverse=False)
    pass

with open('cache/ordersAllTypeIdSorted.bin', 'wb') as output:
    print('Dumping sorted order info to file {}...'.format(output.name))
    pickle.dump(ordersTypeId, output, pickle.HIGHEST_PROTOCOL)
    print('Completed.')
    pass
