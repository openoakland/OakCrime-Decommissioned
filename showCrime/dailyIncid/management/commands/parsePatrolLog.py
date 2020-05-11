'''parsePatrolLogs: convert PDFs
	collapose multiple days' logs allData: froot -> [ { TU->V } ] into
	incidTbl: cid* -> {froot, TU -> V}
	NB: cid from rptno field; random int suffix added if not unique!
	regularize fields, geotag
	save as incidTblArchive_%s.json

@version 0.3: prepare for AWS
	- use BoxID, database tables vs JSON
	
@date 190819
'''

from collections import defaultdict
from datetime import datetime,timedelta,time
import glob
import json
import logging
import os
import pdfquery
import re 

import googlemaps
import mapbox

from django.core.exceptions import ObjectDoesNotExist

from dailyIncid.models import *
from dailyIncid.util import *

logger = logging.getLogger(__name__)

def cmpx(o1,o2):
	if o1 < o2:
		return o1,o2
	return o2,o1

DLogPDFFormFields = ('AREA/BEAT: ', 
					'TIME OF INC:', 
					'NATUREOFINCIDENT(TITLE&CODE):', 
					'LOCATION OF INCIDENT (BLOCK OR AREA ONLY):', 
					'SGT/W. COMMANDER NOTIFIED:', 
					'R/O (SERIAL/CALL SIGN):', 
					'INC#:', 
					'REPORT #:', 
					'CALLOUT/TYPE:', 
					'# OF VICTIMS / GENDERS:', 
					'# OF SUSPECTS:', 
					'# IN-CUSTODY:', 
					'INJURIES/FATAL/CONDITION (GENERAL DESCRIPTION):', 
					'# OF PERSONS TRANSPORTED TO LOCAL HOSPITAL:', 
					'WEAPONS USED (GENERAL DESCRIPTION):', 
					'LOSS(GENERALDESCRIPTION):' )
NDLogPDFFormFields = len(DLogPDFFormFields)

DayLogFields = {'# IN-CUSTODY:': 'ncustody',
				'# OF PERSONS TRANSPORTED TO LOCAL HOSPITAL:': 'nhospital',
				'# OF SUSPECTS:': 'nsuspect',
				'# OF VICTIMS / GENDERS:': 'nvictim',
				'ANY TRANSPORTS TO LOCAL HOSPITAL?': 'hospital',
				'AREA/BEAT:': 'area',
				'CALLOUT/TYPE:': 'callout',
				'i': 'fileIdx',
				'INC#:': 'incno',
				'INJURIES/FATAL/CONDITION (GENERAL DESCRIPTION):': 'injury',
				# NB: other variants?!
				'INJURIES/FATAL/CONDITION  (GENERAL DESCRIPTION):': 'injury',
				'INJURIES/FATAL/CONDITION (GENERAL DECRIPTION):': 'injury',
				'INJURIES/FATAL/CONDITION  (GENERAL DECRIPTION):': 'injury',
				
				'LOCATION OF INCIDENT (BLOCK OR AREA ONLY):': 'location1',
				'LOCATION OF INCIDENT (INTERSECTION, BLOCK, OR AREA ONLY):': 'location2',
				'LOSS(GENERALDESCRIPTION):': 'loss',
				'NATUREOFINCIDENT(TITLE&CODE):': 'nature',
				'R/O (SERIAL/CALL SIGN):': 'ro',
				'REPORT #:': 'rptno',
				'SGT/W. COMMANDER NOTIFIED:': 'sgt',
				'SUSPECT(S)/GENDER(S):': 'suspect',
				'SUSPECT(S) IN-CUSTODY?': 'custody',
				'TIME OF INC:': 'time',
				'VICTIM(S)/GENDER(S):': 'victim',
				'WEAPONS USED (GENERAL DESCRIPTION):': 'weapon' }

SkipFields = ['incno','location1','location2','fileIdx','rptno']
Month3Char = ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec']

