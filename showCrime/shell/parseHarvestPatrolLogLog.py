# parse_OPDLog_PDF: convert PDFs
# 	collapose multiple days' logs allData: froot -> [ { TU->V } ] into
# 	incidTbl: cid* -> {froot, TU -> V}
# 	NB: cid from rptno field; random int suffix added if not unique!
# 	regularize fields, geotag
# 	save as incidTblArchive_%s.json
#
# 181113
#


from collections import defaultdict
import _pickle as cPickle
import datetime
import glob
import json
import os
import pdfquery
import re 

# import opdata
# 
# import opdUtil
# import opdConstant

# from mapzen.api import MapzenAPI
import googlemaps
import mapbox

def cmpx(o1,o2):
	if o1 < o2:
		return o1,o2
	return o2,o1

def freqHist(tbl):
	"Assuming values are frequencies, returns sorted list of (val,freq) items in descending freq order"
	def cmpd1(a,b):
		"decreasing order of frequencies"
		return cmpx(b[1], a[1])

	
	flist = tbl.items()
	flist.sort(cmpd1)
	return flist

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

	# print('getOneLog: NRcd=',len(fndList))

# 	for i,info in enumerate(fndList):
# 		cid = info['REPORT #:']  if ('REPORT #:' in info) else '??'
# 		print(i,cid,info)
	
	return fndList

def collectAllDailyLogs(dataDir):
	'''returns logData: dailyRoot -> [ {allAnnoteInfo} ] 
	getOneLog() builds allAnnoteInfo: TU -> V 
		for all annote fields from pdf.tree.findall('.//Annot')
		concatenate all log entries  the list
	'''
	
	
	logData = {} # dailyRoot -> [ {infoDict} ]
	
	parentDir = os.path.abspath(os.path.join(dataDir, os.pardir))
	
	dailyList = glob.glob(dataDir+'*')
	dailyList.sort()
	print('collectAllDailyLogs: NDays=%d' % (len(dailyList)))
	print('FileRoot,NRcd')
		
	for dlogpath in dailyList:
		dlpBits = os.path.split(dlogpath)
		pdfFile = dlpBits[1]
		
		frootOrig,fext = os.path.splitext(pdfFile)
		froot = frootOrig.replace(' ','')
		froot = froot.replace('OPD-DailyLog','')
		froot = froot.replace('OPDDailyLog','')
		froot = froot.replace('OPD','')
		froot = froot.replace('DailyLog','')
		froot = froot.replace('to','-')
		if froot in logData:
			print('dup froot?!')
		
		try:
			fndList = getOneLog(pdfFile,dataDir)
		except Exception as e:
			print('collectAllDailyLogs: bad file?!',dlogpath,e)
			continue
			
		print('%s,%d' % (froot,len(fndList)))
		logData[froot] = fndList		
				
	return logData

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

def normValue(v):
	if type(v) == type('string'):
		v2 = v.lower().strip()
		# NB: single, double quotes replaced with exclamation marks to facilitate CSV export
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
					print('mergeDailyLogs: odd key?!',k,v)
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
					
					print('mergeDailyLogs: dup CID?! %s NSame=%d' % (cid,len(sameVal)))
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

SkipFields = ['incno','location1','location2','fileIdx','rptno']
Month3Char = ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec']

cid_pat1 = re.compile(r'\d{2}-\d{5,6}')
cid_pat2 = re.compile(r'(\d{2}-\d{5,6})_(\d+)')

date_pat = re.compile(r'(\d+)(\D+)(\d+)')

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

