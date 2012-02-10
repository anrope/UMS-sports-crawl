#!/usr/bin/python

import urllib
import re

BASEURL = 'http://owls.umpi.edu/'
#SPORTSLIST = ['mens-soccer', 'mens-cross-country-running', 'mens-basketball', 'golf', 'mens-nordic-skiing', 'baseball',
#				'women-soccer', 'womens-cross-country', 'womens-basketball', 'volleyball', 'womens-nordic-skiing', 'softball']

# Modified version of the Sports list, right now this script can't handle sports that don't have 'opponents' in the schedule table
SPORTSLIST = ['mens-soccer', 'mens-basketball', 'baseball',
               'women-soccer', 'womens-basketball', 'volleyball', 'softball']
HOMELOC = 'Presque Isle, ME'

def parseSport(sport):
	print "About to parse sport: " + sport

	# Get the HTML for the schedule page
	urlStr = BASEURL + sport + '/schedule'
	f = urllib.urlopen(urlStr)
	html = f.read()
	htmlTableStr = findTableData(html)
	if not htmlTableStr:
		print "Error finding the schedule table data for sport(" + sport
		return

	findHeadingOrder(htmlTableStr)	

def findTableData(html):
	retStr = None
	appending = False	

	lines = html.split("\n")
	for line in lines:
		line = line.strip()

		if re.search('<table.+class="TabData', line):
			appending = True

		if re.search('</table>', line):
			# Append this last line then stop
			if appending:
				retStr += line + "\n"
			appending = False
	
		if appending:
			if retStr == None:
				retStr = ''
			retStr += line + "\n"

	return retStr

def findHeadingOrder(tableStr):
	headingLine = ''

	for line in tableStr.split("\n"):
		if re.search('<th.+</th>', line):
			headingLine = line
			break

	cleanHeadings = []
	rawheadings = headingLine.split("</th>")
	for heading in rawheadings:
		heading = re.sub('<.+>', '', heading)
		if not(heading == ''):
			cleanHeadings.append(heading)

	dateInd = cleanHeadings.index('Date')
	timeInd = cleanHeadings.index('Time/Score')
	oppInd = cleanHeadings.index('Opponent')
	locInd = -1
	try:
		locInd = cleanHeadings.index('Site')
	except ValueError:
		locInd = cleanHeadings.index('Location')

	headingsDict = dict([('Date', dateInd), ('Location', locInd), 
			('Opponent', oppInd), ('Time/Score', timeInd)])

	return headingsDict

#for s in SPORTSLIST:
#	parseSport(s)
parseSport(SPORTSLIST[2])
