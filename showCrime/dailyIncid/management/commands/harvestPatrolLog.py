''' harvestPatrolLogs:  Capture new OPD patrol logs from box.com

@date 181218

@author: rik
'''

from datetime import datetime,timedelta
import dateutil.parser
import environ
import json
import os
import pickle
import pytz
import socket
import sys

from django.core.management.base import BaseCommand, CommandError

import boxsdk 
import googlemaps
import mapbox

from showCrime.settings import MEDIA_ROOT
from dailyIncid.models import *
from dailyIncid.management.commands import parsePatrolLog as parsePL
from dailyIncid.management.commands import postPatrolLog as postPL

env = environ.Env(DEBUG=(bool, False), )

GoogleMapAPIKey = env('GoogleMapAPIKey')
BoxEnterpriseID = env('BoxEnterpriseID')
BoxHarvestBotUserID = env('BoxHarvestBotUserID')
BoxHarvestBotEmail= env('BoxHarvestBotEmail')
BoxDevpToken = env('BoxDevpToken')
BoxClientID = env('BoxClientID')
BoxClientSecret = env('BoxClientSecret')
BoxPublicKeyID = env('BoxPublicKeyID')
BoxRSAFile = env('BoxRSAFile')
BoxPassPhrase = env('BoxPassPhrase')

HarvestRootDir = MEDIA_ROOT + '/PLHarvest/'

RFC3339Format = "%Y-%m-%dT%H:%M:%S%z"
OPDPatrolFolderID =  '8881131962' 

def awareDT(naiveDT):
	utc=pytz.UTC
	return utc.localize(naiveDT)
	
def getMonthFiles(monthFolderID,harvDir):
	
	harvestedFiles = []
	
	items = CurrBoxClient.folder(folder_id=monthFolderID).get_items(limit=100, offset=0)
	nharvest = 0
	nskip = 0
	nerr = 0
	for item in items:
		fpath = harvDir+item.name
		if os.path.exists(fpath):
			print('getMonthFiles: skipping',item.id,item.name)
			nskip += 1
			continue
		try:
			box_file = CurrBoxClient.file(file_id=item.id).get()
			with open(fpath, 'wb') as outs:
				box_file.download_to(outs)
			harvestedFiles.append( (monthFolderID,fpath) )
			
		except Exception as e:
			print('getMonthFiles: cant get file?!',item.id,item.name)
			nerr += 1
		nharvest += 1
	print('getMonthFiles: NHarvest=%d NSkip=%d Nerr=%d' % (nharvest,nskip,nerr))
	
	return harvestedFiles
	
	
def getMiss(missInfo):

	pathStr,id,kidsP = missInfo
	kbits = pathStr.split('_')
	kbits.insert(0,HarvestRootDir)
	# NB: splat to provide all of kbits
	path = os.path.join(*kbits)
	if kidsP:
		try:
			os.mkdir(path)
			print('getMiss: directory created',id,path)
		except Exception as e:
			print('getMiss: directory already exists?!',path,e)
		return None
	try:
		box_file = CurrBoxClient.file(file_id=id).get()
		with open(path, 'wb') as outs:
			box_file.download_to(outs)
		return (pathStr)
	except Exception as e:
		print('getMiss: cant get file?!',id,path,e)
		return None
		

def filterNewDLog(newIncid):
	# after parseOPDLog_PDForm.filterNewDLogTbl()
	# drop any dlog in newIncid that is already in database
	# NB: prevDLog, newIncid may have cid keys with _%d suffix!
	# 	newIncid cid_foo could match ANY cid_bar in prevDLog!
	
	newDLog = {}
	ndup=0	
	nnew=0

	allNCID = list(newIncid.keys())
	allNCID.sort()

	for ncid in allNCID:
		
		# dlogData = True AND lastModDateTime > startDate
		# and also ncid/cid matches
		
		assert False, " 2do ASAP: do query against OakCrime"
		
		newDLog[ncid] = newIncid[ncid].copy()
		
	print('filterNewDLogTbl: NIn=%d NDup=%d NNew=%d/%d' % \
			(len(newIncid),ndup,nnew,len(newDLog)))
			
	return newDLog

