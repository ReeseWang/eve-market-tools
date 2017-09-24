import pickle
import requests
import os

class Cache:

    def __init__(self, name, prefix, suffix, folder='./cache/', fileSuffix='.bin'):
        self.name = name
        self.prefix = prefix
        self.suffix = suffix
        self.folder = folder
        self.fileSuffix = fileSuffix
        if not os.path.isdir(folder):
            os.makedirs(folder)
            pass
        
        try:
            self.filePath = self.folder + self.name + self.fileSuffix
            print("Loading data from '{}'...".format(self.filePath))
            with open(self.filePath, 'rb') as self.file:
                self.data = pickle.load(self.file)
                print('Completed.')
                pass
            pass

        except FileNotFoundError:
            print('File not found, will create a new one.')
            self.data = dict()
            pass

    def get(self, ID):
        if self.data.get(ID) == None:
            print('{} {} not found in local cache, retriving from server...'.
                    format(self.name.capitalize(), ID))
            req = requests.get(self.prefix + ID + self.suffix)
            assert req.status_code == 200
            self.data[ID] = req.json()
            if req.json().get('name') != None:
                print('{} {} is "{}", saved to local cache.'.
                        format(self.name.capitalize(), ID, req.json()['name']))
            pass
        return self.data[ID]
        
    def save(self):
        if os.path.exists(self.filePath):
            os.rename(self.filePath, self.filePath + '.bak')
        with open(self.filePath, 'wb') as self.file:
            pickle.dump(self.data, self.file, pickle.HIGHEST_PROTOCOL)
            pass
