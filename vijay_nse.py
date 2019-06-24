#!/usr/bin/env python3

#from nsetools import Nse
from pprint import pprint
from urllib.request import urlopen
from bs4 import BeautifulSoup
from prettytable import PrettyTable
from termcolor import colored
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib, ssl
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
MailFile = 'mail.cfg'

## During closed hours, previous day's date will be used.
## Eg. if the script is run at 2AM then the data taken 
## while running from cron is yesterday's data. 
## So store with yesterday's date.
## Add cron like, 
## Just run vijay's script 1AM,2AM,3AM,4AM,5AM,6AM,7AM,8AM
## 0	1-8	*	*	*	/home/pi/vijay_nse/vijay_nse.py updatedb
ClosedHours = [ 1, 9 ]

## Dont Update days
SkipDays = [ 'Sat', 'Sun' ]

## default percent
defaultPercent = 25

## default Days to consider data
defaultDays = 90

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
link = 'http://market.mcxdata.in/'
def vijay_mcx():

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
 
def vijay_calc_high_low(commodity, percent):

	for k in commodity.keys():
		#print (k)

		## Find High Low
		dateList = list(commodity[k].keys())
		commodity[k]['High'] = commodity[k][dateList[0]]
		commodity[k]['Low']  = commodity[k][dateList[0]]
		for date in dateList[1:]:
			if commodity[k][date] > commodity[k]['High']:
				commodity[k]['High'] = commodity[k][date]
			elif commodity[k][date] < commodity[k]['Low']:
				commodity[k]['Low'] = commodity[k][date]

		high = float(commodity[k]['High'])
		low  = float(commodity[k]['Low']) 
		ans  = (high-low) * float(percent)/100
		
		commodity[k]['VijayUpLimit'] = high - ans
		commodity[k]['VijayLowLimit'] = low + ans
	
def UpdateCommodity(commodity, commodity_now):
	for c in TrackCommodity:
		commodity[c]['now'] = float(commodity_now[c]['Price'])

def PrepareRowData(sno, date, commodity):
	rowData = []
	rowData.append(str(sno))
	rowData.append(date)
	for c in TrackCommodity:
		if date not in commodity[c].keys():
			rowData.append('NA')
			continue

		price = commodity[c][date]
		if price == commodity[c]['High']:
			rowData.append(('%0.2f'%price))
		elif price == commodity[c]['Low']:
			rowData.append(('%0.2f'%price))
		else:
			rowData.append('%0.2f'%price)

	#print (rowData)
	return rowData
	
def print_text_table(commodity, dateList, arg):

	print (' Date: ' + arg['Date'] 
			+ ' days: ' + arg['days'] 
			+ ' percent: ' + arg['percent'])

	## print Table1
	t1 = PrettyTable(['Sno', 'Date'] + TrackCommodity)
	t1.title=(str(len(dateList))+" day Data")
	sno = 1
	for date in dateList:
		rowData = PrepareRowData(sno, date, commodity)
		t1.add_row(rowData)
		sno += 1
	print(t1.get_string() + '\n\n')

	## print Table2
	Title = ['Sno', 'Commodity', 'Low', 'High', 'LowLimit', 'UpLimit', 'now', 'Call']
	sno = 1
	t2 = PrettyTable(Title)
	t2.title='Commodity BUY/SELL Calculation'
	for c in TrackCommodity:
		PriceNow = commodity[c]['now']
		if PriceNow >= commodity[c]['VijayUpLimit']:
			t2.add_row([colored(str(sno), 'red'), 
							colored(c, 'red'), 
							colored(('%0.2f'%commodity[c]['Low']), 'red'), 
							colored(('%0.2f'%commodity[c]['High']), 'red'),   
							colored(('%0.2f'%commodity[c]['VijayLowLimit']), 'red'),  
							colored(('%0.2f'%commodity[c]['VijayUpLimit']), 'red'),
							colored(('%0.2f'%PriceNow), 'red'),
							colored('SELL', 'red')])
		elif PriceNow <= commodity[c]['VijayLowLimit']:
			t2.add_row([colored(str(sno), 'green'), 
							colored(c, 'green'), 
							colored(('%0.2f'%commodity[c]['Low']), 'green'), 
							colored(('%0.2f'%commodity[c]['High']), 'green'),   
							colored(('%0.2f'%commodity[c]['VijayLowLimit']), 'green'),  
							colored(('%0.2f'%commodity[c]['VijayUpLimit']), 'green'),
							colored(('%0.2f'%PriceNow), 'green'),
							colored('BUY', 'green')])
		else:	
			t2.add_row([str(sno), c, ('%0.2f'%commodity[c]['Low']), ('%0.2f'%commodity[c]['High']), 
						('%0.2f'%commodity[c]['VijayLowLimit']), ('%0.2f'%commodity[c]['VijayUpLimit']),
						('%0.2f'%PriceNow), ''])
		sno += 1
	print(t2.get_string() + '\n\n')

