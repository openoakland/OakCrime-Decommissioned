''' stopData: parse 2015 stop data from OPD/Figuroa

Created on Jun 21, 2016

@author: rik
'''

from collections import defaultdict
import csv
import datetime
import json
import os

RaceNames = {'asian': 0,'aa': 1,'hispanic': 2,'other': 3,'white': 4}
RaceNameList = RaceNames.keys()
RaceNameList.sort()  # ['asian','black','hispanic','other','white']

KnownBeats = ['01X', '02X', '02Y', '03X', '03Y', '04X', '05X', '05Y', '06X', '07X',
			'08X', '09X', '10X', '10Y', '11X', '12X', '12Y', '13X', '13Y', '13Z',
			'14X', '14Y', '15X', '16X', '16Y', '17X', '17Y', '18X', '18Y', '19X',
			'20X', '21X', '21Y', '22X', '22Y', '23X', '24X', '24Y', '25X', '25Y',
			'26X', '26Y', '27X', '27Y', '28X', '29X', '30X', '30Y', '31X', '31Y',
			'31Z', '32X', '32Y', '33X', '34X', '35X', '35Y', '77X', '99X']


def loadFullStops(inf):
	reader = csv.DictReader(open(inf))

	# beatTbl: beatName -> encType -> encResult -> race -> [ (reason, searchType, searchRes, sex) ]
	beatTbl = defaultdict(lambda: 
							defaultdict(lambda: 
									defaultdict(lambda: 
											defaultdict(list))))
	nstop = 0
	encTypeTbl = defaultdict(int)
	encResultTbl = defaultdict(int)
	raceTbl = defaultdict(int)
	
	for i,entry in enumerate(reader):
		# ContactDate,Beat,EncounterType,ReasonForEncounter,ResultOfEncounter,Search,TypeOfSearch,ResultOfSearch,Race,Sex
		date = entry['ContactDate'].strip()
		beat = entry['Beat'].strip()
		encType = entry['EncounterType'].strip().lower()
		reasonforencounter = entry['ReasonForEncounter'].strip().lower()
		encResult = entry['ResultOfEncounter'].strip().lower()
		search = entry['Search'].strip().lower()
		searchType = entry['TypeOfSearch'].strip().lower()
		searchRes = entry['ResultOfSearch'].strip().lower()
		race = entry['Race'].strip().lower()
		sex = entry['Sex'].strip().lower()
		nstop += 1
		if beat not in KnownBeats:
			print 'loadFullStops: bad beat?!',i,beat
			continue
		if race=='afr american':
			race='aa'
		if race not in RaceNameList:
			print 'loadFullStops: bad race?!',i,race
			continue
		
		encTypeTbl[encType] += 1
		encResultTbl[encResult] += 1
		raceTbl[race] += 1
		
		beatTbl[beat][encType][encResult][race].append ( (date,reasonforencounter,searchType,searchRes,sex) )
		
	print 'loadFullStops: done.  NStop=%d' % (nstop)
	print 'loadFullStops: Types', encTypeTbl
	print 'loadFullStops: Results', encResultTbl
	print 'loadFullStops: Race', raceTbl
	
	return beatTbl

def bldBeatSummTbl(beatTbl):
	'''Summarized version for JSON
	NB: encType, encResult values collapsed to smaller set of alternatives for viz
	'''
	# beatTbl: beatName -> encType -> encResult -> race -> [ (reason, searchType, searchRes, sex) ]

	# beatSummTbl: beatName -> encType -> encResult -> race -> freq
	beatSummTbl = defaultdict(lambda: 
							defaultdict(lambda: 
									defaultdict(lambda: 
											defaultdict(int))))

	encTypeTbl = defaultdict(int)
	encResultTbl = defaultdict(int)
	raceTbl = defaultdict(int)

	allBeats = beatTbl.keys()
	allBeats.sort() # for debugging
	for beat in allBeats:
		for encType in beatTbl[beat]:
			
			if encType=='vehicle':
				encTypeIdx = 0
			elif encType=='pedestrian':
				encTypeIdx = 1
			else:
				encTypeIdx = 2
			
			for encResult in beatTbl[beat][encType]:
				if encResult.find('arrest') == -1:
					encResultIdx = 0
				else:
					encResultIdx = 1

				for race in  beatTbl[beat][encType][encResult]:
					nrstop = len(beatTbl[beat][encType][encResult][race])
					raceIdx = RaceNames[race]
					beatSummTbl[beat][encTypeIdx][encResultIdx][raceIdx] += nrstop
					
					encTypeTbl[encTypeIdx] += nrstop
					encResultTbl[encResultIdx] += nrstop
					raceTbl[raceIdx] += nrstop
		
	print 'bldBeatSummTbl: Types',encTypeTbl
	print 'bldBeatSummTbl: Results',encResultTbl
	print 'bldBeatSummTbl: Race',raceTbl
			
	return beatSummTbl

def rptBeatSumm(beatSummTbl,outf):
	outs = open(outf,'w')
	outs.write('Beat,Tot,Vehicle,Ped,Other,NonArrest,Arrest\n')
	allBeats = beatSummTbl.keys()
	allBeats.sort()
	allStop = 0
	for beat in allBeats:
		outs.write('%s' % (beat))
		beatTot=0
		etVec = [0,0,0]
		erVec = [0,0]
		for encTypeIdx in beatSummTbl[beat]:
			for encResultIdx in beatSummTbl[beat][encTypeIdx]:
				tot = 0
				for race in beatSummTbl[beat][encTypeIdx][encResultIdx]:
					tot += beatSummTbl[beat][encTypeIdx][encResultIdx][race]
				etVec[encTypeIdx] += tot
				erVec[encResultIdx] += tot
				beatTot += tot
		
		allStop += beatTot
		outs.write(',%d' % (beatTot))
		for et in etVec:
			outs.write(',%d' % (et))
		for er in erVec:
			outs.write(',%d' % (er))
		outs.write('\n')
			
	outs.write('TOTAL,%d\n' % allStop)
	print 'rptBeatSumm: NStop=',allStop
	outs.close()

if __name__ == '__main__':

	StopDir = '/Data/sharedData/c4a_oakland/OAK_data/StopData/'
	stopFile = StopDir + 'StopData_2015.csv'
	
	beatStopTbl = loadFullStops(stopFile)

	beatSummTbl = bldBeatSummTbl(beatStopTbl)

	beatRptFile = StopDir + 'beatReport.csv'
	rptBeatSumm(beatSummTbl,beatRptFile)
	
	stopSummJSONFile = StopDir + 'beatStopSumm.json'
	json.dump(beatSummTbl,open(stopSummJSONFile,'w'))

