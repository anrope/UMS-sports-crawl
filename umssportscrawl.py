#!/usr/bin/python

import requests
from BeautifulSoup import BeautifulSoup
import re
import datetime
import MySQLdb
import sys

#base urls for the different schools
baseurl = {
	'um': 'http://www.goblackbears.com',
	'umfk': 'http://athletics.umfk.maine.edu'}

#schedule urls for each specific sport
sporturl = {
	('umfk', 'm-basketball'): baseurl['umfk'] + '/schedule/1/',
	('umfk', 'm-soccer'): baseurl['umfk'] + '/schedule/2/',
	('umfk', 'w-basketball'): baseurl['umfk'] + '/schedule/7/',
	('umfk', 'w-soccer'): baseurl['umfk'] + '/schedule/8/',
	('umfk', 'w-volleyball'): baseurl['umfk'] + '/schedule/9/'}

#Pretty names for each school
schoolname = {
	'umfk': 'University of Maine Fort Kent'}

#abbreviations corresponding to pretty school names
schoolabbrev = {v: k for k, v in schoolname.iteritems()}

#regexs for fields we're interested in
gooddata = {
	'time': re.compile('\d?\d\:\d\d [aApP]M'),
	'date': re.compile('[Jj]anuary|[Ff]ebruary|[Mm]arch|[Aa]pril|[Mm]ay|[Jj]une|[Jj]uly|[Aa]ugust|[Ss]eptember|[Oo]ctober|[Nn]ovember|[Dd]ecember \d?\d, \d\d\d\d'),
	'location': re.compile('Maine|Massachusetts|Rhode Island|New York|Vermont|Virginia'),
	'opponent': re.compile('Central Maine'),
	'result': re.compile('^[WwLl] ')}

class Event(object):
	"""
	Event class that performs the necessary manipulation
	for various fields we're interested in.
	"""
	@property
	def date(self):
		return self._date

	@date.setter
	def date(self, d):
		"""date setter turns the date string into a date object"""
		self._date = datetime.datetime.strptime(d, '%B %d, %Y').date()

	@property
	def time(self):
		return self._time

	@time.setter
	def time(self, t):
		"""time setter turns the time string into a time object"""
		self._time = datetime.datetime.strptime(t, '%H:%M %p').time()

	@property
	def datetime(self):
		return datetime.datetime.combine(self._date, self._time)
	
	def __str__(self):
		#return str(self.datetime)
		return 'event: {} at {} | {} | {} | {} | {} | {}'.format(self.date, self.time, self.opponent, self.location, self.home, self.result, self.recap)

def parse_umfk_tr(tag):
	"""
	Passed to BeautifulSoup to pick out useful html tags

	Returns True for useful tags
	"""
	#on the umfk men's basketball page, the useful tags are
	#contained in <tr>'s with class = 'row1' or 'row2'.
	if ('class', 'row1') in tag.attrs or ('class', 'row2') in tag.attrs:
				return True

def umfk_parse_data(row):
	"""
	Given a schedule row from a umfk athletics page,
	return an Event with the proper fields parsed out
	"""
	ev = Event()
	td = row.findAll('td')
	
	ev.date = str(td[2].string)
	
	if td[3].string != 'TBA':
		ev.time = str(td[3].string)
	else:
		ev.time = '11:11 PM'

	if td[4].a:
		ev.opponent = str(td[4].a.string)
	else:
		ev.opponent = str(td[4].string)

	ev.location = str(td[5].string)

	if ev.location == 'Fort Kent, Maine':
		ev.home = True
	else:
		ev.home = False

	if td[6].a:
		ev.result = str(td[6].a.string)
		ev.recap = baseurl['umfk'] + str(td[6].a.attrs[0][1])
	else:
		ev.result = ''
		ev.recap = ''

	if td[7].a:
		ev.video = str(td[7].a.attrs[0][1])

	return ev

def get_events(school, sport):
	"""
	Generic function that accepts a school and sport
	and figures out how to scrape the right data

	Returns a list of Event objects
	"""
	print "getting events:", school, sport

	#Grab the page and let BeautifulSoup parse it
	r = requests.get(sporturl[(school, sport)])
	soup = BeautifulSoup(r.content)

	#Testing source so we don't kill the web servers
	#fin = open('umfk-m-basketball.html')
	#soup = BeautifulSoup(fin.read())

	#Use a school/sport-tailored function to grab useful tags
	tags = soup.findAll(parse_umfk_tr)

	events = []
	#Iterate over matched tags
	for tag in tags:
		ev = umfk_parse_data(tag)
		ev.hometeam = schoolname[school]
		ev.sport = sport
		events.append(ev)
	
	return events

def get_db_cursor():
	"""convenience function for opening a db cursor"""
	db = MySQLdb.connect(host = 'localhost', user = 'root', passwd = '', db = 'umssportscrawl')
	return db.cursor()

def save_events(events):
	"""
	given some events either:
	- update the recap, result, opponent/teamB, modifiedDateTime fields
		if there is already an entry for the date and sport
	- add a new row for the new event
	"""
	cursor = get_db_cursor()

	for ev in events:
		#check to see if there's already a row for this event
		cursor.execute('select * from events where dateTime = %s and sport = %s', (ev.datetime, ev.sport))
		
		if cursor.fetchone():
			#if there is an existing row, just update it
			cursor.execute('''update events set
				recaplink = %s,
				result = %s,
				teamB = %s,
				modifiedDateTime = %s
				where dateTime = %s and sport = %s''', (ev.recap, ev.result, ev.opponent, datetime.datetime.now(), ev.datetime, ev.sport))
		else:
			#if there isn't an existing row, insert a new one
			row = (ev.datetime, ev.home, ev.recap, ev.result, ev.sport, ev.hometeam, ev.opponent, 'yearrange', datetime.datetime.now())
			cursor.execute('insert into events (dateTime, home, recapLink, result, sport, teamA, teamB, yearRange, modifiedDateTime) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)', row)

	cursor.close()

def get_todays_sports():
	"""
	check db to see which sports have events today
	return a list of tuples of (school, sport)
	"""
	cursor = get_db_cursor()
	cursor.execute('select teamA, sport from events where date(dateTime) = date(now())')
	rows = cursor.fetchall()
	cursor.close()
	return rows

def update_all_events():
	"""rescrape all events"""
	for k in sporturl.keys():
		school, sport = k
		events = get_events(school, sport)
		save_events(events)

def update_todays_events():
	"""rescrape just todays events"""
	todays_sports = get_todays_sports()
	for event in todays_sports:
		school, sport = event
		school = schoolabbrev[school]
		events = get_events(school, sport)
		save_events(events)

def main(argv):
	if argv[1] == 'all':
		update_all_events()
	elif argv[1] == 'today':
		update_todays_events()

main(sys.argv)

