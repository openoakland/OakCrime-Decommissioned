''' parseSocrataHarvest: parse logs left by showCrime.dailyIncid harvestSocrata 
Created on Jul 7, 2017

@author: rik
'''

from collections import defaultdict
from datetime import datetime
import glob
import re
import sys

HSRE1 = 'harvestSince: Date=([0-9-:T]+) NResult=([0-9]+)'
HSRE2 = 'do_harvest: NAdd=([0-9]+) NUpdate=([0-9]+) NSame=([0-9]+) NCrimeCat=([0-9]+) NGeo=([0-9]+)'
HSRE3 = "<harvestSocrata ' (.+) ' >"

HSPat1 = re.compile(HSRE1)
HSPat2 = re.compile(HSRE2)
HSPat3 = re.compile(HSRE3)

Socrata_date_format = '%Y-%m-%dT%H:%M:%S' # 2013-12-04T19:00:00
Shell_date_format = '%a %b %d %H:%M:%S UTC %Y' # Thu Jul 6 08:08:01 UTC 2017 
DateOnlyStrFormat = '%y%m%d'
TimeOnlyStrFormat = '%H:%M'

def parseHS(logDir):
	logFiles = glob.glob(logDir+'*')
	print('parseHS: NFiles=%d' % (len(logFiles)))
	
	statTbl = {} # dateTime -> {}
	inRcd = False
	for inf in logFiles:
		ins = open(inf)
		for line in ins.readlines():
			if line.startswith('<harvestSocrata '):
				inRcd = True
				currStats = {}
				m = HSPat3.match(line)
				try:
					(dtstr,) = m.groups()
					harvestDateTime = datetime.strptime( dtstr, Shell_date_format)
					currStats['harvestDateTime'] = harvestDateTime
				except Exception as e:
					print('parseHS: Bad harvest line?! %s,\n\t%s' % (e,line))
					continue
					
				
			elif line.startswith('</harvestSocrata>'):
				currDT = currStats['harvestDateTime']
				statTbl[currDT] = currStats
				inRcd = False
				
			elif line.startswith('harvestSince: Date'):
				m = HSPat1.match(line)
				try:
					(dtstr,nresult) = m.groups()
				except Exception as e:
					print('parseHS: Bad date line?! %s,\n\t%s' % (e,line))
					continue
				begDateTime = datetime.strptime( dtstr, Socrata_date_format)
				currStats['begDateTime'] = begDateTime
				currStats['nresult'] = int(nresult)
				
			elif line.startswith('do_harvest: NAdd'):
				m = HSPat2.match(line)
				try:
					(nadd,nup,nsame,ncc,ngeo) = m.groups()
				except Exception as e:
					print('parseHS: Bad add line?! %s,\n\t%s' % (e,line))
					continue
				currStats['nadd'] = int(nadd)
				currStats['nup'] = int(nup)
				currStats['nsame'] = int(nsame)
				currStats['ncc'] = int(ncc)
				currStats['ngeo'] = int(ngeo)
			
		print('parseHS: %s NRcd=%d' % (inf,len(statTbl)))
		
	print('parseHS: NRcd=%d' % (len(statTbl)))
	return statTbl
	
if __name__ == '__main__':
	# logDir = '/Data/sharedData/c4a_oakland/OAK_data/socrata/harvest-logs/'
	
	hsDir = sys.argv[1] # include the trailing slash on the dir name!
	logDir = '/Data/sharedData/c4a_oakland/OAK_data/socrata/harvest-logs/' + hsDir
	statTbl = parseHS(logDir)
	allDT = statTbl.keys()
	allDT.sort()
	outf = logDir + 'harvestStats.csv'
	outs = open(outf,'w')
	outs.write('HarvestDate,Time,BegDate,BegTime,NAdd,NUp,NSame,Tot,NCC,NGeo\n')
	for dt in allDT:
		hdateStr = dt.strftime(DateOnlyStrFormat)
		htimeStr = dt.strftime(TimeOnlyStrFormat)
		begDT = statTbl[dt]['begDateTime']
		begDateStr = begDT.strftime(DateOnlyStrFormat)
		begTimeStr = begDT.strftime(TimeOnlyStrFormat)
		nadd = statTbl[dt]['nadd']
		nup = statTbl[dt]['nup']
		nsame = statTbl[dt]['nsame']
		ncc = statTbl[dt]['ncc']
		ngeo = statTbl[dt]['ngeo']
		tot = nadd + nup + nsame
		outs.write('%s,%s,%s,%s,%d,%d,%d,%d,%d,%d\n' % \
				 (hdateStr,htimeStr,begDateStr,begTimeStr,nadd,nup,nsame,tot,ncc,ngeo))
		
	outs.close()