def mail_get_info_from_file (FileName):
	dict_mail = {}
	try:
		fp = open (FileName, 'r')
	except:
		print (' ERROR: ' + FileName + ' not found')
		return None
	else:
		for line in fp:
			t1 = line.split(':')
			key = t1[0].strip().lower()
			if (key == 'from'):
				dict_mail[key] = t1[1].strip()
			elif (key == 'to'):
				val = t1[1].split(',')
				dict_mail[key] = [ x.strip() for x in val ]
				#print (dict_mail[key]);
			elif (key == 'password'):
				dict_mail[key] = t1[1].strip()
			elif (key == 'server'):
				dict_mail[key] = t1[1].strip()
				dict_mail['port'] = int(t1[2].strip())
			else:
				print (' ERROR: Parse failed [' + line + ']')
				return None

		if len (dict_mail) != 5:
			print (' ERROR: Need all 5 params (from, to, password, server, port)')
			return None
	return dict_mail

def mail_text_table(commodity, dateList, arg):
	dict_mail = mail_get_info_from_file (os.path.join(HomeDir, MailFile))
	if (dict_mail == None):
		return 

	#pprint (dict_mail)

	## VijayNSE	
	htmlData = (
		'<html><body style="Font:15px Ariel,sans-serif;text-align:center;color:#000000"><table cellpadding="0" style="border-collapse:collapse"><tr><td><div style="width:min-context;">'
		+ '<div style="width:min-content;background:#000000">'
		+ '<h1 style="letter-spacing:1px;font-weight:bold;font-size:40px;display:block;margin:0">&nbsp;'
		+ '<span style="color:#DE2600">VIJAY</span><span style="color:#FFFFFF">NSE</span>&nbsp;</h1>'
		+ '</div></td></tr>')

	htmlData += '<tr><td><div style="width:min-content;">'

	## DateTime when mail is sent
	htmlData += (
		'<ul style="list-style-type:none;display:flex;padding:0;margin:3px 0px 0px 0px">'
		+ '<li style="background:#000000;color:#FFFFFF;font-weight:bold;padding:8px;margin:2px">Mailed&nbsp;Time</li>'
		+ '<li style="background:#D9D9D9;padding:8px;margin:2px">'
		+ now.strftime('%d%b%Y') + '</li>'
		+ '<li style="background:#D9D9D9;padding:8px;margin:2px">'
		+ now.strftime('%H:%M:%S') + '</li>' + '</ul></td></tr>')

	## Date, Days, Percentage
	htmlData += (
		'<tr><td><ul style="list-style-type:none;display:flex;padding:0;margin:2px 0px 0px 0px">'
		+ '<li style="background:#D9D9D9;padding:8px;margin:2px">'
		+ arg['Date'] + '</li>'
		+ '<li style="background:#D9D9D9;padding:8px;margin:2px">'
		+ arg['days'] + '&nbsp;days' + '</li>'
		+ '<li style="background:#D9D9D9;padding:8px;margin:2px">'
		+ arg['percent'] + '%' + '</li>' + '</ul></td></tr>') 

	## Url
	htmlData += (
		'<tr><td><ul style="list-style-type:none;display:flex;padding:0;margin:2px 0px 0px 0px">'
		+ '<li style="background:#000000;color:#FFFFFF;font-weight:bold;padding:8px;margin:2px">Url</li>'
		+ '<li style="background:#D9D9D9;padding:8px;margin:2px">'
		+ '<a style="color:#000000;font-size:15px;text-decoration:none;" href="' + link + '">' + link + '</a>' + '</li>' + '</ul></td></tr>' )

	## Commodity list
	htmlCommodity = ''
	for c in TrackCommodity:
		htmlCommodity += '<li style="background:#D9D9D9;padding:8px;margin:2px">' + c.title() + '</li>'

	htmlData += (
		'<tr><td><ul style="list-style-type:none;display:flex;padding:0;margin:2px 0px 0px 0px">'
		+ '<li style="background:#DE2600;color:#FFFFFF;font-weight:bold;padding:8px;margin:2px">COMMODITY</li>' + htmlCommodity + '</ul></td></tr>')


	### print Table1
	tList = ['Sno', 'Date']	+ TrackCommodity
	htmlData += ('<br><div style="width:min-content;">'
		+ '<h2 style="background:#DE2600;color:#FFFFFF;font-size:15px;font-weight:bold;padding:8px;margin:2px">' + str(len(dateList)) + ' day Data </h2>'
		+ '<table style="border:1px solid black;" cellpadding="3px">'
		+ '<tr style="text-align:center;background:#000000;color:#FFFFFF;vertical-align:middle;text-align: center;"><th>' + '</th><th>'.join(tList) + '</th></tr>')

	### Generates rows for Table1
	sno = 1
	for date in dateList:
		rowData = PrepareRowData(sno, date, commodity)
		htmlData += ('<tr style="background:#D9D9D9;vertical-align:top;text-align:right;">'
			+ '<td style="text-align:center">' + rowData[0] + '</td>'
			+ '<td>' + '</td><td>'.join(rowData[1:]) + '</td></tr>')
		sno += 1
	htmlData += '</table></div>'


	### print Table2
	Title = ['Sno', 'Commodity', 'Low', 'High', 'LowLimit', 'UpLimit', 'now', 'Call']
	htmlData += ('<br><div style="width:min-content;">'
		+ '<h2 style="background:#DE2600;color:#FFFFFF;font-size:15px;font-weight:bold;padding:8px;margin:2px">' +  ' Commodity BUY/SELL Calculation </h2>'
		+ '<table style="border:1px solid black;" cellpadding="3px">'
		+ '<tr style="text-align:center;background:#000000;color:#FFFFFF;vertical-align:middle;text-align: center;"><th>' + '</th><th>'.join(Title) + '</th></tr>')

	### Generate row for Table2
	sno = 1
	for c in TrackCommodity:
		PriceNow = commodity[c]['now']
		if PriceNow >= commodity[c]['VijayUpLimit']:
			htmlData += ('<tr class="sell" style="background:#FFC1C1;vertical-align:top;text-align:right;">'
						+ '<td style="text-align:center">' + str(sno) + '</td>'
						+ '<td style="text-align:left">' + c + '</td>'
						+ '<td>' + '%0.2f'%commodity[c]['Low'] + '</td>'
						+ '<td>' + '%0.2f'%commodity[c]['High'] + '</td>'  
						+ '<td>' + '%0.2f'%commodity[c]['VijayLowLimit'] + '</td>' 
						+ '<td>' + '%0.2f'%commodity[c]['VijayUpLimit'] + '</td>'
						+ '<td>' + '%0.2f'%PriceNow + '</td>'
						+ '<td style="text-align:center">' + 'SELL' + '</td></tr>')
		elif PriceNow <= commodity[c]['VijayLowLimit']:
			htmlData += ('<tr class="buy" style="background:#BDFF7B;vertical-align:top;text-align:right;">'
						+ '<td style="text-align:center">' + str(sno) + '</td>'
						+ '<td style="text-align:left">' + c + '</td>'
						+ '<td>' + '%0.2f'%commodity[c]['Low'] + '</td>'
						+ '<td>' + '%0.2f'%commodity[c]['High'] + '</td>'  
						+ '<td>' + '%0.2f'%commodity[c]['VijayLowLimit'] + '</td>' 
						+ '<td>' + '%0.2f'%commodity[c]['VijayUpLimit'] + '</td>'
						+ '<td>' + '%0.2f'%PriceNow + '</td>'
						+ '<td style="text-align:center">' + 'BUY' + '</td></tr>')
		else:	
			htmlData += ('<tr class="none" style="background:#D9D9D9;vertical-align:top;text-align:right;">'
						+ '<td style="text-align:center">' + str(sno) + '</td>'
						+ '<td style="text-align:left">' + c + '</td>'
						+ '<td>' + '%0.2f'%commodity[c]['Low'] + '</td>'
						+ '<td>' + '%0.2f'%commodity[c]['High'] + '</td>'  
						+ '<td>' + '%0.2f'%commodity[c]['VijayLowLimit'] + '</td>' 
						+ '<td>' + '%0.2f'%commodity[c]['VijayUpLimit'] + '</td>'
						+ '<td>' + '%0.2f'%PriceNow + '</td>'
						+ '<td style="text-align:center">' + '' + '</td></tr>')
		sno += 1
	htmlData += '</table></div></br></br>'

	htmlData += '</div></body></html>'

	#print (htmlData)	

	message = MIMEMultipart('alternative')
	message['Subject'] = (' VijayNSE Date: ' + arg['Date'] 
							+ ' days: ' + arg['days'] 
							+ ' percent: ' + arg['percent'])
	message['From'] = dict_mail['from']
	message['To'] 	= ', '.join(dict_mail['to'])
	message.attach(MIMEText(htmlData, "html"))
	#print (message.as_string())

	# Create secure connection with server and send email
	cxt = ssl.create_default_context()
	with smtplib.SMTP_SSL(dict_mail['server'], dict_mail['port'], context=cxt) as server:
		server.login(dict_mail['from'], dict_mail['password'])
		server.sendmail(dict_mail['from'], dict_mail['to'], message.as_string())
		logging.debug('Mail sent successfully to ' + ','.join(dict_mail['to']))

	return

