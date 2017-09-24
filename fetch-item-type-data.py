#!/usr/bin/env python

import json
import requests
import pickle

print('Getting item list...')
req = requests.get('https://esi.tech.ccp.is/' + 
        'latest/universe/types/?datasource=tranquility&page=1')
assert req.status_code == 200
items = req.json()

page = 2
while len(req.json()) != 0:
    print('Page' + str(page) + '...')
    req = requests.get('https://esi.tech.ccp.is/' + 
            'latest/universe/types/?datasource=tranquility&page=' + \
            str(page))
    assert req.status_code == 200
    items.extend(req.json())
    page += 1
    pass

print('There are {} items in this universe'.format(len(items)))

itemsInfo = dict()
for typeInt in items:
    print('Getting info of item {}...'.format(typeInt))
    req = requests.get('https://esi.tech.ccp.is/' + 
            'latest/universe/types/' + str(typeInt) + 
            '/?datasource=tranquility&language=en-us')
    assert req.status_code == 200
    itemsInfo[str(typeInt)] = req.json()
    print('Item: {}, Volume: {}m3.'.format(
        req.json()['name'], req.json()['volume']))
    pass

with open('./cache/itemsInfo.bin', 'wb') as output:
    print('Dumping items info to file {}...'.format(output.name))
    pickle.dump(itemsInfo, output, pickle.HIGHEST_PROTOCOL)
    print('Completed.')
    pass

