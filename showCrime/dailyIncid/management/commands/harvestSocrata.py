''' harvestSocrata

Created on Jun 19, 2017

command run by runHarvestSocrata.sh, capturing logs, emailing summary

ASSUME crontab entry ala (daily @ 4:08p)

> crontab -l
# run once a day at 16:08
8 16 * * * .../showCrime/shell/runHarvestSocrata.sh

@author: rik
'''

from collections import defaultdict
import pickle # cPickle python2 only
import csv 
from datetime import datetime,timedelta,date
import string 
import subprocess

from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist

from django.contrib.gis.geos import Point

from django.core.mail import send_mail

from sodapy import Socrata

from dailyIncid.models import *

## Utilities
Punc2SpaceTranTbl = {ord(c): ord(u' ') for c in string.punctuation}
def cleanOPDtext(s):
	s = s.strip()
	u = s # s.decode() python2 only
	news = u.translate(Punc2SpaceTranTbl)
	news = news.replace(' ',"_")
	return news

## Constants
OaklandResourceName = "data.oaklandnet.com"
SocrataKey = "CXBxLW1bZbAjvL7FWZLr4hLCE"
OPDKey = "3xav-7geq"

Socrata_date_format = '%Y-%m-%dT%H:%M:%S' # 2013-12-04T19:00:00
DateOnlyStrFormat = '%Y-%m-%d'

IncidKeys = ['address', 'casenumber', 'city', 'crimetype', 'datetime',
			'description', 'location_1', 'location_1_address', 'location_1_city',
			'location_1_state', 'policebeat', 'state']

def harvestSince(minDateTime,qryLimit=500):
	
	client = Socrata(OaklandResourceName,SocrataKey)
	socBegDateStr = minDateTime.strftime(Socrata_date_format)
	results = client.get(OPDKey, where = ("datetime > '%s'" % (socBegDateStr)), limit=qryLimit)

	# import pdb; pdb.set_trace()
	
	print('harvestSince: Date=%s NResult=%d' % (socBegDateStr,len(results)) )
	return results

# from https://docs.djangoproject.com/en/1.11/howto/custom-management-commands/
	
def classify(ctype,desc):
	try:
		cco1 = CrimeCat.objects.get(ctypeDesc=ctype)
		cc = cco1.crimeCat
	except ObjectDoesNotExist:
		try:
			cco2 = CrimeCat.objects.get(ctypeDesc=desc)
			cc = cco2.crimeCat
		except ObjectDoesNotExist:
			cc = ''
	return cc

