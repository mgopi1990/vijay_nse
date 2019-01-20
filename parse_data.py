#!/usr/bin/env python

from bs4 import BeautifulSoup
import pprint
import os
import csv

Dict = {}
dateList = []
for file in os.listdir('xls-data'):
 fp = open('xls-data/' + file, 'r')
 soup = BeautifulSoup(fp, 'html.parser')
 for k in soup.findAll('tr'):
  row = []
  for l in k.findAll('td'):
   val = l.find(text=True)
   row.append(val)
  if len(row) < 9:
   continue
  #print (row)
  date = row[0].replace(' ','-')
  if date not in dateList:
   dateList.append(date)
  Dict.setdefault(date, {})
  Dict[date][row[2].rstrip(' ')] = row[9]
 fp.close()

#pprint.pprint(Dict)
#print(dateList[::-1])

with open('2018.csv', 'w', encoding='utf-8', newline='') as csv_file:
 csv_writer = csv.writer(csv_file, delimiter=',', quoting=csv.QUOTE_MINIMAL)
 for k in dateList[::-1]:
  for l in Dict[k].keys():
   csv_writer.writerow([k, l, Dict[k][l]])