cid_pat1 = re.compile(r'\d{2}-\d{5,6}')
cid_pat2 = re.compile(r'(\d{2}-\d{5,6})_(\d+)')

date_pat = re.compile(r'(\d+)(\D+)(\d+)')

def parseOneLog(inf,dataDir,outXML=False,verbose=False):
	'''returns fndList = [ { allAnnoteInfo and i=nfnd} ]
	'''
	pdf = pdfquery.PDFQuery(dataDir+inf)
	try:
		pdf.load()
	except Exception as e:
		logger.warning('parseOneLog: bad pdf?! inf=%s except=%s',inf,e)
		return []
		
	if outXML:
		outf = inf.replace('.pdf','.xml')
		pdf.tree.write(dataDir+outf, pretty_print=True, encoding="utf-8")
	
	aeList =pdf.tree.findall('.//Annot')
		
	# logger.info('parseOneLog: NAnnote=%d',len(aeList))
	
	fndList = []
	nfnd = 0
	currDict = {'i': 0}
	for ia, ae in enumerate(aeList):
		if 'V' in ae.keys():
			t = ae.get('TU')
			v = ae.get('V')
			
			if verbose: logger.info('ia=%s nfnd=%d t=%s v=%s',ia,nfnd,t,v)
			
			# assert t == DLogPDFFormFields[ia % DLogPDFFormFields]
			# ASSUME first field lexicographically encountered is AREA/BEAT:
			if t=='AREA/BEAT:':
				# assert len(currDict) == DLogPDFFormFields + 1, 'getOneLog: DLogPDFFormFields misordered?!'
				if len(currDict) != NDLogPDFFormFields + 1:
					logger.info('parseOneLog: partial logEntry?! ia=%s currDict=%s',ia,currDict)
				fndList.append(currDict)
				nfnd += 1
				# logger.info('*BREAK* nfnd=%d',nfnd)
				currDict = {'i': nfnd}
			currDict[t] = v
	
	fndList.append(currDict)

	return fndList

def name2froot(name):
	'''returns root of pdf file name
	'''

	if '.pdf' not in name:
		return ''
	
	fbits = name.split('_')
	pdfFile = fbits[-1]
	frootOrig,fext = os.path.splitext(pdfFile)
	froot = normPLogFName(frootOrig)
	return froot

def normPLogFName(frootOrig):
	# 181222: file names normalized in harvestPatrolLog.getBoxIDs() with strip().lower().replace('_','#')
	froot = frootOrig.replace(' ','')
	froot = froot.replace('opd-dailylog','')
	froot = froot.replace('opddailylog','')
	froot = froot.replace('opd','')
	froot = froot.replace('dailylog','')
	froot = froot.replace('to','-')
	froot = froot.strip('-')
	
	if date_pat.match(froot) == None:
		logger.warning('normPLogFName: cant match %s -> %s' ,frootOrig,froot)
	
	return froot

