# parsePatrolLogs: convert PDFs
# 	collapose multiple days' logs allData: froot -> [ { TU->V } ] into
# 	incidTbl: cid* -> {froot, TU -> V}
# 	NB: cid from rptno field; random int suffix added if not unique!
# 	regularize fields, geotag
# 	save as incidTblArchive_%s.json
#
# 181113
#


from collections import defaultdict
import datetime
import glob
import json
import os
import pdfquery
import re 

import googlemaps
import mapbox

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

def getOneLog(inf,dataDir,outXML=False,verbose=False):
	'''returns fndList = [ { allAnnoteInfo and i=nfnd} ]
	'''
	pdf = pdfquery.PDFQuery(dataDir+inf)
	try:
		pdf.load()
	except Exception as e:
		print('getOneLog: bad pdf?!',e,inf)
		return []
		
	if outXML:
		outf = inf.replace('.pdf','.xml')
		pdf.tree.write(dataDir+outf, pretty_print=True, encoding="utf-8")
	
	aeList =pdf.tree.findall('.//Annot')
		
	# print('getOneLog: NAnnote=',len(aeList))
	
	fndList = []
	nfnd = 0
	currDict = {'i': 0}
	for ia, ae in enumerate(aeList):
		if 'V' in ae.keys():
			t = ae.get('TU')
			v = ae.get('V')
			
			if verbose: print(ia,nfnd,t,v)
			
			# assert t == DLogPDFFormFields[ia % DLogPDFFormFields]
			# ASSUME first field lexicographically encountered is AREA/BEAT:
			if t=='AREA/BEAT:':
				# assert len(currDict) == DLogPDFFormFields + 1, 'getOneLog: DLogPDFFormFields misordered?!'
				if len(currDict) != NDLogPDFFormFields + 1:
					print('getOneLog: partial logEntry?!',ia,currDict)
				fndList.append(currDict)
				nfnd += 1
				# print('*BREAK*',nfnd)
				currDict = {'i': nfnd}
			currDict[t] = v
	
	fndList.append(currDict)

	return fndList

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
		print('normPLogFName: cant match %s -> %s' % (frootOrig,froot))
	
	return froot

def collectDailyLogs(files2parse,rootDir):
	'''returns logData: dailyRoot -> [ {allAnnoteInfo} ] 
		getOneLog() builds allAnnoteInfo: TU -> V 
		for all annote fields from pdf.tree.findall('.//Annot')
		concatenate all log entries  the list
	'''
		
	logData = {} # dailyRoot -> [ {infoDict} ]
		
	for k,info in files2parse.items():
		if 'kids' in info:
			print('collectDailyLogs: skipping directory',k)
			continue
		
		fbits = k.split('_')
		pdfFile = fbits[-1]
		
		frootOrig,fext = os.path.splitext(pdfFile)
		
		froot = normPLogFName(frootOrig)
		
		if froot in logData:
			print('collectDailyLogs: dup froot?!')
			continue

		fbits.insert(0,rootDir)
		# NB: splat to provide all of kbits
		fullpath = os.path.join(*fbits)
		# need path containing pdf
		pathDir,pdfFile = os.path.split(fullpath)
		pathDir += '/'

		try:
			fndList = getOneLog(pdfFile,pathDir)
		except Exception as e:
			print('collectAllDailyLogs: bad file?!',fullpath,e)
			continue
			
		print('%s,%d' % (froot,len(fndList)))
		logData[froot] = fndList		
				
	return logData

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
	print('NSame=%d NDiff=%d' % (len(sameVal),len(diffVal)))
	for k in allDiff:
		print('\t%s: %s\n\t%s: %s' % (k,diffVal[k][0],k,diffVal[k][1]))
		