def connectJWTAuth():
	
	auth = boxsdk.JWTAuth(
		client_id=BoxClientID,
		client_secret=BoxClientSecret,
		enterprise_id=BoxEnterpriseID,
		jwt_key_id=BoxPublicKeyID,
		rsa_private_key_file_sys_path=BoxRSAFile,
		rsa_private_key_passphrase=BoxPassPhrase,
		store_tokens=store_tokens)
	
	# https://github.com/box/box-python-sdk#authorization
	# access_token = auth.authenticate_instance()
	
	client = boxsdk.Client(auth)
	return client

def store_tokens(access_token, refresh_token):
	# store the tokens at secure storage (e.g. Keychain)

	# The SDK will keep the tokens in memory for the duration of the Python
	# script run, so you don't always need to pass store_tokens.
	
	# print('store_tokens',access_token, refresh_token)
	pass

def makeBoxConnection():
	global CurrBoxClient
	CurrBoxClient = connectJWTAuth()

	currentUser = CurrBoxClient.user().get()
	currLogin = currentUser.login
	currName = currentUser.name
	print('connectBox: login=%s name=%s' % (currLogin,currName) )
	
	return CurrBoxClient

def makeGConnection():
	
	global CurrGClient
	CurrGClient = googlemaps.Client(key=GoogleMapAPIKey)

	return CurrGClient

def pprintOC(oco):
	ppstr = '%s\n' % (oco.opd_rd)
	allFlds = list([f.name for f in OakCrime._meta.fields])
	allFlds.sort()
	for f in allFlds:
		ppstr += '\t%s: "%s"\n' % (f,getattr(oco, f))
	return ppstr
	
def compBox2Dir(boxIDTbl):
	'''check which kids in boxIDTbl are found under rootPath
	returns list: (k,info['id'],kidsP)
	'''

	missing = []
	nfnd = 0
	ndirMismatch = 0
	for k, info in boxIDTbl.items():
		if k=='root':
			continue
		kbits = k.split('_')
		kbits.insert(0,HarvestRootDir)
		# NB: splat to provide all of kbits
		path = os.path.join( *kbits)
		if os.path.exists(path):
			nfnd += 1
			dirP = os.path.isdir(path)
			if (dirP and 'kids' not in info) or (not dirP and 'kids' in info):
				ndirMismatch += 1
				print('compBox2Dir: dir/file mismatch?!',k)
		else:
			kidsP = 'kids' in info
			missing.append( (k,info['id'],kidsP) )
	print('compBox2Dir: NEntries=%d NFnd=%d NMiss=%d NDirMismatch=%d' % (len(boxIDTbl),nfnd,len(missing),ndirMismatch))
	return missing


def modifiedSince(boxIDTbl,sinceDate):
	'''return filtered boxIDTbl with modified_at dates >= sinceDate
	'''

	modTbl = {}
	nfnd = 0
	for k, info in boxIDTbl.items():
		if k=='root':
			continue
		boxDT = info['mdate']
		# pyDT = datetime.strptime(boxDT,RFC3339Format)
		pyDT = dateutil.parser.parse(boxDT)
		pyDate = pyDT.date()
		if pyDate >= sinceDate:
			nfnd += 1
			modTbl[k] = info
	print('getModifiedSince: NModified since %s: %d' % (sinceDate,len(modTbl)))	
	return modTbl

