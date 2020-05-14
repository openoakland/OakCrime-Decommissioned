''' harvestSocrata

Created on Jun 19, 2017

v 0.2: 190812
	- use :updated_at meta date for harvest range (vs. incidents' cdateTime)
	- smarter match, updates ANY updated fields (not just blank)
	- maintain OCUpdate, audit log of changes
	- respect time zones
	- guard against dupErr
	- be careful about oidx


ASSUME crontab entry ala (daily @ 1am)

> crontab -e
0 1 * * * * source python /pathToApplicationDir/.../manage.py runcrons HarvestSocrataJob > /pathTologFiles/.../cronjob.log

@author: rik
'''

from collections import defaultdict
import csv 
import environ
from datetime import datetime,timedelta,date
import logging
import math
import pickle # cPickle python2 only
import pytz
import string 
import subprocess
import sys

import googlemaps

from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Max

from django.contrib.gis.geos import Point

from django.core.mail import send_mail

from sodapy import Socrata

from dailyIncid.models import *
from dailyIncid.util import *

logger = logging.getLogger(__name__)

# credentials via environment                                                                                                                  
env = environ.Env(DEBUG=(bool, False), )
SocrataKey = env('SOCRATA_KEY')
GoogleMapAPIKey = env('GOOGLE_MAPS_API_KEY')
OPDKey =  'ym6k-rx7a' # env('OPD_KEY')

def parseSocDT(dtstr):
	# HACK; to remove Socrata microseconds & 0Z timezone?!
	rpos = dtstr.rfind('.')
	upstr = dtstr[:rpos]
	upDT = datetime.strptime( upstr, Socrata_date_format)
	locDT =  OaklandTimeZone.localize(upDT)
	return locDT


def socrata2OakCrime(socDict,srcLbl,doGeoTag=True):
	'''Convert Socrata dictionary to OakCrime object
		applies classify()
		attempts geocodeAddr() if location_1 doesn't contain geotags
	'''
	
	newOC = OakCrime()
	
	## non-NULL
	
	# newOC.idx	= PK, established with save()
	newOC.opd_rd = socDict['casenumber']
	
	newOC.socrataDT = parseSocDT(socDict[':updated_at'])
	
	# OIDX used to discriminate among multiple ctype+desc for same incident; 
	# cf. check4changes(), mergeList()
	newOC.oidx = 0
	
	newOC.cdateTime = parseSocDT(socDict['datetime'])
	
	newOC.source = srcLbl
	
	## NULL ok
		
	if 'description' in socDict:
		newOC.desc = cleanOPDtext(socDict['description'])
	else:
		newOC.desc = ''
		
	if 'crimetype' in socDict:
		newOC.ctype = cleanOPDtext(socDict['crimetype'])
	else:
		newOC.ctype = ''
	
	if 'policebeat' in socDict:
		newOC.beat = socDict['policebeat']
	else:
		newOC.beat = ''
		
	if 'address' in socDict and socDict['address'] != 'UNKNOWN':
		newOC.addr = socDict['address']
	else:
		newOC.addr = ''
	
	if 'location_1' in socDict and 'coordinates' in socDict['location_1']:

		# https://dev.socrata.com/docs/datatypes/point.html#2.1,		
		# Contrary to the normal convention of "latitude, longitude" ordering in the coordinates property, 
		# GeoJSON and Well Known Text order the coordinates as "longitude, latitude" (X coordinate, Y coordinate),
		# as other GIS coordiate systems are encoded.
		
		newOC.point	= Point(socDict['location_1']['coordinates'])
		newOC.xlng, newOC.ylat = socDict['location_1']['coordinates']
		
	# 200427:  new format for Socrata location dictionaries?!
	elif 'location_1' in socDict and 'latitude' in socDict['location_1']:
		newOC.xlng = float(socDict['location_1']['longitude'])
		newOC.ylat = float(socDict['location_1']['latitude'])
		newOC.point	= Point(newOC.xlng,newOC.ylat)
		
	else:
		newOC.xlng = None
		newOC.ylat = None
		newOC.point	= None

	newOC.crimeCat = classify(newOC)

	# 2do: Retrain to produce pseudo-UCR, pseudo-PC
	newOC.ucr = ''
	newOC.statute = ''
		
	## 2do: Geo-locate wrt/ zip, beat, census tract
	newOC.zip = None
	newOC.geobeat = None
	newOC.ctractGeoID = None
	
	## Socrata fields dropped
	# 		city
	# 		state
	# 		location_1_address
	# 		location_1_city
	# 		location_1_state
	
	return newOC

