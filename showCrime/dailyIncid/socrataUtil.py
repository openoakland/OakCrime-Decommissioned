''' utilities for showCrime

eg, related to Socrata harvesting

Created on Jun 13, 2017

@author: rik
'''

import csv
import string
from collections import defaultdict
from datetime import datetime

from sodapy import Socrata


# util
def freqHist(tbl):
	"Assuming values are frequencies, returns sorted list of (val,freq) items in descending freq order"
	def cmpd1(a,b):
		"decreasing order of frequencies"
		return cmp(b[1], a[1])

	
	flist = tbl.items()
	flist.sort(cmpd1)
	return flist

# Constants

Socrata_date_format = '%Y-%m-%dT%H:%M:%S' # 2013-12-04T19:00:00
DateOnlyStrFormat = '%Y-%m-%d'

IncidKeys = ['address', 'casenumber', 'city', 'crimetype', 'datetime',
			'description', 'location_1', 'location_1_address', 'location_1_city',
			'location_1_state', 'policebeat', 'state']

ChangeIncidValue = ['city', 'crimetype','description', 'location_1_city',
			'location_1_state', 'policebeat', 'state']

RptAllChanges = True

def diffIncid(i1,i2):
	chgList = []
	for k in IncidKeys:
		if k not in i1:
			# NB: no need to notice if k NOT in i2
			if k in i2:
				s2 = str(i2[k])
				chgList.append( (k,'',s2) )
		elif k not in i2:
			s1 = str(i1[k])
			chgList.append( (k,s1,'') )
		elif i1[k] != i2[k]:
			s1 = str(i1[k])
			s2 = str(i2[k])
			chgList.append( (k,s1,s2) )
	return chgList

def analMissAttrib(incidList):
	missAttrib = defaultdict(int)
	for incidIdx, itbl in enumerate(incidList):
		for k in IncidKeys:
			if k not in itbl:
				missAttrib[k] += 1
	allK = IncidKeys[:]
	allK.sort()
	for k in allK:
		print k, (missAttrib[k] if k in missAttrib else 0)

	
def rptChgDist(chgDistTbl,outf):
	freqItems = freqHist(chgDistTbl)
	
	outs = open(outf,'w')
	outs.write('NChange,F\n')
	for frag,freq in freqItems:
		outs.write('%s,%d\n' % (frag,freq))
	outs.close()

def rptChgTypeDist(chgDist,outf):
	# IncidKey -> From -> To -> [cid]
	
	outs = open(outf,'w')
	outs.write('IncidKey,From,To,F,CID\n')

	allKeys = chgDist.keys()
	allKeys.sort()
	for k in allKeys:
		if RptAllChanges or k in ChangeIncidValue:
			allFrom = chgDist[k].keys()
			allFrom.sort()
			for f in allFrom:
				allTo = chgDist[k][f].keys()
				allTo.sort()
				for t in allTo:
					outs.write('%s,"%s","%s",%d,"%s"\n' % (k,f,t,len(chgDist[k][f][t]), chgDist[k][f][t]) )
		else:
			# just accum freq
			chgList = []
			for f in chgDist[k].keys():
				for t in chgDist[k][f].keys():
					chgList += chgDist[k][f][t]
			outs.write('%s," "," ",%d,"%s"\n' % (k,len(chgList),chgList))
	outs.close()

