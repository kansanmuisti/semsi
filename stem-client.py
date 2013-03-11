#!/usr/bin/env python
import requests
import json

SERVER = "http://localhost:5000"
#SERVER = "http://semsi.kansanmuisti.fi/v1"
STEM_PATH = "/index/kamu/similar"

f = open('stem-client-data.txt')
s = f.read()

params = {'text': s}

url = "%s%s" % (SERVER, STEM_PATH)

#r = requests.get(url, params=params)
#print r
#print r.text

headers = {'Content-type': 'application/json'}
r = requests.get(url, data=json.dumps(params), headers=headers)
print r
print r.text
