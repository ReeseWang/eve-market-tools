#!/usr/bin/env python3

import pickle
import secret
import urllib.parse
import json
import base64
import requests

loginUrlBase = 'https://login.eveonline.com/oauth/authorize/?'
loginUrlPara = { 'response_type': 'code',
        'redirect_uri': secret.callbackUrl,
        'client_id': secret.clientID,
        'scope': ' '.join(secret.scopes)
        }
loginUrl = loginUrlBase + urllib.parse.urlencode(loginUrlPara, quote_via=urllib.parse.quote)
print('Copy following URL to browser and login:\n' + loginUrl)
veriCode = input('Paste veryfication code here: ')

postData = 'grant_type=authorization_code&code=' + veriCode
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

