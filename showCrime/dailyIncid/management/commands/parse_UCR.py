# coding=utf8
''' parse_UCR_pdfquery

parse OPD weekly UCR reports

leans heavily on pdfplumber, esp. its TABLE extraction
	https://github.com/jsvine/pdfplumber says:
	Works best on machine-generated, rather than scanned, PDFs. Built on pdfminer and pdfminer.six.

Created on Nov 3, 2017
	update 12 Feb 19

@author: rik
'''

from collections import defaultdict
import pickle # cPickle for python2
from datetime import datetime
import glob 
import json
import os
import re
import sys

import pdfplumber

OPD_UCR_DateFormat = '%Y-%b-%d'

IgnoredLabels = ['Part 1 Crimes','THIS REPORT IS HIERARCHY BASED.',
				'(homicide, aggravated assault, rape, robbery)' ]

LabelUCROrder = [u'Violent Crime Index', 
				u'Homicide – 187(a)PC', 
				u'Homicide – All Other *', 
				u'Aggravated Assault', 
				# 190212: new labeles
				# u'Shooting with injury – 245(a)(2)PC', 
				u'Assault with a firearm – 245(a)(2)PC',
				# u'Subtotal - Homicides + Injury Shootings',		 
				u'Subtotal - Homicides + Firearm Assault',
				
				u'Shooting occupied home or vehicle – 246PC', 
				u'Shooting unoccupied home or vehicle – 247PC', 
				u'Non-firearm aggravated assaults', 
				u'Rape', 
				u'Robbery', 
				u'Firearm', 
				u'Knife', 
				u'Strong-arm', 
				u'Other dangerous weapon', 
				# u'Residential  robbery – 212.5(A)PC', 
				u'Residential  robbery – 212.5(a)PC', 
				# u'Carjacking – 215(A) PC', 
				u'Carjacking – 215(a) PC', 
				u'Burglary', 
				u'Auto', 
				u'Residential', 
				u'Commercial', 
				u'Other (Includes boats, aircraft, and so on)', 
				u'Unknown', 
				u'Motor Vehicle Theft', 
				u'Larceny', 
				u'Arson', 
				u'Total' ]

IgnoreStatLbl = ['Author', 'CreateDate', 'ModDate', 'fname', 'fromDate', 'rptDate', 'toDate']

FixFilePat = {re.compile(r'Area(\d)WeeklyCrimeReport11Jun17Jun18.pdf'): '180619_Area %d Weekly Crime Report 11Jun - 17Jun18.pdf'}

def dateConvert(o):
	if isinstance(o, datetime):
		return o.strftime('%y%m%d')

def parse_UCR_pdf(inf,rptDate,fdate,tdate,verbose=False):
	
	try:
		pdf = pdfplumber.open(inf)
		docinfo = pdf.metadata

		pdf1 = pdf.pages[0]	
		allTbl = pdf1.extract_tables()
	except Exception as e:
		print('parse_UCR_pdf: cant load',inf,e)
		return None

	# .extract_table returns a list of lists, with each inner list representing a row in the table. 
	tbl = allTbl[0]
	
	if verbose:
		print('parse_UCR_pdf: Table found %d x %d' % (len(tbl),len(tbl[0]) ))
	
	statTbl = {}
	
	for i in range(len(tbl)):
		lbl = tbl[i][0]
		ignore = False
		for ignoreLine in IgnoredLabels:
			if lbl == None or lbl.startswith(ignoreLine):
				ignore = True
				break
					
		if ignore:
			continue
			
		vals = tbl[i][1]
		
		vals = vals.replace(' ','') # multi-digit numbers have intermediate spaces

		if vals=='-':
			val = 0
		else:
			try:
				val = int(vals)
			except Exception as e:
				print(i,lbl,vals,e)
				continue
		
		if verbose:
			print(i,lbl,val)
		statTbl[lbl] = val
				
	statTbl['Author'] = docinfo['Author']
	statTbl['CreateDate'] = docinfo['CreationDate']
	statTbl['ModDate'] = docinfo['ModDate']
	statTbl['fname'] = fname
	statTbl['rptDate'] = rptDate
	statTbl['fromDate'] = fdate
	statTbl['toDate'] = tdate

	if verbose:
		print('parse_UCR_pdf: NKey=%d %s' %(len(statTbl.keys()),inf))
	return statTbl