def getBoxIDs(verbose=True):
	'''traverse all folders under OPDPatrolFolderID FROM SCRATCH to build boxIDTbl
	'''	
	
	nskip = 0
	boxIDTbl = {'root': {'id': OPDPatrolFolderID,'kids': []} }
	yearFolders = CurrBoxClient.folder(folder_id=OPDPatrolFolderID).get_items(limit=100, offset=0)
	for yrf in yearFolders:
		if yrf.type != 'folder':
			print('getBoxIDs: skipping year non-folder %s %s %s' % (yrf.id,yrf.type,yrf.name))
			nskip += 1
			continue
		# NB: '_' used to separate key bits; make sure it isn't already there
		ykey = yrf.name.strip().lower().replace('_','#')
		if ykey in boxIDTbl:
			print('getBoxIDs: duplicate year name?! new: %s %s %s\n\t prevID:%s' % (yrf.id,yrf.type,ykey,boxIDTbl[ykey]['id']))
			nskip += 1
			continue			
		boxIDTbl['root']['kids'].append(ykey)
		yrInfo = CurrBoxClient.folder(folder_id=yrf.id).get(fields=['modified_at'])
		boxIDTbl[ykey] = {'id': yrf.id,'mdate': yrInfo.modified_at,'kids': []}
		for monf in yrf.get_items(limit=100):
			if monf.type != 'folder':
				print('getBoxIDs: skipping month non-folder %s / %s %s %s' % (ykey,monf.id,monf.type,monf.name))
				nskip += 1
				continue
			mkey = ykey + '_' + monf.name.strip().lower().replace('_','#')
			if mkey in boxIDTbl:
				print('getBoxIDs: duplicate month name?! new: %s %s %s\n\t prevID:%s' % \
					(mkey,monf.id,monf.type,boxIDTbl[mkey]['id']))
				nskip += 1
				continue			
			boxIDTbl[ykey]['kids'].append(mkey)
			monInfo = CurrBoxClient.folder(folder_id=monf.id).get(fields=['modified_at'])
			boxIDTbl[mkey] = {'id': monf.id,'mdate': monInfo.modified_at,'kids': []}
			for dayf in monf.get_items(limit=100):
				if dayf.type != 'file':
					print('getBoxIDs: skipping day non-file %s / %s %s %s' % \
						(mkey,dayf.id,dayf.type,dayf.name))
					nskip += 1
					continue
				dkey = mkey + '_' + dayf.name.strip().lower().replace('_','#')
				if dkey in boxIDTbl:
					print('getBoxIDs: duplicate day name?! new: %s / %s %s %s %s' % \
						(dkey, dayf.id, dayf.type, dayf.name, boxIDTbl[dkey]['id']))
					nskip += 1
					continue
				boxIDTbl[mkey]['kids'].append(dkey)
				dayInfo = CurrBoxClient.file(file_id=dayf.id).get(fields=['modified_at'])
				boxIDTbl[dkey] = {'id': dayf.id,'mdate': dayInfo.modified_at}  # NB, no kids for files
			if verbose:
				print('Month %s: %d day files' % (mkey,len(boxIDTbl[mkey]['kids'])))
				
		if verbose:
			print('Year %s: %d month folders' % (ykey,len(boxIDTbl[ykey]['kids'])))
	
	if verbose:
		print('Root: %d year folders' % (len(boxIDTbl['root']['kids'])))
	
	return boxIDTbl

