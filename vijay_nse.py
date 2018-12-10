#!/home/gopi/gopi/vijay_nse/bin/python3

from nsetools import Nse
from pprint import pprint
from urllib.request import urlopen
from bs4 import BeautifulSoup


def vijay_nse():
 nse = Nse()
 print (nse)
 
 all_stock_codes = nse.get_stock_codes()
 pprint(all_stock_codes)
 
 print (nse.is_valid_code('HINDUNILVR'))
 
 q = nse.get_quote('HINDUNILVR')
 pprint(q)


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
  if (cName == ''):
   continue;
  #print(cName)
 
  commodity.setdefault(cName,{})
  i = 0
  for l in k.findAll('td'):
   if (i == 0):
    i += 1
    continue
   cPropValue = l.find(text=True)
   commodity[cName][cProperty[i]] = cPropValue
   print(cName + ':' + str(i) + ':' + cProperty[i])
   i += 1
 
 pprint(commodity)
 

## program starts ##
vijay_mcx()