def update_db(date, commodity):
	dbFile = os.path.join(HomeDir, DbDir, str(now.year)+ '.csv')
	#print(dbFile)
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

	#print(DateList)
	#print(YearsToLoad)
	for year in YearsToLoad:
		dbFile = os.path.join(HomeDir, DbDir, str(year) + '.csv')
		#print (dbFile)
		with open (dbFile, 'r') as csv_file:
			csv_reader = csv.reader(csv_file)
			for row in csv_reader:
				#print (row)

				# load data for wanted dates only
				if row[0] not in DateList:
					continue

				# have commodity name, date as index
				commodity.setdefault(row[1], {})
				commodity[row[1]].setdefault(row[0], float(row[2]))
	
	#pprint (commodity)
	return commodity, DateList

def process_commodity (date, days, percent, console=True, mail=False):
	arg = {}
	arg['Date'] = date.strftime('%d%b%Y')
	arg['days'] = str(days)
	arg['percent'] = str(percent)

	commodity,dateList = LoadCommodity(date, days)
	vijay_calc_high_low(commodity, percent)

	#pprint(dateList)
	#pprint(commodity)

	## Get commodity from server
	commodity_now = vijay_mcx()
	#pprint(commodity_now)

	## Updates the commodity_now to the commodity
	UpdateCommodity(commodity, commodity_now)

	if console:
		print_text_table(commodity, dateList, arg)

	if mail:
		mail_text_table (commodity, dateList, arg)

	#pprint(commodity)