def combineWeeksUCR(allStats):

	allKeys = list(allStats.keys())
	allKeys.sort()
	
	# allLblTbl: lbl -> date -> div -> freq
	allLblTbl = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
	for k in allKeys:
		divs,rptDate = k.split('_')
		div = int(divs)
		
		# NB: need to distinguish stat's lbl which may have \n from mlbl used in LabelUCROrder
		for slbl in allStats[k]:
			if slbl.find('\n') != -1:
				mlbl = slbl.split('\n')[0]
			else:
				mlbl = slbl
			if mlbl in LabelUCROrder:
				allLblTbl[mlbl][rptDate][div] =  allStats[k][slbl]
			elif mlbl not in IgnoreStatLbl:
				print("combineWeeksUCR: unknown label?! %s %s" % (mlbl,k))
				
	return allLblTbl

def rptAllStats(allLblTbl,outf):
	"""produce CSV file of UCR crime categories X dates, breaking out indiv divisions' subtotals
	"""
	allDatesSet = set()
	for lbl in allLblTbl.keys():
		allDatesSet.update(allLblTbl[lbl].keys())
	allDates = list(allDatesSet)
	allDates.sort()

	# ASSUME five OPD division
	OPDivs = range(1,6)
	outs = open(outf,'w')

	line = '"UCRCategory \ Date"'
	for dates in allDates:
		dateDup = 6 * (','+dates)
		line += ('%s' % (dateDup))
	outs.write(line+'\n')
	
	line = 'Division'
	for dates in allDates:
		for div in OPDivs:
			line += (',%d' % (div))
		line += (',tot')
	outs.write(line+'\n')

	for lbl in LabelUCROrder:
		albl = lbl.encode(encoding='utf_8', errors='strict').decode('ascii','ignore')
		line = '"%s"' % (albl)
		for dates in allDates:
			tot = 0
			for div in OPDivs:
				if dates in allLblTbl[lbl] and div in allLblTbl[lbl][dates]:
					val = int(allLblTbl[lbl][dates][div])
				else:
					val = 0
				line += (',%d' % (val))
				tot += val
			line += (',%d' % (tot))
		line += '\n'
		outs.write(line)

	outs.close()

def rptSummStats(allLblTbl,outf):
	"""produce CSV file of UCR crime categories X dates, summing divisions' subtotals
	also echo crime categories across all data
	"""
	allDatesSet = set()
	for lbl in allLblTbl.keys():
		allDatesSet.update(allLblTbl[lbl].keys())
	allDates = list(allDatesSet)
	allDates.sort()

	lblTots = defaultdict(int)
	
	# ASSUME five OPD division
	OPDivs = range(1,6)
	outs = open(outf,'w')

	line = '"UCRCategory \ Date"'
	for dates in allDates:
		line += (',%s' % (dates))
	outs.write(line+'\n')
	for lbl in LabelUCROrder:
		albl = lbl.encode(encoding='utf_8', errors='strict').decode('ascii','ignore')
		line = '"%s"' % (albl)
		for dates in allDates:
			tot = 0
			for div in OPDivs:
				if dates in allLblTbl[lbl] and div in allLblTbl[lbl][dates]:
					tot += int(allLblTbl[lbl][dates][div])
			lblTots[lbl] += tot
			line += (',%s' % (tot))
		line += '\n'
		outs.write(line)
	outs.close()
	
	for lbl in LabelUCROrder:
		if lblTots[lbl] == 0:
			print('%s\t%d <=======' % (lbl,lblTots[lbl]))
		else:	
			print('%s\t%d' % (lbl,lblTots[lbl]))

# Police Area 3 Weekly Crime Reports
DivDirName_pat = re.compile(r'Police Area (\d) Weekly Crime Reports')

# fname = '190114_Area 2 Weekly Crime Report 07Jan - 13Jan19.pdf'
FileName_pat = re.compile(r'(\d+)_Area (\d) Weekly Crime Report (\d+)(\D+) - (\d+)(\D+)(\d+).pdf')
	
def fname2dates(fname):
	# 190212
	# fname = '190114_Area 2 Weekly Crime Report 07Jan - 13Jan19.pdf'
	
	match = FileName_pat.match(fname)
	if match:
		# match.groups() = ('190114', '2', '07', 'Jan', '13', 'Jan', '19')
		(postDateStr,areaNum,fday,fmon,tday,tmon,yr) = match.groups()
	else:
		print('fname2dates: cant parse',fname)
		# import pdb; pdb.set_trace()
		return None,None,None
	
	# HACK: common exceptions (:
	if tmon == 'Sept':
		tmon = 'Sep'
	if yr.startswith('20'):
		yr = yr[2:]
	
	rptDate = datetime.strptime(postDateStr,'%y%m%d')
	try:
		fdate = datetime.strptime('%s%s%s' % (fday,fmon,yr),'%d%b%y')
		tdate = datetime.strptime('%s%s%s' % (tday,tmon,yr),'%d%b%y')
	except:
		print('fname2dates: bad dates?', fname)
		# import pdb; pdb.set_trace()
		fdate = tdate = None
	
	return  rptDate,fdate,tdate 

