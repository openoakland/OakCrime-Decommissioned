# opdata: utilities marshalling Oakland Police data
# @author rik@electronicArtifacts.com 
# @organization OpenOakland.org
# @version 0.1
# @date 161115

import json
import os
import sqlite3 as sqlite
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta

from dateutil.relativedelta import *

import crimeCat
from opdConstant import *
from opdUtil import *


def bld_OPDCrimeTypeTbl():
	opd_file = DataDir+'OPD_crime.csv'
	csvReader = csv.reader(open(opd_file))
	ctypeTbl = {}
	for ri,row in enumerate(csvReader):
		(ctypeAbbr,dateStr,cid,ctype,beat,addr) = row
		if ctype in ctypeTbl:
			ctypeTbl[ctype] += 1
		else:
			ctypeTbl[ctype] = 1
			
	ctypeHist = freqHist(ctypeTbl)
	print '\n# CrimeTypes'
	print 'CType,Freq'
	ndrop = 0
	cummDropped = 0
	for ctype,freq in ctypeHist:
		if freq < MinFreq:
			ndrop += 1
			cummDropped += freq
		else:
			print '"%s",%d' % (ctype,freq)
	print '\n# CTypes dropped = %d Cumm=%d' % (ndrop,cummDropped)
	
	ctKeys = ctypeTbl.keys()
	ctKeys.sort()
	OPD_CrimeTypeFile = DataDir + 'OPD_crimeTypes.csv'
	print ''
	outs = open(OPD_CrimeTypeFile,'w')
	print >> outs, 'Idx,CType,Freq,Features'
	idx = 0
	for ct in ctKeys:
		idx += 1
		idxStr = 'OPD_CT_%03d' % (idx)
		if ct=='':
			print 'bld_OPDCrimeTypeTbl:  Empty string = %s' % (idxStr)
		features = []
		for cat in CrimeLexTbl.keys():
			for clex in CrimeLexTbl[cat]:
				if ct.find(clex) != -1:
					features.append(cat)
					break
		featureStr = str(features)
		print >> outs, '%s,"%s",%d,"%s"' % (idxStr,ct,ctypeTbl[ct],featureStr)
	outs.close()
	print 'bld_OPDCrimeTypeTbl: done. NCrimeTypes=%d' % (len(ctKeys))

def rptYearDist(matchTbl,lbl,restrictDates=True):
	'''report year (both incid# prefix and date) distribution and other key stats
		break down incidents by source; uses cdate.yr
	'''
	
	yrTbl=defaultdict(int)
	cidYrTbl = defaultdict(int)
	incidTbl = defaultdict( lambda: defaultdict( int )) # yr -> src -> nincid
	allSrc = defaultdict(int)
	
	nbadCID=0
	nincid=0
	ngeo=0
	for cid,info in matchTbl.items():
		if cid.find('-')==-1:
			nbadCID += 1
			continue
		hpos = cid.find('-')
		cidYrS = cid[:hpos]
		
		try:
			# HACK: no useful data prior to Y2K
			cidYr = int('20'+cidYrS)
		except:
			print 'rptYearDist: %s bad CID?! %s %s' % (lbl,cid,info)
			nbadCID += 1
			continue
		
		cidYrTbl[cidYr] += 1
		
		(cdate,beat,addr,lat,lng, prevList) = info
		if lat != '':
			ngeo += 1
		yr = cdate.year
		yrTbl[yr] += 1

		nincid += len(prevList)
		for incid in prevList:
			src = incid[0]
			incidTbl[yr][src] += 1
			allSrc[src] +=1 

	cidYrKeys = set(cidYrTbl.keys())
	yrKeys = set(yrTbl.keys())
	allKeysSet = cidYrKeys.union(yrKeys)
	allKeys = list(allKeysSet)
	allKeys.sort()
	allSrcNames = allSrc.keys()
	allSrcNames.sort()
	
	noutDate = 0
	ndefDate = 0

	print '## Year Distribution: %s' % (lbl)
	outs = 'Year,CID,Date'
	for src in allSrcNames:
		outs += ',%s' % src
	print outs
	outs = 'TOT, ,YR'
	for src in allSrcNames:
		outs += ',%d' % allSrc[src]
	print outs
	
	for yr in allKeys:
		if yr==DefaultYear:
			ndefDate += 1
			continue
		elif restrictDates and (yr < MinYear or yr > MaxYear):
			noutDate += 1
			continue
		
		if yr in yrTbl:
			dyr = yrTbl[yr]
		else:
			dyr = 0
		if yr in cidYrTbl:
			cyr = cidYrTbl[yr]
		else:
			cyr = 0
		
		outs = '%s,%d,%d' % (yr,cyr,dyr)
		for src in allSrcNames:
			if src not in incidTbl[yr]:
				outs += ', '
			else:
				outs += ',%d' % incidTbl[yr][src]
		print outs
	print '## NCID=%d NIncid=%d NGeo=%d NBadCID=%d' % (len(matchTbl),nincid,ngeo,nbadCID)
	print '## NDefDate=%d NOutDate=%d' % (ndefDate,noutDate)
	return len(matchTbl),nincid

def rptWeekDist(matchTbl,lbl,bdate,edate):
	'report weekly distribution for [bdate, edate) '
	
	def bldWIdx(cdate):	
		'convert date to week index relative to edate'
		td = cdate - bdate
		wkIdx = td.days / 7
		return wkIdx
	
	td = edate - bdate
	ndays = td.days
	
	wkTbl= {}
	wkLbls = []
	nprevCID=0
	nfutureCID=0
	nbaddate=0
	
	for d in range(0,ndays,7):
		wbeg = bdate + timedelta(days=d)
		widx = bldWIdx(wbeg)
		wkTbl[widx] = 0
		wlbl = wbeg.strftime('%y%m%d')
		wkLbls.append(wlbl)
		
	for cid,info in matchTbl.items():
		
		(cdatetime,beat,addr,lat,lng, prevList) = info
		cdate = cdatetime.date()
		
		if cdate < bdate:
			nprevCID += 1
			continue

		# NB: edate's data dropped, to avoid only it being considered its own week!
		if cdate >= edate:
			nfutureCID += 1
			continue
		
		wkIdx = bldWIdx(cdate)
		if wkIdx not in wkTbl:
			nbaddate += 1
			continue
		
		wkTbl[wkIdx] += 1

	allKeys = wkTbl.keys()
	allKeys.sort()
	print '## Weekly Distribution: %s' % (lbl)
	print '## NCID=%d NBadDate=%d' % (len(matchTbl),nbaddate)

	print '# WeekBegin,NCID'
	print 'Earlier',nprevCID
	for wk in allKeys:
		print '%s,%d' % (wkLbls[wk],wkTbl[wk])
	print 'Later',nfutureCID

def mrgIncident(i1,i2):
	'''first incident dominates; 
		if i2 contains new info, return combined version with src = "src1+src2"
		otherwise returns None
	'''
	[src1, ctype1, desc1, ucr1, stat1, cc1] = i1
	[src2, ctype2, desc2, ucr2, stat2, cc2] = i2
	
	mod1 = False
	if ctype2 != '' and ctype1 == '':
		mod1 = True
		ctype = ctype2
	else:
		ctype = ctype1
	if desc2 != '' and desc1 == '':
		mod1 = True
		desc = desc2
	else:
		desc = desc1
	if ucr2 != '' and ucr1 == '':
		mod1 = True
		ucr = ucr2
	else:
		ucr = ucr1
	if stat2 != '' and stat1 == '':
		mod1 = True
		stat = stat2
	else:
		stat = stat1
	if cc2 != '' and cc1 == '':
		mod1 = True
		cc = cc2
	else:
		cc = cc1
	
	if mod1:
		if not src1.endswith(src2):
			src = src1+'+'+src2
		else:
			src = src1
		return 	[src, ctype, desc, ucr, stat, cc]
	else:
		return None
	
def loadAddrTbl(addrFile):
	'''return addr -> {src, lat, lng, zip, normAddr}
		as saved by saveAddrTbl
	'''

	print 'loadAddrTbl: reading from',addrFile
	addrTbl = defaultdict(list)
	csvDictReader = csv.DictReader(open(addrFile,"r"))
	for entry in csvDictReader:
		# Addr,Lat,Lng,Zip,NormAddr

		infoTbl = {}
		origAddr = entry['Addr']
		
		addr = cleanAddr(origAddr)
		if addr == '':
			continue

		infoTbl['lat'] = float(entry['Lat'])
		infoTbl['lng'] = float(entry['Lng'])
		infoTbl['zip'] = entry['Zip']
		infoTbl['normAddr'] = entry['NormAddr']
			
		addrTbl[addr] = infoTbl
		
	print 'loadAddrTbl: NAddr=%d' % (len(addrTbl))
	return addrTbl

def saveAddrTbl(addrTbl,outf):
	
	outs = open(outf,'w')
	outs.write('Addr,Lat,Lng,Zip,NormAddr\n')
	allAddr = addrTbl.keys()
	allAddr.sort()
	for addr in allAddr:
		if addr == '':
			continue
		info = addrTbl[addr]
		try:
			outs.write('"%s",%s,%s,%s,"%s"\n' % (addr,info['lat'],info['lng'],info['zip'],info['normAddr'] ))
		except:
			print 'huh?'
	outs.close()
	print 'saveAddrTbl: %d addresses saved to %s' % (len(allAddr),outf)
	
def loadCType2stat(c2sfile):
	'''return ct2statTbl: ctype -> (maxStat,freq,prob) most likely statutes'''

	print 'loadCType2stat: reading from',c2sfile
	ct2statTbl = {}
	csvDictReader = csv.DictReader(open(c2sfile,"r"))
	for entry in csvDictReader:
		# CType,Statute,Freq,Prob
		ct2statTbl[entry['CType']] = (entry['Statute'],entry['Freq'],entry['Prob'])
	print 'loadCType2stat: NCType=%d' % (len(ct2statTbl))
	return ct2statTbl
	
def loadStat2UCR(s2ufile):
	'''stat2ucrTbl stat -> (maxUcr,freq,prob) most likely UCR'''

	print 'loadStat2UCR: reading from',s2ufile
	stat2ucrTbl = {}
	csvDictReader = csv.DictReader(open(s2ufile,"r"))
	for entry in csvDictReader:
		# Statute,UCR,Freq,Prob
		stat2ucrTbl[entry['Statute']] = (entry['UCR'],entry['Freq'],entry['Prob'])
	print 'loadStat2UCR: NStatute=%d' % (len(stat2ucrTbl))
	return stat2ucrTbl