def anlyzRegIncidTbl(incidTbl):

	ngsw = 0
	dateTbl = defaultdict(int)
	beatTbl = defaultdict(int)
	lostTbl = defaultdict(int) 
	ncustodyTbl = defaultdict(int)
	weaponTbl = defaultdict(int)
	calloutTbl = defaultdict(int)
	nsuspectTbl = defaultdict(int)
	nvictimTbl = defaultdict(int)
	nhospTbl = defaultdict(int)
	roTbl = defaultdict(int)
	pcTupleTbl = defaultdict(int)
	pcTbl = defaultdict(int)
	
	roPairs = defaultdict(lambda: defaultdict(int))
	
	for k,tbl in incidTbl.items():
		
		if not (cid_pat1.match(k) or cid_pat2.match(k)):
			print('regularizeIncidTbl: bad CID',k)
			continue
		
		# NB: DUPLICATE CID's also regularized!
				
		for fld in tbl.keys():
			if not fld.startswith('reg_'):
				continue
			
			reg = tbl[fld]
			
			if fld=='reg_date':
				dateTbl[reg] += 1

			if fld=='reg_beat':
				beatTbl[reg] += 1
				
			elif fld=='reg_loss':
				for l in reg:
					lostTbl[l] += 1
					
			elif fld=='reg_gsw':
				ngsw += 1
				
			elif fld=='reg_ncustody':
				ncustodyTbl[reg] += 1
				
			elif fld=='reg_weapon':
				weaponTbl[reg] += 1
			
			elif fld=='reg_callout':
				calloutTbl[reg] += 1

			elif fld=='reg_nsuspect':
				nsuspectTbl[reg] += 1
			
			elif fld=='reg_nvictim':
				nvictimTbl[reg] += 1

			elif fld=='reg_nhospital':
				nhospTbl[reg] += 1
				
			elif fld=='reg_ro':
				for o in reg:
					roTbl[o] += 1
				if len(reg) > 1:
					for i,ro1 in enumerate(reg):
						for j,ro2 in enumerate(reg):
							if j<= i:
								continue
							# NB: do NOT sort the order; primary/secondary info
							# ro1,ro2 = cmpx(ro1,ro2)
							roPairs[ro1][ro2] += 1
					
			elif fld=='reg_pc':
				# NB: need to make tuple of pcList
				pcTupleTbl[tuple(reg)] += 1
				for pc in reg:
					pcTbl[pc] += 1

				
	print('analRegIncidTbl: NGSW=%d' % (ngsw))
	allDates = list(dateTbl.keys())
	allDates.sort()
	print('\n* Dates')
	for d in allDates:
		print('\t%d\t%s' % (dateTbl[d],d))
	allBeats = list(beatTbl.keys())
	allBeats.sort()
	print('\n* Beats')
	for b in allBeats:
		print('\t%d\t%s' % (beatTbl[b],b))
		
	tblNames = ['LOST', 'NCUSTODY', 'WEAPON', 'CALLOUT', 'NSUSPECT', 'NVICTIM', 'NHOSP', 'RO', 'PC','PCTuple']
	for i,tbl in enumerate( [lostTbl, ncustodyTbl, weaponTbl, calloutTbl, nsuspectTbl, nvictimTbl, nhospTbl, \
							roTbl, pcTbl,pcTupleTbl] ):
		print('\n*',tblNames[i])
		freqItems = freqHist(tbl)
		for v,freq in freqItems:
			print('\t%d\t%s' % (freq,v))
		
	allRO = list(roPairs.keys())
	allRO.sort()
	print('\n* ROPairs')
	for ro1 in allRO:
		allRO2 = roPairs[ro1].keys()
		for ro2 in allRO2:
			print('%s\t%s\t%d' % (ro1,ro2,roPairs[ro1][ro2]))

def anlyzRO(allDLog,outf):

	ROTbl = defaultdict(int)
	outs = open(outf,'w')
	outs.write('* All RO\nCID,RO,NameP\n')
	for cid in allDLog.keys():
		try:
			roList = eval(allDLog[cid]['RO'])
		except Exception as e:
			continue
		for ro in roList:
			ROTbl[ro] += 1
			rox = ro.replace('_','X')
			nameP = rox.isalpha()
			outs.write('%s,"%s",%d\n' % (cid,ro,nameP))

	outs.write('\n* Freq\nFreq,RO,NameP\n')
	freqItems = freqHist(ROTbl)
	for v,freq in freqItems:
		rox = v.replace('_','X')
		nameP = rox.isalpha()
		outs.write('%d,"%s",%d\n' % (freq,v,nameP))

	outs.close()
			
