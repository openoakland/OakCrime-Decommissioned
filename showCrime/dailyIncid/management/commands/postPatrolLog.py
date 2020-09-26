''' postPatrolLog:

	uses findSimIncident() to attempt matches of DLogs to incidents
	ASSUME geotagging already done
	
@version 0.3: prepare for AWS
	- use BoxID, database tables vs JSON
	
@date 190819
@author: rik
'''

from datetime import datetime,timedelta,date,time
import json
import logging
import pytz

from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D

from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail

import editdistance

from dailyIncid.models import *
from dailyIncid.util import *

logger = logging.getLogger(__name__)

## Constants

SRS_default = 4326 # WGS84
SRS_10N = 26910 	# UTM zone 10N

PlogOCMatchThresh = 0.8  # 190829
PlogCIDMinMatch = 0.8

MaxCIDDiff = 2  # max allowable difference between PatrolLog Report# and opd_rd

DateOnlyStrFormat = '%Y-%m-%d'
Socrata_date_format = '%Y-%m-%dT%H:%M:%S' # 2013-12-04T19:00:00
DLogDateTimeFmt = "%Y-%m-%d %H:%M:%S"

MZDefaultOaklandCoord = [-122.197811, 37.785199]

def mergeDLog2Incid(dpo,incid,nowDate):
	'''Combine dlog dictionary with OakCrime match including existing ocResult incident
	PREFER ocResult fields
	if ocResult==None, fill only fields available in dlog
	'''

	newOC = OakCrime()
	dlogDict = json.loads(dpo.parseDict)
	
	# NB: include froot as part of dlogSrc
	dlogSrc = 'DLog_' + nowDate + '_' + dlogDict['froot']
	
	if incid==None:	
		# New incident indicated to save() by null idx 
		newOC.idx = None
		newOC.opd_rd = dpo.opd_rd
		newOC.oidx = 0

		newOC.cdateTime	= dpo.incidDT 		
		
		newOC.desc = ''		# NB: no description in logs, nature used for pclist
		newOC.ctype = ''
		
		newOC.beat = dlogDict['reg_beat']	
		newOC.addr = dlogDict['location1'].upper()
			
		newOC.xlng = float(dlogDict['XLng']) if dlogDict['XLng'] != '' else None
		newOC.ylat = float(dlogDict['YLat']) if dlogDict['YLat'] != '' else None

		if newOC.xlng != None and newOC.ylat != None:
			try:
				newpt = Point(newOC.xlng,newOC.ylat,srid=SRS_default)
				# 200926: why is this transform here?!
				# newpt.transform(SRS_10N)
				newOC.point = newpt
			except Exception as e:
				logger.warning('mergeDLog2Incid: cant make point for dlog?! %s %s %s\n\t%s' , newOC.opd_rd,newOC.xlng,newOC.ylat,e)
				newOC.point = None
						
		newOC.source = dlogSrc
		
	else:
		# NB: existing ocResult, use cid from it
		# 		and make sure to steal its primary key!
		newOC.idx = incid.idx
		newOC.opd_rd = incid.opd_rd
		newOC.oidx = incid.oidx
		newOC.socrataDT = incid.socrataDT

		## PREFER all ocResult fields
		
		newOC.cdateTime	= incid.cdateTime
		
		if incid.desc != '':
			newOC.desc = incid.desc
		else:
			newOC.desc = ''
			
		if newOC.ctype != '':
			newOC.ctype = incid.ctype
		else:
			newOC.ctype = ''
			
		if incid.beat != '':
			newOC.beat = incid.beat
		else:
			newOC.beat = dlogDict['reg_beat']
			
		if incid.addr != '':
			newOC.addr = incid.addr
		else:
			newOC.addr = dlogDict['location1'].upper()

		if incid.xlng != None:
			newOC.xlng = incid.xlng
		elif dlogDict['XLng'] !='':
			newOC.xlng = float(dlogDict['XLng'])
		else:
			newOC.xlng = None

		if incid.ylat != None:
			newOC.ylat = incid.ylat
		elif dlogDict['YLat'] != '':
			newOC.ylat = float(dlogDict['YLat'])
		else:
			newOC.ylat = None

		if incid.point != None:
			newOC.point = incid.point
		elif newOC.xlng != None and newOC.ylat != None:
			try:
				newpt = Point(newOC.xlng,newOC.ylat,srid=SRS_default)
				# 200926: why is this transform here?!
				# newpt.transform(SRS_10N)
				newOC.point = newpt
			except Exception as e:
				logger.warning('mergeDLog2Incid: cant add point from dlog?! %s %s %s\n\t%s' , incid.opd_rd,newOC.xlng,newOC.ylat,e)
				newOC.point = None
		else:
			newOC.point = None

			
		newOC.source = incid.source + '+' + dlogSrc
		

	# 2do: Retrain to produce pseudo-UCR, pseudo-PC
	newOC.ucr = ''
		
	## 2do: Geo-locate wrt/ zip, beat, census tract
	newOC.zip = None
	newOC.geobeat = None
	newOC.ctractGeoID = None

	# add dlog features

	# NB: all *List fields maintained as STRINGS
	# 2do: replace *List fields as JSONField

	newOC.dlogData = True
	# 2do HACK: parse_OPDLog_PDForm.regularizeIncidTbl() doesn't always provide these fields(:
	newOC.lossList = str(dlogDict['reg_loss'])		if ('reg_loss' in dlogDict) else ''
	# NB: parse_OPDLog_PDForm.regularizeIncidTbl() only includes 'reg_gsw' from some injuries
	newOC.gswP = 'reg_gsw' in dlogDict
	newOC.weapon = dlogDict['reg_weapon']		if ('reg_weapon' in dlogDict) else ''
	newOC.callout = dlogDict['reg_callout']	 if ('reg_callout' in dlogDict) else 'no'
	newOC.ncustody = dlogDict['reg_ncustody']   if ('reg_ncustody' in dlogDict) else 0
	newOC.nsuspect = dlogDict['reg_nsuspect']   if ('reg_nsuspect' in dlogDict) else 0
	newOC.nvictim = dlogDict['reg_nvictim']	 if ('reg_nvictim' in dlogDict) else 0
	newOC.nhospital = dlogDict['reg_nhospital'] if ('reg_nhospital' in dlogDict) else 0
	# 2do HACK: parse_OPDLog_PDForm.regularizeIncidTbl()  WHY WOULD reg_ro and reg_pc be missing?!
	newOC.roList = str(dlogDict['reg_ro'])		   if ('reg_ro' in dlogDict) else ''
	newOC.pcList = str(dlogDict['reg_pc'])			if ('reg_pc' in dlogDict) else ''

	newOC.crimeCat = classify(newOC)
		
	return newOC
	
	