def matchTbl2csv(matchTbl,outf,addrTbl,startIdx=0):
	'''comma separated, QUOTE_NONNUMERIC, with attribute header line
		splitting date timestamp into DATE, TIME '''
		
	
	cidList = matchTbl.keys()
	cidList.sort()
	
	outs = open(outf,'w')
	outAttrib = 'Idx,OPD_RD,OIdx,Date,Time,CType,Desc,Beat,Addr,Lat,Lng,Src,UCR,Statute,CrimeCat'.split(',')
	csvw = csv.writer(outs, delimiter=',', quoting=csv.QUOTE_NONNUMERIC)
	csvw.writerow(outAttrib)
	
	idx = startIdx
	ngeoMod = 0
	nambigCC = 0
	noutDate = 0
	
	for cnum,cid in enumerate(cidList):
		(cdate,beat,addr,lat,lng, incidList) = matchTbl[cid]
		
		if cdate.year<MinYear or cdate.year>MaxYear:
			noutDate += 1
			continue
		
		#  dateStr = cdate.strftime(C4A_date_string)
		dateOnly = cdate.strftime(C4A_date_string)
		timeOnly = cdate.strftime(C4A_time_string)
		
		addr = addr.strip()
		if addr == '' or addr== 'UNKNOWN' or addr== 'UNK' or addr=="Oakland, CA":
			addr = ''
			lat = ''
			lng = ''
		if addr in addrTbl:
			info = addrTbl[addr]
			# NB: previous lat,long always clobbered by whatever is in addrTbl
			lat = info['lat']
			lng = info['lng']
		else:
			lat = ''
			lng = ''
				
		for nocc,oinfo in enumerate(incidList):
			# 2do: HACK!  'early' matchTbl incidents do not have CC, later they do (:
			(src,ctype,desc,ucr,statute,cc) = oinfo
			
			outFlds = (idx,cid,nocc+1,dateOnly,timeOnly,ctype,desc,beat,addr,lat,lng,src,ucr,statute,cc)
			csvw.writerow(outFlds)
			idx += 1


	outs.close()
	print 'done. NOutDate=%d NLines=%d NAmbigCC=%d'% (noutDate,idx,nambigCC)	
	print 'matchTbl2csv: NOutDate=%d  NAmbigCC=%d dumping NCID=%d NIncid=%d to %s...' % \
		(noutDate,nambigCC,len(matchTbl),idx,outf)

def matchTbl2json(matchTbl,outf,addrTbl):
	'''produce json version of matchTbl: cid - > [dateOnly,timeOnly,beat,addr,lat,long, [ctype,desc,ucr,statute,cc]+ ]'''
		
	cidList = matchTbl.keys()
	cidList.sort()
	
	idx = 0
	ngeoMod = 0
	nambigCC = 0
	
	outTbl = {}
	noutDate = 0

	for cnum,cid in enumerate(cidList):
		(cdate,beat,addr,lat,lng, incidList) = matchTbl[cid]
				
		#  dateStr = cdate.strftime(C4A_date_string)
		dateOnly = cdate.strftime(C4A_date_string)
		timeOnly = cdate.strftime(C4A_time_string)
		
		addr = addr.strip()
		if addr == '' or addr== 'UNKNOWN' or addr== 'UNK' or addr=="Oakland, CA":
			addr = ''
		addr = cleanAddr(addr)
		if addr in addrTbl:
			info = addrTbl[addr]
			# NB: previous lat,long always clobbered by whatever is in addrTbl
			lat = info['lat']
			lng = info['lng']
		else:
			lat = ''
			lng = ''
						
		outInfo = [dateOnly,timeOnly,beat,addr,lat,lng, []]
		newIList = []
		for nocc,oinfo in enumerate(incidList):
			# 2do: HACK!  'early' matchTbl incidents do not have CC, later they do (:
			# assert len(oinfo) == 6,  'matchTbl2json: bad oinfo %s %s %s' % (cid, nocc, oinfo)
			# src,ctype,desc,ucr,statute,cc = oinfo
			
# 			global NMissCC
# 			if oinfo[5] == '':
# 				MCCS.write('%s,%s,"%s","%s","%s","%s",%s\n' % tuple([cid]+list(oinfo)))
# 				MCCS.flush()
# 				NMissCC += 1
				
			newIList.append( oinfo )						
		idx += len(newIList)
		outInfo[-1] = newIList
		outTbl[cid] = outInfo
	
	print 'matchTbl2json: NOutDate=%d dumping NCID=%d NIncid=%d to %s...' % \
		(noutDate,len(outTbl),idx,outf)
	json.dump(outTbl,open(outf,'w'))
	print 'done.'

def matchTbl2jsonMonths(matchTbl,outDir):
	'''partition matchTbl by month_year'''
		
	cidList = matchTbl.keys()
	
	outTbl = {} # (year,month) -> cid -> allInfo
	noutDate = 0
	ndateMismatch = defaultdict(int)
	nNearDate = defaultdict(int)
	ngeo = defaultdict(int)
	nincid = defaultdict(int)
	
	for cnum,cid in enumerate(cidList):
		cinfo = matchTbl[cid]
		(cdate,beat,addr,lat,lng, incidList) = cinfo
		
		if cdate.year<MinYear or cdate.year>MaxYear:
			noutDate += 1
			continue
		
		dateOnly = cdate.strftime(C4A_date_string)
		timeOnly = cdate.strftime(C4A_time_string)
		outInfo = [dateOnly,timeOnly,beat,addr,lat,lng, incidList]
		
		k = (cdate.year,cdate.month)
		if not goodCIDDate(cid,cdate.year):
			if goodCIDDate(cid,cdate.year,tolerant=True):
				nNearDate[k] += 1
			else:
				ndateMismatch[k] += 1
				continue
		
		if lat != '':
			ngeo[k] += 1
			
		nincid[k] += len(incidList)
			
		if k in outTbl and cid in outTbl[k]:
			print 'matchTbl2jsonMonths: dup CID?! %s %s; "%s"->"%s' % \
				(k,cid,outTbl[k][cid],outInfo)
				
		if k in outTbl:
			outTbl[k][cid] = outInfo
		else:
			outTbl[k] = {cid:  outInfo}
			
	allMonths = outTbl.keys()
	allMonths.sort()
	
	print 'Year,Month,NCID,NIncid,NGeo,NNearDate,NBadDate'
	for k in allMonths:
		if k in nNearDate:
			nnear = nNearDate[k]
		else:
			nnear = 0
		if k in ndateMismatch:
			nbad = ndateMismatch[k]
		else:
			nbad = 0
		if k in ngeo:
			ng = ngeo[k]
		else:
			ng = 0
		if k in nincid:
			ni = nincid[k]
		else:
			ni = 0
			
		yr,mo = k
		outf = outDir+'OPD_%04d_%02d.json' % (yr,mo)
		json.dump(outTbl[k],open(outf,'w'))
		print '%s,%d,%d,%d,%d,%d,%d' % (k[0],k[1],len(outTbl[k]),ni,ng,nnear,nbad)

def matchTbl2FullJsonBeats(matchTbl,addrTbl,outDir,begYear=None):
	'''json (with attribute labels!) of matchTbl partitioned by beat: 
		cid - > [dateOnly,timeOnly,beat,addr,lat,long, [src,ctype,desc,ucr,statute,cc]+ ]'''
		
	cidList = matchTbl.keys()
	cidList.sort()
	
	outTbl = {} # beat -> cid -> allInfo
	noutDate = 0
	idx=0
	
	for cnum,cid in enumerate(cidList):
		(cdate,beat,addr,lat,lng, incidList) = matchTbl[cid]
		
		if cdate.year<MinYear or cdate.year>MaxYear:
			noutDate += 1
			continue
		
		if begYear and cdate.year < begYear:
			continue
		
		#  dateStr = cdate.strftime(C4A_date_string)
		dateOnly = cdate.strftime(C4A_date_string)
		timeOnly = cdate.strftime(C4A_time_string)
		
		if addr == '' or addr== 'UNKNOWN' or addr== 'UNK' or addr=="Oakland, CA":
			addr = ''
			lat = ''
			lng = ''
		elif addr in addrTbl:			
			info = addrTbl[addr]
			lat = info['lat']
			lng = info['lng']
						
		jsonDict = {'dateOnly': dateOnly,
					'timeOnly': timeOnly,
					'beat': beat,
					'addr': addr,
					'lat': lat,
					'lng': lng}
		
		jsonDict['incidList'] = []
		
		for oinfo in incidList:
			(src,ctype,desc,ucr,statute,cc) = oinfo
			iDict = {'src': src,
					'ctype': ctype,
					'desc': desc,
					'ucr': ucr,
					'statute': statute,
					'cc': cc}
			jsonDict['incidList'].append(iDict)						

		
		idx += len(incidList)
		
		if beat in outTbl:
			outTbl[beat][cid] = jsonDict
		else:
			outTbl[beat] = {cid: jsonDict}
		
	print 'matchTbl2jsonBeats: NOutDate=%d dumping NBeat=%d NCID=%d NIncid=%d to %s...' % \
		(noutDate,len(outTbl),len(matchTbl),idx,outDir)
	
	print 'Beat,NCID,NIncid,Drop?'
	totDrop=0
	for beat in outTbl.keys():
		idx=0
		for cid,info in outTbl[beat].items():
			nincid = len(info['incidList'])
			idx += nincid
		if beat in GoodBeats:
			print '%s,%d,%d' % (beat,len(outTbl[beat]),idx)
			outf = outDir+('%s.json' % (beat))
				
			json.dump(outTbl[beat],open(outf,'w'))
		else:
			print '%s,%d,%d,drop' % (beat,len(outTbl[beat]),idx)
			totDrop += len(outTbl[beat])
	print '\nTotDrop,,%d' % (totDrop)

def json2matchTbl(inf):
	'''rebuild from json matchTbl: cid - > [dateOnly,timeOnly,beat,addr,lat,long,cc, [ctype,desc,ucr,statute,cc]+ ]
		to original	  matchTbl: cid - > (cdate,beat,addr,lat,long, incidList)
		NB: differences from json: date+time reunited
			differences from 'raw' initial matchTbl: info is in tuple, cc in incidList, len(incidList)>0'''
			
	print 'json2matchTbl: Loading %s...' % (inf),
	
	idx = 0	
	inTbl = json.load(open(inf,'r'))
		
	outTbl = {}
	
	for cid, info in inTbl.items():
		[dateOnly,timeOnly,beat,addr,lat,lng,incidList] = info
		
		# 2do: UGH!  dateTime formatting slippage
		# C4A_dateTime_string = '%y%m%d_%H:%M:%S'
		# C4A_date_string = '%Y-%m-%d'
		# C4A_time_string = '%H:%M:%S'
		# patched via
		# C4A_dateTime_string2 = C4A_date_string+'_'+C4A_time_string
		
		dateTimeStr = dateOnly+'_'+timeOnly
		cdate = datetime.strptime(dateTimeStr,C4A_dateTime_string2)
		idx += len(incidList)
		outTbl[cid] = (cdate,beat,addr,lat,lng, incidList)
		
	print 'json2matchTbl: Loaded NCID=%d NIncid=%d' % (len(outTbl),idx)
	return outTbl
			
