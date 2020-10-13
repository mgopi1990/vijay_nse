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
import logging.handlers
import re

## create dbDir within HomeDir manually
HomeDir = '/home/pi/scripts/vijay_nse/'
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
ClosedHours = ( 1, 9 )

## Dont Update days
SkipDays = ( 'Sat', 'Sun' )

## default percent
defaultPercent = 25

## default Days to consider data
defaultDays = 90

## default Max logs
defaultMaxLog = 50

## tracking start date
tracking_start_date = datetime.datetime.strptime('11Oct2018', '%d%b%Y')

## Will track only the commodity in the list
TrackCommodity = ('GOLDM', 'SILVERM', 'ALUMINIUM', 'COPPER',
					'LEAD', 'NICKEL', 'ZINC', 'CRUDEOIL')

## Title for Table1 and Table2
Table1Title = ('Sno', 'Date') + TrackCommodity
Table2Title = ('Sno', 'Commodity', 'Low', 'High', 'LowLimit', 'UpLimit', 
				'now', 'Percent%', 'Call')
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

 # to handle ssl certificate related errors
 if (not os.environ.get('PYTHONHTTPSVERIFY', '') and
      getattr(ssl, '_create_unverified_context', None)):
  ssl._create_default_https_context = ssl._create_unverified_context

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
   my_logger.warning('commodity detail [' + c + '] missing')
   
 return (commodity)
 
def vijay_calc_high_low(commodity, percent):

	for k in TrackCommodity:
		#print (k)

		## Since we are preparing the dateList from 
		## commodity's datelist, naturally the days
		## data was missing (NA) entries will be
		## automatically ignored. Good thing.
		dateList = list(commodity[k].keys())

		## Find High Low
		commodity[k]['High'] = commodity[k][dateList[0]]
		commodity[k]['Low']  = commodity[k][dateList[0]]
		commodity[k]['HighDate'] = dateList[0]
		commodity[k]['LowDate']  = dateList[0]
		for date in dateList[1:]:
			if commodity[k][date] > commodity[k]['High']:
				commodity[k]['High'] = commodity[k][date]
				commodity[k]['HighDate'] = date
			elif commodity[k][date] < commodity[k]['Low']:
				commodity[k]['Low'] = commodity[k][date]
				commodity[k]['LowDate'] = date

		high = float(commodity[k]['High'])
		low  = float(commodity[k]['Low']) 
		ans  = (high-low) * float(percent)/100
		
		commodity[k]['VijayUpLimit'] = high - ans
		commodity[k]['VijayLowLimit'] = low + ans

		deno = high - low
		if deno == 0:
			## Just a minor adjustment
			## To avoid divide by zero exception
			deno += 0.000001

		## Use Vijay's secret formula
		## R1 -> High
		## R2 -> Low
		## R3 -> now
		## Percent = ((R3-R2)/(R1-R2))*100
		commodity[k]['VijayPercent'] = (commodity[k]['now'] - low)/deno * 100
	
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

