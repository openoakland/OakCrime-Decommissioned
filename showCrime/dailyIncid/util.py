''' showCrime.dailyIncid.util:  shared constands and routines 
Created on Aug 25, 2019

@author: rik
'''

from datetime import datetime,timedelta,date
import environ
import logging
import pytz
import string 

from django.core.exceptions import ObjectDoesNotExist

import googlemaps

from dailyIncid.models import *

logger = logging.getLogger(__name__)

## Constants
OaklandTimeZone = pytz.timezone('America/Los_Angeles')
OaklandResourceName = "data.oaklandnet.com"
CityNearOaklandList = ['Berkeley','Piedmont','Emeryville','San Leandro','Alameda']

Socrata_date_format = '%Y-%m-%dT%H:%M:%S' # 2013-12-04T19:00:00
DateOnlyStrFormat = '%Y-%m-%d'

SocrataMaxRecords = 49999

# global CurrGClient
# global logger

# environment required by some utility

env = environ.Env(DEBUG=(bool, False), )
GoogleMapAPIKey = env('GOOGLE_MAPS_API_KEY')

## Utilities
Punc2SpaceTranTbl = {ord(c): ord(u' ') for c in string.punctuation}
def cleanOPDtext(s):
	s = s.strip()
	u = s # s.decode() python2 only
	news = u.translate(Punc2SpaceTranTbl)
	news = news.replace(' ',"_")
	return news

def pprintOC(oco):
	ppstr = '%s\n' % (oco.opd_rd)
	allFlds = list([f.name for f in OakCrime._meta.fields])
	allFlds.sort()
	for f in allFlds:
		ppstr += '\t%s: "%s"\n' % (f,getattr(oco, f))
	return ppstr
	
def awareDT(dt):
	'''strip away any tzinfo, assign it to OaklandTimeZone
	'''
	# https://dev.socrata.com/docs/datatypes/floating_timestamp.html
	# you can usually assume they’re in the timezone of the publisher.

	# https://docs.djangoproject.com/en/2.2/topics/i18n/timezones/#time-zones-faq
	naiveDT = dt.replace(tzinfo=None)
	return OaklandTimeZone.localize(naiveDT)

def makeGConnection():
	
	global CurrGClient
	CurrGClient = googlemaps.Client(key=GoogleMapAPIKey)

	return CurrGClient

def classify(incid):
	''' classification into CrimeCat based on:								  
			1. PC code										  
			2. match ctype, desc against match rules in CTypeDesc2CCTbl				 
	'''													 

	if incid.pcList is not None and len(incid.pcList) > 0:
		# NB: need to evaluate pcList = STRING
		try:
			pcList = eval(incid.pcList)
			for pc in pcList:
				try:
					pco = PC2CC.objects.get(pc=pc)
					# NB: some PC codes are 'qualifiers'			
					if pco.crimeCat.startswith('('):
						continue
					return pco.crimeCat
				
				except ObjectDoesNotExist:
					continue
				except Exception as e:
					logger.warning('classify: bad PC?! opd_rd=%s pc=%s except=%s',opd_rd,pc,e)
					continue

		except Exception as e:
			logger.warning('classify: badPCList?! opd_rd=%s pcList=%s except=%s',incid.opd_rd,incid.pcList,e)
				
	if incid.ctype =='' and incid.desc == '':
		return ''

	# NB: desc limited to first 100 char in CrimeCatMatch
	desc100 = incid.desc[:99]
	
	qs = CrimeCatMatch.objects.filter(matchType='cd') \
							  .filter(ctype=incid.ctype) \
							  .filter(desc=desc100)
	if qs.exists():
		cc = qs[0].crimeCat
		return cc
		
	# NB: match first against DESCRIPTIONS (more specific than ctype)
	qs = CrimeCatMatch.objects.filter(matchType='d') \
							  .filter(desc=desc100)
	if qs.exists():
		cc = qs[0].crimeCat
		return cc

	qs = CrimeCatMatch.objects.filter(matchType='c') \
							  .filter(ctype=incid.ctype)
	if qs.exists():
		cc = qs[0].crimeCat
		return cc

	return ''