def updateBoxIDTbl(boxIDTbl,lastUpdate):
	'''traverse all folders under OPDPatrolFolderID for changes since lastUpdate
	'''	

	nskip = 0
	yearFolders = CurrBoxClient.folder(folder_id=OPDPatrolFolderID).get_items(limit=100, offset=0)
	for yrf in yearFolders:
		if yrf.type != 'folder':
			print('updateBoxIDTbl: skipping year non-folder %s %s %s' % (yrf.id,yrf.type,yrf.name))
			nskip += 1
			continue
		# NB: '_' used to separate key bits; make sure it isn't already there
		ykey = yrf.name.strip().lower().replace('_','#')
		yrInfo = CurrBoxClient.folder(folder_id=yrf.id).get(fields=['modified_at'])
		if ykey not in boxIDTbl['root']['kids']:
			boxIDTbl['root']['kids'].append(ykey)	
		if ykey not in boxIDTbl:
			boxIDTbl[ykey] = {'id': yrf.id,'mdate': yrInfo.modified_at,'kids': []}
		yrModDT = dateutil.parser.parse(yrInfo.modified_at)
		prevYrModDT = dateutil.parser.parse(boxIDTbl[ykey]['mdate'])
		if not (yrModDT > prevYrModDT and yrModDT > lastUpdate):
			continue
		
		print('updateBoxIDTbl: updating year folder %s %s modified %s' % (yrf.id,yrf.name,yrInfo.modified_at))
		boxIDTbl[ykey]['mdate'] = yrInfo.modified_at
		for monf in yrf.get_items(limit=100):
			if monf.type != 'folder':
				print('getBoxIDs: skipping month non-folder %s / %s %s %s' % (ykey,monf.id,monf.type,monf.name))
				nskip += 1
				continue
			mkey = ykey + '_' + monf.name.strip().lower().replace('_','#')
			monInfo = CurrBoxClient.folder(folder_id=monf.id).get(fields=['modified_at'])
			if mkey not in boxIDTbl[ykey]['kids']:
				boxIDTbl[ykey]['kids'].append(mkey)				
			if mkey not in boxIDTbl:
				boxIDTbl[mkey] = {'id': monf.id,'mdate': monInfo.modified_at,'kids': []}
			monModDT = dateutil.parser.parse(monInfo.modified_at)
			prevMonModDT = dateutil.parser.parse(boxIDTbl[mkey]['mdate'])
			if not (monModDT > prevMonModDT and monModDT > lastUpdate):
				continue
			
			print('updateBoxIDTbl: updating month folder %s %s modified %s' % (monf.id,monf.name,monInfo.modified_at))		
			boxIDTbl[mkey]['mdate'] = monInfo.modified_at
			for dayf in monf.get_items(limit=100):
				if dayf.type != 'file':
					print('getBoxIDs: skipping day non-file %s / %s %s %s' % \
						(mkey,dayf.id,dayf.type,dayf.name))
					nskip += 1
					continue
				dkey = mkey + '_' + dayf.name.strip().lower().replace('_','#')
				dayInfo = CurrBoxClient.file(file_id=dayf.id).get(fields=['modified_at'])
				
# 				if dkey not in boxIDTbl[mkey]['kids']:
# 					boxIDTbl[mkey]['kids'].append(dkey)	
# 				if dkey not in boxIDTbl:
# 					boxIDTbl[dkey] = {'id': dayf.id,'mdate': dayInfo.modified_at} # NB, no kids for files

				if dkey in boxIDTbl:
					# ASSUME day is in month parent iff it's also in boxIDTbl itself
					prevDayModDT = dateutil.parser.parse(boxIDTbl[dkey]['mdate'])
				else:
					prevDayModDT = None
					
				dayModDT = dateutil.parser.parse(dayInfo.modified_at)
				if prevDayModDT != None and not (dayModDT > prevDayModDT and dayModDT > lastUpdate):
					continue
			
				print('updateBoxIDTbl: including day %s %s modified %s' % (dayf.id,dayf.name,dayInfo.modified_at))		
				boxIDTbl[mkey]['kids'].append(dkey)
				boxIDTbl[dkey] = {'id': dayf.id,'mdate': dayInfo.modified_at} # NB, no kids for files
			
	
	return boxIDTbl
	
class Command(BaseCommand):
	help = 'harvest updates from OPD PatrolLogs from Box since %Y-%m-%d startDate. defaults to 30 days ago'
# 	def add_arguments(self, parser):
# 		parser.add_argument('startDate', nargs='?', default='noStartSpecified') 

	def handle(self, *args, **options):

		verbose = None
		checkPoint = True