def DrawTable1Rows(dateList, commodity):
	htmlData = ''
	sno = 1
	day = datetime.datetime.strptime(dateList[0],'%d%b%Y').weekday()
	for date in dateList:
		rowData = PrepareRowData(sno, date, commodity)

		## saturday = 5, sunday = 6
		## all rows will be NA NA.
		if (day == 5 or day == 6):
			htmlData += ('<tr style="background:#777777;color:#FFFFFF;vertical-align:top;text-align:center">'
			+ '<td>' + '</td><td>'.join(rowData) + '</td></tr>')
		else:
			## count the non-empty rows
			## commodity starts from rowData[2:]
			c = 0
			for item in rowData[2:]:
				if item != 'NA':
					c += 1

			## for all rows empty
			if c == 0:
				htmlData += ('<tr style="background:#DE2600;color:#FFFFFF;font-weight:bold;vertical-align:top;text-align:center;">'
				+ '<td style="text-align:center">' + rowData[0] + '</td>'
				+ '<td>' + '</td><td>'.join(rowData[1:]) + '</td></tr>')
			else:	
				tempStr = ''

				## sometimes classic C stuff is much better than 
				## python range() :-P 
				i = 0
				while (i < len(TrackCommodity)):
					## skip two rows Sno, Date
					data = rowData[2 + i]

					#print ('{} || {}'.format(rowData, data))
					#print ('{} ({},{}) Data:{} {}'.format(TrackCommodity[i], 
					#				commodity[TrackCommodity[i]]['Low'],
					#				commodity[TrackCommodity[i]]['High'],
					#				i, data))
					if data == 'NA':
						tempStr += '<td style="background:#DE2600;color:#FFFFFF;text-align:center;font-weight:bold">NA</td>'
					elif float(data) == commodity[TrackCommodity[i]]['High']:
						tempStr += '<td style="background:#FFC1C1;font-weight:bold;">{}</td>'.format(data)
					elif float(data) == commodity[TrackCommodity[i]]['Low']:
						tempStr += '<td style="background:#BDFF7B;font-weight:bold;">{}</td>'.format(data)
					else:
						tempStr += '<td>{}</td>'.format(data)

					i += 1

				htmlData += ('<tr style="background:#D9D9D9;vertical-align:top;text-align:right;">'
					+ '<td style="text-align:center">' + rowData[0] + '</td>'
					+ '<td style="text-align:center">' + rowData[1] + '</td>'
					+ tempStr + '</tr>')

		## we can also use the below formula
		## ((7 + BeginDay - (BeginDaySNo % 7)) % 7)
		## where BeginDay -> day,.. say wednesday.
		## BeginDaySNo -> sno corresponding to that day. say 1.
		## Sno: 1 2 3 4 5 6 7 8 9 10 11
		## Day: W T M S S F T W T  M  S
		## Week:2 1 0 6 5 4 3 2 1  0  6
		## Basically we want it to loop through
		## The below if check does it, than the complex mod operations
		day -= 1
		if (day == -1):
			day = 6
	
		sno += 1

	return htmlData


def DrawTable2Rows(commodity):
	FormatTable = {
		'None': {
			'name':		 '',
			'classname': 'none',
			'bgcolor':	 '#D9D9D9'
		},
		'Buy': {
			'name':		 'BUY',
			'classname': 'buy',
			'bgcolor':	 '#BDFF7B'
		},
		'Sell': {
			'name':		 'SELL',
			'classname': 'sell',
			'bgcolor':	 '#FFC1C1'
		}
	}

	htmlData = ''
	sno = 1
	for c in TrackCommodity:
		PriceNow = commodity[c]['now']
		if PriceNow >= commodity[c]['VijayUpLimit']:
			formatT = FormatTable['Sell']
		elif PriceNow <= commodity[c]['VijayLowLimit']:
			formatT = FormatTable['Buy']
		else:
			formatT = FormatTable['None']

		htmlData += ('<tr class="{}" style="background:{};vertical-align:top;text-align:right;">'.format(formatT['classname'],formatT['bgcolor'])
				+ '<td style="text-align:center">' + str(sno) + '</td>'
				+ '<td style="text-align:left">' + c + '</td>'
				+ '<td title="{0}">{1:0.2f}</td>'.format(commodity[c]['LowDate'],commodity[c]['Low'])
				+ '<td title="{0}">{1:0.2f}</td>'.format(commodity[c]['HighDate'],commodity[c]['High'])
				+ '<td>{0:0.2f}</td>'.format(commodity[c]['VijayLowLimit'])
				+ '<td>{0:0.2f}</td>'.format(commodity[c]['VijayUpLimit'])
				+ '<td>{0:0.2f}</td>'.format(PriceNow)
				+ '<td>{0:0.2f}%</td>'.format(commodity[c]['VijayPercent'])
				+ '<td style="text-align:center">{}</td></tr>'.format(formatT['name']))
		sno += 1

	return htmlData

