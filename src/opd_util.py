import csv
from datetime import datetime,timedelta
import geopy
from geopy import distance

import sqlite3 as sqlite

# used to control number of geo queries
GetGeoCodes = False
MaxGoogleReq =  1000 

OPD_date_string = '%Y-%m-%d %H:%M:%S'
USC_date_string = '%m/%d/%Y'


def load_OPDCrimes(inf,currDB):
		
	global TotGoogleReq
					
	print 'load_OPDCrimes: reading from',inf
	csvReader = csv.reader(open(inf, "r"))
   
	cur = currDB.cursor()
	cur.execute('''CREATE TABLE OPD
				   (cid text, ctype text, ctIdx text, dateStr text, addr text, lat real, lng real, beat text, features text)''')

	ndropped = 0
	nbadDate = 0
	nbadTime = 0
	nbadAddr = 0
	yrTbl = {}
	for ri,row in enumerate(csvReader):
		
		if ri % 50000 == 0:
			print 'load_OPDCrimes',ri,nbadDate,nbadTime,nbadAddr
			
		(ctypeAbbr,dateStr,cid,ctype,beat,addr) = row
		
		try:
			cdate = datetime.strptime( dateStr, OPD_date_string)
			yr = cdate.year
			
			hour = cdate.hour
			minute = cdate.minute
			if hour==0 and minute==0:
				nbadTime += 1
			
		except:
			nbadDate += 1
			cdate = datetime.fromordinal(1) 
			yr = 0

		lat = 0.
		lng = 0.
		place = addr
		if GetGeoCodes:
			try:
				fullAddr = addr + ' Oakland CA'
				if TotGoogleReq < MaxGoogleReq:
					place, (lat, lng) = GeoCoder.geocode(fullAddr)
					TotGoogleReq += 1						   
			except:
				nbadAddr += 1											
		
		cur.execute('insert into OPD(cid, ctype, dateStr, addr, lat, lng, beat)'+
					'values (:cid, :ctype, :dateStr, :place, :lat, :lng, :beat)', locals())
 
		lastRow = ri
	ndb = currDB.total_changes
			
	print 'load_OPD: NRow=%d Ndb=%d NBadDate=%d NBadTime=%d NBadAddr=%d' % (lastRow,ndb,nbadDate,nbadTime,nbadAddr)
					
			
def load_ACCrimes(inf,currDB):
	global TotGoogleReq
	print 'load_ACCrimes: reading from',inf
	csvDictReader = csv.DictReader(open(inf,"r"))

	AC_date_string = '%m/%d/%Y %H:%M:%S'
		
	cur = currDB.cursor()
	cur.execute('''CREATE TABLE AC
				   (cid text, ctype text, dateStr text, addr text, lat real, lng real, objid text, agency string, ccode text, gDiff real)''')
	
	nbadDate = 0
	nbadAddr = 0
	ctypeTbl = {}
	totGDiff = 0.

	for ri,entry in enumerate(csvDictReader):
		# AlamedaCty 
		# https://data.acgov.org/Government/Alameda-County-Sheriff-Crime-Reports-Year-to-Date-/2bvq-jv9c
		# 2 Dec 12
		
		if ri % 5000 == 0:
			print 'load_ACCrimes',ri
				
		cid = entry['CrimeId']
		try:
			dateStr = entry['DateTime']
			cdate = datetime.strptime( dateStr, AC_date_string)
			
		except:
			nbadDate += 1
			cdate = datetime.fromordinal(1)
			
		try:
			addr = entry['Address']
			addr = addr.replace(' / ', ' and ')
			fullAddr = addr +' '+ entry['City'] +' '+ entry['State'] +' ' + entry['Zip']
			aclat = float(entry['Latitude'])
			aclng = float(entry['Longitude'])
			if GetGeoCodes and TotGoogleReq < MaxGoogleReq:
				place, (lat, lng) = GeoCoder.geocode(fullAddr)
				TotGoogleReq += 1
				addrPt = geopy.point.Point(lat,lng)
				acLocStr='%s;%s' % (aclat,aclng)
				acPt = geopy.point.Point(acLocStr)
				gdiff = distance.distance(addrPt,acPt).miles
				totGDiff += gdiff
			else:
				place = fullAddr
				lat = 0.
				lng = 0. 
				gdiff = 0. 
				
		except Exception,e:
			nbadAddr += 1
			place = fullAddr
			lat = 0.
			lng = 0. 
			gdiff = 1e8
			
		ctype = entry['CrimeDescr']
		if ctype in ctypeTbl:
			ctypeTbl[ctype] += 1
		else:
			ctypeTbl[ctype] = 1
		   
		objID = entry['OBJECTID']
		agency = entry['AgencyId']
		ccode = entry['CrimeCode']
		cur.execute('insert into AC(cid, ctype, dateStr, addr, lat, lng, objID, agency, ccode, gdiff)'+
					'values (:cid, :ctype, :dateStr, :place, :aclat, :aclng, :objID, :agency, :ccode, :gdiff)', locals())
 
		lastRow = ri
	ndb = currDB.total_changes
			
	avgGDiff = totGDiff / ndb
	print 'load_ACCrimes: NRow=%d Ndb=%d NBadDate=%d NBadAddr=%d AvgGeoDiff=%f'  % (lastRow,ndb,nbadDate,nbadAddr,avgGDiff)
		   
   
