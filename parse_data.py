#!/usr/bin/env python3

from bs4 import BeautifulSoup
import pprint
import os
import csv

Dict = {}
dateList = []
for file in os.listdir('xls-data'):
 fp = open('xls-data/' + file, 'r')

#pprint.pprint(Dict)
#print(dateList[::-1])



