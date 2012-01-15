#!/usr/bin/python
# coding: utf-8

import sys
import urllib
import re
import datetime
import MySQLdb

CURSOR = DBH.cursor()
DB_TABLE = 'SportsEvents_UMA'

BASEURL = 'http://uma.edu/'
# SPORTSLIST = ['womenbasketball', 'menbasketball', 'womensoccers', 'msoccer', 'crosscountry']

# Modified version of the Sports list, right now this script can't handle sports that don't have 'opponents' in the schedule table such as cross country
SPORTSLIST = ['womenbasketball', 'menbasketball', 'womensoccer', 'msoccer']
HOMELOC = 'Augusta, ME'

def parseSport(sport):
	# This function will return a dictionary that represents one row in the schedule table
	# that will allow this function to be called for new events as well as for results
	print "About to parse sport: " + sport

	# Get the HTML for the schedule page
	urlStr = BASEURL + sport + 'schedule'
	f = urllib.urlopen(urlStr)
	html = f.read()

	# Get the year range for this schedule
	yearRange = findYearRange(html)

	# Get the html text for the schedule table
	htmlTableStr = findTableData(html)
	if not htmlTableStr:
		print "Error finding the schedule table data for sport(" + sport + ")"
		return

	headingsDict = findHeadingOrder(htmlTableStr)

	# headings dict is needed to figure out which <td> is which
	# year range is needed to complete the 'timeDate' field for the SQL row
	schedInfo = getScheduleInfo(htmlTableStr, headingsDict, yearRange, sport)

	return schedInfo

def findYearRange(html):
	result = re.search('>\s*[^\d]*\s*(?P<beginyear>(\d){4})(-(?P<endyear>(\d){4}))*\s*\S*\s*(Schedule|Season)\s*<', html)

	beginyear = result.groupdict()['beginyear']
	endyear = result.groupdict()['endyear']
	if(endyear == None):
		endyear = str(int(beginyear) + 1)	

	return str(beginyear) + "-" + str(endyear)

def findTableData(html):
	retStr = None
	appending = False	

	tabStartIndices = []
	tabEndIndices = []
	strongDateIndex = 0
	finalTabStartIndex = 0
	finalTabEndIndex = 0

	# Find all of the indices of the start of the sports table
	i = html.find('<table')
	while i >= 0:
		tabStartIndices.append(i)
		i = html.find('<table', i + 1)
	
	# Reverse the list so we can find the first 
	# index that is less than the <strong>Date text
	tabStartIndices.reverse()

	# Find all of the indices of the end of the sports table
	i = html.find('</table', 0)
	while i >= 0:
		tabEndIndices.append(i)
		i = html.find('</table', i + 1)

	strongDateIndex = html.find('<strong>Date', 0)

	for x in tabStartIndices:
		if x < strongDateIndex:
			finalTabStartIndex = x
			break

	for x in tabEndIndices:
		if x > strongDateIndex:
			finalTabEndIndex = x
			break

	# We want resulting HTML to have the closing </table> tag as well so 
	# add 8 to it for the characters in </table>\n
	finalTabEndIndex += 9

	retStr = html[finalTabStartIndex : finalTabEndIndex]

	return retStr

def findHeadingOrder(tableStr):

	headingsHTML = tableStr[tableStr.find('<strong>'):tableStr.rfind('</strong>')]

	headingsList = headingsHTML.split('\r\n')

	cleanHeadings = []
	for heading in headingsList:
		heading = re.sub('<[^>]+>', '', heading)
		heading = re.sub('&nbsp;', '', heading)
		if not(heading == '' or heading == ' '):
			if heading.find('record') < 0:
				cleanHeadings.append(heading.strip())

	dateInd = cleanHeadings.index('Date')
	oppInd = cleanHeadings.index('Opponent')
	
	# This try needs to be here because the time in the women's basketball page is not between <strong> tags
	locInd = -1
	try:
		locInd = cleanHeadings.index('Time')
	except ValueError:
		locInd = 2
	timeInd = locInd
	
	locInd = -1
	try:
		locInd = cleanHeadings.index('Results')
	except ValueError:
		locInd = timeInd
	resultsInd = locInd

	headingsDict = dict([('Date', dateInd), ('Results', resultsInd), 
			('Opponent', oppInd), ('Time', timeInd)])

	return headingsDict