USC_Fields = ['ID1', 'RD', 'REPORTED', 'YEARRPT', 'OCCURRED', 'YEAROCC', 'TIME', 'DARKNESS', 
			  'DAY', 'MONTH', 'DATE', 'QUARTER', 'UCR', 'STATUTE', 'INCIDENT', 'DESCRIPTION', 
			  'NATURE', 'ADDRESS', 'APT', 'ADDRESSTYPE', 'EXCLUDE', 'PRECISION', 'False', 
			  'BEAT', 'BFO', 'CA', 'Pol_Dist', 'WEAPON', 'GANG', 'Indicators', 
			  'Violence', 'Property', 'Homicide', 'Assaults', 'Robbery', 'Shootings', 
			  'Burglary', 'MV_Theft', 'Rape', 'Weapons', 'Drugs', 'Sex', 'TRACTCE00', 
			  'TRACTCE10', 'BKGPIDFP00', 'BKGPIDFP10', 'LAT', 'LONG', 'ZIP10']

def load_USCCrime(inf,currDB):
	
	cur = currDB.cursor()
	
	createQryStr = 'CREATE TABLE USC_OPD ('
	for f in USC_Fields:
		createQryStr += '%s text,' % f 
	createQryStr = createQryStr[:-6]  # remove trailing " text,"
	createQryStr += ')'
	
	cur.execute(createQryStr)
	
	print 'load_USCCrime: loading USC_OPD from %s ...' % (inf)
	
	insertQryStr = 'insert into USC_OPD ('
	for f in USC_Fields:
		insertQryStr += '%s, ' % f 
	insertQryStr = insertQryStr[:-2] # remove trailing comma
	insertQryStr += ') values ('
	for f in USC_Fields:
		insertQryStr += ':%s, ' % f
	insertQryStr = insertQryStr[:-2] # remove trailing comma
	insertQryStr += ')'

	csvDictReader = csv.DictReader(open(inf))
	for ri,entry in enumerate(csvDictReader):
		if ri % 10000 == 0:
			print ri
						 
		try:
			# NB: query string remains constant, only entry data changes
			cur.execute(insertQryStr, entry)
		except Exception,e:
			print 'load_USCCrime: %d %s\n\t%s' % (ri,e,entry)
			continue
 
		lastRow = ri
		
	ndb = currDB.total_changes
	print 'load_USCCrime: NRow=%d Ndb=%d'  % (lastRow,ndb)