# 		import logging
# 		logging.basicConfig(level=logging.WARNING)

		runDate = awareDT(datetime.now())
		dateStr = datetime.strftime(runDate,'%y%m%d')
		
		## Compare cache to current database
			
		# SQL equivalent query
# 		select "lastModDateTime" from "dailyIncid_oakcrime" where source like '%DLog_%'
# 			order by "lastModDateTime" DESC LIMIT 1	
		lastDLogOC = OakCrime.objects.filter(source__contains='DLog_').latest('lastModDateTime')
		lastDLogDT = lastDLogOC.lastModDateTime
		
		# NB: HarvestOverlapBuffer to avoid missing any in the gap!
		HarvestOverlapBuffer = 2
		lastDLogDT -= timedelta(days=HarvestOverlapBuffer)
		lastDLogDate = lastDLogDT.date()

		print('harvestPatrolLog: %s DB last updated with PatrolLogs %s' % (dateStr,lastDLogDate))

		## Check current files @ Box
		
		makeBoxConnection() # sets CurrBoxClient
		
		boxIDFile = HarvestRootDir + 'boxIDTbl.json'
		if os.path.exists(boxIDFile):
			print('harvestPatrolLog: boxIDFile found, updating')
			currBoxIDTbl = json.load(open(boxIDFile))
			currBoxIDTbl = updateBoxIDTbl(currBoxIDTbl,lastDLogDT)
		else:
			print('harvestPatrolLog: boxIDFile NOT found, building from scratch')
			currBoxIDTbl = getBoxIDs()
			
		json.dump(currBoxIDTbl,open(boxIDFile,'w'),indent=1)
		
		## Compare current Box inventory to cache contents

		# missingList: [ ( '_'-separated full path, boxid, kidsP), ...]
		missingList = compBox2Dir(currBoxIDTbl)
		
		harvestedFiles = []
		for missInfo in missingList:
			pathStr = getMiss(missInfo)
			if pathStr:
				# non-None rval is path string
				harvestedFiles.append(pathStr)

		print('harvestPatrolLog: %s NFilesHarvested=%d' % (dateStr,len(harvestedFiles)))
		
		files2parse = modifiedSince(currBoxIDTbl,lastDLogDate)
		
		print('harvestPatrolLog: %s NFilesToParse=%d' % (dateStr,len(files2parse)))

		## Parse harvested PDF
			
		# logData: dailyRoot -> [ {allAnnoteInfo} ]
		logData = parsePL.collectDailyLogs(files2parse,HarvestRootDir)
		
		if checkPoint:
			# cache results of potentially LONG PDF parse
			ldf = HarvestRootDir + 'logData_%s.json' % (dateStr)
			json.dump(logData,open(ldf,'w'),indent=1)
	
		# logData = json.load(open(ldf))	
		
		print('harvestPatrolLog: %s NParsed=%d' % (dateStr,len(logData)))

		# newIncid: cid* -> {froot, TU -> V}
		inIncid = parsePL.mergeDailyLogs(logData)

		# newIncidTbl = filterNewDLog(logData)
		
		regIncidTbl = parsePL.regularizeIncidTbl(inIncid)

		makeGConnection()  # sets CurrGClient
				
		geoIncidTbl = parsePL.addGeoCode2(regIncidTbl, CurrGClient, verbose=100)
	
		if checkPoint:
			geof = HarvestRootDir + 'geoIncid_%s.pkl' % (dateStr)
			with open(geof, 'wb') as f:
				pickle.dump(geoIncidTbl, f, pickle.HIGHEST_PROTOCOL)