def matchTbl2db(matchTbl,newdb,addrTbl,initDB=True):
	'''v4: including OPD CTYpe, Desc; adding crimeCat.classCrime
		   write to new dbfile'''
		
	# crimeCat.bldClassTbls(crimeCat.newCatFile)
	
	newDB = sqlite.connect(newdb)
	newcur = newDB.cursor()
	# NB:  COMBINED should not exist in this fresh database
	if initDB:
		newcur.execute('DROP TABLE IF EXISTS INCIDENT')
		newcur.execute('DROP TABLE IF EXISTS CHARGE')
		incidtblCmd = '''CREATE TABLE INCIDENT
					   (incididx int, rd text, date text, beat text, addr text, lat real, lng real)'''
		newcur.execute(incidtblCmd)
		chgtblCmd = '''CREATE TABLE CHARGE
					   (chgidx int, rd text, rdchgidx int, src text, ctype text, desc text, ucr text, statute text, crimeCat text)'''
		newcur.execute(chgtblCmd)

	cidList = matchTbl.keys()
	cidList.sort()
	
	print 'matchTbl2db: Writing CASE, CHARGE tables to database in %s...' % (newdb)
	idx = 0
	ngeoMod = 0
	noutDate = 0
	nambigCC=0
	idx2=0
	for cnum,cid in enumerate(cidList):

		(cdate,beat,addr,lat,lng, incidList) = matchTbl[cid]
		
		if cdate.year<MinYear or cdate.year>MaxYear:
			noutDate += 1
			continue
		
		dateTimeStr = cdate.strftime(C4A_dateTime_string)
		
		addr = addr.strip()
		if addr == '' or addr== 'UNKNOWN' or addr== 'UNK' or addr=="Oakland, CA":
			addr = ''
			lat = ''
			lng = ''
			
		if addr in addrTbl:
			info = addrTbl[addr]
			# NB: previous lat,long always clobbered by whatever is in addrTbl
			lat = info['lat']
			lng = info['lng']
		else:
			lat = ''
			lng = ''

		newcur.execute('insert into INCIDENT (incididx, rd, date, beat, addr, lat, lng)'+
					'values (:idx, :cid, :dateTimeStr, :beat, :addr, :lat, :lng)', locals())
		idx += 1		
						
		for nocc,oinfo in enumerate(incidList):
			# 2do: HACK!  'early' matchTbl incidents do not have CC, later they do (:
			(src,ctype,desc,ucr,statute,cc) = oinfo								
				
			newcur.execute('insert into CHARGE(chgidx, rd, rdchgidx, src, ctype, desc, ucr, statute, crimeCat)'+
						'values (:idx2, :cid, :nocc+1, :src, :ctype, :desc, :ucr, :statute, :cc)', locals())		
			idx2 += 1
	newDB.commit()
	print 'done. NOutDate=%d NIncid=%d NCharge=%d NAmbigCC=%d'% (noutDate,idx,idx2,nambigCC)	
	
def anal_OPD_CTypeDesc(inf):
	"analyze interaction between OPD's CRIMETYPE and DESCRIPTION fields"

	print 'anal_OPD_CTypeDesc: reading from',inf
	csvReader = csv.reader(open(inf, "r"))

	ctTbl = {}
	dTbl = {}
	ctdTbl = {}
	dctTbl = {}
	for ri,row in enumerate(csvReader):
		# OPD
		# "OTHER",2010-09-28 00:00:00,"01-053413","GRAND THEFT","",""
		# "MISDEMEANOR WARRANT",2007-03-01 10:40:00,"03-025334","MISDEMEANOR BENCH WARRANT - LOCAL","99X","O/S"
		
		if ri % 50000 == 0:
			print 'anal_OPD_CTypeDesc',ri
			
		(crimeType,dateStr,cid,desc,beat,addr) = row
		
		ct = crimeType.upper().strip()
		d = desc.upper().strip()
		ctd = ct+'_'+d
		dct = d+'_'+ct
		if ct in ctTbl:
			ctTbl[ct] += 1
		else:
			ctTbl[ct] = 1
			
		if d in dTbl:
			dTbl[d] += 1
		else:
			dTbl[d] = 1
			
		if ctd in ctdTbl:
			ctdTbl[ctd] += 1
		else:
			ctdTbl[ctd] = 1
			
		if dct in dctTbl:
			dctTbl[dct] += 1
		else:
			dctTbl[dct] = 1
		
	minFreq = 10	
	ctHist = freqHist(ctTbl)
	print '\n# CType'
	print 'CType,Freq'
	ndrop = 0
	cummDropped = 0
	for ctype,freq in ctHist:
		if freq < minFreq:
			ndrop += 1
			cummDropped += freq
		else:
			print '"%s",%d' % (ctype,freq)
	print '\n# CTypes dropped = %d Cumm=%d' % (ndrop,cummDropped)

	dHist = freqHist(dTbl)
	print '\n# Desc'
	print 'Desc,Freq'
	ndrop = 0
	cummDropped = 0
	for ctype,freq in dHist:
		if freq < minFreq:
			ndrop += 1
			cummDropped += freq
		else:
			print '"%s",%d' % (ctype,freq)
	print '\n# Desc dropped = %d Cumm=%d' % (ndrop,cummDropped)

	ctdHist = freqHist(ctdTbl)
	print '\n# CType_Desc'
	print 'CType_DescType,Freq'
	ndrop = 0
	cummDropped = 0
	for ctype,freq in ctdHist:
		if freq < minFreq:
			ndrop += 1
			cummDropped += freq
		else:
			print '"%s",%d' % (ctype,freq)
	print '\n# CTypes_Desc dropped = %d Cumm=%d' % (ndrop,cummDropped)
	
	dctHist = freqHist(dctTbl)
	print '\n# Desc_CType'
	print 'Desc_CType,Freq'
	ndrop = 0
	cummDropped = 0
	for ctype,freq in dctHist:
		if freq < minFreq:
			ndrop += 1
			cummDropped += freq
		else:
			print '"%s",%d' % (ctype,freq)
	print '\n# Desc_CType dropped = %d Cumm=%d' % (ndrop,cummDropped)
	
def tallyHierOak(csvFile,catPrefix):
	'return annual counts for incidents sharing catPrefix'
	
	print 'tallyHierOak: loading CrimeCat from %s ...' % (csvFile)
	csvDictReader = csv.DictReader(open(csvFile))
	catTbl = {} # catLbl -> {nstat:1}
	plen = len(catPrefix)
	# Cat,Stats
	for ri,entry in enumerate(csvDictReader):
		cat = entry['Cat']
		# "OPD_LARCENY_BURGLARY_FORCIBLE-ENTRY"
		
		if cat.startswith(catPrefix):
			if cat == catPrefix:
				rem = 'TOP'
			else:
				rem = cat[plen+1:]  # past _
				if '_' in rem:
					upos = rem.index('_')
					rem = rem[:upos]
					
			if rem not in catTbl:
				catTbl[rem] = {}
					
			statList = eval(entry['Stats'])
			for stat in statList:
				catTbl[rem][stat] = 1
			
	cntTbl = {}
	for cat in catTbl.keys():
		cntTbl[cat] = [0 for y in range(MinYear,MaxYear+1)]

	print 'tallyHierOak: loading crime data from %s ...' % (csvFile)
	csvDictReader = csv.DictReader(open(csvFile),delimiter='\t')
	# Idx,OPD_RD,OIdx,Date,CType,Beat,Addr,Lat,Long,UCR,Statute
	for ri,entry in enumerate(csvDictReader):
			
		stat = entry['Statute']
		if stat=='':
			continue
		dateStr = entry['Date']
		cdate = datetime.strptime( dateStr, C4A_date_string)
		cyr = cdate.year
		if cyr < MinYear or cyr > MaxYear:
			continue
		yrIdx = cyr-MinYear
		nstat = crimeCat.normStat(stat)
		
		# 2do: replace exhaustive search with stat2cat dict!
		for cat in catTbl.keys():
			if nstat in catTbl[cat]:
				cntTbl[cat][yrIdx] += 1
				
	return cntTbl

def tallyAllCrimeCat(csvFile,propLeafCnt=True):
	'return annual counts for all categories in catList'
	
	allCat = crimeCat.bldCrimeCatList(CurrCatFile)
			
	cntTbl = {}
	for cat in allCat:
		cntTbl[cat] = [0 for y in range(MinYear,MaxYear+1)]

	nnocc = 0
	ndropDate = 0
	print 'tallyAllCrimeCat: loading crime data from %s ...' % (csvFile)
	csvReader = csv.reader(open(csvFile),delimiter='\t')
	ctypeTbl = {}
	for ri,row in enumerate(csvReader):
		(Idx,OPD_RD,OIdx,Date,Time,CType,Desc,Beat,Addr,Lat,Lng,UCR,Statute,CrimeCat) = row
		if CrimeCat=='':
			nnocc += 1
			continue
		cdate = datetime.strptime( Date, C4A_date_string)
		cyr = cdate.year
		if cyr < MinYear or cyr > MaxYear:
			ndropDate += 1
			continue
		yrIdx = cyr-MinYear
		cntTbl[CrimeCat][yrIdx] += 1
	
	print 'tallyAllCrimeCat: NNoCrimeCat=%d NDropDate=%d' % (nnocc,ndropDate)
		
	if not propLeafCnt:
		return cntTbl
	
	# propogate leaf counts to inclusive parents
	for fullCat in allCat:
		totCnt = sum( [cntTbl[fullCat][y-MinYear] for y in range(MinYear,MaxYear+1)] )
		if totCnt == 0:
			continue
		prefix = ''
		path = fullCat.split('_')
		path = path[:-1] # don't need to propagate count to leaf itself
		while len(path)>0:
			cat = path.pop(0)  # treat as queue
			if prefix != '':
				prefix += '_'
			prefix = prefix+cat
			for y in range(MinYear,MaxYear+1):
				yrIdx = y-MinYear
				leafCnt = cntTbl[fullCat][yrIdx]
				cntTbl[prefix][yrIdx] += leafCnt			
				
	return cntTbl

def ppCrimeCatTally(cntTbl,outf):
	
	outs = open(outf,'w')
	outs.write('CrimeCat')
	for y in range(MinYear,MaxYear+1):
		outs.write(',%d' % y)
	outs.write('\n')
	allCat = cntTbl.keys()
	allCat.sort()
	for cat in allCat:
		outs.write(cat)
		for y in range(MinYear,MaxYear+1):
			outs.write(',%d' % cntTbl[cat][y-MinYear])
		outs.write('\n')
	outs.close()	
	
def tallyBeatPeriod(matchTbl,beatList,crimeCatFile,sdate,edate):	
	'''build	crimeCummTbl[cat] -> (catTot,avg,sd)
				statTbl: [cat][beat] -> (beatTot,beatAvg,beatSD,
										  periodTot,periodZ,periodRatio,periodAvg,periodSD, 
										  seasonTot,seasonZ,seasonRatio,seasonAvg,seasonSD)
		beat monthly average, sd over entire history
		Period monthly average, sd during focused period bdate-edate 
		Season monthly average, sd considering only same seasonal months in previous years
		motivated by Liu13 Rockridge patrols
	'''
	
	perStartDate = datetime.strptime( sdate+' 00:00', '%y%m%d %H:%M')
	perEndDate = datetime.strptime( edate+' 23:59', '%y%m%d %H:%M')
	# UGG need to bump to next day to get round months!
	oneMinute = timedelta(minutes=1)
	perEndDate = perEndDate + oneMinute
	
	minDate = datetime.strptime( ('%02d' % (MinYear-2000)) +'0101 00:00', '%y%m%d %H:%M')
	# HACK: constrain to Feb'14
	# maxDate = datetime.strptime( ('%02d' % (MaxYear-2000)) +'1231 23:59', '%y%m%d %H:%M')
	
	maxDate = datetime.strptime( CurrDate + ' 00:00', '%y%m%d %H:%M')
	
	# 2do: other date checks possible
	assert (minDate < perStartDate and \
			perStartDate < perEndDate and \
			perEndDate <= maxDate), 'bad dates %s %s %s %s' % ( minDate,perStartDate,perEndDate,maxDate)
	
	allMonths = relativedelta(maxDate,minDate)
	nmonths = 12* allMonths.years + allMonths.months

	def bldMIdx(cdate):	
		'convert date to month index relative to minDate'
		dateDiff = relativedelta(cdate,minDate)
		monthIdx = 12* dateDiff.years + dateDiff.months
		return monthIdx
	
	begPeriodIdx = bldMIdx(perStartDate)
	endPeriodIdx = bldMIdx(perEndDate)
	
	periodMonths = range(begPeriodIdx,endPeriodIdx+1)

	print 'tallyBeatsPeriod: %d months to be evaluated; periodMonths = %d - %d' % (nmonths,begPeriodIdx,endPeriodIdx)
	
	## indicator functions here
	
	def inPeriod(monthIdx):
		'indicator function for designated sdate-edate period'
		
		return monthIdx in periodMonths
			
	def wtrSeason(monthIdx):
		'indicator function for months SHARING SAME "SEASON" as those in sdate-edate period'
		
		# HACK: should compute months from sdate, edate (:
		winterMonths = [11,12,1,2]
		
		monthMod = (monthIdx % 12) + 1
		return monthMod in winterMonths

	# Test dates