def mergeIncid2List(matchObjList,newOC):
	'''match newOC against LIST of all previous matchObj with same opd_rd
		prefer CLOSEST matching, requiring fewest updates
		identify SINGLE BEST updated object
		
		if best match requires no updates, return None 
		else APPLY mergeIncidSingle() TO IT (since updates already computed) and return  that
	
		ASSUME they share same opd_rd (because of query forming matchObjList in mergeList()
	'''
	
	nup = 0
	bestMatch = None
	minNUpdate = int(1e6)
	minUpdateList = []
	
	for prevObj in matchObjList:

		updates = bldUpdates(prevObj,newOC)

		# prefer CLOSEST matching, requiring fewest updates
		if len(updates) < minNUpdate:
			minNUpdate = len(updates)
			minUpdateList = updates
			bestMatch = prevObj
				
	if bestMatch == None or minNUpdate == 0:
		return None
	else:
		return mergeIncidSingle(bestMatch,newOC,updates=minUpdateList)

def check4changes(obj1,obj2):
	'''	returns {fldName: (oldval,newval)} for  fields changed from obj1 in obj2
	'''
	
	# NB: fldName will be unique
	updates = {} # {fldName: (oldval,newval)}
	ignoreFlds = ('idx','oidx','source','lastModDateTime')

	for fld in obj1._meta.fields:
		fldName = fld.name
		if fldName in ignoreFlds:
			continue
		currFld =  OakCrime._meta.get_field(fldName)
		prevVal = currFld.value_from_object(obj1)
		newVal = currFld.value_from_object(obj2)

		if prevVal != newVal:
			updates[fldName] = (prevVal,newVal)
							
	return updates

def bldUpdates(prevObj,newOC):
	'''	returns {fldName: (oldval,newval)} for  fields changed from prevObj in newOC
	
		ASSUME nil values NOT allowed to clobber existing values
			
		ASSUME only dailyIncid (not patrol log) fields can change:
			updates only modifiableFields
			
		ASSUME cdateTime differences < minTimeDiffSec (=60sec)  ignored
		
		ASSUME point differences < minPointDistance (=1e3)  ignored

		ASSUME crimeCat DERIVED from ctype,desc in dailyIncid; don't include it
		
		ASSUME xlng, ylat DERIVED from point; only changes in point are checked

							
	'''
	global NSmallDist
	
	modifiableFields = ('cdateTime', 'ctype', 'desc', 'beat', 'addr','point')

	minTimeDiffSec = 60.
	minPointDistance = 1e-3
	
	# NB: fldName will be unique
	updates = {} # {fldName: (oldval,newval)}

	for fld in prevObj._meta.fields:
		fldName = fld.name
		if fldName in modifiableFields:
			currFld =  OakCrime._meta.get_field(fldName)
			prevVal = currFld.value_from_object(prevObj)
			newVal = currFld.value_from_object(newOC)

			# ASSUME nil values NOT allowed to clobber existing values
			if newVal == None or newVal == '':
				continue
			
			if fldName == 'cdateTime' and prevVal != None:
				try:
					timeDiffSec = (newVal - prevVal).total_seconds()
				except Exception as e:
					logger.warning('bldUpdates: bad timeDiff?! prev=%s new=%s except=%s',prevVal.tzinfo,newVal.tzinfo,e)
					
				if timeDiffSec < minTimeDiffSec:
					continue
				
			elif fldName == 'point' and prevVal != None and prevVal != newVal:
				# GEOS distance calculations are linear
				# GEOS does not perform a spherical calculation
				try:
					dist = newVal.distance(prevVal)
				except Exception as e:
					logger.warning('bldUpdates: bad distance?! %s',e)
					continue
				if dist < minPointDistance:
# 					logger.info('check4changes: small distance; considered equiv opd_rd=%s dist=%s prev=%s new=%s', \
# 						prevObj.opd_rd,dist,str(prevVal),str(newVal))
					NSmallDist += 1
					continue
			
				# NB: xlng, ylat DERIVED from point
				# changes to them deferred

			if prevVal != newVal:
				updates[fldName] = (prevVal,newVal)
				
				
	return updates