def getBestMatch(dpo,dlogCID,verbose=False,cidFilter=True):
	'''query existing OakCrime database for exact opd_rd match,
	then approx dateTime+location similarity
	  - logStream: non-None is a stream to write matching detailed log
	  - cidFilter: pre-filter against matches with CID > MaxCIDDiff
	ASSUME dlog contains date and xlng,ylat 
	'''
	
	
	dlog = json.loads(dpo.parseDict)
	dlogDateTime = dpo.incidDT
			
	minDate = (dlogDateTime - timedelta(days=DateRange))
	maxDate = (dlogDateTime + timedelta(days=DateRange))

	if not('location1' in dlog and dlog['location1'] != '' and \
			'XLng' in dlog and dlog['XLng'] != ''):
		# nmissGC += 1
		return 'missGC'
	
	dlXLng = dlog['XLng']
	dlYLat = dlog['YLat']
	
	dlPt = Point(dlXLng,dlYLat,srid=SRS_default)

	try:
		result = OakCrime.objects.filter(cdateTime__gte=minDate) \
								 .filter(cdateTime__lte=maxDate) \
								 .exclude(point__isnull=True) \
								 .filter(point__distance_lte=(dlPt, D(m=CloseRadius)))
	except Exception as e:
		logger.warning(f'bestMatch: query failed: {dlog["rptno"]} {e}')
		return None
	
	matchTbl = {}
	for i,incid in enumerate(result):
					
		opd_rd = incid.opd_rd
		match = {'cid': opd_rd}
		
		idDist = editdistance.eval(opd_rd,dlogCID)
		
		if cidFilter and idDist > MaxCIDDiff:
			continue

		match['idDist'] = idDist

		dayDiff, distKM = compTimePlace(dlogDateTime,dlPt,incid.cdateTime,incid.point)
		match['dayDiff'] = dayDiff
		match['dist'] = distKM
		
		timePlaceScore = timePlaceMatchScore(dayDiff,distKM)
		match['mscore'] = timePlaceScore
		
		# include all of OakCrime incident features
		match['incid'] = incid
		
		matchTbl[opd_rd] = match
		
		if verbose:
			# dRptNo,dLoc,dxlng,dylat,dDT,dPC,iCID,iAddr,ixlng,iylat,iDT,iCC,iCType,iDesc,matchScore,idDist,distMeter,dayDiff,majorCrime
			
			logFlds = [dlog['rptno'],dlog['location1'],dlXLng,dlYLat,dlogDateTime,dlog['reg_pc'], \
						incid.opd_rd,incid.addr,incid.xlng,incid.ylat,incid.cdateTime,incid.crimeCat,incid.ctype,incid.desc, \
						timePlaceScore,idDist,distKM,dayDiff]
			logStrFlds = ['"'+str(f)+'"' for f in logFlds]
			outline = ','.join(logStrFlds)
			logger.info('getBestMatch: '+ outline)
		
	allMatch = list(matchTbl.keys())
	bestMatch = None
	bestMatchScore = 0. 
	
	# select exact match CID result,
	for opd_rd in allMatch:
		match = matchTbl[opd_rd]
		if opd_rd==dlogCID or opd_rd==dpo.opd_rd:
			bestMatch = match
			break

	# or best-matching 
	if not bestMatch:
		for opd_rd in allMatch:
			match = matchTbl[opd_rd]	
			if match['mscore'] > bestMatchScore:
				bestMatch = match
				bestMatchScore = match['mscore']
			
	if bestMatch and verbose:
		# dRptNo,dLoc,dxlng,dylat,dDT,dPC,iCID,iAddr,ixlng,iylat,iDT,iCC,iCType,iDesc,matchScore,idDist,distMeter,dayDiff,majorCrime
		incid = bestMatch['incid']
		# NB: prefix best's CID with star!
		logFlds = [dlog['rptno'],dlog['location1'],dlXLng,dlYLat,dlogDateTime,dlog['reg_pc'], \
					incid.opd_rd,incid.addr,incid.xlng,incid.ylat,incid.cdateTime,incid.crimeCat,incid.ctype,incid.desc, \
					timePlaceScore,idDist,distKM,dayDiff]
		logStrFlds = ['"'+str(f)+'"' for f in logFlds]
		outline = ','.join(logStrFlds)
		logger.info('bestMatch: '+outline)
		
	return bestMatch

