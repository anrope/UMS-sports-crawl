#!/usr/bin/python

import urllib
import re

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

	print yearRange

	# Get the html text for the schedule table
	htmlTableStr = findTableData(html)
	if not htmlTableStr:
		print "Error finding the schedule table data for sport(" + sport + ")"
		return

	headingsDict = findHeadingOrder(htmlTableStr)

	print headingsDict

	# headings dict is needed to figure out which <td> is which
	# year range is needed to complete the 'timeDate' field for the SQL row
	schedInfo = getScheduleInfo(htmlTableStr, headingsDict, yearRange)

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

def getScheduleInfo (tablehtml, headings, years):
	resultRows = []
	dateInd = headings['Date']
	oppInd = headings['Opponent']
	timeInd = headings['Time']
	resultInd = headings['Results']

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
		
		print cols	

		date = cols[dateInd].strip()
		opp = cols[oppInd].strip()
		time = cols[timeInd].strip()
		result = cols[resultInd].strip()
		
		tempresultRow['DateTime'] = date
		tempresultRow['Opponent'] = opp
		# TODO: in the future this will be combined with the date time field
		tempresultRow['Time'] = time
		tempresultRow['Result'] = result

		print tempresultRow
		resultRows.append(tempresultRow)

	# SPECIAL CASE some rows contain all blank entries... WHY?!

#for s in SPORTSLIST:
#	parseSport(s)
parseSport(SPORTSLIST[0])