def touch(fname):
	open(fname, 'a').close()
	os.utime(fname, None)

def printHelpAndExit():
	print('\r' + argv[0] + ' help\tDisplays this message')
	print('\r' + argv[0] + ' <date>\tProcesses for the date.'
			   + ' Uses today if no arg is specified')
	print('\r' + argv[0] + ' days=90\tSet days')
	print('\r' + argv[0] + ' percent=25\tSet percent')
	exit()

## program starts ##

## Performs path conversion. Find a better way 
t1 = HomeDir.split('\\')
t1[0] = t1[0].replace(':', ':/')
HomeDir = os.path.join(*t1)

#print ('\r [' + HomeDir + ']')

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
	if (ClosedHours[0] <= now.hour <= ClosedHours[1]):
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

	## Sends mail
	process_commodity (now, defaultDays, defaultPercent, console=False, mail=True)

	#vijay_calc_high_low(commodity)
	#pprint(commodity)
else:
	percent = defaultPercent
	days = defaultDays 	
	date = now
	mail = False

	if len(sys.argv) > 1:
		for argv in sys.argv[1:]:
			if (argv == 'help'):
				printHelpAndExit()
			elif (argv == 'mail'):
				mail = True
				continue

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

	process_commodity (date, days, percent, mail=mail)
