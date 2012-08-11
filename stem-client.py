#!/usr/bin/env python
import requests

SERVER = "http://localhost:8000/v1"
STEM_PATH = "/stem"

f = open('stem-client-data.txt')
s = f.read()

params = {'text': s}

url = "%s%s" % (SERVER, STEM_PATH)

#r = requests.get(url, params=params)
#print r
#print r.text

r = requests.post(url, data=params)
print r
print r.text
