#!/usr/bin/env python3

from bs4 import BeautifulSoup
import pprint
import os
import csv
import datetime

## Ensure that the below parameters are upto date as in vijay_nse.py
HomeDir = '/home/pi/scripts/vijay_nse/'
xlsDir  = 'xls-data/'
outDir  = 'output/'
TrackCommodity = ('GOLDM', 'SILVERM', 'ALUMINI', 'COPPER',
		'LEADMINI', 'NICKEL', 'ZINCMINI', 'CRUDEOIL')

def process_excel_sheet():
	DictCommodity = {}
	for fname in os.listdir('xls-data'):
		with open('xls-data/' + fname, 'r') as fp:
			csv_reader = csv.reader(fp, delimiter=',', 
									quoting=csv.QUOTE_MINIMAL)
			line = 1
			## Validate the heading row
			for row in csv_reader:
				if (len (row) < 10):
					print (' ERROR: [{}:{}] Not enough len {}:{}'.
									format(fname, line, row, len(row)))
					return DictCommodity

				if ((row[0] != 'Date') and
					(row[2] != 'Symbol') and
					(row[9] != 'Close')):
					print (' ERROR: [{}:{}] Invalid format: ({},{},{})'.
								format(fname, line, row[0], row[2], row[9]))
					return DictCommodity
				line += 1
				break

			## Parse the csv file 
			for row in csv_reader:
				if (len(row) < 10):
					print (' ERROR: [{}:{}] Parse failed {}:{}'.
								format(fname, line, row, len(row)))
					line += 1
					continue
				date = row[0].replace(' ','')
				year = date[5:]
				commodity = row[2].replace (' ','')
				price = row[9]
				DictCommodity.setdefault(year, {})
				DictCommodity[year].setdefault(date, {})
				DictCommodity[year][date][commodity] = price
				line += 1

	#pprint.pprint(DictCommodity)
	return DictCommodity

def convert_to_db():
	commodity = process_excel_sheet() 
	for year in sorted(commodity.keys()):
		#print (year)

		## we need to arrange the days in order
		TempDate = datetime.datetime(int(year)-1, 12, 31, 0, 0)
		NextYr = int(year)+1

		## Prepare the output dir
		fname = os.path.join(HomeDir, outDir, year + '_.csv')
		with open(fname, 'w', encoding='utf-8', newline='') as csv_file:
			csv_writer = csv.writer(csv_file, delimiter=',', 
									quoting=csv.QUOTE_MINIMAL)
			while (TempDate.year < NextYr):
				TempDate += datetime.timedelta(days=1)
				TempDateStr = TempDate.strftime('%d%b%Y')
				if (TempDateStr not in commodity[year].keys()):
					continue

				for cname in TrackCommodity:
					if cname not in commodity[year][TempDateStr].keys():
						continue 
					csv_writer.writerow([TempDateStr, cname,
								commodity[year][TempDateStr][cname]])

## Main Program begins here
if __name__ == "__main__":
	convert_to_db()