def rptLogSumm(incidTbl,outf):

	nbadCID = 0
	nout = 0
	outs = open(outf,'w')
	outs.write('CID,Date,Time,IncNo,Location1,Beat,GSW,RO,PCList,PCRaw,Loss,Ncustody,Nsuspect,Nvictim,Nhospital,Weapon,Callout\n')

	allCID = list(incidTbl.keys())
	allCID.sort()
	for cid in allCID:
		if not (cid_pat1.match(cid) or cid_pat2.match(cid)):
			nbadCID += 1
			continue

		tbl = incidTbl[cid]
		
		# NB: DUPLICATE CID's reported!
		dateStr = 		tbl['reg_date'] if 'reg_date' in tbl else ''
		timeStr = 		tbl['reg_time'] if 'reg_time' in tbl else ''
		incNoStr = 		tbl['incno'] if 'incno' in tbl else ''
		locateStr = 	tbl['location1'] if 'location1' in tbl else ''
		beatStr = 		tbl['reg_beat'] if 'reg_beat' in tbl else ''
		gswStr = 		1 if 'reg_gsw' in tbl else 0
		roStr =   		tbl['reg_ro'] if 'reg_ro' in tbl else ''
		pcStr=    		tbl['reg_pc'] if 'reg_pc' in tbl else ''
		pcRawStr = 		tbl['nature'] if 'nature' in tbl else ''
		lossStr=    	tbl['reg_loss'] if 'reg_loss' in tbl else ''
		ncustodyStr=    tbl['reg_ncustody'] if 'reg_ncustody' in tbl else ''
		nsuspectStr=    tbl['reg_nsuspect'] if 'reg_nsuspect' in tbl else ''
		nvictimStr=     tbl['reg_nvictim'] if 'reg_nvictim' in tbl else ''
		nhospitalStr=   tbl['reg_nhospital'] if 'reg_nhospital' in tbl else ''
		weaponStr=    	tbl['reg_weapon'] if 'reg_weapon' in tbl else ''
		calloutStr=    	tbl['reg_callout'] if ('reg_callout' in tbl and tbl['reg_callout'] != 'no') else ''
				
		outLine = '%s,%s,%s,%s,"%s",%s,%d,"%s","%s","%s","%s",%s,%s,%s,%s,"%s","%s"' % \
				(cid,dateStr,timeStr,incNoStr,locateStr,beatStr,gswStr,roStr,pcStr,pcRawStr, \
				lossStr,ncustodyStr,nsuspectStr,nvictimStr,nhospitalStr,weaponStr,calloutStr) 
		outs.write(outLine+'\n')
		nout += 1
	outs.close()
	print('rptLogSumm: NIncid=%d/%d NBadCID=%d' % (len(incidTbl),nout,nbadCID))
	
def compLog2Daily(regTbl,incidTbl):

	nmiss=0
	nbadCID=0
	nfnd=0
	minDate = datetime.date(2017,2,27)
	maxDate = datetime.date(2000,1,1)
	C4A_date_string = '%Y-%m-%d'
	
	for k,tbl in regTbl.items():
		
		if not (cid_pat1.match(k) or cid_pat2.match(k)):
			nbadCID += 1
			continue
		
		# NB: DUPLICATE CID's treated independently
		
		if k.find('_') != -1:
			bpos = k.find('_')
			qryCID = k[:bpos]
		else:
			qryCID = k 
			
		if qryCID not in incidTbl:
			print('%s *' % (qryCID))
			nmiss += 1
			continue
		
		nfnd += 1
		incid = incidTbl[qryCID]
		print('%s\nlog:   %s\nincid: %s\n' % (qryCID,tbl,incid))
		
		(cdate,beat,addr,lat,lng, incidList) = incidTbl[qryCID]
		dateOnly = datetime.date(cdate.year,cdate.month,cdate.day)
		
		if dateOnly < minDate:
			minDate = dateOnly
		if dateOnly > maxDate:
			maxDate = dateOnly
	
	print('compLog2Daily: NMiss=%d NFnd=%d' % (nmiss,nfnd))
	print('Counting incidents between %s - %s ...' % (minDate,maxDate))
	
	nwithin = 0
	for cid in incidTbl.keys():
		(cdate,beat,addr,lat,lng, incidList) = incidTbl[cid]
		dateOnly = datetime.date(cdate.year,cdate.month,cdate.day)
		if dateOnly >= minDate and dateOnly <= maxDate:
			nwithin += 1
	print('compLog2Daily: NWithin=%d' % (nwithin))
	

