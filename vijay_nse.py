#!/usr/bin/env python

#from nsetools import Nse
from pprint import pprint
from urllib.request import urlopen
from bs4 import BeautifulSoup
import os
import datetime
import csv
import sys
import logging
import re

## create dbDir within HomeDir manually
HomeDir = '/home/gopi/gopi/vijay_nse/'
DbDir = 'db'
StatFile = 'vijay_nse'

## During closed hours, previous day's date will be used.
## Eg. if the script is run at 2AM then the data taken 
## while running from cron is yesterday's data. 
## So store with yesterday's date.
ClosedHours = [ 1, 9 ]

## Dont Update days
SkipDays = [ 'Sat', 'Sun' ]

## default percent
defaultPercent = 25

## default Days to consider data
defaultDays = 60

# Will track only the commodity in the list
TrackCommodity = ['GOLDM', 'SILVERM', 'COPPERM', 'ALUMINI', 'LEADMINI', 'ZINCMINI', 'NICKELM', 'CRUDEOILM'] 

#def vijay_nse():
# nse = Nse()
# print (nse)
# 
# all_stock_codes = nse.get_stock_codes()
# #pprint(all_stock_codes)
# 
# #print (nse.is_valid_code('HINDUNILVR'))
# 
# q = nse.get_quote('HINDUNILVR')
# #pprint(q)
# all_stock_codes = nse.get_stock_codes()
# #pprint(all_stock_codes)
# 
# #print (nse.is_valid_code('HINDUNILVR'))
# 
# q = nse.get_quote('HINDUNILVR')
# #pprint(q)


# parses commodity data from http://market.mcxdata.in/
def vijay_mcx():

 link = 'http://market.mcxdata.in/'
 page = urlopen(link)
 
 soup = BeautifulSoup(page, 'html.parser')
 #print(soup.prettify())
 
 mcxTable = soup.find('table', id='fullMcxPriceTable')
 #print(mcxTable.prettify())
 
 cProperty = []
 for k in mcxTable.findAll('th'):
  cProperty.append(k.find(text=True))
 
 #print(cProperty)
 
 commodity={}
 for k in mcxTable.findAll('tr'):
  cName = k.find(text=True)
  if (cName == '' or cName == ' '):
   continue;
  #print(cName)
 
  # Track only the commodity in the list
  if (cName not in TrackCommodity):
   continue;

  commodity.setdefault(cName,{})
  i = 0
  for l in k.findAll('td'):
   if (i == 0):
    i += 1
    continue
   cPropValue = l.find(text=True)
   commodity[cName][cProperty[i]] = cPropValue
   #print(cName + ':' + str(i) + ':' + cProperty[i])
   i += 1
 
 #pprint(commodity)

 for c in TrackCommodity:
  if c not in commodity.keys():
   logging.warning('commodity detail [' + c + '] missing')
   
 return (commodity)
 
def vijay_calc_high_low(date, days, percent):

   for k in commodity.keys():
      #print (k)
      high = float(commodity[k]['High'])
      low  = float(commodity[k]['Low']) 
      ans  = (high-low) * float(percent)/100

      commodity[k]['VijayUpLimit'] = high + ans
      commodity[k]['VijayLowLimit'] = high - ans

def update_db(date, commodity):
	dbFile = os.path.join(HomeDir, DbDir, str(now.year)+ '.csv')
	dateStr = date.strftime('%d%b%Y')
	with open(dbFile, 'a', encoding='utf-8', newline='') as csv_file:
		csv_writer = csv.writer(csv_file, delimiter=',', quoting=csv.QUOTE_MINIMAL)
		for k in commodity.keys():
			csv_writer.writerow([dateStr, k, commodity[k]['Price']])

def LoadCommodity(date, days):
	commodity = {}	
	DateList = []
	YearsToLoad = [ (date-datetime.timedelta(days=days)).year ]	
	if date.year != YearsToLoad[0]:
		YearsToLoad.append(date.year)

	for i in range(0,days):
		DateList.append(date.strftime('%d%b%Y'))	
		date -= datetime.timedelta(days=1)	

	for year in YearsToLoad:
		dbFile = os.path.join(HomeDir, DbDir, str(year) + '.csv')
		#print (dbFile)
		with open (dbFile, 'r') as csv_file:
			csv_reader = csv.reader(csv_file)
			for row in csv_reader:

				# load data for wanted dates only
				if row[0] not in DateList:
					continue

				# have date, commodity name as index
				commodity.setdefault(row[0], {})
				commodity[row[0]].setdefault(row[1], row[2])
	
	#pprint (commodity)
	return commodity, DateList

def touch(fname):
	open(fname, 'a').close()
	os.utime(fname, None)

def printHelpAndExit():
	print('\r' + argv[0] + ' help\tDisplays this message')
	print('\r' + argv[0] + ' <date>\tProcesses for the date.'
			   + ' Uses today if no arg is specified')
	print('\r' + argv[0] + ' days=60\tSet days')
	print('\r' + argv[0] + ' percent=25\tSet percent')
	exit()

## program starts ##

## Performs path conversion. Find a better way 
t1 = HomeDir.split('\\')
t1[0] = t1[0].replace(':', ':/')
HomeDir = os.path.join(*t1)

## Gets current time
now = datetime.datetime.now()
logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s] %(levelname)s: %(message)s', datefmt='%d-%b-%y %H:%M:%S')

if len(sys.argv) == 2 and sys.argv[1] == 'updatedb':
	## Check if touch file is updated.
	## If so, just quit.
	## if not updatedb, touch file, quit.
	logging.debug('Trying DB update')
	StatFile = os.path.join(HomeDir, StatFile)
	if (os.path.exists(StatFile)):
		fs = os.stat(StatFile)
		mtime = datetime.datetime.fromtimestamp(fs[8])

		## do nothing if we have already updated db	
		if (now.date() == mtime.date()):
			logging.debug('Skipping DB update: Already updated')
			exit()

	## Incase the cron is scheduled to run on inactive time
	if (ClosedHours[0] <= now.hours <= ClosedHours[1]):
		now -= datetime.timedelta(days=1)

	if (now.strftime('%a') in SkipDays):
		logging.debug('Skipping DB update: Skipping updates on holidays')
		exit()
	
        ## Get commodity from server
	commodity = vijay_mcx()

	## Write to db YYYY.csv
	update_db(now, commodity)
	touch(StatFile)
	logging.debug('Data Updated now')

	#vijay_calc_high_low(commodity)
	#pprint(commodity)
else:
	percent = defaultPercent
	days = defaultDays 	
	date = now

	if len(sys.argv) > 1:
		for argv in sys.argv[1:]:
			if (argv == 'help'):
				printHelpAndExit()

			z=re.match(r'(days|percent)=([0-9]+)', argv)
			if (z != None):
				if (z.group(1) == 'days'):
					days = int(z.group(2))
				elif (z.group(1) == 'percent'):
					percent = int(z.group(2))
				else:
					print ('Invalid argument')
					printHelpAndExit()
			else:
				try:
					date = datetime.datetime.strptime(argv,'%d%b%Y')
				except:
					print ('Invalid date argument')
					printHelpAndExit()
			
	print (' Date: ' + date.strftime('%d%b%Y') 
			+ ' days: ' + str(days) 
			+ ' percent: ' + str(percent))

	commodity,dateList = LoadCommodity(date, days)
	#vijay_calc_high_low(date, days, percent)
	#pprint(commodity)