# 	for m in range(nmonths+1):
# 		print m,inPeriod(m),inSeason(m)
# 		
# 	testDates = [date(2007,1,1),
# 				date(2013,6,1),
# 				date(2013,12,31),
# 				date(2014,1,1),
# 				date(2014,2,28) ]
# 	
# 	for d in testDates:
# 		midx = bldMIdx(d)
# 		print d,midx,inPeriod(midx),inSeason(midx)

	domCat = {}
	print 'tallyBeatsPeriod: loading CrimeCat from %s ...' % (crimeCatFile)
	csvReader = csv.reader(open(crimeCatFile))
	for ri,row in enumerate(csvReader):
		# Category,CType,Desc
		if ri==0: # skip header
			continue
		dcat = row[0] 
		domCat[dcat] = True
	print 'tallyBeatsPeriod: done. NDomCat=%d' % (len(domCat))

	cntTbl = {}
	noutdate=0
	nnbeat = 0
	nnocc = 0
	ngood = 0
	nambigCC=0
	nnewcc=0
	ctypeTbl = {}
	
	for cid,cinfo in matchTbl.items():
		cdate,beat,addr,lat,lng,incidList = cinfo
		if beat not in beatList:
			nnbeat += 1
			continue
				
		monthIdx = bldMIdx(cdate)	
		
		for iinfo in incidList:
			(src,ctype,desc,ucr,statute,cc) = iinfo

			if cc=='':
				# HACK:  updated CrimeCat - 1 Apr 14
				# should be removed after full dataset rerun
# 				cc2 = crimeCat.classCrime(ctype, desc)
# 				if cc2 != '':
# 					cc = cc2
# 					nnewcc += 1
# 				else:
				nnocc += 1
				continue

			ngood += 1
				
			# demand-driven initialization for leaf count categories
			if cc not in cntTbl:
				cntTbl[cc] = {}
				for b in beatList:
					cntTbl[cc][b] = [0 for m in range(nmonths+1)]			
					
			try:
				cntTbl[cc][beat][monthIdx] += 1
			except Exception,e:
				print 'tallyBeatsPeriod: monIdx out of range?! %s %d %s %s %s %s' % (cid,monthIdx,cdate,cc,beat,e)
		
	print 'tallyBeatsPeriod: NGood=%d NOBeat=%d NNewCC=%d NNoCrimeCat=%d' % (ngood,nnbeat,nnewcc,nnocc)


	# propogate leaf counts to ONLY DOMINANT inclusive parents
	leafKeys = cntTbl.keys()
	for fullCat in leafKeys:
		prefix = ''
		if fullCat.find('_') == -1:
			continue
		path = fullCat.split('_')
		path = path[:-1] # don't need to propagate count to leaf itself
		while len(path)>0:
			cat = path.pop(0)  # treat as queue
			if prefix != '':
				prefix += '_'
			prefix = prefix+cat
			
			if prefix in domCat and prefix not in cntTbl:
				cntTbl[prefix] = {}
				for b in beatList:
					cntTbl[prefix][b] = [0 for m in range(nmonths+1)]				
			
				for b in beatList:
					for m in range(nmonths):
						leafCnt = cntTbl[fullCat][b][m]
						cntTbl[prefix][b][m] += leafCnt	
	
	## Collect stats wrt/ both inPeriod and inSeason predicates
	statTbl = {}
	# allCatTbl: inter/other -> [tot, periodSet, seasonSet]
	allCatTbl = {'inter': [ [0 for m in range(nmonths+1)], {}, {}],
				 'other': [ [0 for m in range(nmonths+1)], {}, {}] }
	
	# keep all, period,season stats aggregated across intervention-beats vs. others
	interBeat = ['12X','12Y']
	# aggTbl: inter/other -> cc -> (setMonths)
	aggTbl = {'inter': {}, 'other': {} }
	
	for cat in domCat:
		if cat not in cntTbl:
			print 'tallyBeatsPeriod: missing dominant category?',cat
			continue
		
		statTbl[cat] = {}
		aggTbl['inter'][cat] = [ [0 for m in range(nmonths+1)], {}, {}]
		aggTbl['other'][cat] = [ [0 for m in range(nmonths+1)], {}, {}]

		for beat in beatList:
			inPeriodList = []
			inSeasonList = []
			allMonth = []
			
			for m in range(nmonths+1):
				thisMonth = cntTbl[cat][beat][m]
				
				if beat in interBeat:
					allCatTbl['inter'][0][m] += thisMonth
				else:
					allCatTbl['other'][0][m] += thisMonth
					
				allMonth.append(thisMonth)
				if beat in interBeat:
					aggTbl['inter'][cat][0][m] += thisMonth
				else:
					aggTbl['other'][cat][0][m] += thisMonth
					
				if inPeriod(m):
					inPeriodList.append(thisMonth)
					if beat in interBeat:
						if m in aggTbl['inter'][cat][1]:
							aggTbl['inter'][cat][1][m] += thisMonth
						else:
							aggTbl['inter'][cat][1][m] = thisMonth
													
						if m in allCatTbl['inter'][1]:
							allCatTbl['inter'][1][m] += thisMonth
						else:
							allCatTbl['inter'][1][m] = thisMonth
						
					else:
						if m in aggTbl['other'][cat][1]:
							aggTbl['other'][cat][1][m] += thisMonth
						else:
							aggTbl['other'][cat][1][m] = thisMonth
							
						if m in allCatTbl['other'][1]:
							allCatTbl['other'][1][m] += thisMonth
						else:
							allCatTbl['other'][1][m] = thisMonth
					
				if wtrSeason(m):
					inSeasonList.append(thisMonth)
					if beat in interBeat:
						if m in aggTbl['inter'][cat][2]:
							aggTbl['inter'][cat][2][m] += thisMonth
						else:
							aggTbl['inter'][cat][2][m] = thisMonth
							
						if m in allCatTbl['inter'][2]:
							allCatTbl['inter'][2][m] += thisMonth
						else:
							allCatTbl['inter'][2][m] = thisMonth
					else:
						if m in aggTbl['other'][cat][2]:
							aggTbl['other'][cat][2][m] += thisMonth
						else:
							aggTbl['other'][cat][2][m] = thisMonth

						if m in allCatTbl['other'][2]:
							allCatTbl['other'][2][m] += thisMonth
						else:
							allCatTbl['other'][2][m] = thisMonth
			
			beatTot = sum( allMonth )
			beatAvg,beatSD = basicStats(allMonth)
		
			periodTot = sum( inPeriodList )
			periodAvg,periodSD = basicStats(inPeriodList)
			if beatAvg==0.:
				periodRatio = 0.
			else:
				periodRatio = periodAvg / beatAvg
			if beatSD==0.:
				periodZ = 0.
			else:
				periodZ = float((periodAvg - beatAvg) / beatSD)

			seasonTot = sum( inSeasonList )
			seasonAvg,seasonSD = basicStats(inSeasonList)				
			if beatAvg==0.:
				seasonRatio = 0.
			else:
				seasonRatio = seasonAvg / beatAvg
			if beatSD==0.:
				seasonZ = 0.
			else:
				seasonZ = float((seasonAvg - beatAvg) / beatSD)
							
			statTbl[cat][beat] = (beatTot,beatAvg,beatSD, \
								  periodTot,periodZ,periodRatio,periodAvg,periodSD, \
								  seasonTot,seasonZ,seasonRatio,seasonAvg,seasonSD)
			
		# NB: Aggregated stats added to statTbl as 'inter','other'
		for ak in ['inter','other']:
			beatTot = sum( aggTbl[ak][cat][0] )
			beatAvg,beatSD = basicStats( aggTbl[ak][cat][0] )
		
			perVal = aggTbl[ak][cat][1].values()
			periodTot = sum( perVal )
			periodAvg,periodSD = basicStats( perVal )
			if beatAvg==0.:
				periodRatio = 0.
			else:
				periodRatio = periodAvg / beatAvg
			if beatSD==0.:
				periodZ = 0.
			else:
				periodZ = float((periodAvg - beatAvg) / beatSD)
	
			seaVal = aggTbl[ak][cat][2].values()
			seasonTot = sum( seaVal )
			seasonAvg,seasonSD = basicStats( seaVal )				
			if beatAvg==0.:
				seasonRatio = 0.
			else:
				seasonRatio = seasonAvg / beatAvg
			if beatSD==0.:
				seasonZ = 0.
			else:
				seasonZ = float((seasonAvg - beatAvg) / beatSD)

			statTbl[cat][ak] = (beatTot,beatAvg,beatSD, \
								  periodTot,periodZ,periodRatio,periodAvg,periodSD, \
								  seasonTot,seasonZ,seasonRatio,seasonAvg,seasonSD)
			
	# print allCat stats
	# allCatTbl: inter/other -> tot/period/season
	print 'tallyBeatsPeriod: AllCat totals'
	print 'Area,Treat,Tot,Avg,SD'
	for area in allCatTbl.keys():
		for i in range(3):
			if i==0:
				treat='Tot'
				allVal = allCatTbl[area][0]
			else:
				allVal = allCatTbl[area][i].values()
				if i==1:
					treat='Period'
				else:
					treat='Season'
			tot = sum(  allVal )
			avg,sd = basicStats( allVal )
			
			print '%s,%s,%d,%f,%f' % (area,treat,tot,avg,sd)	
				
	return statTbl

def ppStatTbl(statTbl,outf):
	outs = open(outf,'w')
	outs.write('CC,Beat,Tot,Avg,SD,perTot,perRatio,perZ,perAvg,perSD,seaTot,seaRatio,seaZ,seaAvg,seaSD\n')
	for cc in statTbl.keys():
		for beat in statTbl[cc].keys():
			(beatTot,beatAvg,beatSD,periodTot,periodZ,periodRatio,periodAvg,periodSD, \
				seasonTot,seasonZ,seasonRatio,seasonAvg,seasonSD) = statTbl[cc][beat]
				
			outs.write('%s,%s,%d,%f,%f,%d,%f,%f,%f,%f,%d,%f,%f,%f,%f\n' % \
					(cc,beat,beatTot,beatAvg,beatSD,periodTot,periodRatio,periodZ,periodAvg,periodSD, \
					seasonTot,seasonRatio,seasonZ,seasonAvg,seasonSD))
	outs.close()
	