# 		geof = HarvestRootDir + 'geoIncid.pkl'
# 		with open(geof, 'rb') as f:
# 			geoIncidTbl = pickle.load(f)

		print('harvestPatrolLog: %s NGeoIncid=%d' % (dateStr,len(geoIncidTbl)))

		# dlogMatchTbl: 	cid -> OakCrime() and 
		# dlogUnmatchTbl: 	dlogCID -> OakCrime()
		
		# match log written in postPL.getBestMatch()
		matchLogFile = HarvestRootDir + 'matchLog_%s.csv' % (dateStr)
		matchLogStream = open(matchLogFile,'w')
		matchLogStream.write('dRptNo,dLoc,dxlng,dylat,dDT,dPC,iCID,iAddr,ixlng,iylat,iDT,iCC,iCType,iDesc,matchScore,idDist,distMeter,dayDiff,majorCrime\n')
			
		dlMatchTbl, unMatchTbl = postPL.findSimIncid(geoIncidTbl,dateStr,logStr=matchLogStream,verbose=100)

		matchLogStream.close()

		if checkPoint:		
			dlf = HarvestRootDir + 'dlMatch_%s.pkl' % (dateStr)
			with open(dlf, 'wb') as f:
				pickle.dump(dlMatchTbl, f, pickle.HIGHEST_PROTOCOL)
	
			unf = HarvestRootDir + 'unMatch_%s.pkl' % (dateStr)
			with open(unf, 'wb') as f:
				pickle.dump(unMatchTbl, f, pickle.HIGHEST_PROTOCOL)

# 		dlf = HarvestRootDir + 'dlMatch_%s.pkl' % (dateStr)
# 		with open(dlf, 'rb') as f:
# 			dlMatchTbl = pickle.load(f)
# 		unf = HarvestRootDir + 'unMatch_%s.pkl' % (dateStr)
# 		with open(unf, 'rb') as f:
# 			unMatchTbl = pickle.load(f)	
# 		print('harvestPatrolLog: %s dlMatch=%d unMatch=%d' % (dateStr,len(dlMatchTbl),len(unMatchTbl)))

		allCID = list(dlMatchTbl.keys())
		allCID.sort()
		nupdate =0
		nerr=0
		for i,cid in enumerate(allCID):
			if verbose != None and (i % verbose)==0:
				print('harvestPatrolLog: %s Matches saved %d NUpdate=%d NErr=%d' % (dateStr,i,nupdate,nerr))
			newOC = dlMatchTbl[cid]
						
			try:
				# NB: newOC.idx set in mergDLog2Incid, forcing update vs insert
				assert bool(newOC.idx) == True, 'harvestDLog: No idx for update?! %s\n%s' % (cid,pprintOC(newOC))
				newOC.save()
				nupdate += 1
			except Exception as e:
				print('harvestPatrolLog: cant save merge?! %s %s\n\t%s' % (cid,e,pprintOC(newOC)) )
				# import pdb; pdb.set_trace()
				nerr += 1
				continue
		print('harvestPatrolLog: %s Matches saved FINAL NUpdate=%d NErr=%d' % (dateStr,nupdate,nerr))
			
		allCID = list(unMatchTbl.keys())
		allCID.sort()
		
		nupdate =0
		nerr=0
		for i,cid in enumerate(allCID):
			if verbose != None and (i % verbose)==0:
				print('harvestPatrolLog: %s Unmatched saved %d NUpdate=%d NErr=%d' % (dateStr,i,nupdate,nerr))
			newOC = unMatchTbl[cid]
			# NB: findSimIncid() returns None in unMatchTbl for cid's without any best match
			
			try:
				assert bool(newOC.idx) == False, 'harvestPatrolLog: Idx for insert?! %s\n%s' % (cid,pprintOC(newOC))
				newOC.save()
				nupdate += 1
			except Exception as e:
				print('harvestPatrolLog: cant save new?! %s %s\n\t%s' % (cid,e,pprintOC(newOC)) )
				# import pdb; pdb.set_trace()
				nerr += 1
				continue
			
		print('harvestPatrolLog: %s Unmatched saved FINAL NUpdate=%d NErr=%d' % (dateStr,nupdate,nerr))
		

	