def parseLogFiles(files2parse,rootDir,verbose=False):
	'''returns list of DailyParse pkey associated with these files
		getOneLog() builds allAnnoteInfo: TU -> V 
		for all annote fields from pdf.tree.findall('.//Annot')
		concatenate all log entries  the list
	'''
	
	dpIdxList = []
	# files2parse = [(name,boxobj.boxidx,haveKids)]
	npreParse = 0
	startParseDT = datetime.now()
	for (nfiles,boxidx) in enumerate(files2parse):
		try:
			boxobj = BoxID.objects.get(idx=boxidx)
		except ObjectDoesNotExist:
			logger.warning('parseLogFiles: missing BoxID?! boxidx=%s',boxidx)
			continue

		name = boxobj.name
		nkids = boxobj.kids.all().count()
		haveKids = nkids > 0
		
		if haveKids:
			logger.info('parseLogFiles: skipping directory name=%s',name)
			continue

		fbits = name.split('_')
		froot = name2froot(name)		
		
		qs = DailyParse.objects.filter(froot=froot)
		nparse = qs.count()
		if nparse > 0:
			logger.info('parseLogFiles: already pre-parsed froot=%s nparse=%d', froot,nparse)
			npreParse += nparse
			continue

		fbits.insert(0,rootDir)
		# NB: splat to provide all of kbits
		fullpath = os.path.join(*fbits)
		# need path containing pdf
		pathDir,pdfFile = os.path.split(fullpath)
		pathDir += '/'

		try:
			########
			fndList = parseOneLog(pdfFile,pathDir)
			########
		except Exception as e:
			logger.warning('parseLogFiles: bad file?! fullpath=%s except=%e',fullpath,e)
			continue
		
		# NB: same dp.parseDT for all parses from same parsed froot
		nowDT = datetime.now()
		locDT =  OaklandTimeZone.localize(nowDT)		

		nowDT = datetime.now()
		locDT = awareDT(nowDT)
		boxobj.parseDT = locDT
		boxobj.save()
				
		ndrop = 0
		incidList = []
		cidFld = 'rptno'
		for fnd in fndList:
			# standardize field names to DayLogFields, normalize values
			newData = {'froot': froot}
			for k,v in fnd.items():
				if k in DayLogFields:
					newData[ DayLogFields[k] ] = normValue(v)
				elif k != None:
					logger.warning('parseLogFiles: odd key?! froot=%s k=%s v=%s',froot,k,v)

			# NB: entries missing cid/opd_rd are DROPPED!
			if cidFld in newData:
				incidList.append(newData)
			else:
				ndrop += 1
		
		logger.info('%s: %s NIncid=%d NDrop=%d' , nowDT,froot,len(incidList),ndrop)
		if verbose:
			elapTime = datetime.now() - startParseDT
			logger.info('parseLogFiles: done parsing file %s %d elapTime=%s', froot,nfiles,elapTime.total_seconds())
		
		for nfnd,incidParse in enumerate(incidList):
			dp = DailyParse()
			dp.parseOrder = nfnd
			dp.froot = froot
			dp.boxobj = boxobj
			opd_rdStr = incidParse[cidFld]
			if len(opd_rdStr) > 10:
				logger.warning('parseLogFiles: odd opd_rd?! %s truncated froot=%s nfnd=%d',opd_rdStr,froot,nfnd)
				opd_rdStr = opd_rdStr[:10]
			dp.opd_rd = opd_rdStr
			dp.incidDT = None  # filled in regularizedIncidTbl()
			dp.parseDict = json.dumps(incidParse)
			dp.parseDT = locDT
			dp.save()
			dpIdx = dp.pk
			dpIdxList.append(dpIdx)
	
	logger.info('parseLogFiles: done. NParse=%d NPreParse=%d',len(dpIdxList),npreParse)
	return dpIdxList

def normValue(v):
	if type(v) == type('string'):
		v2 = v.lower().strip()
		# HACK: single, double quotes replaced with exclamation marks to facilitate CSV export
		v2 = v2.replace("'","!!")
		v2 = v2.replace('"','!!!')
		if v2 != v:
			v = v2

	if v=='None':
		return ''
	else:
		return v 
	
def diffDict(i1,i2):
	bothKeys = list(i1.keys()) + list(i2.keys())
	bothKeys.sort()
	sameVal = []
	diffVal = {}
	for k in bothKeys:
		if k in i1 and k in i2:
			if i1[k] == i2[k]:
				sameVal.append(k)
			else:
				diffVal[k] = (i1[k],i2[k])
		elif k in i1:
			diffVal[k] = (i1[k],None)
		else:
			diffVal[k] = (None,i2[k])
	return sameVal,diffVal

def rptDiff(sameVal,diffVal):					
	allDiff = list(diffVal.keys())
	allDiff.sort()
	logger.info('NSame=%d NDiff=%d', len(sameVal),len(diffVal))
	for k in allDiff:
		logger.info('\t%s: %s\n\t%s: %s' , k,diffVal[k][0],k,diffVal[k][1])
		
