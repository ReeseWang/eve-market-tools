#!/usr/bin/env python3

import requests
import pickle
import os
from concurrent.futures import ThreadPoolExecutor


def getOrders(ordersList, reg, page):
    req = requests.get('https://esi.tech.ccp.is/latest/markets/' +
                       str(reg) + '/orders/?datasource=tranquility' +
                       '&order_type=all&page=' + str(page))
    assert req.status_code == 200
    ordersList.extend(req.json())
    print('Region {} Page {} received.'.format(reg, page))
    pass


def getFirstPage(ordersDict, pageCountsDict, reg):
    print('Getting the first page of orders in region', reg)
    req = requests.get('https://esi.tech.ccp.is/latest/markets/' +
                       reg + '/orders/?datasource=tranquility' +
                       '&order_type=all&page=1')
    assert req.status_code == 200
    # return req.json(), int(req.headers['x-pages'])
    ordersDict[reg] = req.json()
    pageCountsDict[reg] = int(req.headers['x-pages'])


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
pageCounts = dict.fromkeys(regionsStr, 0)

with ThreadPoolExecutor(max_workers=10) as executor:
    for reg in regionsStr:
        executor.submit(getFirstPage, orders, pageCounts, reg)
        pass

with ThreadPoolExecutor(max_workers=10) as executor:
    for reg in regionsStr:
        assert pageCounts[reg] >= 1
        for page in range(1, pageCounts[reg]):
            executor.submit(getOrders, orders[reg], reg, page+1)
            pass
        pass
    pass

for reg in regionsStr:
    print('Region {} has {} orders'.format(reg, len(orders[reg])))
    pass

if not os.path.isdir('./cache/'):
    os.makedirs('./cache/')
    pass

with open('cache/ordersAll.bin', 'wb') as output:
    print('Dumping order info to file {}...'.format(output.name))
    pickle.dump(orders, output, pickle.HIGHEST_PROTOCOL)
    print('Completed.')
    pass