def getScheduleInfo (tablehtml, headings, years, sport):
	resultRows = []
	dateInd = headings['Date']
	oppInd = headings['Opponent']
	timeInd = headings['Time']
	resultInd = headings['Results']
	firstMonth = None

	# We really just want the <tr> ... </tr> tags so do some trimming here
	curhtml = tablehtml[tablehtml.rfind('</strong>') : ]
	curhtml = curhtml[curhtml.find('<tr>') : ]
	curhtml = curhtml[ : curhtml.rfind('</tr>') + 5]

	# Take out all opening tags (we are going to split on closing tags, 
	# and other miscellaneous html junk
	curhtml = re.sub('(\r\n|<tr>|<td>|&nbsp;)', '', curhtml)

	htmlRows = curhtml.split('</tr>')

	for row in htmlRows:
		tempresultRow = {}
		cols = [re.sub('<[^>]+>', '', c) for c in row.split('</td>')]

		# Remove empty strings from the columns (may not be necessary)
		cols = filter(None, cols)
		if(len(cols) == 0):
			continue

		date = cols[dateInd].strip()
		opp = cols[oppInd].strip()
		time = cols[timeInd].strip()
		if resultInd <= (len(cols) - 1):
			result = cols[resultInd].strip()
		else:
			result = None	
	
		# Dates and time will be combined when doing the sql query
		# this is because if there is a result then we won't have a time 
		# field so we will need to use just the date to perform the sql UPDATE
		if firstMonth == None:
			firstMonth = int(date.split('/')[0])
			date = date + "/" + years.split('-')[0]
		else:
			if(int(date.split('/')[0]) < firstMonth):
				date = date + "/" + years.split('-')[1]
			else:
				date = date + "/" + years.split('-')[0]
		tempDateComps = date.split("/")
		tempMonth = tempDateComps[0].zfill(2)
		tempDay = tempDateComps[1].zfill(2)
		tempresultRow['Date'] = tempMonth + "/" + tempDay + "/" + tempDateComps[2]

		# set the time to be 00:00:00 if it is a result string instead of an actual time
		finalTime = ""
		if ((time.find('PM') < 0) and (time.find('AM') < 0)):
			finalTime = "00:00:00"
		else:
			timeMatch = re.search('(?P<hour>\d+)(:(?P<minutes>\d+))*\s*(AM|PM)+', time)
			if(timeMatch != None):
				minutes = "00"
				if (timeMatch.groupdict()['minutes'] != None):
					minutes = timeMatch.groupdict()['minutes']
				finalTime = timeMatch.groupdict()['hour'] + ":" + minutes + ":" + "00"

		if finalTime == "":
			finalTime = "00:00:00"

		tempresultRow['Time'] = finalTime

		# if the result is really a time we want to set it to None so it does not get inserted in the DB
		finalResult = result
		if (result and ((result.find('PM') >= 0) or (result.find('AM') >= 0) or (result.find('TBA') >= 0))):
			finalResult = None	

		tempresultRow['Result'] = finalResult
		tempresultRow['Home'] = opp.startswith('vs')
		opp = re.sub('^(vs(\.)*\s*|at\s*)', '', opp)
		tempresultRow['TeamB'] = re.sub('\s*\([^\)]+\)\s*$', '', opp)
		tempresultRow['TeamA'] = "Maine"
		tempresultRow['Sport'] = sport
		tempresultRow['YearRange'] = years
		now = datetime.datetime.now()
		tempresultRow['ModifiedDateTime'] = now.strftime("%Y-%m-%d %H:%M:%S")

		resultRows.append(tempresultRow)

	return resultRows

def areGamesToday(date):
	CURSOR.execute("SELECT sport FROM " + DB_TABLE + ' WHERE dateTime LIKE "' + date + '%"')
	
	# If no games today then return None
	if(int(CURSOR.rowcount) == 0):
		return None

	ret = []
	result = CURSOR.fetchall()
	for sport in result:
		ret.append(sport[0])

	# Return a list of sports that have games today
	return ret

def doesEventExist(date, sport, tA, tB):
	ret = False

	CURSOR.execute("SELECT sport FROM " + DB_TABLE + ' WHERE dateTime LIKE "' + date + '%" AND sport="' + sport + '" AND teamA="' + tA + '" AND teamB LIKE "%' + tB + '%"')
	
	# If no games today then return None
	if(int(CURSOR.rowcount) != 0):
		ret = True

	return ret

