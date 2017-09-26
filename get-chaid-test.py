#!/usr/bin/env python3

import pickle
import secret
import urllib.parse
import json
import base64
import requests
from bravado.requests_client import RequestsClient
from bravado.client import SwaggerClient

with open('./secret.bin', 'rb') as tokenFile:
    tokenData = pickle.load(tokenFile)
    print('Loaded token from file.')
    pass

headers = {
        'Authorization': tokenData['token_type'] + ' ' + tokenData['access_token'],
        'Host': 'login.eveonline.com'
        }

respond = requests.get('https://login.eveonline.com/oauth/verify',
        headers = headers)

if respond.ok:
    print('Got character info. Character ID: {}.'.format(respond.json()['CharacterID']))
    pass
elif respond.json()['error_description'] == 'expired':
    print('Token expired, refreshing...')
    postData = 'grant_type=refresh_token&refresh_token=' + tokenData['refresh_token']
    headerAuthString = 'Basic ' + \
                    base64.b64encode(
                            (secret.clientID + 
                                ':' + 
                                secret.secretKey).encode('utf-8')).decode('utf-8')
    postHeaders = {
            'Authorization': headerAuthString,
            'Content-Type': 'application/x-www-form-urlencoded',
            'Host': 'login.eveonline.com'
            }

    respond = requests.post('https://login.eveonline.com/oauth/token',
            headers = postHeaders,
            data = postData)

    if respond.ok:
        tokenData = respond.json()
        print('Successfully got token, writing to file...')
        with open('./secret.bin', 'wb') as tokenFile:
            pickle.dump(tokenData, tokenFile, pickle.HIGHEST_PROTOCOL)
            pass
        print('Done.')
        pass
    else:
        print('Error {}: {}. {}.'.format(
            respond.status_code,
            respond.json()['error'],
            respond.json()['error_description'])
            )
        pass
else:
    print('Error {}: {}. {}.'.format(
        respond.status_code,
        respond.json()['error'],
        respond.json()['error_description'])
        )
    pass
