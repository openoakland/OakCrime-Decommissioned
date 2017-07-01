''' harvestSocrata

Created on Jun 19, 2017


ASSUME crontab entry ala (daily @ 1am)

> crontab -e
0 1 * * * * source python /pathToApplicationDir/.../manage.py runcrons HarvestSocrataJob > /pathTologFiles/.../cronjob.log

@author: rik
'''

from collections import defaultdict
import pickle # cPickle python2 only
import csv 
from datetime import datetime,timedelta,date
import string 

from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist

from django.contrib.gis.geos import Point

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
			
	if newOC.ctype != '' or newOC.desc != '':
		newOC.crimeCat = classify(newOC.ctype,newOC.desc)
	else:
		newOC.crimeCat = ''

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

def mergeIncid(matchObjList,newOC):
	'''match newOC against all previous matchObj with same opd_rd
	Require exact date+time match
	returns number of updated objects, or None if newOC is to be added 

	ASSUME they share same opd_rd (because of query forming matchObjList in mergeList()
	updates beat, address, ctype, desc, crimeCat, ucr, statute if these were blank previously
	adds newOC.source to end of matching previous object
	then SAVES matching, updated previous object
	
	similar to merge code in opdata.applyPatch() 
	'''
	
	# ASSUME all matchObj share same cdateTime
	prevObj0 = matchObjList[0]

	# requre cdateTime match
	if prevObj0.cdateTime != newOC.cdateTime:
		return None
	
	# update missing addr, beat, point (shared across all incidents)
	upAddr = False
	upPoint = False
	upBeat = False
	if (prevObj0.addr == '' and newOC.addr != ''):
		upAddr = True
		
	if (prevObj0.point == None and newOC.point != None):
		upPoint = True
		
	if prevObj0.beat=='' and newOC.beat != '':
		upBeat = True

	otherUp = []
	nup = 0
	for prevObj in matchObjList:

		if upAddr:
			prevObj.addr = newOC.addr
		if upPoint:
			prevObj.point = newOC.point

		if upBeat:
			prevObj.beat = newOC.beat
		
		# NB: CType+Desc the only guaranteed commonality with new data
					
		if prevObj.ctype == '' and newOC.ctype != '':
			prevObj.ctype = newOC.ctype
			otherUp.append('ctype')

		if prevObj.desc == '' and newOC.desc != '':
			prevObj.desc = newOC.desc
			otherUp.append('desc')
			
		# NB: only update this incident UCR, statute, CC if ctype and desc match
		if (prevObj.ctype == newOC.ctype and prevObj.desc == newOC.desc):			
			
			if prevObj.ucr == '' and newOC.ucr != '':
				prevObj.ucr = newOC.ucr
				otherUp.append('ucr')
				
			if prevObj.statute == '' and newOC.statute != '':
				prevObj.statute = newOC.statute
				otherUp.append('stat')
	
			if prevObj.crimeCat == '' and newOC.crimeCat != '':
				prevObj.crimeCat = newOC.crimeCat
				otherUp.append('cc')

		if upAddr or upPoint or upBeat or len(otherUp)>0:
			# import pdb; pdb.set_trace()
			# cf. 
			# print(upAddr,upPoint,upBeat,otherUp )
			
			prevObj.source += '+' + newOC.source
			prevObj.save()
			nup += 1
			
	return nup

def mergeList(results,startDate,verboseFreq=None):
		
# 	histDay = 45
# 	now = datetime.now()
# 	hday = now - timedelta(days=histDay)
# 	hdayStr = hday.strftime(DateOnlyStrFormat)

	nadd = 0
	nupdate = 0
	nsame = 0
	ncc = 0
	ngeo = 0
	print('do_harvest: NIncid=%d' % (len(results)) )
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
				print('do_harvest: non-unique match?',cid,len(matchObjList)			 )
			
			result = mergeIncid(matchObjList,newOC)
			if result==None:
				# no match; add newOC as new incident
				try:
					newOC.save()
					nadd += 1
				except Exception as e:
					print('do_harvest: cant save merge?! %d %s\n\t%s' % (incidIdx,e,socDict) )
					continue
			elif result==0:
				nsame += 1
			else:
				nupdate += result
				
		else:
			# add if not already present
			try:
				newOC.save()
				nadd += 1
			except Exception as e:
				print('do_harvest: cant save new?! %d %s\n\t%s' % (incidIdx,e,socDict) )
				continue
						
		if verboseFreq != None and incidIdx % verboseFreq == 0:
			print('Idx=%d nadd=%d nupdate=%d nsame=%d tot=%d' % \
				(incidIdx,nadd,nupdate,nsame,(nadd+nupdate+nsame)) )
	
	print('do_harvest: NAdd=%d NUpdate=%d NSame=%d NCrimeCat=%d NGeo=%d' % \
		(nadd,nupdate,nsame,ncc,ngeo) )


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
		DefaultNDays = 7
		
		# TEST: preharvest of Socrata
# 		pf = '/Data/sharedData/c4a_oakland/OAK_data/socrata/fullSocrata_170618.pkl'
# 		results = cPickle.load(open(pf,'rb'))

		startDate = options['startDate']
		
		if startDate=='noStartSpecified':
			nowDT = datetime.now()
			minDateTime = nowDT - timedelta(days=DefaultNDays)
		else:
			minDateTime = datetime.strptime(startDate,DateOnlyStrFormat)

		results = harvestSince(minDateTime,qryLimit=20000)	
		mergeList(results,startDate,verboseFreq=1000)


# if __name__ == "__main__":
# 	do_harvest()		