def mergeIncidSingle(prevObj,newOC,updates=None):
	'''match newOC against SINGLE prevObj with same opd_rd
		non-nil updates when precomputed by mergeIncid2List()

		if non-nil updates identifies changed fields
		
			incidents with ONLY changes to descFldSet generate new oidx record 
			
			adds newOC.source to end of matching previous object
			creates OCUpdate records for all changes
			SAVES updated previous object 
			and returns it
		else: returns None ==> no changes
		returns ('update' updatedOC) 
				('newOIDX' newOC)
				(err,info) on errors
	'''

	if updates == None: # ie, not being called by mergeIncid2List()
		updates = bldUpdates(prevObj,newOC)

	descFldSet = {'ctype', 'desc'}
	
	chgFldSet = set(updates.keys())
	if len(updates)>0:
		
		# NB: incidents with ONLY changes to descFldSet generate record 
		#		based on newOC with new oidx
		
		if len(chgFldSet.difference(descFldSet)) == 0:
			
			# Many of the updates simply add a missing ctype; 
			# no newOIDX for these, handled as normal update below
			if not (chgFldSet == {'ctype'} and updates['ctype'][0] == ''):
			
				qs = OakCrime.objects.filter(opd_rd = prevObj.opd_rd).aggregate(maxOIDX=Max('oidx'))
				currMaxOIDX = qs['maxOIDX']
				newOC.oidx = currMaxOIDX+1

				# NB: newOC has no xlng,ylat,point set; borrow these from prevObj
				# assert(prevObj.addr == newOC.addr,'new/old addresses are different?!')
				if prevObj.point != None:
					newOC.xlng = prevObj.xlng
					newOC.ylat = prevObj.ylat
					newOC.point = prevObj.point
				
				try:
					newOC.save()
				except Exception as e:
					logger.warning('mergeIncidSingle: cant save newOIDX cid=%s idx=%s oidx=%d %s' , prevObj.opd_rd,prevObj.idx, newOC.oidx, e)
					errmsg = 'cid=%s %s' % (newOC.opd_rd, e)
					return ('saveNewErr',errmsg)
				
				return ('newOIDX',newOC)

		# NB: only FIRST (non-newOIDX, above) change to an incident from same socrata update applied
		if (prevObj.socrataDT != None and prevObj.socrataDT == newOC.socrataDT):
			upStr = ';'.join( [ ('%s: "%s"->"%s"' % (k,v[0],v[1])) for k,v in updates.items() ] )
			errmsg = '%s %s' % (newOC.opd_rd,upStr)
			return ('dupErr', errmsg)
				
		# NB: two different socrataDT may occur in same run; only update source once
		if newOC.source not in prevObj.source:
			prevObj.source += '+' + newOC.source
		
		# apply updates to prevObj
		for fldName,oldNew in updates.items():
			prevVal,newVal = oldNew
			setattr(prevObj,fldName,newVal)
			
		# DEFERRED geotag missing addresses, eg "IFO address"
		if prevObj.point == None and prevObj.addr.strip() != '':
		
			rv = geocodeAddr(prevObj.addr)
			global NGGeoTag
			NGGeoTag += 1

			if type(rv) == type("string") and rv.startswith('GMiss-'):
				logger.info('mergeIncidSingle: geotagErr "%s" %s' ,prevObj.addr,rv)
				
			else:
				xlng,ylat = rv
				prevObj.point = Point(xlng,ylat)
				prevObj.xlng = xlng
				prevObj.ylat = ylat
				# add to updates, for OCUpdate below
				updates['point'] = (None,prevObj.point)
				updates['xlng'] = (None,prevObj.xlng)
				updates['ylat'] = (None,prevObj.ylat)
				
		# changes to descFldSet impact crimeCat
		newCC = classify(prevObj)
		if newCC != prevObj.crimeCat:
			# include crimeCat in OCUpdate
			updates['crimeCat'] = (prevObj.crimeCat,newCC)
			prevObj.crimeCat = newCC
			
		# NB: updated record gets timestamp associated with newOC socrata :updated_at
		prevSocDT = prevObj.socrataDT
		prevObj.socrataDT = newOC.socrataDT

		try:
			prevObj.save()
		except Exception as e:
			logger.warning('mergeIncidSingle: cant save prevObj?! cid=%s idx=%s %s' , prevObj.opd_rd,prevObj.idx, e)
			errmsg = 'cid=%s %s' % (prevObj.opd_rdx, e)
			return ('savePrevErr',errmsg)

		# create OCUpdate records for all changes
		for fldName,oldNew in updates.items():
			prevVal,newVal = oldNew
			# create OCUpdate audit record
			
			ocup = OCUpdate()
			ocup.opd_rd = prevObj.opd_rd
			ocup.oidx = prevObj.oidx
			ocup.fieldName = fldName
			ocup.newSrc = newOC.source
			ocup.prevSocDT = prevSocDT
			ocup.newSocDT = newOC.socrataDT
			ocup.prevVal = str(prevVal)
			ocup.newVal = str(newVal)
			ocup.save()

		return ('update',prevObj)
	else:
		return None