def DrawTable3Log(commodity_HL_log):
	htmlData = '<div style="text-align:left;">'
	for k in TrackCommodity:
		htmlData += '<br/><b>{}:</b><br/>'.format(k)

		i = 0
		for date in reversed(commodity_HL_log[k]['DateList']):
			if (i >= defaultMaxLog):
				break

			htmlData += ' {}:'.format(date)
			if (commodity_HL_log[k][date][0] == 'H'):
				htmlData += ' <span style="color:red">{}</span><br/>'.format(commodity_HL_log[k][date][1])
			else:
				htmlData += '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:green">{}</span><br/>'.format(commodity_HL_log[k][date][1])

			i += 1
	htmlData += '<br/>'
	return htmlData

def DrawHTMLData(commodity, dateList, commodity_HL_log, arg):
	## VijayMCX
	htmlData = (
		'<html><body style="Font:15px Ariel,sans-serif;text-align:center;color:#000000"><table cellpadding="0" style="border-collapse:collapse"><tr><td><div style="width:min-context;">'
		+ '<div style="width:min-content;background:#000000">'
		+ '<h1 style="letter-spacing:1px;font-weight:bold;font-size:40px;display:block;margin:0">&nbsp;'
		+ '<span style="color:#DE2600">VIJAY</span><span style="color:#FFFFFF">MCX</span>&nbsp;</h1>'
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
		+ datetime.datetime.strptime(arg['Date'],'%d%b%Y').strftime('%A') + '</li>' 
		+ '<li style="background:#D9D9D9;padding:8px;margin:2px">'
		+ arg['Date'] + '</li>'
		+ '<li style="background:#D9D9D9;padding:8px;margin:2px">'
		+ arg['days'] + '&nbsp;days' + '</li>'
		+ '<li style="background:#D9D9D9;padding:8px;margin:2px">'
		+ arg['percent'] + '%' + '</li>' 
		+ '<li style="background:#DE2600;color:#FFFFFF;font-weight:bold;padding:8px;margin:2px">'
		+ arg['by'] + '</li>' 
		+ '</ul></td></tr>') 

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
	htmlData += ('<br><div style="width:min-content;">'
		+ '<h2 style="background:#DE2600;color:#FFFFFF;font-size:15px;font-weight:bold;padding:8px;margin:2px">' + str(len(dateList)) + ' day Data </h2>'
		+ '<table style="border:1px solid black;" cellpadding="3px">'
		+ '<tr style="text-align:center;background:#000000;color:#FFFFFF;vertical-align:middle;text-align: center;"><th>' + '</th><th>'.join(Table1Title) + '</th></tr>')

	### Generates rows for Table1
	htmlData += DrawTable1Rows(dateList, commodity)

	htmlData += '</table></div>'


	### print Table2
	htmlData += ('<br><div style="width:min-content;">'
		+ '<h2 style="background:#DE2600;color:#FFFFFF;font-size:15px;font-weight:bold;padding:8px;margin:2px">' +  ' Commodity BUY/SELL Calculation </h2>'
		+ '<table style="border:1px solid black;" cellpadding="5px">'
		+ '<tr style="text-align:center;background:#000000;color:#FFFFFF;vertical-align:middle;text-align: center;"><th>' + '</th><th>'.join(Table2Title) + '</th></tr>')

	### Generate row for Table2
	htmlData += DrawTable2Rows(commodity)
	htmlData += '</table></div></br></br>'

	### Generate table for log
	htmlData += DrawTable3Log(commodity_HL_log)

	htmlData += '</div></body></html>'

	#print (htmlData)	
	
	return htmlData

	