def findSimIncid(dpIdxList,nowString,verbose=None):
	'''go through all DailyParse objects arising from recent parse
		try to match based on opd_rd unique or otherwise
		if this fails try heuristic matching based on dateTime+location
		separate into two dicts of matching+merged or unmatched NEW OakCrime objects
		NB: objects have not been saved yet
		
	return dlogMatchTbl: 	cid -> merged OakCrime 
		   dlogUnmatchTbl: 	cid -> new OakCrime  
	'''
		
	nhit = 0
	nmissGC = 0
	nmissDate = 0
	nmissTime = 0
	nnearMatch = 0
	nunmatch = 0
	nbadTransform = 0
	nprepost = 0
	ndrop = 0
	dlMatchTbl = {}
	unMatchTbl = {}

	for i,dpIdx in enumerate(dpIdxList):
		dpo = DailyParse.objects.get(idx=dpIdx)
		cid = dpo.opd_rd
		dlog = json.loads(dpo.parseDict)

		if verbose != None and i % verbose == 0:
			logger.info('findSimIncid: verbose NHit=%d NDrop=%d NPrePost=%d NMissGC=%d NMissDate=%d NBadTran=%d NMissTime=%d NNearMatch=%d NMatch=%d NUnmatch=%d/%d (%d)' , \
				nhit,ndrop,nprepost,nmissGC,nmissDate,nbadTransform,nmissTime, nnearMatch, len(dlMatchTbl), \
				len(unMatchTbl),nunmatch, (len(dlMatchTbl)+len(unMatchTbl)))

		# Can't confirm matching OPD_RD or  approximate match without date and location
		# drop those missing either
		if not (dpo.incidDT != None and 'location1' in dlog and 'XLng' in dlog and 'YLat' in dlog):
			ndrop += 1
			logger.warning('findSimIncid: i=%d cid=%s dropped, missing time/date' , i,cid)
			continue

		## first try using cid directly
		sameCIDIncid = OakCrime.objects.filter(opd_rd=cid)
			
		# not uncommon to have multiple incident records sharing same OPD_RD
		if len(sameCIDIncid) >= 1:
			if len(sameCIDIncid) > 1:
				
				# NB: attach dailyLog info to oidx=0 incident; all should share same date, location
				# NB: 190902: There exist multiple oidx=0 records for same OPD_RD
				incidList = list(sameCIDIncid.filter(oidx=0))
				# NB: if there are more than one, arbitrarily pick first
				incid = incidList[0]
			else:
				incid = sameCIDIncid[0]

			# ensure same patrol log doesn't post twice to same OakCrime instance!
			
			if incid.source.find(dpo.froot) != -1:
				nprepost += 1
				ndrop += 1
				continue
			
			# ASSUME without location info in existing incid, need to assume the match is correct?!
			if incid.point == None:
				nhit += 1
				newOC = mergeDLog2Incid(dpo,incid,nowString)
				dlMatchTbl[cid] = newOC
				continue

			# 190829: otherwise, test matching opd_rd is time+space nearby
	
			dlXLng = dlog['XLng']
			dlYLat = dlog['YLat']
			if dlXLng=='' or dlYLat=='':
				logger.warning('findSimIncid: i=%d cid=%s blank xlng/ylat?!' , i, cid)
				ndrop += 1
				continue
			
			dlPt = Point(dlXLng,dlYLat,srid=SRS_default)
		
			dayDiff, distKM = compTimePlace(dpo.incidDT,dlPt,incid.cdateTime,incid.point)
			timePlaceScore = timePlaceMatchScore(dayDiff,distKM)
			if timePlaceScore > PlogCIDMinMatch:
				nhit += 1
				newOC = mergeDLog2Incid(dpo,incid,nowString)
				dlMatchTbl[cid] = newOC
				continue
			else:
				ndrop += 1
				logger.warning('findSimIncid: i=%d shared OPD_RD but large timePlaceScore?! dayDiff=%5.2f geoDist=%5.2f Score=%5.2f \n\t patrolLog (%s,%s,%s,%s) \n\t prevOC    (%s,%s,%s,%s/%s)' , \
				i,dayDiff,distKM, timePlaceScore, \
				 dpo.opd_rd, dpo.incidDT, dlog['location1'],dlog['nature'], \
			 	 incid.opd_rd, incid.cdateTime, incid.addr, incid.desc, incid.ctype)
				continue
		
		## Next try heuristic matching based on date, 
		bestMatch = getBestMatch(dpo,cid,verbose)
		
		if bestMatch=='missGC':
			nmissGC += 1
			bestMatch = None
		elif bestMatch=='missDate':
			nmissDate += 1
			bestMatch = None
		elif bestMatch=='cantTransformPt':
			nbadTransform += 1
			bestMatch = None
		
		if (bestMatch == None):
			nunmatch += 1
			newOC = mergeDLog2Incid(dpo,None, nowString)
			unMatchTbl[cid] = newOC
			
		elif bestMatch['mscore'] > PlogOCMatchThresh:
			nnearMatch += 1
			bestIncid = bestMatch['incid']
			
			logger.info('findSimIncid: i=%d nearMatch idDist=%d dayDiff=%5.2f geoDist=%5.2f Score=%5.2f \n\t patrolLog (%s,%s,%s,%s)\n\t prevOC    (%s,%s,%s,%s/%s)' , \
					i,bestMatch['idDist'],bestMatch['dayDiff'],bestMatch['dist'],bestMatch['mscore'], \
					 dpo.opd_rd, dpo.incidDT, dlog['location1'],dlog['nature'], \
				 	 bestIncid.opd_rd, bestIncid.cdateTime, bestIncid.addr, bestIncid.desc, bestIncid.ctype)
			newOC = mergeDLog2Incid(dpo,bestIncid, nowString)	
			dlMatchTbl[cid] = newOC

		else:
			nunmatch += 1
			newOC = mergeDLog2Incid(dpo,None, nowString)
			unMatchTbl[cid] = newOC
					
		# import pdb; pdb.set_trace()

	# Interpretting log lines
	# 	
	# 	NHit=289	nhit	NHit	query on CID returns >= 1
	# 	NDrop=0	ndrop	NDrop	no date or no time
	# 	NMissGC=4	nmissGC	NMissGC	getBestMatch: no location, X, Y
	# 	NMissDate=0	nmissDate	NMissDate	getBestMatch: no reg_date
	# 	NBadTran=27	nbadTransform	NBadTran	getBestMatch: dlPt.transform(SRS_10N) exception
	# 	NMissTime=0	nmissTime	NMissTime	N/A!
	# 	NCIDMatch=0	ncidMatch	NCIDMatch	exact CID match
	# 	NNearMatch=19	nnearMatch	NNearMatch	match above sim thresh
	# 	NMatch=308	len(dlMatchTbl)	NMatch	
	# 	NUnmatch=60/60	len(unMatchTbl)	NUnmatch	
	# 	nunmatch	“ / Nunmatch”	no best nor ncidMatch nor above match thresh
	# 	(368)	(len(dlMatchTbl)+len(unMatchTbl))	“( )”	
		
	logger.info('findSimIncid: FINAL NHit=%d NDrop=%d NPrePost=%d NMissGC=%d NMissDate=%d NBadTran=%d NMissTime=%d NNearMatch=%d NMatch=%d NUnmatch=%d/%d (%d)' , \
		nhit,ndrop,nprepost,nmissGC,nmissDate,nbadTransform,nmissTime, nnearMatch, len(dlMatchTbl), \
		len(unMatchTbl),nunmatch, (len(dlMatchTbl)+len(unMatchTbl)))

	return dlMatchTbl, unMatchTbl