def analyzeHist(histTbl,outDir):
	'''prelim analysis of daily queries
	'''
		
	allDateStr = histTbl.keys()
	allDateStr.sort()
	allDates = [] # datetime version
	
	dateCIDTbl = {} 
	cidTbl = {} # cid -> date -> incidChg
	firstDate = {} # cid -> minDate
	lastDate = {} # cid -> maxDate
	
	cidRange = {} # date -> (minCID,maxCID)
	
	# chgType: IncidKey -> From -> To -> Freq
	chgType = defaultdict(lambda: defaultdict (lambda: defaultdict  (list) ))

	dupes = defaultdict(lambda: defaultdict(list)) # cid -> date -> [redun records]
	dayDiff = defaultdict(int) # Ndays -> freq
	
	for dateStr in allDateStr:
		incidList = histTbl[dateStr]
		harvestDate = datetime.strptime( dateStr, DateOnlyStrFormat)
		allDates.append(harvestDate)
		cidList = []
		minCID = '99-999999'
		maxCID = '00-000000'
		
		for incidIdx, itbl in enumerate(incidList):
			cid = itbl['casenumber']
			if cid < minCID:
				minCID = cid
			if cid > maxCID:
				maxCID = cid
			dtstr = itbl['datetime']
			# HACK; to remove Socrata microseconds?!
			rpos = dtstr.rfind('.')
			dtstr = dtstr[:rpos]
			cdate = datetime.strptime( dtstr, Socrata_date_format)
				
			itbl['datetime'] = cdate
			
			cidList.append(cid)
			if cid in cidTbl:
				# check for multiple reports with same CID in same harvest
				if harvestDate in cidTbl[cid]:
					print 'analyzeHist: multiple records with same CID=%s in same date=%s' % (cid,harvestDate)
					dupes[cid][harvestDate].append( (cidTbl[cid][harvestDate],itbl) )
					continue
					
				diffList = diffIncid(itbl,cidTbl[cid][ lastDate[cid] ] )
				# only capture changed versions
				if len(diffList)>0:
					lastDate[cid] = harvestDate
					 # IncidKey distribution
					for diff in diffList:
						k,fval,tval = diff
						if RptAllChanges or k in ChangeIncidValue:
							fstr = fval.encode('ascii')
							tstr = tval.encode('ascii')
							chgType[ k ][ fstr ][ tstr ].append(cid)
						else:
							chgType[ k ][ ' ' ][ ' ' ]  += 1
							
					# 2do: add suffix but keep dupe
					# cidTbl[cid][harvestDate + ('_%05d' % incidIdx) ] = itbl
					
					cidTbl[cid][harvestDate ] = itbl
			else:
				# harvest delay for FIRST mention
				timeDiff = cdate - harvestDate
				dayDiff[timeDiff.days] += 1
			
				firstDate[cid] = harvestDate
				lastDate[cid] = harvestDate
				cidTbl[cid] = {}
				cidTbl[cid][harvestDate] = itbl
				
		cidRange[harvestDate] = (minCID,maxCID)
		dateCIDTbl[harvestDate] = set(cidList)
		
	allDates.sort() # necessary?   allDateStr sorted
	
	print 'analyzeHist: CID Range'
	for date in allDates:
		print date,cidRange[date][0],cidRange[date][1]
		
	nchgTbl = {} # date1 -> date2 -> ncommon
	for date1 in allDates:
		nchgTbl[date1] = {}
		for date2 in allDates[1:]:
			nchgTbl[date1][date2] = len(dateCIDTbl[date1].intersection(dateCIDTbl[date2]))
			
	allCID = dateCIDTbl[allDates[0]]
	for date1 in allDates[1:]:
		allCID = allCID.union(dateCIDTbl[date1])
	totCID = len(allCID)
	print 'analyzeHist: NAllCID=%d' % (totCID)

	print 'analyzeHist: dupes:'
	for cid in dupes.keys():
		allDates = dupes[cid].keys()
		allDates.sort()
		for date in allDates:
			# 2do: ugg! indices for dupes(:
			for dpair in dupes[cid][date]:
				print '%s,%s\n\t%s\n\t%s' % (cid,date,dpair[0],dpair[1])

	print 'analyzeHist: HarvestDelay'
	allDelay = dayDiff.keys()
	allDelay.sort()
	nlongDelay = 0
	longDelay=45
	for nday in allDelay:
		if nday>longDelay:
			nlongDelay += 1
			continue
		print '%s,%d' % (nday,dayDiff[nday])
	print 'LONGER,%d' % (nlongDelay)
	
	rptRange = defaultdict(int)
	print 'analyzeHist: reportRange'
	oddRange = 0
	for cid in allCID:
		if not(cid in firstDate and cid in lastDate):
			oddRange += 1
			continue
		rng = lastDate[cid] - firstDate[cid]
		rptRange[rng.days] += 1
	allRange = rptRange.keys()
	allRange.sort()
	for nday in allRange:
		print '%s,%d' % (nday,rptRange[nday])
		

	outf = outDir + 'fromToChgRpt.csv'
	outs = open(outf,'w')
	outs.write('Date1 \ Date2,NDate1')
	for d2 in allDates:
		outs.write(',%s' % (d2))
	outs.write('\n')
	for di,d1 in enumerate(allDates):
		# ASSUME allDates, allDateStr remain parallel
		dateStr = allDateStr[di]
		outs.write('%s,%d' % (d1,len(histTbl[dateStr])))
		for d2 in allDates:
			if d2<=d1:
				outs.write(', ')
			else:
				outs.write(',%d' % (nchgTbl[d1][d2]))
		outs.write('\n')
	outs.close()
	
	chgDistTbl = defaultdict(int)
	for cid in cidTbl.keys():
		chgDistTbl[ len(cidTbl[cid]) ] += 1
	
	outf = outDir + 'chgDistRpt.csv'
	rptChgDist(chgDistTbl,outf)
	
	outf = outDir + 'chgTypeDistRpt.csv'
	rptChgTypeDist(chgType,outf)