def reg_remove_victim(s):
	reg = s.replace('(v)','')
	reg = reg.replace("v1's",'')
	reg = reg.replace("v1",'')
	reg = reg.replace("victim",'')
	reg = reg.replace("victims",'')
	reg = reg.replace("victim's",'')
	return reg

def reg_removeParens(s):
	'NB: replaces with spaces'
	reg = s.replace('(',' ')
	reg = reg.replace(')',' ')
	return reg 

def reg_numWord(s):
	numWords = {'one': '1', 'two': '2', 'three': '3', 'four': '4', 'five': '5'}
	if s in numWords:
		return numWords[s]
	else:
		return s
	
beat_pat = re.compile(r'([0-9]+)([XY])')
	
def normBeat(beat):
	'''tolerate missing '0' prefix, missing 'X/Y' suffice
	'''
	match = beat_pat.match(beat)
	if match:
		(num,suf) = match.groups()
		if len(num)<2:
			num = '%02d' % (int(num))
		return num + suf 
	else:
		return ''
	
# from harvestDLog.py for regularizeIncidTbl()

def regularizeIncidTbl(dpIdxList):
	"""regularize strings, fields, dates, times, areas, beats, 
		loss, injury, weapon, callout, ncustody, nsuspect, nvictim, nhospital
		responding officer, nature
		opd_rd, dates, times placed directly into dpo.incidDT
	"""
	
	nbadCID = 0
	ngoodDate = 0
	nbadDate = 0
	ngoodTime = 0
	nbadTime = 0
	nbadBeat = 0
	
	for dpIdx in dpIdxList:
		dpo = DailyParse.objects.get(idx=dpIdx)
		cid = dpo.opd_rd
		
		incidInfo = json.loads(dpo.parseDict)
		newIncidInfo = incidInfo.copy()
			
		# NB: fields sorted to ensure DATE from froot established before time
		for fld in sorted(incidInfo.keys()):

			v = incidInfo[fld]
			
			# normalize strings
			if type(v) == type('string'):
				v2 = v.lower().strip()
				# NB: single, double quotes replaced with exclamation marks to facilitate CSV export
				v2 = v2.replace("'","!!")
				v2 = v2.replace('"','!!!')
				if v2 != v:
					newIncidInfo[fld] = v2
					v = v2

			# some fields unprocessed
			if fld in SkipFields:
				continue 
			
			if fld=='froot':
				match = date_pat.match(v)
				if match:
					(day,mon,year) = match.groups()
					if len(year)==2:
						year = '20'+year
					mon = mon.lower()
					try:
						moni = Month3Char.index(mon)
						dpo.incidDT = datetime(year=int(year),month=moni+1,day=int(day))
						dpo.incidDT = OaklandTimeZone.localize(dpo.incidDT)
						ngoodDate += 1
					except Exception as e:
						logger.warning('regularizeIncidTbl: cant construct dateTime?! cid=%s v=%s e=%s',cid,v,e)
						nbadDate += 1
				else:
					logger.warning('regularizeIncidTbl: bad date?! cid=%s v=%s',cid,v)
					nbadDate += 1
				
				continue

			if fld=='time':
				ftime = None
				if v.find('/') != -1:
					spos = v.find('/')
					time1 = v[:spos]
					if len(time1)==4:
						ftime = time1
				elif len(v)==4:
					ftime = v 
					
				if ftime != None:
					hr = int(ftime[:2])
					min = int(ftime[2:])
					try:
						dpo.incidDT = dpo.incidDT.replace(hour=hr,minute=min)
						ngoodTime += 1
					except Exception as e:
						logger.warning('regularizeIncidTbl: bad ftime?! cid=%s ftime=%s',cid,ftime)
						nbadTime += 1
				else:
					logger.warning('regularizeIncidTbl: bad time?! cid=%s v=%s',cid,v)
					nbadTime += 1
			
			if fld == 'area':
				v = v.replace('?','/')
				flds = v.upper().split('/')
				if len(flds)==2:
					newIncidInfo['reg_area'] = flds[0].strip()
					beatFnd = flds[1].strip()
				elif len(flds)==1:
					if flds[0].find('X') != -1 or flds[0].find('Y') != -1:
						beatFnd = flds[0].strip()
					else:
						newIncidInfo['reg_area'] = flds[0].strip()
				else:
					logger.warning('regularizeIncidTbl: bad area/beat?! cid=%s v=%s',cid,v)
					nbadBeat += 1
					beatFnd = ''
				
				newIncidInfo['reg_beat'] = normBeat(beatFnd)
				
			
			## augment existing fields with regularized 'reg_' versions
			# NB: fields not regularized
			# sgt
			# suspect: 0,1,multiple
			# custody: 0,1
			# victim: parens; "victims"
			
			# loss: comma "and" & sep; victim ref, "v1"; 
			# reg_loss: list of items
			if fld=='loss':
				if v == 'none' or v == "n/a" or v == 'unk' or v == 'unknown' or v == 'no loss':
					newIncidInfo['reg_loss'] = []
				else:
					reg = reg_remove_victim(v)
					reg = reg.replace('(recovered)','')
							
					reg = reg.replace(' and ',', ')
					reg = reg.replace(' with ',', ')
					reg = reg.replace(' containing ',', ')
					reg = reg.replace(' & ',', ')				
					reg = reg.replace('/',', ')				
					lossList = reg.split(',')
					rll = []
					for l in lossList:
						l.replace('.','')
						l = l.strip()
						if len(l) ==0:
							continue
						if l.find('cash') != -1 or l.find('currency') != -1 or l.find('money') != -1  or l.find('$') != -1:
							rll.append('cash')
						elif l.find('phone') != -1:
							rll.append('phone')
						elif l.find('personal') != -1:
							rll.append('personalProperty')
						elif l.find('gun') != -1 or l.find('firearm') != -1 or l.find('pistol') != -1:
							rll.append('gun')
						else:
							rll.append(l)
					newIncidInfo['reg_loss'] = rll
					
			# injury: gsw; condition (stable); moderate; noise words
			if fld=='injury':
				if v.find('gsw') != -1 or v.find('gunshot') != -1:
					newIncidInfo['reg_gsw'] = True
			
			# weapon: handgun, gun, knife, personal; caliber; possible qualifier
			if fld=='weapon':
				if v == '' or v == ' ' or v == 'none' or v == 'unknown' or v == 'unkown' or v == 'unk' or v == 'n/a':
					newIncidInfo['reg_weapon'] = ''
				elif v.find('gun') != -1 or v.find('firearm') != -1 or v.find('rifle') != -1 or v.find('pistol') != -1:
					reg = 'gun'
					qual = ''
					if v.find('simulate') != -1:
						qual = 'simulate'
					else:
						for gtype in ['40','45','9mm','auto']:
							if v.find(gtype) != -1:
								qual = gtype
								break
					if qual != '':
						reg += ':'+qual	
					newIncidInfo['reg_weapon'] = reg
				elif v.find('knife') != -1:
					newIncidInfo['reg_weapon'] = 'knife'
				elif v.find('personal') != -1 or v.find('hands') != -1:
					newIncidInfo['reg_weapon'] = 'personal'
				else:
					newIncidInfo['reg_weapon'] = v.strip()
					
			# callout: yes, no; / qualifier
			if fld=='callout':
				if v == '' or v.find('no') != -1:
					newIncidInfo['reg_callout'] = 'no'
				else:
					reg = v.replace('yes','')
					for p in ['/','-',';']:
						reg = reg.replace(p,' ')
					reg = reg.strip()
					newIncidInfo['reg_callout'] = 'yes:' + reg
			
			# ncustody: number word -> integer; "suspect"; parens
			if fld=='ncustody':
				if v == '0' or v == '' or v == 'n/a' or v.find('no') != -1:
					newIncidInfo['reg_ncustody'] = 0
				elif v == 'yes':
					newIncidInfo['reg_ncustody'] = 1
				else:
					reg = v.replace('suspect','')
					reg = reg.replace('suspects','')
					reg = reg.replace('in-custody','')
					reg = reg_removeParens(reg)
					
					n = -1
					# break on first number found
					for w in reg.split():
						w2 = reg_numWord(w)
						try:
							n = int(w2)
							break
						except Exception as e:
							continue
					if n !=-1:
						newIncidInfo['reg_ncustody'] = n
					
			# nsuspect: number word -> integer; parens; multiple; gender; "suspects
			if fld=='nsuspect':
				if v == '0' or v == '' or v == 'n/a' or v.find('no') != -1 or v.find('unk') != -1:
					newIncidInfo['reg_nsuspect'] = 0
				else:
					reg = v.replace('suspect','')
					reg = reg.replace('suspects','')
					reg = reg_removeParens(reg)
					
					# NB: dropping gender
					reg = reg.replace('male','')
					reg = reg.replace('males','')
					reg = reg.replace('female','')
					reg = reg.replace('females','')
					
					reg = reg.replace('/',' ')
					reg = reg.replace('-',' ')
					
					n = -1
					# break on first number found
					for w in reg.split():
						w2 = reg_numWord(w)
						try:
							n = int(w2)
							break
						except Exception as e:
							continue
					if n != -1:
						newIncidInfo['reg_nsuspect'] = n
								
			# nvictim: number word -> integer; / gender; business; "victim"
			if fld=='nvictim':
				if v == '0' or v == '' or v == 'n/a' or v.find('no') != -1 or v.find('unk') != -1:
					newIncidInfo['reg_nvictim'] = 0
				else:
					reg = v.replace('victim','')
					reg = reg_removeParens(reg)

					# NB: dropping gender
					reg = reg.replace('male','')
					reg = reg.replace('males','')
					reg = reg.replace('female','')
					reg = reg.replace('females','')
					reg = reg.replace('m','')
					reg = reg.replace('f','')

					reg = reg.replace('/',' ')
					reg = reg.replace('-',' ')

					n = -1
					# break on first number found
					for w in reg.split():
						w2 = reg_numWord(w)
						try:
							n = int(w2)
							break
						except Exception as e:
							continue
					if n != -1:
						newIncidInfo['reg_nvictim'] = n
					
			# nhospital: number word -> integer; parens; self transported; refused; "victim"
			if fld=='nhospital':
				if v == '0' or v == '' or v == ' ' or v == 'n/a' or v.find('no') != -1 or v.find('unk') != -1:
					newIncidInfo['reg_nhospital'] = 0
				elif v == 'yes' or v.find('self') != -1:
					newIncidInfo['reg_nhospital'] = 1
				else:
					reg = reg_removeParens(v)

					n = -1
					# break on first number found
					for w in reg.split():
						w2 = reg_numWord(w)
						try:
							n = int(w2)
							break
						except Exception as e:
							continue
					if n != -1:
						newIncidInfo['reg_nhospital'] = n
			
			# ro: split on /; record first, second; names, replace '. ' with '_'; "ofc ", "
			if fld=='ro':
				reg = v.replace('/',' ')
				reg = reg_removeParens(reg)
				reg = reg.replace('desk officer','deskOfficer')
				reg = reg.replace('ofc. ','ofc_')
				reg = reg.replace('ofc.','ofc_')
				reg = reg.replace('ofc ','ofc_')
				reg = reg.replace('sgt. ','sgt_')
				reg = reg.replace('. ','_')
				olist = []
				for o in reg.split(' '):
					o = o.strip()
					if len(o) ==0:
						continue
					if o.endswith('p'):
						o = o[:-1]
					olist.append(o)
				newIncidInfo['reg_ro'] = olist
				
			# nature
			if fld=='nature':
				punc = ['-']
				reg = v.replace('/',' ')
				reg = reg.replace(',',' ')
				pcList = []
				for n in reg.split():
					if n.endswith('-'):
						n = n[:-1]
					if n.startswith('(') and n.endswith(')'):
						n = n[1:-1]
					if n.startswith('pc'):
						n = n[2:]
					if n.endswith('pc'):
						n = n[:-2]
					if len(n)==0 or n.isalpha() or n in punc:
						continue
					pcList.append(n)
				newIncidInfo['reg_pc'] = pcList
				
			# eo fld loop

		dpo.parseDict = json.dumps(newIncidInfo)
		dpo.save()
				
	logger.info('regularizeIncidTbl: NIncid=%d NBadCID=%d NDate=%d/%d NTime=%d/%d NBadBeat=%d' , \
			len(dpIdxList),nbadCID,ngoodDate,nbadDate,ngoodTime,nbadTime,nbadBeat)