NGGeoTag = 0
NSmallDist = 0
def mergeList(results,srcLbl,verboseFreq=None,rptAll=False):
	'''mrege results of socrata client.get() query into existing OakCrime database
	'''
		
	nadd = 0
	ndup = 0
	nupdate = 0
	nsame = 0
	ncc = 0
	ngeo = 0
	nerr = 0
	noidx = 0
	nbadAddr = 0
	nGeoTag = 0
	nbadDate = 0
	currSocDT = None
	minGoodDate = awareDT(datetime(2014,1,1))
	nowDT = datetime.now(tz=OaklandTimeZone)
	
	rptMsg = 'mergeList: NIncid=%d' % (len(results)) 
	logger.info(rptMsg)
	
	for incidIdx,socDict in enumerate(results):
		socDT = socDict[':updated_at']
		if socDT != currSocDT:
			if verboseFreq == 'chgSocDT':
				tot = (nadd+nupdate+nsame+noidx+nerr+nbadDate)
				logger.info('Idx=%d ChgSocDT: %s nadd=%d NDupCID=%d nupdate=%d nsame=%d noidx=%d NBadDate=%d nerr=%d tot=%d' , \
					incidIdx, currSocDT,nadd,ndup,nupdate,nsame,noidx,nbadDate,nerr,tot)
			currSocDT = socDT	
			
		cid = socDict['casenumber']
		
		try:
			cdateTime = parseSocDT(socDict['datetime'])
		except Exception as e:
			logger.warning('mergeList: missing datetime?! incidIdx=%d srcLbl=%s socDict="%s"', incidIdx,srcLbl,socDict)
			continue
		
		# ignore updates referring to distant past or future
		if cdateTime < minGoodDate or cdateTime > nowDT:
			nbadDate += 1
			continue
		
		# no geotagging in tests
		# newOC = socrata2OakCrime(socDict,srcLbl,doGeoTag=False) 
		newOC = socrata2OakCrime(socDict,srcLbl)

		# test if cid already in database
		
		qs = OakCrime.objects.filter(opd_rd = cid)
		alreadyPresent = qs.exists()

		if alreadyPresent:
			# compare alternatives
			matchObjList = list(qs)
			rv = None
			if len(matchObjList) > 1:			
				rv = mergeIncid2List(matchObjList,newOC)	
			else:	
				match0 = matchObjList[0]	
				rv = mergeIncidSingle(match0,newOC)
			
			# NB: TUPLE returned to distinguish update vs newOIDX, and to include error info
			if type(rv) == type((1,2)):
					
				if rv[0] == 'update':
					nupdate += 1
					prevObj = rv[1]
					if prevObj.crimeCat != '':
						ncc += 1
					if prevObj.point != None:
						ngeo += 1
					if rptAll:
						rptMsg = 'mergeList: update %d %s' % (incidIdx,cid)
						logger.info(rptMsg)
				elif rv[0] == 'newOIDX':
					noidx += 1
					newOC = rv[1]
					if newOC.crimeCat != '':
						ncc += 1
					if newOC.point != None:
						ngeo += 1

					if rptAll:
						rptMsg = 'mergeList: newOIDX %d %s %d' % (incidIdx,cid,newOC.oidx)
						logger.info(rptMsg)
				else:
					nerr += 1
					rptMsg = 'mergeList: error %s %s' % (rv[0],rv[1])
					logger.info(rptMsg)

			elif rv==None:
				nsame += 1
				
		else:
			# add newOC if not already present
			
			# DEFERRED geotag missing addresses
			# newOC with address but potentially without Socrata point
			if newOC.point == None and newOC.addr != '' and newOC.addr != 'UNKNOWN':
			
				rv = geocodeAddr(newOC.addr)
				
				# NB: geocodeAddr() checks for bad addresses without doing geotag
				if rv == None:
					nbadAddr += 1
				elif type(rv) == type("string") and rv.startswith('GMiss-'):
					nbadAddr += 1											
					logger.info('mergeList: geotagErr "%s" %s' ,newOC.addr,rv)
					
				else:
					xlng,ylat = rv
					newOC.point = Point(xlng,ylat)
					newOC.xlng = xlng
					newOC.ylat = ylat
			
			if newOC.crimeCat != '':
				ncc += 1
			if newOC.point != None:
				ngeo += 1
		
			try:
				newOC.save()				
				nadd += 1
				if rptAll:
					rptMsg = 'mergeList: new added %d %s' % (incidIdx,cid)
					logger.info(rptMsg)
			except Exception as e:
				rptMsg = 'mergeList: cant save new?! %d %s %s\n\t%s' % (incidIdx,cid,e,socDict)
				nerr += 1
				logger.warning(rptMsg)
				continue
						
		if type(verboseFreq) == type(1) and (incidIdx % verboseFreq == 0):
			tot = (nadd+nupdate+nsame+noidx+nerr+nbadDate)
			logger.info('Idx=%d Verbose nadd=%d NDupCID=%d nupdate=%d nsame=%d noidx=%d NBadDate=%d nerr=%d tot=%d' , \
				incidIdx, nadd,ndup,nupdate,nsame,noidx,nbadDate,nerr,tot)

	if verboseFreq == 'chgSocDT':
		tot = (nadd+nupdate+nsame+noidx+nerr+nbadDate)
		logger.info('Idx=%d ChgSocDT: %s nadd=%d NDupCID=%d nupdate=%d nsame=%d noidx=%d NBadDate=%d nerr=%d tot=%d' % \
			(incidIdx, currSocDT,nadd,ndup,nupdate,nsame,noidx,nbadDate,nerr,tot) )

	nincid = OakCrime.objects.all().count()
	rptMsg = 'mergeList: NAdd=%d NDupCID=%d NUpdate=%d NSame=%d NOIDX=%d NBadDate=%d NErr=%d NCrimeCat=%d NSmallDist=%d NGeo=%d NGoogleGeoTag=%d NIncid=%d' % \
		(nadd,ndup,nupdate,nsame,noidx,nbadDate,nerr,ncc,NSmallDist,ngeo,NGGeoTag,nincid) 
	logger.info(rptMsg)
	return rptMsg

