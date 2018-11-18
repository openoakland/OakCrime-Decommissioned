''' opdUtil: basic routines expected by opdata
Created on Nov 15, 2016

@author: rik
'''

import csv
import math
import string


def loadCSVTbl(csvf,keyTbl,keyname):
	'''create tbl -> key -> attrib for all rows in csvf
		using all attributes with header row names matching keys in keyTbl
		entries' accessed by keyname attribute
	'''

	csvTbl = {}
	reader = csv.DictReader(open(csvf))
	for i,entry in enumerate(reader):
		tbl = {}
		for bk,bkname in keyTbl.items():
			tbl[bkname] = entry[bk]
		bkey = tbl[keyname]
		csvTbl[bkey] = tbl
	
	return csvTbl

def freqHist(tbl):
	"Assuming values are frequencies, returns sorted list of (val,freq) items in descending freq order"
	def cmpd1(a,b):
		"decreasing order of frequencies"
		return cmp(b[1], a[1])

	
	flist = tbl.items()
	flist.sort(cmpd1)
	return flist

def distL2(x,y):
	'convert x=(lat,long) y=(lat,long) pairs to L2 distance; tolerate string values for lat,long'
	
	for i in [0,1]:
		x[i] = float(x[i])
		y[i] = float(y[i])
	ss = (x[0]-y[0])*(x[0]-y[0]) + (x[1]-y[1])*(x[1]-y[1])
	return math.sqrt(ss)

def basicStats(l):
	"Returns avg and stdev"
	if len(l) == 0:
		return(0.,0.)

	sum = 0
	for n in l:
		sum += n
	avg = float(sum) / len(l)

	sumDiffSq = 0.
	for n in l:
		sumDiffSq += (n-avg)*(n-avg)

	stdev = math.sqrt(sumDiffSq) / float(len(l))
	return (avg,stdev)

Punc2SpaceTranTbl = {ord(c): ord(u' ') for c in string.punctuation}
def cleanOPDtext(s):
	u = s.decode()
	news = u.translate(Punc2SpaceTranTbl)
	news = news.replace(' ',"_")
	return news

def cleanAddr(addr):
	newAddr = addr.replace('"','')  # to avoid quotes issues in CSV file
	newAddr = whitespace_pat.sub(' ',newAddr) # replace mult whitespace to single space
	newAddr = newAddr.strip().upper()
	if newAddr.endswith(', OAKLAND CA'):
		rpos = newAddr.rindex(',')
		newAddr = addr[:rpos]
	if newAddr.find('OAKLAND') != -1:
		abits = newAddr.split(',')
		newAddr = abits[0]
	if newAddr.endswith(' AVE'):
		newAddr = newAddr.replace(' AVE',' AV')

	return newAddr
	
def goodCIDDate(cid,year,tolerant=False):
	
	hpos = cid.index('-')
	# HACK: no Y2K issue in this data
	cidYrS = '20'+cid[:hpos]
	cidYr = int(cidYrS)
	if tolerant:
		# ASSUME: CID could be added later, but should be >= occurrance date
		return 0 <= cidYr-year <= 1
	else:
		return cidYr == year
	
def bldRatioPhrase(normFreq,ratio):	
	if ratio < 2.:
		# p = '%5.1f%% (%+6.2f s.d.) of' % ((ratio * 100),normFreq)
		p = '%5.1f%% of' % ((ratio * 100))
	else:
		# p = '%5.1f (%+6.2f s.d.) times the' % (ratio,normFreq)
		p = '%5.1f times' % (ratio)
	return p
