#!/usr/bin/env python3

import requests
import pickle
import os
from concurrent.futures import ThreadPoolExecutor


def getOrdersRegion(ordersList, reg):
    print('Getting orders in region {}...'.format(reg))
    page = 1
    while True:
        req = requests.get('https://esi.tech.ccp.is/latest/markets/' +
                           str(reg) + '/orders/?datasource=tranquility' +
                           '&order_type=all&page=' + str(page))
        assert req.status_code == 200
        ordersList.extend(req.json())
        print('Region {} Page {} received.'.format(reg, page))
        pageCount = int(req.headers['x-pages'])
        page += 1
        if page > pageCount:
            break
        pass

    print('Region {} has {} orders'.format(reg, len(ordersList)))
    pass


print('Getting region list...')
req = requests.get('https://esi.tech.ccp.is/\
latest/universe/regions/?datasource=tranquility')
assert req.status_code == 200
regionsInt = req.json()

regionsStr = []
for reg in regionsInt:
    regionsStr.append(str(reg))
    pass

orders = dict.fromkeys(regionsStr, [])
with ThreadPoolExecutor(max_workers=10) as executor:
    for reg in regionsStr:
        executor.submit(getOrdersRegion, orders[reg], reg)
        pass

if not os.path.isdir('./cache/'):
    os.makedirs('./cache/')
    pass

with open('cache/ordersAll.bin', 'wb') as output:
    print('Dumping order info to file {}...'.format(output.name))
    pickle.dump(orders, output, pickle.HIGHEST_PROTOCOL)
    print('Completed.')
    pass