def bldBeatVec(beatTbl,outDir,annoteThresh = 3):
	'''create normalized per-beat vectors wrt/ dominant crime categories TOTAL freq
	   also per-beat annotation of significant features'''
	
	beatVecTbl = {}
	
	beatAnnoteTbl = {} 
	
	for b in GoodBeats:
		beatVecTbl[b] = []
		beatAnnoteTbl[b] = {}
		
	eps = 1e-5
	domCat = beatTbl.keys()
	domCat.sort()
	for ic,cat in enumerate(domCat):
		
		vec = []
		for b in GoodBeats:
			vec.append(beatTbl[cat][b][0])  # just total stat used
		avg,sd = basicStats(vec)
			
		for bi,b in enumerate(GoodBeats):
			normFreq = (float(beatTbl[cat][b][0]) - avg) / sd
			(beatTot,beatZ,beatRatio,beatAvg,beatSD,z11,z12) = beatTbl[cat][b]
			
			# double checking calculation of normed crime rate
			assert abs(normFreq-beatZ) < eps,  'bad z score?!'
			
			beatVecTbl[b].append(normFreq)
			
			if abs(normFreq) > annoteThresh:
				if cat not in beatAnnoteTbl[b]:
					beatAnnoteTbl[b][cat] = {}
				beatAnnoteTbl[b][cat]['BeatZ'] = (normFreq,beatRatio)
			if abs(z11) > annoteThresh:
				if cat not in beatAnnoteTbl[b]:
					beatAnnoteTbl[b][cat] = {}
				beatAnnoteTbl[b][cat]['Z11'] = z11
			if abs(z12) > annoteThresh:
				if cat not in beatAnnoteTbl[b]:
					beatAnnoteTbl[b][cat] = {}
				beatAnnoteTbl[b][cat]['Z12'] = z12
		
	beatVecFile = outDir +'beatVec.csv'	
	print 'bldBeatVec: writing BeatVec to', beatVecFile
	outs = open(beatVecFile,'w')
	# no headers for numpy.loadtxt()
	outs.write('Beat,')
	for ic,cat in enumerate(domCat):
		outs.write('C%d,' % ic)
	outs.write('\n')
	
	for b in GoodBeats:
		outs.write('%s,' % b)
		cvec = beatVecTbl[b]
		# 2do: remove trailing comma!!
		for ic,cat in enumerate(domCat):
			outs.write('%f,' % cvec[ic])
		outs.write('\n')
	outs.close()
		
	beatAnnoteFile = outDir + 'beatAnnote_sd_%d.txt' % (annoteThresh)
	print 'annoteBeatVec: writing BeatAnnote to', beatAnnoteFile
	outs = open(beatAnnoteFile,'w')
	
	## listing view
	for b in GoodBeats:
		outs.write('\n# %s\n' % b)
		acat = beatAnnoteTbl[b].keys()
		acat.sort()
		npos = 0
		nneg = 0
		maxCat = None
		minCat = None
		maxCatVal = -10.
		minCatVal = 10.
		
		for cat in acat:
			bothChg = False
			outs.write('%30s: ' % cat[:30])
			for atype in ['BeatZ','Z11','Z12']:
							
				if atype in beatAnnoteTbl[b][cat]:					
					if atype=='BeatZ':
						normFreq = beatAnnoteTbl[b][cat]['BeatZ'][0]
						outs.write('%s=%6.2f ' % (atype,normFreq))
						if normFreq > 0 :
							npos +=1
							if normFreq > maxCatVal:
								maxCatVal = normFreq
								maxCat = cat
						else:
							nneg +=1
							if normFreq < minCatVal:
								minCatVal = normFreq
								minCat = cat
								
					elif atype=='Z11' and 'Z12' in beatAnnoteTbl[b][cat]:
						# check if signs of both Z11, Z12 the same
						if beatAnnoteTbl[b][cat]['Z11'] * beatAnnoteTbl[b][cat]['Z12'] > 0:
							bothChg = True
					
				else:
					outs.write(12*' ')
					
			if bothChg:
				outs.write(' <--Chg')
			outs.write('\n')
			
		outs.write('\n* %s: NPos=%d NNeg=%d\n' % (b, npos,nneg))
		if maxCat:
			outs.write('* %s: MaxCat=%s %6.2f\n' % (b,maxCat,maxCatVal))
		if minCat:
			outs.write('* %s: MinCat=%s %6.2f\n' % (b,minCat,minCatVal))
		outs.write('\n') 
	outs.close()	

	## textual view

	print 'annoteBeatVec: writing BeatText HTML to %s' % (outDir + 'beat_rpts/')
	
	moreInfoFile = ''
	
	for b in GoodBeats:
		# NB: separate file for each beat's report, for mail merge
		# NB:  HTML files normalized to lowercase!
		beatTextFile = outDir + 'beat_rpts/%s_beat_rpt.html' % (b.lower())
		outs = open(beatTextFile,'w')

		outs.write('<html><h1>Beat %s</h1>\n' % (b))
		outs.write('''<p>Below are listed all those crime categories for which Beat %s has experienced 
						either <font color=red>significantly higher (red for bad!)</font> or <font color=green>significantly lower (green for good!)</font> 
						crime than the Oakland average during 2007-2012.  If crimes of a certain type are
						either <font color=red>increasing</font> or <font color=green>decreasing</font> 
						significantly during 2011 and 2012, these are also listed.</p>\n''' % (b))
		outs.write('''<p>Further details concerning the analysis and how this particular beat fits 
						into patterns across Oakland can be found in <a href="beat_anal_details.html">Further Details</a></p>\n''')
		outs.write('<p>Regarding beat %s</p>\n<ul>\n' % (b))
		acat = beatAnnoteTbl[b].keys()
		acat.sort()
		npos = 0
		nneg = 0
		maxCat = None
		minCat = None
		maxCatVal = -10.
		minCatVal = 10.
		minRatio = ''
		maxRatio = ''
		
# 		Recall:
# 		build beatSummTbl: [cat][beat] -> [tot,avg4,std4,z11,z12]
# 										   tot=2007-12 total; 
#											avg, sd =avg(2007-2010); 
#											z11 = (2011-avg)/std
#											z12 = (2012-avg)/std

		for cat in acat:
			
			bothChg = False
			for atype in ['BeatZ','Z11','Z12']:
				if atype not in beatAnnoteTbl[b][cat]:
					continue
				
				if atype=='BeatZ' :
					
					(normFreq, beatRatio) = beatAnnoteTbl[b][cat]['BeatZ']
					ratioPhrase = bldRatioPhrase(normFreq,beatRatio)
					
					if normFreq > 0 :
						npos +=1
						if normFreq > maxCatVal:
							maxCatVal = normFreq
							maxCat = cat
							maxRatio = ratioPhrase
						color = 'red'
					else:
						nneg +=1
						if normFreq < minCatVal:
							minCatVal = normFreq
							minCat = cat
							minRatio = ratioPhrase
						color = 'green'
					
					compPhrase = '<font color=%s> %s</font>' % (color,ratioPhrase)
					outs.write('\t<li>wrt/ %s, your beat was %s the Oakland average.</li>\n' % (cat,compPhrase))
					
							
				elif atype=='Z11'  and 'Z12' in beatAnnoteTbl[b][cat]:
					# check if signs of both Z11, Z12 the same
					if beatAnnoteTbl[b][cat]['Z11'] * beatAnnoteTbl[b][cat]['Z12'] > 0:
						bothChg = True
								
			if bothChg:
				if beatAnnoteTbl[b][cat]['Z11'] > 0:
					outs.write('\t<li>wrt/ %s, there has been a <font color="red">significant increase</font> in the level of this activity over 2011-2012.</li>\n' % (cat))
				else:
					outs.write('\t<li>wrt/ %s, there has been a <font color="green">significant decrease</font> in the level of this activity over 2011-2012.</li>\n' % (cat))
			else:
				outs.write('')

			# 2do: BUG, make ranking by ratios, too!	
# 				> ha, that's a bug: i originally reported all these as z-scores (eg, -4.7
# 				> s.d.) vs. as percent of average, and am still ranking by z-score.
# 				> so you're pointing to spots
# 				> where the reported ratios are NOT min/max even though the z-scores are.
# 				> i'll have to do something about that,

		outs.write('</ul>\n')
		outs.write('<p>Considering all categories, your beat %s was worse (higher average) in %d crime categories, and better off in %d.</p>\n' % (b, npos,nneg))
		if maxCat:
			outs.write('Your <font color="red">worst category was %s: %s above</font>  the city-wide average.</p>\n' % (maxCat,maxRatio))
		if minCat:
			outs.write('Your  <font color="green">best category was %s: %s below</font>  the city-wide average.</p>\n' % (minCat,minRatio))

		# ASSUME HTML file being closed by addCorrHTML()
		# outs.write('</html>\n') 
		outs.close()	

		
	## table view
		
	beatAnnoteTblFile = outDir + 'beatAnnoteTbl_sd_%d.txt' % (annoteThresh)
	print 'bldBeatVec: writing BeatAnnote to', beatAnnoteTblFile
	outs = open(beatAnnoteTblFile,'w')
	
	# Simple: Tot only
	outs.write('%s |' % 'CrimeCat')
	for b in GoodBeats:
		outs.write('  %s |' % b)
	outs.write('\n')
	for ic,cat in enumerate(domCat):
		outs.write('%s |' % cat)
		for b in GoodBeats:
			if cat in beatAnnoteTbl[b] and 'BeatZ' in beatAnnoteTbl[b][cat]:
				outs.write('%5.2f |' % beatAnnoteTbl[b][cat]['BeatZ'][0])
			else:
				outs.write(6*' '+'|')
		outs.write('\n')
	outs.close()
	
	## Complex: All three beat stats
	
	# 2do: Create simple HTML tables showing both percent and SD