def mergeDailyLogs(allData):
	'''collapose multiple days' logs allData: froot -> [ { TU->V } ] into
	incidTbl: cid* -> {froot, TU -> V}
	NB: cid from rptno field; random int suffix added if not unique! 
	'''
	
	allFRoots = list(allData.keys())
	allFRoots.sort()
	nlog = sum([ len(lst) for lst in allData.values() ])
	
	incidTbl = {} # cid -> [ {pdfRoot,} ]
	ndup = 0
	nident = 0
	ndrop = 0
	nmissCID = 0
	nextIdx = 1
	for froot in allFRoots:
		for infoTbl in allData[froot]:
			newData = {'froot': froot}
			for k,v in infoTbl.items():
				if k in DayLogFields:
					newData[ DayLogFields[k] ] = normValue(v)
				elif k != None:
					print('mergeDailyLogs: odd key?!',froot,k,v)
			if 'rptno' in newData:
				cid = newData['rptno']
				if cid == 'N/A':
					# NB: create DailyLog CID from file and index pos within file
					cid = 'DL_' + newData['froot'] + '_' + str(newData['fileIdx'])
					nmissCID += 1
				if cid in incidTbl:
					# print('mergeDailyLogs: dup CID?! %s\n\t%s\n\t%s' % (cid,incidTbl[cid],newData))
					sameVal,diffVal = diffDict(incidTbl[cid],newData)
					
					# ignore pairs differing only in froot; don't add newData rcd
					if list(diffVal.keys()) == ['froot']:
						nident += 1
						continue
					
					print('mergeDailyLogs: %s dup CID?! %s NSame=%d nextIdx=%d' % (froot,cid,len(sameVal),nextIdx))
					rptDiff(sameVal,diffVal)
										
					ndup += 1
					# HACK: add unique but random suffix
					cid = '%s_%d' % (cid,nextIdx)
					nextIdx += 1
				incidTbl[cid] = newData
			else:
				# initial field detritus from parse
				# {'fileIdx': 0, 'froot': '(13-14Jul16)'}
				# print(newData)
				ndrop += 1
					
	print('* mergeDailyLogs: NIncid=%d/%d NDup=%d NIdent=%d NDrop=%d NMissCID=%d' % \
			(nlog,len(incidTbl),ndup,nident,ndrop,nmissCID))
	return incidTbl	

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

def regularizeIncidTbl(incidTbl):
	"""regularize strings, fields, dates, times, areas, beats, 
		loss, injury, weapon, callout, ncustody, nsuspect, nvictim, nhospital
		responding officer, nature
	"""
	
	nbadCID = 0
	ngoodDate = 0
	nbadDate = 0
	ngoodTime = 0
	nbadTime = 0
	nbadBeat = 0
	
	newIncidTbl = {}
	
	for cid,incidInfo in incidTbl.items():
		
		if not (cid_pat1.match(cid) or cid_pat2.match(cid)):
			print('regularizeIncidTbl: bad CID',cid)
			nbadCID += 1
			continue
		
		# NB: DUPLICATE CID's also regularized!
		
		newIncidInfo = incidInfo.copy()
				
		for fld in incidInfo.keys():

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
						date = datetime.date(int(year),moni+1,int(day))
						newIncidInfo['reg_date'] = date
						ngoodDate += 1
					except Exception as e:
						nbadDate += 1
						pass
				continue

			if fld=='time':
				time = None
				if v.find('/') != -1:
					spos = v.find('/')
					time1 = v[:spos]
					if len(time1)==4:
						time = time1
				elif len(v)==4:
					time = v 
					
				if time != None:
					hr = int(time[:2])
					min = int(time[2:])
					try:
						timeobj = datetime.time(hr,min)
						newIncidInfo['reg_time'] = timeobj
						ngoodTime += 1
					except Exception as e:
						nbadTime += 1
						pass
			
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
					print('regularizeIncidTbl: bad area/beat?!',cid,v)
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
				# print(v,pcList)
				newIncidInfo['reg_pc'] = pcList
				
			# eo fld loop
			
		newIncidTbl[cid] = newIncidInfo
				
	print('* regularizeIncidTbl: NIncid=%d NBadCID=%d NDate=%d/%d NTime=%d/%d NBadBeat=%d' % \
			(len(newIncidTbl),nbadCID,ngoodDate,nbadDate,ngoodTime,nbadTime,nbadBeat))
	return newIncidTbl