def harvest(startDate):

	DefaultNDays = 14
	nowDT = datetime.now(OaklandTimeZone)
	
	client = Socrata(OaklandResourceName,SocrataKey)
	
	if startDate == '':
		minDateTime = nowDT - timedelta(days=DefaultNDays)	
	else:
		minDateTime = datetime.strptime(startDate,'%Y-%m-%d')
	
	socBegDateStr = minDateTime.strftime(Socrata_date_format)

	
	# Endpoint Version: 2.1
	results = client.get(OPDKey, where = (":updated_at > '%s'" % (socBegDateStr)), \
						limit=SocrataMaxRecords, 
						exclude_system_fields=False, 
						order=':updated_at')
	
	# HACK: cache as pkl to support local testing without hitting Socrata
	# pickle.dump(results,open('pathToSocrataCache.pkl','wb'))
	# results = pickle.load(open('pathToSocrataCache.pkl','rb'))
	
	last = results[-1]
	rptMsg = 'do_harvest: StartDate = %s NResult=%d last update=%s' % \
		(socBegDateStr,len(results),last[':updated_at'])
		
	logger.info(rptMsg)
	
	if len(results) == SocrataMaxRecords:
		rptMsg = 'do_harvest: MAX records retrieved?!'
		logger.warning(rptMsg)
		
	# NB: underbar format to separate, ala OPD_date
	srcLbl = 'SOC_' + nowDT.strftime('%y%m%d')
	
	#########
	summRpt = mergeList(results,srcLbl,verboseFreq='chgSocDT',rptAll=True)  # verboseFreq=100, 
	#########

	bits = summRpt.split(' ')
	hdrStats = ' '.join([ 'Socrata:',bits[1],bits[3],bits[11] ])
	elapTime = datetime.now(OaklandTimeZone) - nowDT
	rptMsg = 'do_harvest: Completed %s sec' % (elapTime.total_seconds())
	logger.info(rptMsg)
	summRpt = summRpt + '\n' + rptMsg

	#  email summRpt
	send_mail(hdrStats, summRpt, 'rik@electronicArtifacts.com', \
			['rik@electronicArtifacts.com'], fail_silently=False)

	
class Command(BaseCommand):
	help = 'harvest updates from Socrata; harvests all available'
	def add_arguments(self, parser):
		parser.add_argument(
			'--startDate',
			default='',
			help='harvest only those with :updated_at > startDate %Y-%m-%d'
		)

	def handle(self, *args, **options):
		
		startDate = options['startDate']
		logger.info('harvestSocrata: startDate=%s' % (startDate))
		makeGConnection()
		harvest(startDate)