# 		-------- Original Message --------
# 		Subject: Re: [OpenOakland Brigade] [CRIME] Per-beat analysis of Oakland crime 2007-2012, for CityCamp NCPC chats
# 		Date: Sat, 2 Nov 2013 13:31:05 -0700
# 		From: Mike Linksvayer <ml@gondwanaland.com>
# 		To: rik belew <rik@electronicartifacts.com>
# 		
# 		On Sat, Nov 2, 2013 at 12:34 PM, rik belew <rik@electronicartifacts.com> wrote:
# 		>>  > wrt/ SEX_PROSTITUTION, your beat was 2.7 times the Oakland average.
# 		>>
# 		>> 270% of the Oakland average, if stated in the same fashion as the others?
# 		>
# 		>
# 		> correct; i have special code that swaps to the %5.1f format when the
# 		> ration > 2; this wording was suggested by my in-house editors (my very
# 		> literate son:)
# 		
# 		Ah. I would prefer no words at all, just all the relevant data in a
# 		table. But I guess that caters to a different sort of literacy that is
# 		not the right one for general accessibility. :)

	
	
	beatAnnoteCompactFile = outDir + 'beatAnnoteCompact_sd_%d.txt' % (annoteThresh)
	print 'bldBeatVec: writing BeatAnnoteCompact to', beatAnnoteCompactFile
	outs = open(beatAnnoteCompactFile,'w')
	
	outs.write('%30s |' % 'CrimeCat')
	for b in GoodBeats:
		outs.write('  %s |' % b)
	outs.write('\n')
	for ic,cat in enumerate(domCat):
		outs.write('%30s |' % cat[:30])
		for b in GoodBeats:
			if cat in beatAnnoteTbl[b]:
				s = ''
				for atype in ['BeatZ','Z11','Z12']:
					if atype in beatAnnoteTbl[b][cat]:
						if atype=='BeatZ':
							normFreq = beatAnnoteTbl[b][cat][atype][0]
						else:
							normFreq = beatAnnoteTbl[b][cat][atype]
						if abs(normFreq)>9.5:
							if normFreq > 0:
								s += '+!'
							else:
								s += '-!'
						else:
							s += '%+1d' % normFreq
					else:
						s += '  '
						
				s += '|'
				outs.write(s)
			else:
				outs.write(6*' '+'|')
		outs.write('\n')
		
def analBeat(bcTbl):
	print '# Cat,',
	for b in GoodBeats:
		print ('%s,' % b),
	print 'BAD,TOT'
	
	NSD4Out = 2
	outBeatTbl = {} # (cat,beat) -> (n,avg,sd)
	allCat =  bcTbl.keys()
	allCat.sort()
	nbeats = len(GoodBeats)
	for cat in allCat:
		tot = 0
		yrSumVec = []
		print ('"%s",' % cat),
		for b in GoodBeats:
			yrSum = sum(bcTbl[cat][b])
			yrSumVec.append(yrSum)
			tot += yrSum
			print ('%d,' % yrSum),
			
		avg,sd = basicStats(yrSumVec)
		for bi,b in enumerate(GoodBeats):
			if abs(yrSumVec[bi]-avg) > NSD4Out * sd:
				outBeatTbl[(cat,b)] = (yrSumVec[bi], avg, sd)
				
		yrSum = sum(bcTbl[cat]['BAD'])
		tot += yrSum
		print ('%d,' % yrSum),
		print ('%d' % tot)
		
	# NSD4Out=1 : NOutlier=2479
	# NSD4Out=2 : NOutlier=2101
	# NSD4Out=3 : NOutlier=1812
	# NSD4Out=4 : NOutlier=1510

	
	print 'tallyBeat: NOutlier=%d' % (len(outBeatTbl))
	obKeys = outBeatTbl.keys()
	obKeys.sort()
	print '\n# Cat,Beat,N,Avg,SD'
	for obk in obKeys:
		(cat,beat) = obk
		(n,avg,sd) = outBeatTbl[obk]
		print '"%s",%s,%d,%f,%f' % (cat,beat,n,avg,sd)
		
def ppCntTbl(cntTbl):
	print 'Cat,',
	for yr in range(MinYear,MaxYear+1):
		print ('%d,' % yr),
	print
	catList = cntTbl.keys()
	catList.sort()
	for cat in catList:
		print ('%s,' % cat),
		for v in cntTbl[cat]:
			print ('%d,' % v),
		print

	
def loadDataSlice(plbl,inf, updateOnMatch=True):
	'''only basic details returned in newTbl: cid -> (cdate,beat,addr,fooLat,barLong, [ (ctype,desc) ] )
		NB: fooLat,barLong included to allow parallel treatment with regular matchTbl (eg, by rptYearDist) from FTP site, ala load_OPDCrimes()
		NB: DataFormatTbl consulted for any oddly formatted files
	'''
					
	hdrLine = False
	cityState = True
	beatAddrSwap = False
			
	print 'loadDataSlice: %s hdr=%s cityState=%s beatAddrSwap=%s reading from %s' % (plbl,hdrLine,cityState,beatAddrSwap,inf)
	csvReader = csv.reader(open(inf, "r"))

	nbadDate = 0
	nbadTime = 0
	ndup = 0
	nmult = 0
	nupdate = 0
	nbadCID=0
	noutDate=0
	nbeatFix=0
	nbadBeat=0
	ntcc=0
	ndcc=0
	newCType= defaultdict(int)
	newDesc= defaultdict(int)

	newDataTbl = {}
	prefixTbl = {}
	ri = 0
	
	randIdx = 10  # for echo

	patchLbl = 'OPD_%s' % plbl	
	
	for ir,row in enumerate(csvReader):
		
		if hdrLine and ir==0:
			continue
		
		if cityState:
			(ctype,dateStr,cid,desc,beat,addr,city,state) = row
		else:
			(ctype,dateStr,cid,desc,beat,addr) = row
			city = 'Oakland'
			state = 'CA'
		
		if beatAddrSwap:
			beat,addr = addr,beat
		
		
		# echo random record, to confirm fields haven't moved again!!
		
		if ri==randIdx:
			print 'loadDataSlice: Record echo #',randIdx
			print '\tctype:',ctype
			print '\tdateStr:',dateStr
			print '\tcid:',cid
			print '\tdesc:',desc
			print '\tbeat:',beat
			print '\taddr:',addr
			print '\tcity:',city
			print '\tstate:',state
			print 'loadDataSlice: echo done'	
			
		ri += 1
		
		# import pdb; pdb.set_trace()

		cid = cid.strip()
		if cid=='' or cid.find('-')==-1:
			nbadCID += 1
			continue
		
		hpos = cid.index('-')
		cidYrS = cid[:hpos]
		try:
			# HACK: no useful data prior to Y2K
			cidYr = int('20'+cidYrS)
		except:
			# 140328: 2012 data sometimes has alpha prefix on CaseID?!
			# 		use hyphen and back up 2 year digits!
			
			try:
				cid2 = cid[hpos-2:]
				prefix = cid[:hpos-2]
				if prefix in prefixTbl:
					prefixTbl[prefix] += 1
				else:
					prefixTbl[prefix] = 1
				cidYrS = cid2[:2]
				cidYr = int('20'+cidYrS)
				cid = cid2
			except Exception,e:
			
				print 'loadDataSlice: bad CID?! %s %s' % (cid,e)
				nbadCID += 1
				continue

		try:
			cdate = datetime.strptime( dateStr, OPD_date_string)			
			hour = cdate.hour
			minute = cdate.minute
			if hour==0 and minute==0:
				nbadTime += 1
			
		except:
			nbadDate += 1
			continue

		if cdate.year<MinYear or cdate.year>MaxYear:
			noutDate += 1
			continue
			
		ctype = ctype.strip().upper()
		desc = desc.strip().upper()
		
		addr = cleanAddr(addr)
		
		if beat not in GoodBeats:
			# check for single digit beats
			if '0'+beat in GoodBeats:
				beat = '0'+beat
				nbeatFix += 1
			else:
				nbadBeat += 1	

		if ctype in CType2CCTbl:
			cc = CType2CCTbl[ctype]
			ntcc += 1
		elif desc in CType2CCTbl:
			cc = CType2CCTbl[desc]
			ndcc += 1
		else:
			if ctype != '':
				newCType[ctype] += 1
			if desc != '':
				newDesc[desc] += 1
			cc = ''
			
		# NB: no statute, UCR in data slices
		newInfo = (patchLbl,ctype,desc,'','',cc)
		
		if cid in newDataTbl:
			(prev_cdate,prev_beat,prev_addr,fooLat,barLong,prev_incid) = newDataTbl[cid]
			if (prev_cdate==cdate and \
			   	 prev_beat==beat and \
				 prev_addr==addr):

				if newInfo in prev_incid:
					ndup += 1
# 					prev_dates = prev_cdate.strftime(C4A_dateTime_string2)
# 					dates  = cdate.strftime(C4A_dateTime_string2)
# 					print 'loadDataSlice: dup caseid, (ctype,desc)?! %d %s "%s" "%s" \n\tprev: %s\n\tcurr: %s' % \
# 						(ri, cid, ctype, desc, str((prev_dates,prev_beat,prev_addr)), str((dates,beat,addr)))
				else:
					prev_incid.append(newInfo)
					nmult += 1
					
				newDataTbl[cid] = (cdate,beat,addr,'','',prev_incid)
				
			elif updateOnMatch:
				nupdate += 1
				
				# ASSUME newer date is more accurate, so weaker test on dates
				if (cdate != ''):
					prev_cdate == cdate
					
				if (prev_beat=='' and beat != ''):
					prev_beat == beat
				if (prev_addr=='' and addr != ''):
					prev_addr == addr
				
				newDataTbl[cid] = (prev_cdate,prev_beat,addr,'','', [ newInfo ] )
				
			else:
				ndup += 1
				prev_dates = prev_cdate.strftime(C4A_dateTime_string2)
				dates  = cdate.strftime(C4A_dateTime_string2)
				print 'loadDataSlice: dup caseid?! %d %s\n\tprev: %s\n\tcurr: %s' % \
					(ri, cid, str((prev_dates,prev_beat,prev_addr)), str((dates,beat,addr)))
		else:
			newDataTbl[cid] = (cdate,beat,addr,'','', [ newInfo ] )
		
	print "loadDataSlice: NData=%d NMult=%d NTCC=%d NDCC=%d NDup=%d NUpdate=%d NBadCID=%d NOutDate=%d NBadDate=%d NBadTime=%d NBeatFix=%d NBadBeat=%d" % \
		(len(newDataTbl),nmult,ndup,ntcc,ndcc,nupdate,nbadCID,noutDate,nbadDate,nbadTime,nbeatFix,nbadBeat)
	if len(prefixTbl)>0:
		print "loadDataSlice: NPrefix=%d" % (len(prefixTbl))
		for k,v in prefixTbl.items():
			print '%s,%d' % (k,v)

	if len(newCType)>0:
		print "loadDataSlice: New CType=%d" % (len(newCType))
		for k,v in newCType.items():
			print '%s,%d' % (k,v)

	if len(newDesc)>0:
		print "loadDataSlice: New Desc=%d" % (len(newCType))
		for k,v in newCType.items():
			print '%s,%d' % (k,v)
			
	return newDataTbl

def loadDataSlice_json(inf):
	'''only basic details returned in newTbl: cid -> (cdate,beat,addr, [ (ctype,desc) ] )
		capture Socrata data into newDataTbl: caseID -> (i,ctype,datetime,desc,beat,loc)
		hack to capture addresses from json
	'''
	print 'loadDataSlice: reading from',inf

	newData = json.load(open(inf,'r'))

	locID = None
	
	for i,c in enumerate(newData['meta']['view']['columns']): 
		# print i,c['name'],
		if 'tableColumnId' in c:
			# print c['tableColumnId']
			if c['name']=='Location 1':
				locID = c['tableColumnId']