def addEvent(gameInfo):
	# Only add an event if it does not already exist this script is run
	# enough with 'getresults' that we don't need to do the updating here

	month = int(gameInfo['Date'].split('/')[0])
	tempDay = gameInfo['Date'].split('/')[1]
	if(tempDay.find('-') >= 0):
		tempDay = tempDay[0: tempDay.find('-')]
	day = int(tempDay)
	year = int(gameInfo['Date'].split('/')[2])

	# dateTime Field
	date = str(year) + "-" + str(month).zfill(2) + "-" + str(day).zfill(2)
	dateTime = date + " " + gameInfo['Time']
	
	# Home Field
	home = 0
	if(gameInfo['Home']):
		home = 1
	
	# Result Field	
	result = gameInfo['Result']

	# Sport Field
	sport = gameInfo['Sport']

	teamA = gameInfo['TeamA']
	teamB = gameInfo['TeamB']

	yearRange = gameInfo['YearRange']
	yearRange = yearRange[:yearRange.find('-') + 1] + yearRange[len(yearRange) - 2:]

	modifiedDateTime = gameInfo['ModifiedDateTime']
	
	# If the event isn't already in the table then add it in
	if(not doesEventExist(date, sport, teamA, teamB)):
		cols = "dateTime, home, "
		vals = '"' + dateTime + '", "' + str(home) + '", "'

		if(result):
			cols += "result, "
			vals += result + '", "'

		cols += "sport, teamA, teamB, yearRange, modifiedDateTime"
		vals += sport + '", "' + teamA + '", "' + teamB + '", "' + yearRange + '", "' + modifiedDateTime + '"'

		insertQ = "INSERT INTO " + DB_TABLE + " (" + cols + ") VALUES (" + vals + ")"
		CURSOR.execute(insertQ)

def getNewEvents():
	for sport in SPORTSLIST:
		sched = parseSport(sport)
		for game in sched:
			addEvent(game)

def updateEvent(date, gameInfo):

	if(gameInfo['Result'] == None):
		return

	updateQ = 'UPDATE ' + DB_TABLE + ' SET result="' + gameInfo['Result'] + '" WHERE sport="' + gameInfo['Sport'] + '" AND dateTime LIKE "' + date + '%" AND teamA="' + gameInfo['TeamA'] + '" AND teamB="' + gameInfo['TeamB'] + '"';

	CURSOR.execute(updateQ)

def getResults(dates):

	datesList = dates

	if(dates == None):
		# If dateStr = None then use todays date
		datesList = []
		now = datetime.datetime.now()
		datesList.append(now.strftime("%Y-%m-%d"))

	for date in datesList:
		print "Getting Results for date: " + date
	
		dateComps = date.split('-')
		year = dateComps[0]
		month = dateComps[1]
		day = dateComps[2]
		schedDateFormat = month + "/" + day + "/" + year

		# Find out if there are any games on this day, if not just return	
		# TODO: This should get the rowIDs of the games today, that will make the UPDATE query easier		
		sportsWithGames = areGamesToday(date)

		if (sportsWithGames == None):
			return

		for sport in sportsWithGames:
			# parse the sport and look for the date we are looking for
			sched = parseSport(sport)
			
			for game in sched:
				if(game['Date'] == schedDateFormat):
					updateEvent(date, game)


def getAllPreviousResults():
	getDatesQ = 'SELECT dateTime FROM ' + DB_TABLE;
	CURSOR.execute(getDatesQ)

	result = CURSOR.fetchall()
	datesToCheck = []
	for row in result:
		checkDate = str(row[0]).split(' ')[0]
		datesToCheck.append(checkDate)

	getResults(datesToCheck)


## The main program ##
if(len(sys.argv) < 2):
	print "Incorrect number of arguments"
	sys.exit()

op = sys.argv[1]

if(op == "getevents"):
	print "Getting events"
	getNewEvents()
elif(op == "getresults"):
	print "Getting results"
	getResults(None)
elif(op == "getpreviousresults"):
	print "GETTING ALL PREVIOUS RESULTS"
	getAllPreviousResults()

#parseSport(SPORTSLIST[0])
