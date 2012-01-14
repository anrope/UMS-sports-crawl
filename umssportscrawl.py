#!/usr/bin/python

import requests
from BeautifulSoup import BeautifulSoup
import re
import datetime

#base urls for the different schools
baseurls = {
	'um': 'http://www.goblackbears.com',
	'umfk': 'http://athletics.umfk.maine.edu'}

#schedule urls for each specific sport
sporturl = {
	'umfk-m-basketball': baseurls['umfk'] + '/schedule/9/'}

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

	def __init__(self):
		self._date = None
		self._time = None
		self.location = None
		self.opponent = None
		self.result = None

	@property
	def date(self):
		return self._date

	@date.setter
	def date(self, d):
		'''date setter turns the date string into a date object'''
		self._date = datetime.datetime.strptime(d, '%B %d, %Y').date()

	@property
	def time(self):
		return self._time

	@time.setter
	def time(self, t):
		'''time setter turns the time string into a time object'''
		self._time = datetime.datetime.strptime(t, '%H:%M %p').time()

	@property
	def datetime(self):
		return datetime.datetime.combine(self._date, self._time)
	
	def __str__(self):
		#return str(self.datetime)
		return 'event: {} at {} {} {} {}'.format(self.date, self.time, self.opponent, self.location, self.result)

def parse_umfk_tr(tag):
	"""
	Passed to BeautifulSoup to pick out useful html tags

	Returns True for useful tags
	"""

	#on the umfk men's basketball page, the useful tags are
	#contained in <tr>'s with class = 'row1' or 'row2'.
	#We want the <td>'s contained in those <tr>'s (hence the .parent.).
	if ('class', 'row1') in tag.parent.attrs or ('class', 'row2') in tag.parent.attrs:
				return True

def get_events(url, school = None, sport = None):
	"""
	Generic function that accepts a school and sport
	and figures out how to scrape the right data

	Returns a list of Event objects
	"""

	#Grab the page and let BeautifulSoup parse it
	#r = requests.get(url)
	#soup = BeautifulSoup(r.content)
	
	#Testing source so we don't kill the web servers
	fin = open('umfk-m-basketball.html')
	soup = BeautifulSoup(fin.read())

	#Use a school/sport-tailored function to grab useful tags
	tags = soup.findAll(parse_umfk_tr)

	events = []
	event = Event()
	#Iterate over matched tags
	for tag in tags:
		#See if the tag contains any useful fields
		for field, re in gooddata.iteritems():
			m = re.match(str(tag.string))
			if m:
				#If we've already filled the field in this Event
				#instance, we've filled out the instance and need
				#to start a new instance
				if getattr(event, field):
					events.append(event)
					event = Event()
				setattr(event, field, m.string)
				break
	
	events.append(event)
	
	return events

def main():
	events = get_events(sporturl['umfk-m-basketball'])
	for e in events:
		print e

main()

