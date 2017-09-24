#!/usr/bin/env python3

import json
import requests
import pickle

print('Getting region list...')
req = requests.get('https://esi.tech.ccp.is/latest/universe/regions/?datasource=tranquility')
assert req.status_code == 200
regions = req.json()

orders = dict()
for reg in regions:
    print('Getting orders in region {}...'.format(reg))
    req = requests.get('https://esi.tech.ccp.is/latest/markets/' + \
            str(reg) + '/orders/?datasource=tranquility&order_type=all&page=1')
    assert req.status_code == 200
    orders[str(reg)] = req.json()
    print('Page 1 received.')
    
    pages = int(req.headers['x-pages'])
    if pages > 1:
        for page in range(2, pages + 1):
            req = requests.get('https://esi.tech.ccp.is/latest/markets/' + \
                    str(reg) + '/orders/?datasource=tranquility' + \
                    '&order_type=all&page=' + str(page))
            assert req.status_code == 200
            orders[str(reg)].extend(req.json())
            print('Page {} received.'.format(page))
            pass
        pass
    print('Region {} has {} orders'.format(reg, len(orders[str(reg)])))
    pass
with open('cache/ordersAll.bin', 'wb') as output:
    print('Dumping order info to file {}...'.format(output.name))
    pickle.dump(orders, output, pickle.HIGHEST_PROTOCOL)
    print('Completed.')
    pass


