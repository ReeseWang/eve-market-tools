#!/usr/bin/env python

import json
import requests
import pickle

print('Getting solar systems list...')
req = requests.get('https://esi.tech.ccp.is/latest/universe/systems/?datasource=tranquility')
assert req.status_code == 200
systems = req.json()

systemsInfo = dict()
for systemId in systems:
    print('Getting info of system {}...'.format(systemId))
    req = requests.get('https://esi.tech.ccp.is/latest/universe/systems/' + \
            str(systemId) + '/?datasource=tranquility')
    assert req.status_code == 200
    systemsInfo[str(systemId)] = req.json()
    print('System: {}, Security: {}'.format(
        req.json()['name'], req.json()['security_status']
        ))
    pass

with open('./cache/systemsInfo.bin', 'wb') as output:
    print('Dumping systems info to file {}...'.format(output.name))
    pickle.dump(systemsInfo, output, pickle.HIGHEST_PROTOCOL)
    print('Completed.')
    pass