if __name__ == '__main__':

	dataDir = '/Data/c4a-Data/OAK_data/OPD-UCR/190212-harvest/'

	begTime = datetime.now()
	dateStr = begTime.strftime('%y%m%d')	
	jsonFile = dataDir + 'UCR_WeeklyStats_%s.json'  % (dateStr)
	statsOnly = False
	
	if statsOnly:
		print('parse_UCR: loading data from JSON file',jsonFile)
		allStats = json.load(open(jsonFile))
		print('parse_UCR: NStatFiles = %d' % (len(allStats)))

	else:

		rptFreq = 10
		checkPointFreq = 50
		
		divDirList = glob.glob(dataDir+'Police Area *')
		
		allPDFiles = []
		for divDirPath in divDirList:
			if not os.path.isdir(divDirPath):
				continue
	
			ddpath,divDir = os.path.split(divDirPath)
	
			match = DivDirName_pat.match(divDir)
			if match:
				# match.groups() = ('2')
				divNumStr = match.groups()
				divNum = int(divNumStr[0])
			else:
				print('parse_UCR: cant parse divDir',divDir)
				continue
	
			print('parse_UCR: NFiles=%d searching files for Div=%d : %s' % (len(allPDFiles),divNum,divDir ))
			
			for divSubDir in  glob.glob(divDirPath+'/*'):
				
				# NB: pdfs are posted at top-level within division?!
				if os.path.isfile(divSubDir):
					if divSubDir.endswith('.pdf'):
						allPDFiles.append( (divNum,divSubDir) )
					else:
						print('parse_UCR: skipping non-PDF file',divSubDir)
						continue
					
				if os.path.isdir(divSubDir):
					for f in glob.glob(divSubDir+'/*.pdf'):
						allPDFiles.append( (divNum,f) )
		
		print('parse_UCR: NFiles found=%d' % (len(allPDFiles)))
	
		nbad = 0
		allStats = {}
		for i,info in enumerate(allPDFiles):
			# NB: checkpoint saved at top of loop, 
			if i > 0 and (i % checkPointFreq == 0):
				cpjson = dataDir + 'UCR_WeeklyStats_%s_cp-%d.json'  % (dateStr,i)
				json.dump(allStats,open(cpjson,'w'),indent=1,default=dateConvert)

	
			divNum,pdff = info
			dirname,fname = os.path.split(pdff)
			
			for fixPat in FixFilePat.keys():
				match = fixPat.match(fname)
				if match:
					# match.groups() = ('2')
					divNumStr = match.groups()
					divNum = int(divNumStr[0])
					newfname = FixFilePat[fixPat] % divNum
					print('parse_UCR: fixing bad fname: %s <- %s' % (newfname,fname))
					fname = newfname
					
						
			# fname = '190114_Area 2 Weekly Crime Report 07Jan - 13Jan19.pdf'		
			rptDate,fdate,tdate = fname2dates(fname)
			
			try:
				statTbl = parse_UCR_pdf(pdff,rptDate,fdate,tdate)
			except Exception as e:
				print('parse_UCR: cant process %d %s %s' % (i,fname,e))
				nbad += 1
				continue	
			if statTbl==None:
				print('parse_UCR: cant process (None) %d %s' % (i,fname))
				nbad += 1
				continue
			
			if rptDate == None:
				rptDateStr = 'missDate-%d' % (i)
			else:
				rptDateStr = rptDate.strftime('%y%m%d')
			k = '%d_%s' % (divNum,rptDateStr)
			if k in allStats:
				print('parse_UCR_Pdf: duplicate keys?! %s\n\t%s\n\t%s' % \
					(k,statTbl,allStats[k]))
				continue
			allStats[k] = statTbl
			
			# NB: reporting at end of loop, 
			if i > 0 and (i % rptFreq == 0):
				elapTime = datetime.now() - begTime
				print('%d %s done (%s sec)' % (i,k,elapTime.total_seconds()))
	
		print('parse_UCR: NStatFiles = %d' % (len(allStats)))
		json.dump(allStats,open(jsonFile,'w'),indent=1,default=dateConvert)
	
	allLblTbl = combineWeeksUCR(allStats)
	
	statFile = dataDir + 'UCR_WeeklyStats_%s.csv' % (dateStr)
	rptAllStats(allLblTbl, statFile)
	statFile = dataDir + 'UCR_WeeklySummStats_%s.csv' % (dateStr)
	rptSummStats(allLblTbl, statFile)
	

	
