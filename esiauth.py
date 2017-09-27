#!/usr/bin/env python3

import os
import pickle
import secret
import urllib.parse
import json
import base64
import requests

class authedClient:

    def __init__(self, tokenFilePath = './secret.bin'):
        self.tokenFilePath = tokenFilePath
        if not os.path.exists(self.tokenFilePath):
            print('Token file not found, starting login process...')
            self.getToken('login')
        else:
            self.getToken('file')
            pass
        pass

    def updateAuthHeader(self):
        self.headers = {
                'Authorization': self.tokenData['token_type'] + ' ' + \
                        self.tokenData['access_token']
                }
        pass

    def _login(self):
        loginUrlBase = 'https://login.eveonline.com/oauth/authorize/?'
        loginUrlPara = { 'response_type': 'code',
                'redirect_uri': secret.callbackUrl,
                'client_id': secret.clientID,
                'scope': ' '.join(secret.scopes)
                }
        loginUrl = loginUrlBase + \
                urllib.parse.urlencode(loginUrlPara, quote_via=urllib.parse.quote)
        print('Copy following URL to browser and login:\n' + loginUrl)
        veriCode = input('Paste veryfication code here: ')

        postData = 'grant_type=authorization_code&code=' + veriCode
        self.tokenData = self.postToGetToken(postData)
        pass

    def _refresh(self):
        print('Token expired, refreshing...')
        postData = 'grant_type=refresh_token&refresh_token=' + self.tokenData['refresh_token']
        self.tokenData = self.postToGetToken(postData)
        pass

    def getToken(self, source):
        assert source in ['login', 'file', 'refresh']
        if source == 'refresh':
            self._refresh()
            self.writeTokenFile()
        elif source == 'file':
            with open(self.tokenFilePath, 'rb') as self.tokenFile:
                self.tokenData = pickle.load(self.tokenFile)
                print('Loaded token from file.')
                pass
            pass
        elif source == 'login':
            self._login()
            self.writeTokenFile()
            pass
        self.updateAuthHeader()
        pass

    def postToGetToken(self, postData):
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

        response = requests.post('https://login.eveonline.com/oauth/token',
                headers = postHeaders,
                data = postData)

        if response.ok:
            return response.json()
        else:
            sys.exit('Could not get token. {}'.format(self.genErrorString(response)))
            pass
        pass

    def genErrorString(response):
        return('Error {}: {}. {}.'.format(
                response.status_code,
                response.json()['error'],
                response.json()['error_description']))

    def writeTokenFile(self):
        print('Successfully got token, writing to file...')
        if os.path.exists(self.tokenFilePath):
            os.rename(self.tokenFilePath, self.tokenFilePath + '.bak')
            print('Old file found and backed up.')
        with open(self.tokenFilePath, 'wb') as self.tokenFile:
            pickle.dump(self.tokenData, self.tokenFile, pickle.HIGHEST_PROTOCOL)
            pass
        print('Done.')
        pass

    def get(self, url):
        try:
            response = requests.get(url, headers = self.headers)
            response.raise_for_status()
            if response.ok:
                return response
        except requests.exceptions.HTTPError as error:
            if 'expired' in response.text:
                self.getToken('refresh')
                response = requests.get(url, headers = self.headers)
                return response
            else:
                import sys
                sys.exit(error)
        except Exception as error:
            import sys
            sys.exit(error)

    def post(self, url, data=None):
        try:
            response = requests.post(url, data, headers = self.headers)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as error:
            if 'expired' in response.text:
                self.getToken('refresh')
                response = requests.get(url, headers = self.headers)
                return response
            else:
                import sys
                sys.exit(error)
        except Exception as error:
            import sys
            sys.exit(error)

    def getCharacterID(self):
        cha = self.get('https://login.eveonline.com/oauth/verify').json()
        return cha['CharacterID']

if __name__ == '__main__':
    import sys
    client = authedClient(tokenFilePath = sys.argv[1])
    print('Auth successful, got character ID: {}.'.format(client.getCharacterID()))