def json_serial(o):
	'''serialize dates as ISO, all others as strings
	'''
	if isinstance(o, (datetime.datetime, datetime.date)):
		return o.isoformat()
	else:
		return str(o)


def addGeoCode2(dpIdxList,gconn,verbose=None):
	'''create updated dlogTbl with XLng, YLat and GCConf columns
	180131: search against Google
	'''

	
	nMBmiss = 0
	nMZmiss = 0
	nggc = 0
	ngmiss = 0
	nhit=0
	newDLogTbl = {}
	
	for i,dpIdx in enumerate(dpIdxList):
		dpo = DailyParse.objects.get(idx=dpIdx)
		cid = dpo.opd_rd
		
		dlog = json.loads(dpo.parseDict)
		newdlog = dlog.copy()
		newdlog['XLng'] = ''
		newdlog['YLat'] = ''
		newdlog['GCConf'] = ''
		
		if verbose != None and i % verbose == 0:
			logger.info('addGeoCodeVerbose: %d NMBMiss=%d NMZMiss=%d NGGC=%d NGMiss=%d NHit=%d NLogOut=%d'  , \
					i,nMBmiss,nMZmiss,nggc,ngmiss,nhit,len(newDLogTbl))
						
		if 'location1'  in dlog:
			loc = dlog['location1'].strip()
		else:
			loc = ''
		
		if len(loc)==0:
			# print(('addGeoCode: %d %s "%s" %s EMPTY' % (i,dlogCID,loc,GCConf)))
			nMBmiss += 1
			dpo.parseDict = json.dumps(newdlog)
			dpo.save()
			continue

		rv = geocodeAddr(loc)
							
		if rv==None or \
			   (type(rv) == type("string") and rv.startswith('GMiss-')):
			logger.warning('addGeoCode2: geotagErr "%s" %s' ,loc,rv)
			ngmiss += 1
			
		else:
			xlng,ylat = rv
			newdlog['XLng'] = xlng
			newdlog['YLat'] = ylat
			newdlog['GCConf'] = '1.0'  # NB: no confidence from Google
			nggc += 1
			if verbose==1:
				logger.info('addGeoCode G:  i=%d cid=%s loc="%s" xlng=%f ylat=%f', i,cid,loc,newdlog['XLng'],newdlog['YLat'])
			nhit += 1

		dpo.parseDict = json.dumps(newdlog)
		dpo.save()
		continue

	logger.info('addGeoCode2: NDLogIn=%d NGGC=%d NGMiss=%d NHit=%d'  , \
			len(dpIdxList),nggc,ngmiss,nhit)

def checkTblOverlap(d1,d2):
	
	redunKeys = set(d1.keys()).intersection(set(d2.keys()))
	if len(redunKeys)>0:
		logger.info('checkTblOverlap: redundant keys?! nredun=%d',len(redunKeys))
		return len(redunKeys)
	else:
		return 0
	
