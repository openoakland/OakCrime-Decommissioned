''' loadJSON: utility to boot dailyIncid_oakcrime table from opdata matchTbl.json

Created on Jun 20, 2017

@author: rik
'''

from collections import defaultdict
import csv 
from datetime import datetime
import json
import string

from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist

from django.contrib.gis.geos import Point

from dailyIncid.models import *

# C4A_dateTime_string = '%y%m%d_%H:%M:%S'
JSON_dateTime_format = '%Y-%m-%d_%H:%M:%S'
srs_default = 4326 # WGS84

Punc2SpaceTranTbl = {ord(c): ord(u' ') for c in string.punctuation}
def cleanOPDtext(s):
	s = s.strip()
	u = s # s.decode()  # python2 only!
	news = u.translate(Punc2SpaceTranTbl)
	news = news.replace(' ',"_")
	return news

CType2CCTbl = {}

def loadCType2CCTbl(inf):
	'''return ctype2ccTbl: ctype -> cc'''

	ctype2ccTbl = {}
	allCC = defaultdict(int)
	csvDictReader = csv.DictReader(open(inf))
	for entry in csvDictReader:
		# CType, CC
		cc = entry['CC']
		ctype2ccTbl[entry['CType']] = cc
		allCC[cc] += 1
	print('loadCType2CCTbl: NCType=%d NCC=%d' % (len(ctype2ccTbl), len(allCC)) )
	return ctype2ccTbl


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

def json2matchTbl(inf,verboseFreq):
	'''rebuild from json matchTbl: cid - > [dateOnly,timeOnly,beat,addr,lat,long,cc, [ctype,desc,ucr,statute,cc]+ ]
		to original	  matchTbl: cid - > (cdate,beat,addr,lat,long, incidList)
		NB: differences from json: date+time reunited
			differences from 'raw' initial matchTbl: info is in tuple, cc in incidList, len(incidList)>0'''
			
	print('json2matchTbl: Loading %s ...' % (inf) )
		
	ncid = 0
	nadd = 0
	ngeo = 0
	ncc = 0
	nmultIncid = 0
	inTbl = json.load(open(inf,'r'))
	
	print('json2matchTbl: NCID=%d' % (len(inTbl)) )
	if verboseFreq != None:
		print('NCID NAdd NCC NGeo' )
		
	for cid, jdict in inTbl.items():
		ncid += 1
		[dateOnly,timeOnly,beat,addr,ylat,xlng,incidList] = jdict

		dateTimeStr = dateOnly+'_'+timeOnly
		cdate = datetime.strptime(dateTimeStr,JSON_dateTime_format)
		
		if len(incidList) > 1:
			nmultIncid += 1	

		for iidx,incidInfo in enumerate(incidList):		
			src,ctype,desc,ucr,statute,cc = incidInfo
			
			newOC = OakCrime()
			
			## non-NULL

			try:
				# NB: newOC.idx is AutoField: idx/PK auto-incremented			
				newOC.opd_rd = cid
				newOC.oidx = iidx
				newOC.cdateTime	= cdate
				newOC.source = src
				
				## NULL ok
				newOC.desc = cleanOPDtext(desc) #NB: enforce cleanOPDtext() on desc
				newOC.beat = beat
				newOC.addr = addr
				
				if xlng == '' or ylat == '' :
					newOC.point = None
					newOC.xlng = None
					newOC.ylat = None
				else:
					newOC.point	=Point(xlng,ylat,srid=srs_default)
					# NB: for consistency, newOC's (redundant) xlng, ylat derived from Point, not taken from xlng float string
					newOC.xlng, newOC.ylat  = newOC.point.coords
					ngeo += 1
		
				newOC.ctype = cleanOPDtext(ctype) #NB: enforce cleanOPDtext() on ctype
									
				newOC.crimeCat = classify(newOC.ctype,newOC.desc)
				
				if newOC.crimeCat != '':
					ncc += 1
						
				newOC.ucr = ucr
				newOC.statute = statute
					
				## 2do: Geo-locate wrt/ zip, beat, census tract
				newOC.zip = None
				newOC.geobeat = None
				newOC.ctractGeoID = None
				
				# 2do: use explicit commit_manually or transaction.commit() 
				# for batch update?	
	
				newOC.save()

				nadd += 1
				
			except Exception as e:
				print('json2matchTbl: Exception: cid=%s %s\n\t%s ' % (cid,e,incidInfo) )
				continue
				
			if verboseFreq != None and (nadd % verboseFreq == 0):
				print(ncid,nadd,ncc,ngeo )
	
	nrcd = OakCrime.objects.count()
	print('json2matchTbl: Loaded NAdd=%d NRcd=%d NMultIncid=%d NCC=%d NGeo=%d' % \
		(nadd,nrcd,nmultIncid,ncc,ngeo) )

# from https://docs.djangoproject.com/en/1.11/howto/custom-management-commands/

class Command(BaseCommand):
	help = 'Load JSON version of opdata.matchTbl into dailyIncid_oakcrime table from JSONFileName'

	def add_arguments(self, parser):
		# import pdb; pdb.set_trace()
		parser.add_argument('JSONFileName',nargs='?')
		
	def handle(self, *args, **options):
		jfname = options['JSONFileName']
		
# 		DataDir = '/Data/sharedData/c4a_oakland/OAK_data/' 
# 		CType2CCFile = DataDir + 'ctype2cc_170627.csv'
# 		global CType2CCTbl
# 		CType2CCTbl = loadCType2CCTbl(CType2CCFile)

		json2matchTbl(jfname,verboseFreq=10000)

# if __name__ == '__main__':	
# 	import sys
# 	jfname = sys.argv[1]
# 			
# 	json2matchTbl(jfname)