def print_text_table(commodity, dateList, commodity_HL_log, arg):

	print (' Date: ' + arg['Date'] 
			+ ' days: ' + arg['days'] 
			+ ' percent: ' + arg['percent'])

	## print Table1
	t1 = PrettyTable(Table1Title)
	t1.title=(str(len(dateList))+" day Data")
	sno = 1
	for date in dateList:
		rowData = PrepareRowData(sno, date, commodity)
		t1.add_row(rowData)
		sno += 1
	print(t1.get_string() + '\n\n')

	## print Table2
	sno = 1
	t2 = PrettyTable(Table2Title)
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
							colored(('%0.2f'%commodity[c]['VijayPercent'] + '%'), 'red'),
							colored('SELL', 'red')])
		elif PriceNow <= commodity[c]['VijayLowLimit']:
			t2.add_row([colored(str(sno), 'green'), 
							colored(c, 'green'), 
							colored(('%0.2f'%commodity[c]['Low']), 'green'), 
							colored(('%0.2f'%commodity[c]['High']), 'green'),   
							colored(('%0.2f'%commodity[c]['VijayLowLimit']), 'green'),  
							colored(('%0.2f'%commodity[c]['VijayUpLimit']), 'green'),
							colored(('%0.2f'%PriceNow), 'green'),
							colored(('%0.2f'%commodity[c]['VijayPercent'] + '%'), 'green'),
							colored('BUY', 'green')])
		else:	
			t2.add_row([str(sno), c, 
						('%0.2f'%commodity[c]['Low']), 
						('%0.2f'%commodity[c]['High']), 
						('%0.2f'%commodity[c]['VijayLowLimit']), 
						('%0.2f'%commodity[c]['VijayUpLimit']),
						('%0.2f'%PriceNow), 
						('%0.2f'%commodity[c]['VijayPercent'] + '%'),
						''])
		sno += 1
	print(t2.get_string() + '\n\n')

	## print commodity_HL_log
	for k in TrackCommodity:
		print ('\n{}:'.format(k))

		i = 0
		for date in reversed(commodity_HL_log[k]['DateList']):
			if (i >= defaultMaxLog):
				break

			line = ' {}: '.format(date)
			if (commodity_HL_log[k][date][0] == 'H'):
				line += colored(commodity_HL_log[k][date][1], 'red')
			else:
				line += '\t' + colored(commodity_HL_log[k][date][1], 'green')
			print(line)

			i += 1


def mail_get_info_from_file (FileName):
	dict_mail = {}
	try:
		fp = open (FileName, 'r')
	except:
		my_logger.error ('Unable to open Mail config file '+ FileName)
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
				my_logger.error ('Parsing '+ FileName +' failed')
				fp.close()
				return None
		fp.close()

		if len (dict_mail) != 5:
			my_logger.error ('Few params missing (from,to,password,server,port)')
			return None
	return dict_mail