# 		else:
# 			print

		# 0 sid
		# 1 id
		# 2 position
		# 3 created_at
		# 4 created_meta
		# 5 updated_at
		# 6 updated_meta
		# 7 meta
		# 8 CRIMETYPE 7183382
		# 9 DATETIME 7183383
		# 10 CASENUMBER 7183384
		# 11 DESCRIPTION 7183385
		# 12 POLICEBEAT 7183386
		# 13 Location 1 7183387

	# print 'loadDataSlice_json: locID=%d' % (locID)
	locIDstr = str(locID)
	
	# [[1, u'7978C229-A42A-48AC-8C4D-7B587D3461C1', 1, 1391352753, u'703903', 1391352753, u'703903', 
	#	  u'{\n  "invalidCells" : {\n	"7183387" : "300 WEBSTER ST"\n  }\n}', 
	#	  u'GRAND THEFT', u'2013-10-08T17:10:00', u'13-051656', u'GRAND THEFT:MONEY/LABOR/PROPERTY  OVER $400', u'01X', 
	#	  [None, None, None, None, None]], 
	
	# newData['data'] is a long vector
	nloc1 = 0
	nloc2 = 0
	nbadDate = 0
	nbadTime = 0
	ndup = 0
	nmult = 0
	nupdate = 0
	newDataTbl = {}
	for ri,row in enumerate(newData['data']):
		ctype = row[8]
		dateStr = row[9]
		caseid = row[10]
		desc = row[11]
		beat = row[12]
		loc = ''
		if row[13][0]:
			# [u'{"address":"900 CAMPBELL","city":"VILLAGE","state":"CT","zip":""}', u'41.35716290200048', u'-73.18955857699967', None, False]
			addr = eval(row[13][0])
			addr = cleanAddr(addr)
			loc = addr['address']+' '+addr['city']+' '+addr['state']
			nloc1 += 1
		else:
			meta = eval(row[7])
			if 'invalidCells' in meta and locIDstr in meta['invalidCells']:
				loc = meta['invalidCells'][locIDstr]
				nloc2 += 1
				
		try:
			cdate = datetime.strptime( dateStr, Socrata_date_string)
			dateTimeStr = cdate.strftime(C4A_dateTime_string)
			hour = cdate.hour
			minute = cdate.minute
			if hour==0 and minute==0:
				nbadTime += 1
	
		except:
			nbadDate += 1
			cdate = DefaultDate
			dateTimeStr = cdate.strftime(C4A_dateTime_string)
			yr = 0
					
		# NB: only basics here
		newInfo = (ctype,desc)
		
		if caseid in newDataTbl:		
			(prev_cdate,prev_beat,prev_addr,prev_incid) = newDataTbl[caseid]
			if ((prev_cdate==cdate and \
			   	 prev_beat==beat and \
				 prev_addr==addr)) or \
			   (prev_beat=='' and beat != ''):
				if (prev_beat=='' and beat != ''):
					# 2do: allow update of bad date/time, address
					nupdate += 1

				if newInfo in prev_incid:
					ndup += 1
					prev_dates = prev_cdate.strftime(C4A_dateTime_string2)
					dates  = cdate.strftime(C4A_dateTime_string2)
					print 'loadDataSlice_json: dup caseid, (ctype,desc)?! %d %s "%s" "%s" \n\tprev: %s\n\tcurr: %s' % \
						(ri, caseid, ctype, desc, str((prev_dates,prev_beat,prev_addr)), str((dates,beat,addr)))
				else:
					prev_incid.append(newInfo)
					nmult += 1
					
				newDataTbl[caseid] = (cdate,beat,addr,prev_incid)
				
			else:
				prev_dates = prev_cdate.strftime(C4A_dateTime_string2)
				dates  = cdate.strftime(C4A_dateTime_string2)
				print 'loadDataSlice_json: dup caseid?! %d %s\n\tprev: %s\n\tcurr: %s' % \
					(ri, caseid, str((prev_dates,prev_beat,prev_addr)), str((dates,beat,addr)))
		else:
			newDataTbl[caseid] = (cdate,beat,addr, [ newInfo ] )
		
	print "loadDataSlice_json: NData=%d NDup=%d NBadDate=%d NBadTime=%d NLoc1=%d NLoc2=%d" % \
		 (len(newDataTbl),ndup,nbadDate,nbadTime,nloc1,nloc2)
	return newDataTbl
	
def applyPatch(newDataList,matchTbl,addrTbl,missAddrFile,diffFile):
	'''Incorporate new data into existing data set
		Extrapolate previously geo-coded addresses to new incidents
	'''
	
	ncid_init, nincid_init = rptYearDist(matchTbl,'applyPatch_initial')

	nupdate = 0
	ndup = 0
	nmult = 0
	nnew = 0
	nincid = 0
	nambigCC = 0
	nmatchAddr=0
	nmissAddr=0
	nmrg=0
	nhardMatch=0
	
	for plbl, newDataFile in newDataList:
		
		newDataTbl  = loadDataSlice(plbl,newDataFile)
		patchLbl = 'OPD_%s' % plbl
		
		# NB: Since OPD data turns over every 90 days, only go back that far
		
		# HACK: use normal plbl for beginning date		
		
		if len(plbl) == 6:
			endDateTime = datetime.strptime( plbl, '%y%m%d')
			endDate = endDateTime.date()
		else:
			endDate = date.today()
			
		minDate = endDate - timedelta(days=90)
		rptWeekDist(newDataTbl,'New data slice',minDate,endDate)
		
		rptYearDist(newDataTbl,'applyPatch_new_%s' % (plbl))
				
		mas = open(missAddrFile,'w')
		mas.write('CID,Addr\n')
	
		diffs = open(diffFile,'w')
		diffs.write('CID,Prev,Curr\n')
		
		for newCID in newDataTbl:
			(new_cdate,new_beat,new_addr,fooLat,barLong,newIncidList) = newDataTbl[newCID]
			if newCID in matchTbl:
				(prev_cdate,prev_beat,prev_addr,prev_lat,prev_long,prev_incid) = matchTbl[newCID]
				
				# NB: CType+Desc the only guaranteed commonality with new data
				allPrevCTD = [ctype+':'+desc for (src,ctype,desc,ucr,statute,cc) in prev_incid]
				
				if (prev_cdate==new_cdate and \
					prev_addr==new_addr and \
				   	(prev_beat==new_beat or (prev_beat=='' and new_beat != ''))):
					
					if (prev_beat=='' and new_beat != ''):
						# 2do: allow update of bad date/time, address
						nupdate += 1
	
					for newInfo in newIncidList:
						nsrc,ctype,desc,ucr,statute,cc = newInfo
						ctd = ctype+':'+desc
						if ctd in allPrevCTD:
							ndup += 1
							continue

						# 150120: beyond exact match on both ctype+desc
						uct = cleanOPDtext(ctype)
						ud = cleanOPDtext(desc)
						fnd = None
						for ip,pinfo in enumerate(prev_incid):
							(psrc,pctype,pdesc,pucr,pstat,pcc) = pinfo
							pct = cleanOPDtext(pctype)
							pd = cleanOPDtext(pdesc)
							if (pct == uct or uct=='' or pct=='') and \
								(pd == ud or ud=='' or pd==''):
								fnd = ip
								nhardMatch += 1
								break
						if fnd != None:
							# previous ctype and desc dominate
							(psrc,pctype,pdesc,pucr,pstat,pcc) = prev_incid[fnd]
							if psrc.endswith(patchLbl):
								msrc = psrc
							else:
								msrc = psrc+'+'+patchLbl
								
								#2do: test intra-OPD merges?
# 								if psrc.startswith('OPD'):
# 									print 'intra-OPD merge?: cid=%s\n%s\n%s' % (newCID,prev_incid[fnd],str([msrc, mctype,mdesc,ucr,statute,cc]))
									
							if pctype=='':
								mctype = ctype
							else:
								mctype = pctype
							if pdesc == '':
								mdesc = desc
							else:
								mdesc = pdesc
							
							newInfo = [msrc, mctype,mdesc,ucr,statute,cc]
							prev_incid[fnd] = newInfo
							nmrg += 1
						else:				
							nincid += 1
							prev_incid.append(newInfo)
						
					newDataTbl[newCID] = (new_cdate,new_beat,new_addr,prev_incid)
					
				# non-matching details
				else:
					prev_dates = prev_cdate.strftime(C4A_dateTime_string2)
					prevTuple = tuple([prev_dates,prev_beat,prev_addr])
					dates  = new_cdate.strftime(C4A_dateTime_string2)
					newTuple = tuple([dates,new_beat,new_addr])
					diffs.write('%s,"%s","%s"\n' % (newCID, str(prevTuple), str(newTuple)))
					
			# new CID
			else:
	
				## try to get lat, long for new_addr
				addrFnd = new_addr in addrTbl
				if addrFnd:
					nmatchAddr += 1
					info = addrTbl[new_addr]
					lat = info['lat']
					lng = info['lng']
				else:
					nmissAddr += 1
					mas.write('%s,%s\n' % (newCID,new_addr))
					lat = ''
					lng = ''
				
				# NB: new_incid elements only have basic ctype,desc here
				new_incid = []
				for newInfo in newIncidList:				
					new_incid.append(newInfo)
				
				matchTbl[newCID] = (new_cdate,new_beat,new_addr,lat,lng, new_incid )
				nincid += len(new_incid)
				nnew += 1

		print "applyPatch: NData=%d NNew=%d NIncid=%d,NDup=%d NMult=%d NMerge=%d NHardMatch=%d NAmbigCC=%d NMatchAddr=%d NMissAddr=%d" % \
			 (len(newDataTbl),nnew,nincid,ndup,nmult,nmrg,nhardMatch,nambigCC,nmatchAddr,nmissAddr)
			 
		# rptYearDist(matchTbl,'applyPatch_after_%s' % (plbl))
		
	mas.close()
	diffs.close()

	ncid_rpt, nincid_rpt = rptYearDist(matchTbl,'applyPatch_final')
		
	netCID = ncid_rpt - ncid_init
	netIncid = nincid_rpt - nincid_init
	print '# netCID = ncid_rpt - ncid_init'
	print '# nincid_rpt - nincid_init'
	print 'applyPatch: NNewCID=%d NNewIncid=%d NetCID = %d  NetIncid=%d' % (nnew,nincid,netCID,netIncid)
	
	return matchTbl

def bldBeatCrimeTbl(matchTbl,rbeat,bdate,edate,ccList):
	ccTbl={} # cc -> ncharge
	for cid,iinfo in matchTbl.items():
		cdate,beat,addr,lat,lng,incidList = iinfo
		if beat != rbeat or cdate < bdate or cdate > edate:
			continue
		for cinfo in incidList:
			src,ctype,desc,ucr,statute,cc = cinfo
			if cc in ccList:
				if cc in ccTbl:
					ccTbl[cc] += 1
				else:
					ccTbl[cc] = 1
	return ccTbl

def rptCrimeCatBeatPeriod(matchTbl,beatList,periodList,ccList):
	
	for beat in beatList:
		allPerTbls = []
		hdr = 'Beat %s' % (beat)
		for sdate,edate in periodList:
			hdr += ',"%s-%s"' % (sdate,edate)

			perStartDate = datetime.strptime( sdate+' 00:00', '%y%m%d %H:%M')
			perEndDate = datetime.strptime( edate+' 23:59', '%y%m%d %H:%M')
			# UGG need to bump to next day to get round months!
			oneMinute = timedelta(minutes=1)
			perEndDate = perEndDate + oneMinute
			
			ccTbl = bldBeatCrimeTbl(matchTbl,beat,perStartDate,perEndDate,ccList)
			allPerTbls.append(ccTbl)
		
		print hdr
		ccList.sort()
		for cc in ccList:
			data = '"%s"' % (cc)
			for ip,ccTbl in enumerate(allPerTbls):
				if cc in allPerTbls[ip]:
					n = allPerTbls[ip][cc]
				else:
					n = 0
				data += ',%d' % (n)
			print data

