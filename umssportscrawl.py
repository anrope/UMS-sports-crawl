import requests
from BeautifulSoup import BeautifulSoup
import datetime
import MySQLdb

mysqldb_host = 'localhost'
mysqldb_user = ''
mysqldb_password = ''
mysqldb_database = 'umssportscrawl'

#Pretty names for each school

schoolname = {
	'umfk': 'University of Maine Fort Kent',
	'um': 'University of Maine'
	}

#abbreviations corresponding to pretty school names

schoolabbrev = dict((v,k) for k, v in schoolname.iteritems())

class Event(object):
	"""
	Event class that performs the necessary manipulation
	for various fields we're interested in.
	"""
	def __init__(self, date_format, time_format):
		self._date = None
		self._time = None
		self.opponent = None
		self.location = None
		self.home = None
		self.result = None
		self.recap = None
		self.video = None

		self.date_format = date_format
		self.time_format = time_format
	
	def _get_date(self):
		return self._date

	def _set_date(self, value):
		"""date setter turns the date string into a date object"""
		self._date = datetime.datetime.strptime(value, self.date_format).date()

	date = property(_get_date, _set_date)

	def _get_time(self):
		return self._time

	def _set_time(self, value):
		"""time setter turns the time string into a time object"""
		self._time = datetime.datetime.strptime(value, self.time_format).time()

	time = property(_get_time, _set_time)

	@property
	def datetime(self):
		return datetime.datetime.combine(self._date, self._time)
	
	def __str__(self):
		return 'event: {} at {} | {} | {} | {} | {} | {}'.format(self.date, 
			self.time, self.opponent, self.location, self.home, self.result, 
			self.recap)

class Scraper(object):
	def __init__(self, sporturl, identify_row, parse_row, sports, table_name):
		self.sporturl = sporturl
		self.identify_row = identify_row
		self.parse_row = parse_row
		self.sports = sports
		self.table_name = table_name

	def get_db_cursor(self):
		"""convenience function for opening a db cursor"""
		db = MySQLdb.connect(host=mysqldb_host, user=mysqldb_user, 
			passwd=mysqldb_password, db=mysqldb_database)
		return db.cursor()
	
	def get_events(self, school, sport):
		"""
		Generic function that accepts a school and sport
		and figures out how to scrape the right data

		Returns a list of Event objects
		"""
		print "getting events:", school, sport

		#Grab the page and let BeautifulSoup parse it
		#Manipulate headers to look like chrome, because some sites are
		#serving different content based on user-agent

		r = requests.get(self.sporturl[(school, sport)], headers={'user-agent': 
			'Mozilla/5.0 (X11; Linux i686) AppleWebKit/535.7 (KHTML, '
			'like Gecko) Chrome/16.0.912.77 Safari/535.7'})
		soup = BeautifulSoup(r.content,
			convertEntities=BeautifulSoup.HTML_ENTITIES)

		#Use a school/sport-tailored function to grab useful tags
		
		tags = soup.findAll(self.identify_row)

		events = []

		#Iterate over matched tags

		for tag in tags:
			ev = self.parse_row(tag)
			ev.hometeam = schoolname[school]
			ev.sport = sport
			events.append(ev)
		
		return events

	def save_events(self, events):
		"""
		given some events either:
		- update the recap, result, opponent/teamB, modifiedDateTime fields
			if there is already an entry for the date and sport
		- add a new row for the new event
		"""
		cursor = self.get_db_cursor()

		for ev in events:

			# check to see if there's already a row for this event.
			# an event is uniquely identified by a date, time, and sport.
			# all other fields can be changed on update

			cursor.execute('select * from ' + self.table_name +
				' where dateTime = %s and sport = %s', (ev.datetime, ev.sport))
			
			if cursor.fetchone():

				#if there is an existing row, just update it

				cursor.execute('update ' + self.table_name + ' set '
					'recaplink = %s, result = %s, teamB = %s, '
					'modifiedDateTime = %s where dateTime = %s and sport = %s', 
					(ev.recap, ev.result, ev.opponent, datetime.datetime.now(), 
					ev.datetime, ev.sport))
			else:

				# if there isn't an existing row, insert a new one

				beginYear = str(datetime.datetime.now().year)
				endYear = str(int(beginYear[2:]) + 1)
				yearRange = beginYear + '-' + endYear
				cursor.execute('insert into ' + self.table_name +
					' (dateTime, home, recapLink, result, sport, teamA, teamB, '
					'yearRange, modifiedDateTime) values (%s, %s, %s, %s, %s, '
					'%s, %s, %s, %s)', (ev.datetime, ev.home, ev.recap, 
					ev.result, ev.sport, ev.hometeam, ev.opponent, 
					yearRange, datetime.datetime.now()))

		cursor.close()

	def get_todays_sports(self):
		"""
		check db to see which sports have events today
		return a list of tuples of (school, sport)
		"""
		cursor = self.get_db_cursor()
		cursor.execute('select teamA, sport from ' + self.table_name +
			' where date(dateTime) = date(now())')
		rows = cursor.fetchall()
		cursor.close()
		return rows

	def update_events(self):
		"""rescrape all events"""
		for k in self.sports:
			school, sport = k
			events = self.get_events(school, sport)
			self.save_events(events)

	def update_todays_events(self):
		"""rescrape just todays events"""
		todays_sports = self.get_todays_sports()
		for event in todays_sports:
			school, sport = event
			school = schoolabbrev[school]
			events = self.get_events(school, sport)
			self.save_events(events)
