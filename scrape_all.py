#!/usr/bin/python
"""
Fantastic doctsring
"""

import argparse
import sys
import datetime
import umssportscrawl

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
	('umfk', 'w-volleyball'): baseurl['umfk'] + '/schedule/9/',

	('um', 'm-baseball'): baseurl['um'] + '/sports/m-basebl/2011-12/schedule',
	('um', 'm-basketball'): baseurl['um'] + '/sports/m-baskbl/2011-12/schedule',
	('um', 'm-crosscountry'): baseurl['um'] + '/sports/m-xc/2011-12/schedule',
	('um', 'm-football'): baseurl['um'] + '/sports/m-footbl/2011-12/schedule',
	('um', 'm-icehockey'): baseurl['um'] + '/sports/m-hockey/2011-12/schedule',
	('um', 'm-swimming'): baseurl['um'] + '/sports/m-swimonly/2011-12/schedule',
	('um', 'm-track'): baseurl['um'] + '/sports/m-track/2011-12/schedule',

	('um', 'w-basketball'): baseurl['um'] + '/sports/w-baskbl/2011-12/schedule',
	('um', 'w-crosscountry'): baseurl['um'] + '/sports/w-xc/2011-12/schedule',
	('um', 'w-fieldhockey'): baseurl['um'] + '/sports/w-fieldh/2011-12/schedule',
	('um', 'w-icehockey'): baseurl['um'] + '/sports/w-hockey/2011-12/schedule',
	('um', 'w-soccer'): baseurl['um'] + '/sports/w-soccer/2011-12/schedule',
	('um', 'w-softball'): baseurl['um'] + '/sports/softbl/2011-12/schedule',
	('um', 'w-swimming'): baseurl['um'] + '/sports/w-swimonly/2011-12/schedule',
	('um', 'w-track'): baseurl['um'] + '/sports/w-track/2011-12/schedule',
	}

def schedule_identify_row(tag):
	if (('class', 'schedule-row0') in tag.attrs or 
		('class', 'schedule-row1') in tag.attrs):
		if tag.td.string:
			return True

def schedule_parse_row(row):
	ev = umssportscrawl.Event('%b %d, %Y', '%I:%M %p')
	tds = row.findAll('td')

	ev.date = str(tds[0].string)

	if tds[1].b:
		ev.home = True
		ev.opponent = ' '.join(str(tds[1].b.string).split()[1:])
		ev.location = ev.opponent
	else:
		ev.home = False
		ev.opponent = ' '.join(str(tds[1].string).split()[1:])
		ev.location = ev.opponent

	if tds[2].string != 'TBA':
		if str(tds[2].string) != '11 AM':
			ev.time = str(tds[2].string)
		else:
			ev.time = '1:01 AM'
	else:
		ev.time = '4:04 AM'

	# This nasty line gets rid of the annoying extra whitespace

	ev.result = ' '.join(unicode(tds[3].string).split())

	if tds[4].a:
		ev.recap = str(tds[4].a.string)
	else:
		ev.recap = ''

	return ev

def conf_identify_row(tag):
	pass

def conf_parse_row(row):
	pass

def umfk_identify_row(tag):
	"""
	Passed to BeautifulSoup to pick out useful html tags

	Returns True for useful tags
	"""
	#on the umfk men's basketball page, the useful tags are
	#contained in <tr>'s with class = 'row1' or 'row2'.
	if ('class', 'row1') in tag.attrs or ('class', 'row2') in tag.attrs:
				return True

def umfk_parse_row(row):
	"""
	Given a schedule row from a umfk athletics page,
	return an Event with the proper fields parsed out
	"""
	ev = umssportscrawl.Event('%B %d, %Y', '%I:%M %p')
	td = row.findAll('td')

	ev.date = str(td[2].string)

	if td[3].string != 'TBA':
		ev.time = str(td[3].string)
	else:
		ev.time = '4:04 AM'

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

def main(scrape_type):
	umfk_sports = [t for t in sporturl.keys() if t[0] == 'umfk']

	schedule_row_sports = [
		('um', 'm-track'), ('um', 'm-crosscountry'), 
		('um', 'm-swimming'), ('um', 'w-track'),
		('um', 'w-crosscountry'), ('um', 'w-swimming'),
		]

	conf_row_sports = [
		('um', 'm-baseball'), ('um', 'm-basketball'),
		('um', 'm-icehockey'), ('um', 'm-football'),
		('um', 'w-basketball'), ('um', 'w-fieldhockey'),
		('um', 'w-icehockey'), ('um', 'w-soccer'),
		('um', 'w-softball'),
		]

	umfk_scraper = umssportscrawl.Scraper(sporturl, umfk_identify_row, 
		umfk_parse_row, umfk_sports, 'events')

	schedule_row_scraper = umssportscrawl.Scraper(sporturl, 
		schedule_identify_row, schedule_parse_row, 
		schedule_row_sports, 'events')

	conf_row_scraper = umssportscrawl.Scraper(sporturl, conf_identify_row,
		conf_parse_row, conf_row_sports, 'events')

	scrapers = [umfk_scraper, schedule_row_scraper]

	print "Scraping events ({}):".format(scrape_type)

	for s in scrapers:
		if scrape_type == 'all':
			s.update_events()
		elif scrape_type == 'today':
			s.update_todays_events()

if __name__ == '__main__':
	parser = argparse.ArgumentParser(
		description='Scrapes sports schedules from UMS sites')
	parser.add_argument(
		'scrape_type', action='store', 
		choices=['all', 'today'], help='Scrape type')
	args = parser.parse_args()
	
	if args.scrape_type: # make sure user gave both arguments
		main(args.scrape_type)
	else:
		parser.print_help()