OaklandResourceName = "data.oaklandnet.com"
SocrataKey = "CXBxLW1bZbAjvL7FWZLr4hLCE"
OPDKey = "3xav-7geq"

def harvestSince(begDate,qryLimit=500):
	
	client = Socrata(OaklandResourceName,SocrataKey)
	results = client.get(OPDKey, where = ("datetime > '%s'" % (begDate)), limit=qryLimit)

	print 'harvestSince: Date=%s NResult=%d' % (begDate,len(results))
	return results

Punc2SpaceTranTbl = {ord(c): ord(u' ') for c in string.punctuation}
def cleanOPDtext(s):
	s = s.strip()
	u = s.decode()
	news = u.translate(Punc2SpaceTranTbl)
	news = news.replace(' ',"_")
	return news

def cleanCrimeCat():

	qs = OakCrime.objects.filter(opd_rd = cid)
	
	DataDir = '/Data/sharedData/c4a_oakland/OAK_data/' 
	oldCCF = DataDir + 'ctype2cc.csv'
	newCCF = DataDir + 'ctype2cc-cleansed.csv'
	outs = open(newCCF,'w')
	outs.write('"CType","CC"\n')

	csvDictReader = csv.DictReader(open(oldCCF))
	for entry in csvDictReader:
		# CType, CC
		ctype = entry['CType']
		cc = entry['CC']
		newctype = cleanOPDtext(ctype)
		outs.write('"%s","%s"\n' % (newctype,cc))
	outs.close()

def analMissCrimeCat(outf,verbose=None):
	'''NEEDS TO BE RUN AS DJANGO COMMAND, ala:
	
	def handle(self, *args, **options):

		missCCFile = '/Data/sharedData/c4a_oakland/OAK_data/missCrimeCat.csv'
		analMissCrimeCat(missCCFile)
		
	'''
	
	qs = OakCrime.objects.all()
	ncc = 0
	nblank = 0
	missPairTbl = defaultdict(int) # (ctype,desc) -> freq
	allOCList = list(qs)
	print 'analMissCrimeCat: NOC=%d' % (len(allOCList))
	for i,oc in enumerate(allOCList):
		if verbose is not None and i % verbose == 0:
			print '%d NCC=%d NBlank=%d NPair=%d' % (i,ncc,nblank,len(missPairTbl))
			
		if oc.crimeCat != '':
			ncc += 1
			continue
		ctype = oc.ctype
		desc = oc.desc
		if ctype=='' and desc=='':
			nblank += 1
			continue
		
		missPairTbl[ (ctype,desc) ] += 1
		
	print 'analMissCrimeCat: NCC=%d NBlank=%d NPair=%d' % (ncc,nblank,len(missPairTbl))
	freqItems = freqHist(missPairTbl)

	outs = open(outf,'w')
	outs.write('CType,Desc,F\n')
	for pair,freq in freqItems:
		outs.write('%s,%s,%d\n' % (pair[0],pair[1],freq))
	outs.close()


				
if __name__ == '__main__':
	
	cleanCrimeCat()
	
# 	FirstRun = False
# 	socDataDir = '/Data/sharedData/c4a_oakland/OAK_data/socrata/170617/'
# 	
# 	pf = socDataDir + 'historicalSocrata_170617.pkl'
# 	
# 	if FirstRun:
# 		histTbl = {}
# 		histDay = 45
# 		now = datetime.now()
# 		for h in range(histDay):
# 			hday = now - timedelta(days=h)
# 			hdayStr = hday.strftime(DateOnlyStrFormat)
# 			results = harvestSince(hdayStr,qryLimit=5000)
# 			histTbl[hdayStr] = results
# 			cPickle.dump(results, open(pf,'wb'), -1)
# 			
# 	else:
# 
# 		histTbl = cPickle.load(open(pf,'rb'))
# 	
# 	analyzeHist(histTbl,socDataDir)
	
# 	# 170618: collect full 90d retrieval ~ comparable to crimePublicData_170614
# 	# crimePublicData_170614 results:  10010 lines
# 	# 90 days = >~March 17; search past this
# 	pf = socDataDir + 'fullSocrata_170618.pkl'
# 	
# 	results = harvestSince('2017-03-01',qryLimit=15000)
# 	cPickle.dump(results, open(pf,'wb'), -1)
