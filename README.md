# vijay_nse
Vijay's mini project to fetch daily commodity value and apply his secret formula

Collects data and mails midnight

Vijay's secret recipe:
 1. Find high/low of 90 days
 2. Find 25% of the increase. (high-low) * .25
 3. Fixes uplimit and lowlimit from high/low
 4. Compare current price against the uplimit and lowlimit.
 5. Decide buy/sell based on these parameters

##########################
use,

$ vijay_nse.py help
	To get help. Look for more options

$ vijay_nse.py
	Doesnt trigger mail. Displays output on the screen. Useful for debugging	

$ vijay_nse.py 01Jan2021 
	Specify date to run/check

$ vijay_nse.py mail
	Trigger mail. Mail Id could be specified	

$ vijay_nse.py updatedb
	To trigger it from cron. Sample cron as below.

	0       1-8     *       *       *       /home/pi/scripts/vijay_nse/vijay_nse.py updatedb >> /home/pi/scripts/vijay_nse/vijay_nse.log


############################

./parse_data.py

Sometimes when raspberry pi crashes, or the daemon didnt run for long. Vijay will share the xls file.
We need to convert the xls file to .csv for vijay_nse.py to understand.

Place the xls file into xls-data/ directory, and run. Output generated into folder output/

############################