def geocodeAddr(addrIn):
	'''return (xlng,ylat) or None, GMiss-none, GMiss-noCity
		None implies no geotag performed
	'''
	
	global CurrGClient
	
	if CurrGClient:
		gconn = CurrGClient
	else:
		# logger.info('geocodeAddr: connection restored')
		print('geocodeAddr: connection restored')
		gconn = makeGConnection()
		CurrGClient = gconn

	# Normalize addr
	addr = addrIn.upper().strip()

	if addr == '' or \
		addr.startswith('UNKNOWN') or \
		addr.startswith('UNK ') or \
		addr.startswith('NOT GIVEN') or \
		addr.startswith('PO BOX') :
		
		# NB: None implies no geotag performed
		return None
				
	addr = addr.replace('ACROSS FROM ',' ')
	addr = addr.replace('BEHIND ',' ')
	addr = addr.replace('BETWEEN ',' ')
	addr = addr.replace('BLK ',' ')
	addr = addr.replace('BLOCK ',' ')
	addr = addr.replace('IFO ',' ')
	addr = addr.replace('IN FRONT OF ',' ')
	addr = addr.replace('I.F.O. ',' ')
	addr = addr.replace('IRO ',' ')
	addr = addr.replace('PARKING LOT OF ',' ')
			
	# Geocoding via Google
	# print('trying google...')
	
	# NB: CityNearOaklandList NOT checked as part of location passed to Google
	addr += ' Oakland CA'
	geoCodeG = gconn.geocode(addr)
		
	# NB: python API doesn't provide status, only results!?
	# if geoCodeG['status'] == 'OK':
	#	f = geoCodeG['results'][0]

	if len(geoCodeG) < 1:
		return('GMiss-none')
	
	f = geoCodeG[0]
	cityFnd = False
	for ac in f['address_components']:
		
		if 'locality' in ac['types']:
			locName =  ac['long_name']
			# Prefer long_name == Oakland
			if locName == 'Oakland':
				cityFnd = True
				break
			# NB: SEQUENTIAL search thru CityNearOaklandList
			elif locName in CityNearOaklandList:
				cityFnd = True
				break				
				
	if cityFnd:
		xlng = f['geometry']['location']['lng']
		ylat = f['geometry']['location']['lat']
		return (xlng,ylat)
	else:
		return('GMiss-noCity')

def compTimePlace(dt1,pt1,dt2,pt2):
	
	dateDiff = dt1 - dt2
	# NB: can't use dateDiff.seconds across days!
	dateDiffSeconds = dateDiff.total_seconds()
	dayDiff = abs(float(dateDiffSeconds)) / 60 / 60 / 24

	# EarthEquatorialRadius = 6378000 
# 	Degree2Meter = 111317 # EarthEquatorialRadius * Pi / 180 
# 	distMeter = distDegree * Degree2Meter

	# distance on a 2d plane
	dist10m = pt1.distance(pt2) # degrees!
	distMeter = dist10m * 100


	return dayDiff, distMeter

CloseRadius = 500 # half kilometer
DateRange = 3
LocationScale = 0.5
DateScale = 0.5

def distWgt(dist,maxDist):
	'''linear ramp weight from 1.0 to 0.0 at maxDist
	'''
	dist = max([0,min([dist,maxDist])])
	return (maxDist-dist)/maxDist

def dateDiffWgt(dayDiff,maxDays):
	'''linear ramp weight from 1.0 to 0.0 at maxDays
	'''
	return (float(maxDays) - abs(dayDiff)) / maxDays

def timePlaceMatchScore(dayDiff,distMeter):

	distw = distWgt(distMeter, CloseRadius)		
	datew = dateDiffWgt(dayDiff, DateRange)
	matchScore = LocationScale * distw + DateScale * datew
	
	return matchScore