def dbug_OPD_USC(dbfile):
	"collect details for USC coding oddities for set of probe CTypes"

	probeTbl = {"BATTERY": "PC242", 
				"BURGLARY-AUTO": "PC459",
				"BATTERY:SPOUSE/EX SPOUSE/DATE/ETC": "PC243 (E)(1)", 
				"BURGLARY-FORCIBLE ENTRY": "PC459"}
	
	probeCTypes = probeTbl.keys()

	currDB = sqlite.connect(dbfile)
	
	# check to make sure it loaded as expected
	curs = currDB.cursor()
	curs.execute("select tbl_name from sqlite_master")
	allTblList = curs.fetchall()
	assert ('OPD',) in allTblList, "analOPD: no OPD table?!"
	assert ('USC_OPD',) in allTblList, "analOPD: no OPD table?!"

	## first load OPD incidents
	
	matchTbl={}
	curs.execute('SELECT cid, ctype, dateStr, addr FROM OPD')
	for ri,cursorRow in enumerate(curs):
		if ri % 10000 == 0:
			print ri
			
		(cid, ctype, dateStr, opd_addr) = cursorRow
		try:
			cdate = datetime.strptime( dateStr, OPD_date_string)
		except Exception,e:
			# print 'matchOPD_USC_Crime: bad OPD date %d %s\n\t%s' % (ri,e,dateStr)
			continue

		matchTbl[cid] = (cdate,ctype, [])
		last_OPD_ri = ri
		
	## next load USC 
	
	curs.execute('SELECT ID1, RD, REPORTED, OCCURRED, UCR, STATUTE, DESCRIPTION, ADDRESS FROM USC_OPD')

	for ri,cursorRow in enumerate(curs):
		if ri % 10000 == 0:
			print ri

		(id1, rd, rptDateStr, occDateStr, ucr, statute, desc, usc_addr) = cursorRow
		if rd not in matchTbl:
			continue
		(cdate,ctype,prevList) = matchTbl[rd]
		
		if ctype not in probeCTypes:
			continue
		
		try:
			odate = datetime.strptime( occDateStr, USC_date_string)
			rdate = datetime.strptime( rptDateStr, USC_date_string)
		except Exception,e:
			continue

		d = cdate-odate
		if d.days != 0:
			continue
		
		prevList.append( (id1, ucr,statute,desc))
		matchTbl[rd] = (cdate,ctype, prevList)

	# Overlapping years of OPD and USC
	minYr = 2007
	maxYr = 2012
	
	outf = DataDir+'USC_dbug_sample.csv'
	print 'Writing USC dbg examples to',outf
	outs = open(outf,'w')
	outs.write('OPD_ID,USC_ID,CType,ODate,UCR,Statute,USC_Desc,RDate\n')

	missf = DataDir+'USC_dbug_miss.csv'
	print 'Writing  missing USC to',missf
	misss = open(missf,'w')
	misss.write('OPD_ID,Date\n')
	for cid,info in matchTbl.items():
		(cdate,ctype, mlist) = info
		nmatch = len(mlist)
		
		if nmatch==0 and cdate.year >= minYr and cdate.year <= maxYr:
			misss.write('%s,%s\n' % (cid,cdate))
			
		if nmatch==1:
			(id1, ucr,statute,desc) = mlist[0]
			if statute != probeTbl[ctype]:
				outs.write('%s,%s,"%s",%s,%s,%s,"%s",%s\n' % \
						(cid, id1, ctype, cdate, ucr, statute, desc, rdate))
		
	outs.close()
	misss.close()
	

GeoCoder = None
TotGoogleReq = 0

def loadCrimes(dbfile):
	currDB = sqlite.connect(dbfile)

	global GeoCoder
	GeoCoder = geopy.geocoders.Google()
		
	curs = currDB.cursor()
	curs.execute("select tbl_name from sqlite_master")
	allTblList = curs.fetchall()

	if ('OPD',) in allTblList:
		print 'loadCrimes: OPD already loaded'
	else:
		opd_file = DataDir+'OPD_crime.csv'	
		load_OPDCrimes(opd_file,currDB)
		currDB.commit()
		currDB.close()
		
	if ('AC',) in allTblList:
		print 'loadCrimes: AC already loaded'
	else:
		ac_file = DataDir+'AC_CrimeReports.csv'
		currDB = sqlite.connect(dbfile)
		load_ACCrimes(ac_file,currDB)
		currDB.commit()
		currDB.close()
	
	if ('USC_OPD',) in allTblList:
		print 'loadCrimes: USC_OPD already loaded'
	else:
		usc_file = DataDir+'OaklandCrimes2003-2011_2.csv'
		currDB = sqlite.connect(dbfile)
		load_USCCrime(usc_file,currDB)
		currDB.commit()
		currDB.close()
	
def analOPD_dateDist(dbfile):
	
	conn = sqlite.connect(dbfile)
	# check to make sure it loaded as expected
	curs = conn.cursor()
	curs.execute("select tbl_name from sqlite_master")
	allTblList = curs.fetchall()
	assert ('OPD',) in allTblList, "analOPD: no OPD table?!"

	print 'analOPD: OPD loaded from %s: ' % (dbfile)
		
	freqTbl = {} # (crimeCat,yr) -> freq
	curs.execute('SELECT dateStr FROM OPD')
	nline = 0
	minYr = 2000
	maxYr = 2012
	nbadYear = 0
	for ri,cursorRow in enumerate(curs):
		if ri % 10000 == 0:
			print ri
		dateStr = cursorRow[0]
		try:
			cdate = datetime.strptime( dateStr, OPD_date_string)
		except:
			# NB: silently ignore bad/blank dates
			continue
		
		yr = cdate.year
		if yr > maxYr or yr < minYr:
			nbadYear += 1
			continue
		if yr in freqTbl:
			freqTbl[yr] += 1
		else:
			freqTbl[yr] = 1
	
	years = freqTbl.keys()
	years.sort()
	print 'analOPD_dateDist: NBadYear=%d' % nbadYear
	print 'Year,Freq'
	for y in years:
		print y,freqTbl[y]
		
	