def mail_text_table(commodity, dateList, commodity_HL_log, arg):
	dict_mail = mail_get_info_from_file (os.path.join(HomeDir, MailFile))
	if (dict_mail == None):
		return 
	dict_mail['to'] += arg['mailids']

	#pprint (dict_mail)
	htmlData = DrawHTMLData(commodity, dateList, commodity_HL_log, arg)

	message = MIMEMultipart('alternative')
	message['Subject'] = (' VijayMCX Date: ' + arg['Date'] 
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
		my_logger.debug('Mail sent successfully to ' + ','.join(dict_mail['to']))

	return

def update_db(date, commodity):
	dbFile = os.path.join(HomeDir, DbDir, str(date.year)+ '.csv')
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

	for i in range(0,days+1):
		DateList.append(date.strftime('%d%b%Y'))	
		date -= datetime.timedelta(days=1)	

	#print(DateList)
	#print(YearsToLoad)
	for year in YearsToLoad:
		dbFile = os.path.join(HomeDir, DbDir, str(year) + '.csv')
		#print (dbFile)
		try:
			csv_file = open (dbFile, 'r')
		except:
			## Just log
			my_logger.warning ('Failed to open dbFile '+ dbFile)
			continue
		else:
			csv_reader = csv.reader(csv_file)
			for row in csv_reader:
				#print (row)

				# load data for wanted dates only
				if row[0] not in DateList:
					continue

				# have commodity name, date as index
				commodity.setdefault(row[1], {})
				commodity[row[1]].setdefault(row[0], float(row[2]))
			csv_file.close()
	#pprint (commodity)
	return commodity, DateList

def commodity_LH_make_first_entry(one_commodity_LH_log):
	## Makes the first entry of low and high	
	cur_low  = one_commodity_LH_log['current_low']
	cur_high = one_commodity_LH_log['current_high']

	one_commodity_LH_log[cur_low[0]]  = ('L', cur_low[1])
	one_commodity_LH_log[cur_high[0]] = ('H', cur_high[1])

	if (datetime.datetime.strptime(cur_low[0],'%d%b%Y') < 
		datetime.datetime.strptime(cur_high[0],'%d%b%Y')):
		one_commodity_LH_log['DateList'].append(cur_low[0])
		one_commodity_LH_log['DateList'].append(cur_high[0])
	else:
		one_commodity_LH_log['DateList'].append(cur_high[0])
		one_commodity_LH_log['DateList'].append(cur_low[0])

def vijay_generate_log(date, days, max_log=defaultMaxLog):
	## set default
	commodity_LH_log = {}
	for k in TrackCommodity:
		commodity_LH_log[k] = {}

		## Used to log high/low after warmup is over
		commodity_LH_log[k]['warmup_days'] = 0

		## DateList to track entries
		commodity_LH_log[k]['DateList'] = []

		## Current High/Low value
		commodity_LH_log[k]['current_high'] = ('NA', 'NA', 0)
		commodity_LH_log[k]['current_low']  = ('NA', 'NA', 0)

	## load values from DB
	for yr in range(tracking_start_date.year, date.year+1):
		## To handle the leap year case,
		## last_day - first_day + 1
		last_day = datetime.datetime(yr,12,31)
		first_day = datetime.datetime(yr,1,1)
		commodity,dateList = LoadCommodity(last_day, (last_day-first_day).days)
		#print (dateList)
		#print (commodity)

		for k in commodity.keys():
			## Validate commodity 
			if k not in TrackCommodity:
				continue

			for date in reversed(dateList):

				## Validate date
				if date not in commodity[k].keys():
					continue

				## reset highLow
				highLow = ''

				if (commodity_LH_log[k]['current_high'][1] == 'NA'):
					commodity_LH_log[k]['current_high'] = (date, commodity[k][date])
					highLow = 'H'
				elif (commodity[k][date] > commodity_LH_log[k]['current_high'][1]):
					commodity_LH_log[k]['current_high'] = (date, commodity[k][date])
					highLow = 'H'

				if (commodity_LH_log[k]['current_low'][1] == 'NA'):
					commodity_LH_log[k]['current_low'] = (date, commodity[k][date])
					highLow = 'L'
				elif (commodity[k][date] < commodity_LH_log[k]['current_low'][1]):
					commodity_LH_log[k]['current_low'] = (date, commodity[k][date])
					highLow = 'L'	

				if ((commodity_LH_log[k]['warmup_days'] > days) and
					((highLow == 'H') or (highLow == 'L'))):
					commodity_LH_log[k][date] = (highLow, commodity[k][date])
					#print ('{}:{} {} {}'.format(k, date, highLow, commodity[k][date]))
					commodity_LH_log[k]['DateList'].append(date)
				elif (commodity_LH_log[k]['warmup_days'] == days):
					commodity_LH_make_first_entry(commodity_LH_log[k])
				commodity_LH_log[k]['warmup_days'] += 1
			## incase we dont have enough entries,
			## Just make it out with what we have
			if (commodity_LH_log[k]['warmup_days'] < days):
				commodity_LH_make_first_entry(commodity_LH_log[k])
	return commodity_LH_log

def process_commodity (date, days, percent, mailList=[], console=True, mail=False):
	arg = {}
	arg['Date'] = date.strftime('%d%b%Y')
	arg['days'] = str(days)
	arg['percent'] = str(percent)
	arg['mailids'] = mailList

	## It happens when mail is triggered from crontab
	## console is True when user runs it.
	if (console == False and mail == True):
		arg['by'] = 'cron'
	else:
		arg['by'] = 'manual'

	commodity,dateList = LoadCommodity(date, days)

	## Get commodity from server
	commodity_now = vijay_mcx()
	#pprint(commodity_now)

	## Updates the commodity_now to the commodity
	UpdateCommodity(commodity, commodity_now)

	## Lets high low
	vijay_calc_high_low(commodity, percent)

	#pprint(dateList)
	#pprint(commodity)

	## generate high low log
	commodity_HL_log = vijay_generate_log(date, days)
	#pprint(commodity_HL_log)

	if console:
		print_text_table (commodity, dateList, commodity_HL_log, arg)

	if mail:
		mail_text_table (commodity, dateList, commodity_HL_log, arg)

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
	print('\r' + argv[0] + ' mail=id1,id2..\tSends mail.'
						 + ' Additional mailIds can be specified to add in mailing list')
	exit()

## program starts ##

## Performs path conversion. Find a better way 
t1 = HomeDir.split('\\')
t1[0] = t1[0].replace(':', ':/')
HomeDir = os.path.join(*t1)

#print ('\r [' + HomeDir + ']')

## Gets current time
now = datetime.datetime.now()

############################
## Basic syslog configuration
logging.basicConfig(level=logging.DEBUG,
                    format='[%(asctime)s] %(levelname)s: %(message)s',
                    datefmt='%d-%b-%y %H:%M:%S')

## Get a logger for us
my_logger = logging.getLogger('vijay_nse')

## Open log handler
log_handler = logging.handlers.SysLogHandler(address = '/dev/log')

## Not sure if this is correct way of doing
## But we could add tags
log_handler.ident = 'vijay_nse: '

## Attach the handler
my_logger.addHandler(log_handler)
############################

if len(sys.argv) == 2 and sys.argv[1] == 'updatedb':
	## Check if touch file is updated.
	## If so, just quit.
	## if not updatedb, touch file, quit.
	my_logger.debug('Trying DB update')
	StatFile = os.path.join(HomeDir, StatFile)
	if (os.path.exists(StatFile)):
		fs = os.stat(StatFile)
		mtime = datetime.datetime.fromtimestamp(fs[8])

		## do nothing if we have already updated db	
		if (now.date() == mtime.date()):
			my_logger.debug('Skipping DB update: Already updated')
			exit()

	## Incase the cron is scheduled to run on inactive time
	c_now = now
	if (ClosedHours[0] <= now.hour <= ClosedHours[1]):
		c_now -= datetime.timedelta(days=1)

	if (c_now.strftime('%a') in SkipDays):
		my_logger.debug('Skipping DB update: Skipping updates on holidays')
		exit()

	## Get commodity from server
	commodity = vijay_mcx()

	## Write to db YYYY.csv
	update_db(c_now, commodity)
	touch(StatFile)
	my_logger.debug('Data Updated now')

	## Sends mail
	process_commodity (c_now, defaultDays, defaultPercent, console=False, mail=True)

	#pprint(commodity)
else:
	percent = defaultPercent
	days = defaultDays 	
	date = now
	mail = False
	mailList = []

	if len(sys.argv) > 1:
		for argv in sys.argv[1:]:
			if (argv == 'help'):
				printHelpAndExit()
			elif (argv == 'mail'):
				mail = True
				continue

			z=re.match(r'(days|percent|mail)=([0-9]+|.*@.*\..*)', argv)
			if (z != None):
				if (z.group(1) == 'days'):
					days = int(z.group(2))
				elif (z.group(1) == 'percent'):
					percent = int(z.group(2))
				elif (z.group(1) == 'mail'):
					mail = True
					mailList = z.group(2).split(',')
				else:
					print ('Invalid argument')
					printHelpAndExit()
			else:
				try:
					date = datetime.datetime.strptime(argv,'%d%b%Y')
				except:
					print ('Invalid date argument')
					printHelpAndExit()

	process_commodity (date, days, percent, mailList, mail=mail)