def analCrimeTypeDist(matchTbl,outf):
	
	ctypeTbl = defaultdict( lambda: defaultdict( int )) # ctype -> stat -> freq
	
	cidList = matchTbl.keys()	
	for cnum,cid in enumerate(cidList):
		(cdate,beat,addr,lat,lng, incidList) = matchTbl[cid]
		for nocc,oinfo in enumerate(incidList):
			# 2do: HACK!  'early' matchTbl incidents do not have CC, later they do (:
			(src,ctype,desc,ucr,stat,cc) = oinfo
			ctypeTbl[ctype][stat] += 1

	def totStat(statTbl):
		return sum([ statTbl[k] for k in statTbl.keys() ])
	
	allCType = ctypeTbl.keys()
	allCType.sort(key=(lambda k: totStat(ctypeTbl[k])),reverse=True)
	
	maxrptStat = 5
	outs = open(outf,'w')
	outs.write('Freq,CType,NStat,TotStat,NMiss')
	for i in range(maxrptStat):
		outs.write(',Stat-%d,Freq-%d' % (i+1,i+1) )
	outs.write('\n')
	for ctype in allCType:
		tot = totStat(ctypeTbl[ctype])
		allStat = ctypeTbl[ctype].keys()
		allStat.sort(key=(lambda k: ctypeTbl[ctype][k]),reverse=True)
		if '' in ctypeTbl[ctype]:
			nstat = len(allStat)-1
			nmiss = ctypeTbl[ctype]['']
			sumStat = tot - nmiss
		else:
			nstat = len(allStat)
			nmiss = 0
			sumStat = tot

		outs.write('%d,"%s",%d,%d,%d' % (tot,ctype,nstat,sumStat,nmiss))
		for stat in allStat[:maxrptStat]:
			outs.write(',"%s",%d' % (stat,ctypeTbl[ctype][stat]))
		outs.write('\n')
	outs.close()

def analIncidClusters(matchTbl,outf):
	
	descSetTbl = defaultdict(int)
	statSetTbl = defaultdict(int)
	
# 	probeSet1 = set(['ROBBERY/INHABITED DWELLING - FIREARM','ROBBERY - FIREARM'])
# 	# 07-005295, 08-045842, 07-088986, 07-060367, 08-035817, 08-018863 ... nothing > 2010!
# 	probeSet2 = set(['ASSAULT WITH FIREARM ON PERSON','SHOOT AT INHABITED DWELLING/VEHICLE/ETC'])
# 	# 13-058548, 11-053072, 14-009259, 11-059500, 12-042229

	
	cidList = matchTbl.keys()	
	for cnum,cid in enumerate(cidList):
		(cdate,beat,addr,lat,lng, incidList) = matchTbl[cid]

		descSet = set()
		statSet = set()
		
		for nocc,oinfo in enumerate(incidList):
			# 2do: HACK!  'early' matchTbl incidents do not have CC, later they do (:
			(src,ctype,desc,ucr,statute,cc) = oinfo
			if desc != '':
				descSet.add(desc)
			if statute != '':
				statSet.add(statute)			
				
		descFSet = frozenset(descSet)
		statFSet = frozenset(statSet)
		
		
		descSetTbl[descFSet] += 1
		statSetTbl[statFSet] += 1

	allDS = descSetTbl.keys()
	allSS = statSetTbl.keys()
	allDS.sort(key = lambda s: descSetTbl[s], reverse=True)
	allSS.sort(key = lambda s: statSetTbl[s], reverse=True)
	
	outs = open(outf,'w')
	outs.write('Type,Set,N,Freq\n')
	for ds in allDS:
		dsStr = '|'.join(ds)
		dslen = len(ds)
		if dslen==1:
			continue
		outs.write('desc,"%s",%d,%d\n' % (dsStr,dslen,descSetTbl[ds]))
	for ss in allSS:
		ssStr = '|'.join(ss)
		sslen = len(ss)
		if sslen==1:
			continue
		outs.write('stat,"%s",%d,%d\n' % (ssStr,sslen,statSetTbl[ss]))
	outs.close()
			
def analCIDincid(matchTbl,outf):
	
	monTbl = defaultdict( lambda: defaultdict( dict )) # yr -> mo -> ('ncid','nincid') -> freq
	nincidDistTbl = defaultdict( lambda: defaultdict( lambda: defaultdict( int ))) # yr -> mo -> nincid -> freq
	
	cidList = matchTbl.keys()	
	for cnum,cid in enumerate(cidList):
		(cdate,beat,addr,lat,lng, incidList) = matchTbl[cid]
		yr = cdate.year
		mo = cdate.month
		nincid = len(incidList)
		if 'ncid' in monTbl[yr][mo]:
			monTbl[yr][mo]['ncid'] += 1
		else:
			monTbl[yr][mo]['ncid'] = 1
		if 'nincid' in monTbl[yr][mo]:
			monTbl[yr][mo]['nincid'] += nincid
		else:
			monTbl[yr][mo]['nincid'] = nincid
		nincidDistTbl[yr][mo][nincid] += 1					

	maxIFreq = 7
	outs = open(outf,'w')
	hdrLine = 'Year,Mon,NCID,NIncid,'
	outIdxSet = set([i+1 for i in range(maxIFreq-1)])
	for i in range(maxIFreq-1):
		hdrLine += 'In%d,' % (i+1)
	hdrLine += 'InMore\n'
	outs.write(hdrLine)
	
	for yr in monTbl.keys():
		for mo in monTbl[yr].keys():
			ncid = monTbl[yr][mo]['ncid']
			nincid = monTbl[yr][mo]['nincid']
			outLine = '%d,%d,%d,%d,' % (yr,mo,ncid,nincid)
			for i in range(maxIFreq-1):
				idx = i+1
				if idx in nincidDistTbl[yr][mo]:
					outLine += '%d,' % (nincidDistTbl[yr][mo][idx])
				else:
					outLine += ' ,'
			bigIdx = list(set(nincidDistTbl[yr][mo].keys()).difference(outIdxSet))
			bigIdx.sort()
			tot = sum([nincidDistTbl[yr][mo][idx] for idx in bigIdx])
			outLine += '%d\n' % (tot)
			outs.write(outLine)
	outs.close()

def loadCType2CCTbl(inf):
	# CID,Address,FullAddr,Long,Lat
	'''return ctype2ccTbl: ctype -> cc'''

	ctype2ccTbl = {}
	allCC = defaultdict(int)
	csvDictReader = csv.DictReader(open(inf))
	for entry in csvDictReader:
		# CType, CC
		cc = entry['CC']
		ctype2ccTbl[entry['CType']] = cc
		allCC[cc] += 1
	print 'loadCType2CCTbl: NCType=%d NCC=%d' % (len(ctype2ccTbl), len(allCC))
	return ctype2ccTbl

def rptCCDist(matchTbl,ctype2ccTbl,outf):
	
	ccTbl = defaultdict(int) # cc -> freq
	for k,v in ctype2ccTbl.items():
		ccTbl[v] = 0
	
	nmissCType = 0
	nincid = 0
	noctype = 0
	cidList = matchTbl.keys()	
	for cnum,cid in enumerate(cidList):
		(cdate,beat,addr,lat,lng, incidList) = matchTbl[cid]
						
		for nocc,oinfo in enumerate(incidList):
			nincid += 1
			(src,ctype,desc,ucr,stat,prevCC) = oinfo
			if ctype == '':
				nmissCType += 1
				continue
			elif ctype not in ctype2ccTbl:
				noctype += 1
				continue
			ccFromCType = ctype2ccTbl[ctype]
			ccTbl[ccFromCType]+= 1

	print 'rptCCDist: done. NIncid=%d NMissCType=%d NOtherCType=%d' % (nincid,nmissCType,noctype)
	allCC = ccTbl.keys()
	allCC.sort()
	
	outs = open(outf,'w')
	outs.write('Freq,CC\n')
	for cc in allCC:
		outs.write('%d,%s\n' % (ccTbl[cc],cc))
	outs.close()
	
def addCC(prevMatchTbl,ctype2ccTbl):
	'''add CrimeCat based on simple CType->CC table
		NB: will CLOBBER any other CC
	'''
	newMatchTbl = {}
	
	nmissCType = 0
	nincid = 0
	noctype = 0
	cidList = prevMatchTbl.keys()	
	for cnum,cid in enumerate(cidList):
		(cdate,beat,addr,lat,lng, incidList) = prevMatchTbl[cid]
		
		newIList = []				
		for nocc,oinfo in enumerate(incidList):
			nincid += 1
			(src,ctype,desc,ucr,stat,prevCC) = oinfo
			if ctype == '':
				nmissCType += 1
				cc = ''
			elif ctype not in ctype2ccTbl:
				noctype += 1
				cc = ''
			else:
				cc = ctype2ccTbl[ctype]
			newIList.append( (src,ctype,desc,ucr,stat,cc) )
			
		newMatchTbl[cid] = (cdate,beat,addr,lat,lng, newIList)
			
	print 'addCC: done. NIncid=%d NMissCType=%d NOtherCType=%d' % (nincid,nmissCType,noctype)
	
	return newMatchTbl
	
### TopLevel Run

# NMissCC = 0

if __name__ == '__main__':

	if len(sys.argv) < 4:
		sys.exit('opdata: missing lastRunDate currDate updateList arguments?!')

	DataDir = '/Data/sharedData/c4a_oakland/OAK_data/' 
	NewPatchDir = DataDir + 'ftp_CrimePublicData/'
		
	addrTbl = loadAddrTbl(DataDir+'addrTbl_150309.csv')

	CurrCatFile = DataDir + 'crimeCat_140403.csv'
	CType2CCFile = DataDir + 'ctype2cc.csv'
	CType2CCTbl = loadCType2CCTbl(CType2CCFile)
	
	# 161027 run: argv = 160127 161027 "['160415', '160610', '160906', '161027']"
	
	LastRunDate = sys.argv[1] 
	CurrDate = sys.argv[2] 
	updateList = eval(sys.argv[3]) 

	print 'opdata: LastRunDate=%s CurrDate=%s updateList=%s' % \
		(LastRunDate,CurrDate,updateList)
	
	lastRunDataFile = DataDir + 'OPD_' + LastRunDate + '.json'
	lastMatchTbl = json2matchTbl(lastRunDataFile)
	
	RunDir = DataDir + CurrDate + '/'
	if not os.path.isdir(RunDir):
		print 'opdata: creating RunDir',RunDir
		os.makedirs(RunDir)
		
	PatchList = [(dddate,NewPatchDir +dddate+'.csv') for dddate in updateList]
	missAddrFile = RunDir+'missAddr.csv'
	diffFile = RunDir+'diff.csv'
	matchTbl2 = applyPatch( PatchList, lastMatchTbl, addrTbl, missAddrFile,diffFile)
	matchFile2 = RunDir+'OPD_' + CurrDate + '.json'
	matchTbl2json(matchTbl2,matchFile2,addrTbl)