def dbg_OPD_USC(dbfile):
	"collect details for USC coding oddities for set of probe CTypes"

	probeTbl = {"BATTERY": "PC242", 
				"BURGLARY-AUTO": "PC459",
				"BATTERY:SPOUSE/EX SPOUSE/DATE/ETC": "PC243 (E)(1)", 
				"BURGLARY-FORCIBLE ENTRY": "PC459"}
	
	probeCTypes = probeTbl.keys()

	currDB = sqlite.connect(dbfile)
	
	# check to make sure it loaded as expected
	curs = currDB.cursor()
	curs.execute("select tbl_name from sqlite_master")
	allTblList = curs.fetchall()
	assert ('OPD',) in allTblList, "analOPD: no OPD table?!"
	assert ('USC_OPD',) in allTblList, "analOPD: no OPD table?!"

	## first load OPD incidents
	
	matchTbl={}
	curs.execute('SELECT cid, ctype, dateStr, addr FROM OPD')
	for ri,cursorRow in enumerate(curs):
		if ri % 10000 == 0:
			print ri
			
		(cid, ctype, dateStr, opd_addr) = cursorRow
		try:
			cdate = datetime.strptime( dateStr, OPD_date_string)
		except Exception,e:
			# print 'matchOPD_USC_Crime: bad OPD date %d %s\n\t%s' % (ri,e,dateStr)
			continue

		matchTbl[cid] = (cdate,ctype, [])
		last_OPD_ri = ri
		
	## next load USC 
	
	curs.execute('SELECT ID1, RD, REPORTED, OCCURRED, UCR, STATUTE, DESCRIPTION, ADDRESS FROM USC_OPD')

	for ri,cursorRow in enumerate(curs):
		if ri % 10000 == 0:
			print ri

		(id1, rd, rptDateStr, occDateStr, ucr, statute, desc, usc_addr) = cursorRow
		if rd not in matchTbl:
			continue
		(cdate,ctype,prevList) = matchTbl[rd]
		
		if ctype not in probeCTypes:
			continue
		
		try:
			odate = datetime.strptime( occDateStr, USC_date_string)
			rdate = datetime.strptime( rptDateStr, USC_date_string)
		except Exception,e:
			continue

		d = cdate-odate
		if d.days != 0:
			continue
		
		prevList.append( (id1, ucr,statute,desc))
		matchTbl[rd] = (cdate,ctype, prevList)

	minYr = 2007
	maxYr = 2012

	outf = DataDir+'USC_dbug_sample.csv'
	print 'Writing USC dbg examples to',outf
	outs = open(outf,'w')
	outs.write('OPD_ID,USC_ID,CType,ODate,UCR,Statute,USC_Desc,RDate\n')

	missf = DataDir+'USC_dbug_miss.csv'
	print 'Writing  missing USC to',missf
	misss = open(missf,'w')
	misss.write('OPD_ID,Date\n')
	for cid,info in matchTbl.items():
		(cdate,ctype, mlist) = info
		nmatch = len(mlist)
		
		if nmatch==0 and cdate.year >= minYr and cdate.year <= maxYr:
			misss.write('%s,%s\n' % (cid,cdate))
			
		if nmatch==1:
			(id1, ucr,statute,desc) = mlist[0]
			if statute != probeTbl[ctype]:
				outs.write('%s,%s,"%s",%s,%s,%s,"%s",%s\n' % \
						(cid, id1, ctype, cdate, ucr, statute, desc, rdate))
		
	outs.close()
	misss.close()
	
DataDir = '/Data/corpora/c4a_oakland/'

if __name__ == '__main__': 
	
	dbfile = DataDir+'crime.db'
	loadCrimes(dbfile)
	analOPD_dateDist(dbfile)
	dbug_OPD_USC(dbfile)