def socrata2OakCrime(socDict,startDate):
	'''Convert Socrata dictionary to OakCrime object
	'''
	
	newOC = OakCrime()
	
	## non-NULL
	
	# newOC.idx	= PK, established with save()
	newOC.opd_rd = socDict['casenumber']
	newOC.oidx = 0
	
	newOC.cdateTime	= socDict['datetime']
	# NB: underbar to separate ala OPD_date
	newOC.source = 'SOC_'+startDate
	
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
		
	if 'address' in socDict:
		newOC.addr = socDict['address']
	else:
		newOC.addr = ''
	
	if 'location_1' in socDict:
		newOC.point	= Point(socDict['location_1']['coordinates'])
		# 2do: extract (redundant) xlng,ylat
		newOC.xlng, newOC.ylat = socDict['location_1']['coordinates']
	else:
		newOC.point = None
		newOC.xlng = newOC.ylat = None
			
	# 2do ASAP: attempt to geotag missing addresses, eg "IFO address"
	
	if newOC.ctype != '' or newOC.desc != '':
		newOC.crimeCat = classify(newOC.ctype,newOC.desc)
	else:
		newOC.crimeCat = ''

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
	Require exact date+time match
	returns SINGLE BEST updated object (already saved), or None if no changes

	ASSUME they share same opd_rd (because of query forming matchObjList in mergeList()
	updates beat, address, ctype, desc, crimeCat, ucr, statute if these were blank previously
	adds newOC.source to end of matching previous object
	then SAVES matching, updated previous object
	
	similar to merge code in opdata.applyPatch() 
	'''
	
	nup = 0
	bestMatch = None
	minNUpdate = int(1e6)
	
	for prevObj in matchObjList:

		updates = []

		if prevObj.cdateTime != newOC.cdateTime:
			continue

		if prevObj.addr == '' and newOC.addr != '':
			prevObj.addr = newOC.addr
			updates.append('addr')

		if prevObj.beat == '' and newOC.beat != '':
			prevObj.beat = newOC.beat
			updates.append('beat')

		if prevObj.point == '' and newOC.point != '':
			prevObj.point = newOC.point
			updates.append('point')
		
		# NB: CType+Desc the only guaranteed commonality with new data
					
		if prevObj.ctype == '' and newOC.ctype != '':
			prevObj.ctype = newOC.ctype
			updates.append('ctype')

		if prevObj.desc == '' and newOC.desc != '':
			prevObj.desc = newOC.desc
			updates.append('desc')
			
		# NB: only update this incident UCR, statute, CC if ctype and desc match
		if (prevObj.ctype == newOC.ctype and prevObj.desc == newOC.desc):			
			
			if prevObj.ucr == '' and newOC.ucr != '':
				prevObj.ucr = newOC.ucr
				updates.append('ucr')
				
			if prevObj.statute == '' and newOC.statute != '':
				prevObj.statute = newOC.statute
				updates.append('stat')
	
			if prevObj.crimeCat == '' and newOC.crimeCat != '':
				prevObj.crimeCat = newOC.crimeCat
				updates.append('cc')

		# prefer CLOSEST matching, requiring fewest updates
		if  len(updates) > 0 and len(updates) < minNUpdate:
			
			minNUpdate = len(updates)
			bestMatch = prevObj
	
	# NB: minUpdate might still have initialized value 
	#	if all matchObjList have different cdateTime than newOC
	if minNUpdate == int(1e6) or minNUpdate == 0:
		return None
	else:
		bestMatch.source += '+' + newOC.source
		try:
			bestMatch.save()
		except Exception as e:
			print('mergeIncid2List: cant save?! cid=%s bestIdx=%s' % \
				(newOC.opd_rd,bestMatch.idx))
			return None
		return bestMatch

def mergeIncidSingle(prevObj,newOC):
	'''match newOC against SINGLE prevObj with same opd_rd
	ASSUME exact date+time match
	returns  updated object (already saved), or None if no changes

	updates beat, address, ctype, desc, crimeCat, ucr, statute if these were blank previously
	adds newOC.source to end of matching previous object
	then SAVES matching, updated previous object
	
	similar to merge code in opdata.applyPatch() 
	'''

	if prevObj.cdateTime != newOC.cdateTime:
		return None
	
	updates = []

	if prevObj.addr == '' and newOC.addr != '':
		prevObj.addr = newOC.addr
		updates.append('addr')

	if prevObj.beat == '' and newOC.beat != '':
		prevObj.beat = newOC.beat
		updates.append('beat')

	if prevObj.point == '' and newOC.point != '':
		prevObj.point = newOC.point
		updates.append('point')
	
	# NB: CType+Desc the only guaranteed commonality with new data
				
	if prevObj.ctype == '' and newOC.ctype != '':
		prevObj.ctype = newOC.ctype
		updates.append('ctype')

	if prevObj.desc == '' and newOC.desc != '':
		prevObj.desc = newOC.desc
		updates.append('desc')
		
	# NB: only update this incident UCR, statute, CC if ctype and desc match
	if (prevObj.ctype == newOC.ctype and prevObj.desc == newOC.desc):			
		
		if prevObj.ucr == '' and newOC.ucr != '':
			prevObj.ucr = newOC.ucr
			updates.append('ucr')
			
		if prevObj.statute == '' and newOC.statute != '':
			prevObj.statute = newOC.statute
			updates.append('stat')

		if prevObj.crimeCat == '' and newOC.crimeCat != '':
			prevObj.crimeCat = newOC.crimeCat
			updates.append('cc')

	if len(updates)>0:
		# import pdb; pdb.set_trace()
		# print(updates )
		
		prevObj.source += '+' + newOC.source

		try:
			prevObj.save()
		except Exception as e:
			print('mergeIncidSingle: cant save?! cid=%s prevIdx=%s' % \
				(newOC.opd_rd,prevObj.idx))
			return None

		return prevObj
	else:
		return None

def mergeList(results,startDate,verboseFreq=None,rptAll=False):
		
# 	histDay = 45
# 	now = datetime.now()
# 	hday = now - timedelta(days=histDay)
# 	hdayStr = hday.strftime(DateOnlyStrFormat)

	nadd = 0
	ndup = 0
	nupdate = 0
	nsame = 0
	ncc = 0
	ngeo = 0
	
	rptLines = []
		
	rptMsg = 'mergeList: NIncid=%d' % (len(results)) 
	print(rptMsg)
	rptLines.append(rptMsg)

	for incidIdx, socDict in enumerate(results):
		# socDict is a dictionary of IncidKeys
		
		currSum = nadd + nupdate
		
		cid = socDict['casenumber']
			
		# HACK; to remove Socrata microseconds?!
		dtstr = socDict['datetime']
		rpos = dtstr.rfind('.')
		dtstr = dtstr[:rpos]
		cdate = datetime.strptime( dtstr, Socrata_date_format)
		socDict['datetime'] = cdate
		
		newOC = socrata2OakCrime(socDict,startDate)
		if newOC.crimeCat != '':
			ncc += 1
		if newOC.point != None:
			ngeo += 1
		
		# test if cid already in database
		
		qs = OakCrime.objects.filter(opd_rd = cid)
		alreadyPresent = qs.exists()

		# import pdb; pdb.set_trace()
		
		if alreadyPresent:
			# compare alternatives
			matchObjList = list(qs)
			
			if len(matchObjList) > 1:
				
# 				rptMsg = 'mergeList: non-unique match? %s %d' % (cid,len(matchObjList))
# 				print(rptMsg)
# 				rptLines.append(rptMsg)
				
				result = mergeIncid2List(matchObjList,newOC)
			
			else:	
				match0 = matchObjList[0]
		
				result = mergeIncidSingle(match0,newOC)
			
			if result==None:
				nsame += 1
			else:
				nupdate += 1
				if rptAll:
					rptMsg = 'mergeList: update %d %s' % (incidIdx,cid)
					print(rptMsg)
					rptLines.append(rptMsg)
				
		else:
			# add if not already present
			try:
				newOC.save()
				nadd += 1
				if rptAll:
					rptMsg = 'mergeList: new added %d %s' % (incidIdx,cid)
					print(rptMsg)
					rptLines.append(rptMsg)
			except Exception as e:
				rptMsg = 'mergeList: cant save new?! %d %s %s\n\t%s' % (incidIdx,cid,e,socDict)
				print(rptMsg)
				rptLines.append(rptMsg)
				continue
						
		if verboseFreq != None and incidIdx % verboseFreq == 0:
			# NB: not added to rptLines
			print('Idx=%d CID=%s nadd=%d nupdate=%d nsame=%d tot=%d' % \
				(incidIdx, cid, nadd,nupdate,nsame,(nadd+nupdate+nsame)) )
			
			# stop after verboseFreq, for profiling
# 			if incidIdx > 0:
# 				break

	nincid = OakCrime.objects.all().count()
	rptMsg = 'mergeList: NAdd=%d NDupCID=%d NUpdate=%d NSame=%d NCrimeCat=%d NGeo=%d NIncid=%d' % \
		(nadd,ndup,nupdate,nsame,ncc,ngeo,nincid) 
	print(rptMsg)
	rptLines.append(rptMsg)
	
	return rptLines

def freqHist(tbl):
	"Assuming values are frequencies, returns sorted list of (val,freq) items in descending freq order"
	def cmpd1(a,b):
		"decreasing order of frequencies"
		return cmp(b[1], a[1])

	
	flist = tbl.items()
	flist.sort(cmpd1)
	return flist

class Command(BaseCommand):
	help = 'harvest updates from Socrata since %Y-%m-%d startDate. defaults to 7 days ago'
	def add_arguments(self, parser):
		parser.add_argument('startDate', nargs='?', default='noStartSpecified') 

	def handle(self, *args, **options):
		DefaultNDays = 90
		
		# TEST: preharvest of Socrata
# 		pf = '/Data/sharedData/c4a_oakland/OAK_data/socrata/fullSocrata_170618.pkl'
# 		results = cPickle.load(open(pf,'rb'))

		
		nowDT = datetime.now()
		minDateTime = nowDT - timedelta(days=DefaultNDays)

		rptLines = []
		rptMsg = 'harvestSocrata: full date range from %s' % (minDateTime) 
		print(rptMsg)
		rptLines.append(rptMsg)

		results = harvestSince(minDateTime,qryLimit=20000)
		nowString = nowDT.strftime('%y%m%d')
		# mrgRptLines = mergeList(results,nowString,rptAll=True,verboseFreq=1000)
		mrgRptLines = mergeList(results,nowString,rptAll=True)
		
		rptLines += mrgRptLines

		elapTime = datetime.now() - nowDT
		rptMsg = 'harvestSocrata: Completed %s sec' % (elapTime.total_seconds())
		print(rptMsg)
		rptLines.append(rptMsg)

		fullRpt = '\n'.join(rptLines)

		send_mail('Socrata harvest', fullRpt, 'rik@electronicArtifacts.com', \
				['rik@electronicArtifacts.com'], fail_silently=False)

# if __name__ == "__main__":
# 	do_harvest()		