def json_serial(o):
	'''serialize dates as ISO, all others as strings
	'''
	if isinstance(o, (datetime.datetime, datetime.date)):
		return o.isoformat()
	else:
		return str(o)

def addGeoCode2(dlogTbl,gconn,verbose=None):
	'''create updated dlogTbl with XLng, YLat and GCConf columns
	180131: search against Google
	'''

	allCID = list(dlogTbl.keys())
	allCID.sort()
	
	MZDefaultOaklandCoord = [-122.197811, 37.785199]

	nMBmiss = 0
	nMZmiss = 0
	nggc = 0
	ngmiss = 0
	nhit=0
	newDLogTbl = {}
	for i,dlogCID in enumerate(allCID):
		if verbose != None and i % verbose == 0:
			print('addGeoCodeVerbose: %d NMBMiss=%d NMZMiss=%d NGGC=%d NGMiss=%d NHit=%d NLogOut=%d'  % \
					(i,nMBmiss,nMZmiss,nggc,ngmiss,nhit,len(newDLogTbl)))
			
		dlog = dlogTbl[dlogCID]
		newdlog = dlog.copy()
			
		if 'location1'  in dlog:
			loc = dlog['location1'].strip()
		else:
			loc = ''
		
		if len(loc)==0:
			# print(('addGeoCode: %d %s "%s" %s EMPTY' % (i,dlogCID,loc,GCConf)))
			newdlog['XLng'] = ''
			newdlog['YLat'] = ''
			newdlog['GCConf'] = ''
			newDLogTbl[dlogCID] = newdlog
			nMBmiss += 1
			continue

		loc2 = loc.replace('blk ',' ')
		loc2 = loc2.replace('block ',' ')
		loc2 = loc2.replace('of ',' ')
		loc2 = loc2.replace('IFO ',' ') # 180131
				
		# Geocoding via Google
		# print('trying google...')
		
		loc2 += ' Oakland CA'
		geoCodeG = gconn.geocode(loc2)
		
		# NB: python API doesn't provide status, only results!?
		# if geoCodeG['status'] == 'OK':
		#	f = geoCodeG['results'][0]

		if len(geoCodeG) < 1:
			print(('addGeoCode G: %d %s "%s" GMiss-none' % (i,dlogCID,loc)))
			newdlog['XLng'] = ''
			newdlog['YLat'] = ''
			newdlog['GCConf'] = ''
			newDLogTbl[dlogCID] = newdlog
			ngmiss += 1
			continue
			
		f = geoCodeG[0]
		oakFnd = False
		for ac in f['address_components']:
			if 'locality' in ac['types'] and ac['long_name'] == 'Oakland':
				oakFnd = True
				break
		if oakFnd:
			xlng = f['geometry']['location']['lng']
			ylat = f['geometry']['location']['lat']
			newdlog['XLng'] = xlng
			newdlog['YLat'] = ylat
			newdlog['GCConf'] = '1.0'  # NB: no confidence from Google
			nggc += 1
			newDLogTbl[dlogCID] = newdlog
			if verbose==1:
				print(('addGeoCode G:  %d %s "%s" "%s" %f %f' % (i,dlogCID,loc,loc2,newdlog['XLng'],newdlog['YLat'])))
			nhit += 1
		else:
			print(('addGeoCode G: %d %s "%s" GMiss-noOak' % (i,dlogCID,loc)))
			newdlog['XLng'] = ''
			newdlog['YLat'] = ''
			newdlog['GCConf'] = ''
			newDLogTbl[dlogCID] = newdlog
			ngmiss += 1
			continue

	print('addGeoCode2: NDLogIn=%d NGGC=%d NGMiss=%d NHit=%d NLogOut=%d'  % \
			(len(dlogTbl),nggc,ngmiss,nhit,len(newDLogTbl)))
	
	return newDLogTbl

def checkTblOverlap(d1,d2):
	
	redunKeys = set(d1.keys()).intersection(set(d2.keys()))
	if len(redunKeys)>0:
		print('checkTblOverlap: redundant keys?!',len(redunKeys))
		return len(redunKeys)
	else:
		return 0
	