def json_serial(o):
	'''serialize dates as ISO, all others as strings
	'''
	if isinstance(o, (datetime.datetime, datetime.date)):
		return o.isoformat()
	else:
		return str(o)

## from log2incid

def makeGConnection():
	
	GoogleMapAPIKey = 'AIzaSyDBCmD8wWNkJWo5DmLWu96xReCZbqQRZVk'

	gconn = googlemaps.Client(key=GoogleMapAPIKey)

	return gconn

# def makeMZConnection():
# 
# 	myMZapiKey = 'mapzen-QutHoCK'
# 	
# 	try:
# 		mzServer = MapzenAPI(myMZapiKey)
# 	except Exception as e:
# 		print('makeMZConnection: unable to connect',e)
# 		return None
# 	
# 	return mzServer

def makeMBConnection():

	myMBaccessToken = 'pk.eyJ1IjoicmlrYmVsZXciLCJhIjoiY2pieTZwNnB4MzR5YjMybWtld3FzODFvZyJ9.w0Sqg1pkABegUuQhBTPKwQ';

	try:
		geocoder = mapbox.Geocoder(access_token=myMBaccessToken)

	except Exception as e:
		print('makeMBConnection: unable to connect',e)
		return None
	
	return geocoder

def OBS_addGeoCode1(dlogTbl,mbconn,mzconn,gconn,verbose=None):
	'''create updated dlogTbl with XLng, YLat and GCConf columns
	search against Mapzen first (cheaper!) with problematic addresses sent to Google
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

		# mapbox
		# Use of the Geocoding API is rate-limited by access token?. These limits vary by plan.
		# Pay-as-you-go: 600 requests per minute
				
		try:
			
			# https://www.mapbox.com/api-documentation/?language=Python#response-object
			# The {proximity} parameter biases search results within 5 miles of a
			# specific location given in {longitude},{latitude} coordinates. Results
			# will not be filtered by location or ordered by distance, but location
			# will be considered along with textual relevance and other criteria
			# when scoring and sorting results.

			response = mbconn.forward(loc2, lon=MZDefaultOaklandCoord[0], lat=MZDefaultOaklandCoord[1])
		
		except Exception as e:
			print(('addGeoCode MB: %d %s "%s" "%s" ERROR: %s ' % (i,dlogCID,loc,loc2,e)))
			nMBmiss += 1


		# relevance: A numerical score from 0 (least relevant) to 0.99 (most relevant)
		# measuring how well each returned feature matches the query. You can
		# use the relevance property to remove results which don't fully match
		# the query.

		gj = response.geojson()
		flist = gj['features']
		oakFnd = []
		for f in flist:
			fname = f['place_name']
			if fname.find('Oakland') != -1:
				oakFnd.append(f)
		print(('addGeoCode MB: %d %s "%s" "%s" NOak=%d ' % (i,dlogCID,loc,loc2,len(oakFnd) ) ))
		if len(oakFnd) == 0:
			nMBmiss += 1
		elif len(oakFnd) == 1:
			f = oakFnd[0]
			coord = f['center']
			newdlog['XLng'] = coord[0]
			newdlog['YLat'] = coord[1]
			newdlog['GCConf'] = f['relevance']
			newDLogTbl[dlogCID] = newdlog
			if verbose==1:
				print(('addGeoCode MB: %d %s "%s" "%s" %f %f' % (i,dlogCID,loc,loc2,newdlog['XLng'],newdlog['YLat'])))
		else:
			oakFnd.sort(key=lambda f: f['relevance'], reverse=True)
			for f in oakFnd:
				coord = f['center']
				xlng = coord[0]
				ylat = coord[1]
				rel = f['relevance']
				print('\t%f %f %f %s' % (rel,xlng,ylat,f['place_name']))
				
			print('which?')
				
					
		# mapzen
				
		try:
			geoCodeMZ = MZgeoCode(loc2, mzconn)
			f = geoCodeMZ['features'][0]
			coord = f['geometry']['coordinates']
			GCConf = f['properties']['confidence']

			newdlog['XLng'] = coord[0]
			newdlog['YLat'] = coord[1]
			newdlog['GCConf'] = GCConf
			newDLogTbl[dlogCID] = newdlog
			
		except Exception as e:
			print(('addGeoCode MZ: %d %s "%s" "%s" ERROR: %s ' % (i,dlogCID,loc,loc2,e)))
			newdlog['XLng'] = ''
			newdlog['YLat'] = ''
			newdlog['GCConf'] = ''
			newDLogTbl[dlogCID] = newdlog
			nMZmiss += 1
			
		if coord == MZDefaultOaklandCoord:
			print(('addGeoCode MZ: %d %s "%s" "%s" DEFAULT' % (i,dlogCID,loc,loc2)))
			nMZmiss += 1
		else:
			if verbose==1:
				print(('addGeoCode MZ: %d %s "%s" "%s" %f %f' % (i,dlogCID,loc,loc2,newdlog['XLng'],newdlog['YLat'])))
			nhit += 1
			continue

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

	print('addGeoCode: NDLogIn=%d NMBMiss=%d NMZMiss=%d NGGC=%d NGMiss=%d NHit=%d NLogOut=%d'  % \
			(len(dlogTbl),nMBmiss,nMZmiss,nggc,ngmiss,nhit,len(newDLogTbl)))
	
	return newDLogTbl

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


def filterNewDLogTbl(prevDLog,newIncid):
	# drop any dlog in newIncid that is already in prevDLog
	# NB: prevDLog, newIncid may have cid keys with _%d suffix!
	# 	newIncid cid_foo could match ANY cid_bar in prevDLog!
	
	
	prevCIDSibs = defaultdict(list)
	for pcid in prevDLog.keys():
		if pcid.find('_') != -1:
			cid,suf = pcid.split('_')
			prevCIDSibs[cid] += pcid
	
	newDLog = {}
	allNCID = list(newIncid.keys())
	allNCID.sort()
	
	nnew = 0
	ndup = 0
	for ncid in allNCID:
		if ncid.find('_') != -1:
			bits = ncid.split('_')
			if len(bits) != 2:
				print('filterNewDLogTbl: odd ncid?!',ncid)
				continue
			cid,suf = bits
			
			if cid in prevCIDSibs:
				for i,pcid in enumerate(prevCIDSibs[cid]):
					same,diff = diffDict(newIncid[ncid], prevDLog[pcid])
					print('filterNewDLogTbl: sib match',ncid,cid,i,pcid)
					rptDiff(same,diff)
					# ASSUME match dropped
					ndup += 1
			else:
				# new with cid suffix; no previous matches
				newDLog[ncid] = newIncid[ncid].copy()
				nnew += 1
		elif ncid in prevDLog:
			same,diff = diffDict(newIncid[ncid], prevDLog[ncid])
			print('filterNewDLogTbl: match',ncid)
			rptDiff(same,diff)
			# ASSUME match dropped
			ndup += 1
		else:
			newDLog[ncid] = newIncid[ncid].copy()
			nnew += 1
	
	print('filterNewDLogTbl: NPrev=%d NIn=%d NDup=%d NNew=%d/%d' % \
			(len(prevDLog),len(newIncid),ndup,nnew,len(newDLog)))
			
	return newDLog 

def checkTblOverlap(d1,d2):
	
	redunKeys = set(d1.keys()).intersection(set(d2.keys()))
	if len(redunKeys)>0:
		print('checkTblOverlap: redundant keys?!',len(redunKeys))
		return len(redunKeys)
	else:
		return 0
	
def MZgeoCode(addr,mzconn):

	addr += ', Oakland, CA'

	r = mzconn.search(addr)
	
	return r

if __name__ == '__main__': 

	dataDir = '/Data/c4a-Data/OAK_data/dailyLog/'
	
	## 171027: Re-engineer for regular use
	
	# ASSUME: 
	# maintain previous archive of (regularized, geotagged) DLogs as JSON file
	# process incremental new dlogs
	# produce new, complete archive and NewDLog.json for use by harvestDLog

# 	runDate = '171027'
# 	lastArchiveDate = '171023'
# 	inPDFDir = dataDir + '2017/October 2017/'
# 	verbose = 100
# 	restartSpot = 2

# 	runDate = '171205'
# 	lastArchiveDate = '171027'
# 	inPDFDir = dataDir + '2017/OctNov17/'
# 	verbose = 100
# 	restartSpot = 1

# 	runDate = '171212'
# 	lastArchiveDate = '171205'
# 	inPDFDir = dataDir + '2017/December17_171112/'
# 	verbose = 100
# 	restartSpot = 0

# 	runDate = '171231'
# 	lastArchiveDate = '171212'
# 	inPDFDir = dataDir + '2017/December17_171231/'
# 	verbose = 100
# 	restartSpot = 0

# 	runDate = '180109'
# 	lastArchiveDate = '171231'
# 	inPDFDir = dataDir + '2018/Jan18-180109/'
# 	verbose = 100
# 	restartSpot = 0

# 	runDate = '180117'
# 	lastArchiveDate = '180109'
# 	inPDFDir = dataDir + '2018/Jan18-180117/'
# 	verbose = 1
#	restartSpot = 1

# 	runDate = '180131'
# 	lastArchiveDate = '180117'
# 	inPDFDir = dataDir + '2018/Jan18-180131/'
# 	verbose = 1
# 	restartSpot = 0

# 	runDate = '180314'
# 	lastArchiveDate = '180131'
# 	inPDFDir = dataDir + '2018/JanFebMar18_180314/'
# 	verbose = 1
# 	restartSpot = 0
	
# 	runDate = '180412'
# 	lastArchiveDate = '180314'
# 	inPDFDir = dataDir + '2018/MarApr18_180412/'
# 	verbose = 1
# 	restartSpot = 0

# 	runDate = '180518'
# 	lastArchiveDate = '180412'
# 	inPDFDir = dataDir + '2018/AprMay_180518/'
# 	verbose = 1
# 	restartSpot = 0

# 	runDate = '180702'
# 	lastArchiveDate = '180518'
# 	inPDFDir = dataDir + '2018/MayJun_180702/'
# 	verbose = 1
# 	restartSpot = 0

# 	runDate = '180915'
# 	lastArchiveDate = '180702'
# 	inPDFDir = dataDir + '/harvest/'
# 	verbose = 1
# 	restartSpot = 0

	runDate = '181113'
	lastArchiveDate = '180915'
	inPDFDir = dataDir + '/harvest/'
	verbose = 1
	restartSpot = 0
	
	prevDLogArchive = dataDir + ('incidTblArchive_%s.json' % lastArchiveDate)
	
	prevDLog = json.load(open(prevDLogArchive))
	print('%s Previous archive loaded. NCID=%d' % (runDate,len(prevDLog)))
	
	if restartSpot < 1:
		inLog = collectAllDailyLogs(inPDFDir)

		print('%s Directory Data loaded. NDay=%d %s' % (runDate,len(inLog), inPDFDir))
		cPickle.dump(inLog, open(dataDir+('logData_%s.pkl' % (runDate)),'wb'))
	else:
		inLog = cPickle.load(open(dataDir+('logData_%s.pkl' % (runDate)),'rb'))
		print('%s PKL loaded. NDay=%d %s' % (runDate,len(inLog), inPDFDir))
		
	inIncid = mergeDailyLogs(inLog)
	
	newIncid = filterNewDLogTbl(prevDLog,inIncid)
	
	newRegIncid = regularizeIncidTbl(newIncid)
	
	# mzconn = makeMZConnection()
	mbconn = makeMBConnection()
	gconn = makeGConnection()
	
	# newGeoIncid = addGeoCode1(newRegIncid, mbconn, mzconn, gconn, verbose)
	# 180131: use only google's geotagger
	
	newGeoIncid = addGeoCode2(newRegIncid, gconn, verbose)
	
	# gcDLogPkl = dataDir + 'logSummGeoCode_%s.pkl' % (runDate)
	# cPickle.dump(newGeoIncid, open(gcDLogPkl,'wb'))
	
	outs = open((dataDir + 'newIncidTbl_%s.json' % (runDate)),'w')
	json.dump(newGeoIncid,outs,default=json_serial)
	outs.close()
		
	rc = checkTblOverlap(prevDLog,newGeoIncid)
	assert rc == 0
	
	prevDLog.update(newGeoIncid)

	outs = open((dataDir + 'incidTblArchive_%s.json' % (runDate)),'w')
	json.dump(prevDLog,outs,default=json_serial)
	outs.close()
	
