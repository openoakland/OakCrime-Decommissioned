''' harvestPatrolLogs:  Capture new OPD patrol logs from box.com

ASSUME crontab entry ala (daily @ 4:20p)

> crontab -l
# run once a day at 16:20
20 16 * * * .../showCrime/dailyIncid/management/commands/harvestPatrolLog.py

@version 0.3: prepare for AWS
	- use BoxID, database tables vs JSON
	
@date 190819

@author: rik
'''

from datetime import datetime,timedelta
import dateutil.parser
# import environ # in settings
import json
import logging
import os
import pickle
import pytz
import socket
import sys
import time

import boxsdk 
import googlemaps
import mapbox

from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail

from showCrime.settings import MEDIA_ROOT

from dailyIncid.models import *
from dailyIncid.util import *

from dailyIncid.management.commands import parsePatrolLog as parsePL
from dailyIncid.management.commands import postPatrolLog as postPL

logger = logging.getLogger(__name__)

# Credentials
# env = environ.Env(DEBUG=(bool, False), ) # in settings
GoogleMapAPIKey = env('GOOGLE_MAPS_API_KEY')
BoxEnterpriseID = env('BOX_ENTERPRISE_ID')
BoxClientID = env('BOX_CLIENT_ID')
BoxClientSecret = env('BOX_CLIENT_SECRET')
BoxPublicKeyID = env('BOX_PUBLIC_KEY_ID')
BoxRSAKey = env('BOX_RSA_KEY')
BoxPassPhrase = env('BOX_PASS_PHRASE')

# Constants
HarvestRootDir = MEDIA_ROOT + '/PLHarvest/'
BoxDateTimeFmt = "%Y-%m-%dT%H:%M:%S"
PythonCTimeFmt = "%a %b %d %H:%M:%S %Y"
OPDPatrolFolderID =  '8881131962' 
OCSourceDateFmt = '%y%m%d'

def getMiss(boxidx,verbose=True):
	''' download file missing from cache
		create subdirectory if it has kids		
	'''
	
	try:
		boxobj = BoxID.objects.get(boxidx=boxidx)
	except ObjectDoesNotExist:
		logger.warning('getMiss: missing BoxID?! boxidx=%s',boxidx)
		return None
	
	name = boxobj.name
	nkids = boxobj.kids.all().count()
	haveKids = nkids > 0

	# missInfo = ( '_'-separated path relavitive to HarvestRootDir, boxid, kidsP)
	kbits = name.split('_')
	kbits.insert(0,HarvestRootDir)
	# NB: splat to provide all of kbits
	path = os.path.join(*kbits)
	# create subdirectory for those with kids
	if haveKids:
		try:
			os.mkdir(path)
			logger.info('getMiss: directory created id=%s path=%s',id,path)
		except Exception as e:
			logger.warning('getMiss: directory already exists?! path=%s except=%s',path,e)
		return None
	try:
		box_file = CurrBoxClient.file(file_id=boxidx).get()
		with open(path, 'wb') as outs:
			box_file.download_to(outs)
			if verbose:
				logger.info('getMiss: retrieved path=%s',path)
				
		nowDT = datetime.now()
		locDT = awareDT(nowDT)
		boxobj.harvestDT = locDT
		boxobj.save()
		return True
	except Exception as e:
		logger.warning('getMiss: cant get file?! id=%s path=%s except=%s',id,path,e)
		return None
		
def connectJWTAuth():
	
	print('initBRK',BoxRSAKey)
	brk2 = BoxRSAKey.replace('\\n','\n')
	
	auth = boxsdk.JWTAuth(
		client_id=BoxClientID,
		client_secret=BoxClientSecret,
		enterprise_id=BoxEnterpriseID,
		jwt_key_id=BoxPublicKeyID,
		# NB: BoxRSAKey needs to be byte string vs. unicode
		rsa_private_key_data = brk2.encode, # BoxRSAKey.encode(),
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
	logger.info('connectBox: login=%s name=%s' , currLogin,currName )
	
	return CurrBoxClient

def compBox2Dir(chgList,init=False):
	'''identify which BoxID (from list identified by updateBoxID) have NOT (yet) been harvested 
		as files under HarvestRootDir
		if init, initialize harvestDT from files' timestamp
		returns missing list: [boxidx]
	'''

	missing = []
	nfnd = 0
	ndirMismatch = 0
	for boxidx in chgList:	
		try:
			boxobj = BoxID.objects.get(idx=boxidx)
		except ObjectDoesNotExist:
			logger.warning('compBox2Dir: missing BoxID?! boxidx=%s',boxidx)
			continue

		name = boxobj.name
		nkids = boxobj.kids.all().count()
		haveKids = nkids > 0
		if name=='root':
			continue
		kbits = name.split('_')
		kbits.insert(0,HarvestRootDir)
		# NB: splat to provide all of kbits
		path = os.path.join( *kbits)
		if os.path.exists(path):
			nfnd += 1
			dirP = os.path.exists(path) and os.path.isdir(path)
			if (dirP and not haveKids) or (not dirP and haveKids):
				ndirMismatch += 1
				logger.info('compBox2Dir: dir/file mismatch?! name=%s',name)
				continue
			if init:
				boxobj.froot = parsePL.name2froot(name)
				# NB: use file's modif timestamp as assumed harvestDT
				fileMTime = os.path.getmtime(path)
				harvestDT = datetime.strptime(time.ctime(fileMTime), PythonCTimeFmt)
				boxobj.harvestDT = OaklandTimeZone.localize(harvestDT)
				boxobj.save()

		else:
			missing.append( boxobj.boxidx )
	logger.info('compBox2Dir: NFnd=%d NMiss/HarvestNext=%d NDirMismatch=%d' , nfnd,len(missing),ndirMismatch)
	return missing
	
def getBoxIDs(verbose=True):
	'''traverse all folders under OPDPatrolFolderID FROM SCRATCH to build boxIDTbl
	'''	
	
	nskip = 0
	boxIDTbl = {'root': {'id': OPDPatrolFolderID,'kids': []} }
	yearFolders = CurrBoxClient.folder(folder_id=OPDPatrolFolderID).get_items(limit=100, offset=0)
	for yrf in yearFolders:
		if yrf.type != 'folder':
			logger.info('getBoxIDs: skipping year non-folder %s %s %s' , yrf.id,yrf.type,yrf.name)
			nskip += 1
			continue
		# NB: '_' used to separate key bits; make sure it isn't already there
		ykey = yrf.name.strip().lower().replace('_','#')
		if ykey in boxIDTbl:
			logger.info('getBoxIDs: duplicate year name?! new: %s %s %s\n\t prevID:%s' , yrf.id,yrf.type,ykey,boxIDTbl[ykey]['id'])
			nskip += 1
			continue			
		boxIDTbl['root']['kids'].append(ykey)
		yrInfo = CurrBoxClient.folder(folder_id=yrf.id).get(fields=['modified_at'])
		boxIDTbl[ykey] = {'id': yrf.id,'mdate': yrInfo.modified_at,'kids': []}
		for monf in yrf.get_items(limit=100):
			if monf.type != 'folder':
				logger.info('getBoxIDs: skipping month non-folder %s / %s %s %s' , ykey,monf.id,monf.type,monf.name)
				nskip += 1
				continue
			mkey = ykey + '_' + monf.name.strip().lower().replace('_','#')
			if mkey in boxIDTbl:
				logger.info('getBoxIDs: duplicate month name?! new: %s %s %s\n\t prevID:%s' , \
					mkey,monf.id,monf.type,boxIDTbl[mkey]['id'])
				nskip += 1
				continue			
			boxIDTbl[ykey]['kids'].append(mkey)
			monInfo = CurrBoxClient.folder(folder_id=monf.id).get(fields=['modified_at'])
			boxIDTbl[mkey] = {'id': monf.id,'mdate': monInfo.modified_at,'kids': []}
			for dayf in monf.get_items(limit=100):
				if dayf.type != 'file':
					logger.info('getBoxIDs: skipping day non-file %s / %s %s %s' , \
						mkey,dayf.id,dayf.type,dayf.name)
					nskip += 1
					continue
				dkey = mkey + '_' + dayf.name.strip().lower().replace('_','#')
				if dkey in boxIDTbl:
					logger.info('getBoxIDs: duplicate day name?! new: %s / %s %s %s %s' , \
						dkey, dayf.id, dayf.type, dayf.name, boxIDTbl[dkey]['id'])
					nskip += 1
					continue
				boxIDTbl[mkey]['kids'].append(dkey)
				dayInfo = CurrBoxClient.file(file_id=dayf.id).get(fields=['modified_at'])
				boxIDTbl[dkey] = {'id': dayf.id,'mdate': dayInfo.modified_at}  # NB, no kids for files
			if verbose:
				logger.info('Month %s: %d day files' , mkey,len(boxIDTbl[mkey]['kids']))
				
		if verbose:
			logger.info('Year %s: %d month folders' , ykey,len(boxIDTbl[ykey]['kids']))
	
	if verbose:
		logger.info('Root: %d year folders' , len(boxIDTbl['root']['kids']))
	
	return boxIDTbl

def updateBoxID(lastUpdate,verbose=False):
	'''traverse all folders under OPDPatrolFolderID @ Box for changes since lastUpdate
	return list of new BoxID.idx changed
	'''	

	nskip = 0
	yearFolders = CurrBoxClient.folder(folder_id=OPDPatrolFolderID).get_items(limit=100, offset=0)
	newChanges = set()
	for yrf in yearFolders:
		if yrf.type != 'folder':
			if verbose:
				logger.info('updateBoxID: skipping year non-folder %s %s %s' , yrf.name,yrf.id,yrf.type)
			nskip += 1
			continue
		# NB: '_' used to separate key bits; make sure it isn't already there
		ykey = yrf.name.strip().lower().replace('_','#')
		yrInfo = CurrBoxClient.folder(folder_id=yrf.id).get(fields=['modified_at'])
		
		try: 
			ybo = BoxID.objects.get(name=ykey)
			prevYrModDT = ybo.boxModDT
		except ObjectDoesNotExist:
			rootBO = BoxID.objects.get(name='root')
			
			yrKids = rootBO.kids.filter(name=ykey)
			assert yrKids.count()==0, "updateBoxID: ykey already kid of root?! %s" % (ykey)
			
			ybo = BoxID()
			ybo.name = ykey
			ybo.froot = parsePL.name2froot(ykey)		
			ybo.boxidx = int(yrf.id)
			ybo.boxModDT = yrInfo.modified_at
			ybo.save()
			newChanges.add(ybo.idx)
			rootBO.kids.add(ybo)
			rootBO.save()
			newChanges.add(rootBO.idx)
			
			prevYrModDT = None
			logger.info('updateBoxID: including year %s (boxidx=%s) modified %s' , ybo.name,ybo.boxidx,ybo.boxModDT)					
		
		yrModDT = dateutil.parser.parse(yrInfo.modified_at)
		
		if prevYrModDT is not None and not (yrModDT > prevYrModDT and yrModDT > lastUpdate):
			if verbose:
				logger.info('updateBoxID: skipping year %s (boxidx=%s %s) yrModDT=%s prevYrModDT=%s lastUpdate=%s' , \
					yrf.name,yrf.id,yrf.type,yrModDT,prevYrModDT,lastUpdate)
			continue
		
		if verbose:
			logger.info('updateBoxID: updating year folder %s (boxidx=%s) modified %s' , ybo.name,ybo.boxidx,ybo.boxModDT)

		for monf in yrf.get_items():
			if monf.type != 'folder':
				if verbose:
					logger.info('updateBoxID: skipping month non-folder in %s / %s (boxidx=%s %s)' , ykey,monf.name,monf.boxidx,monf.type)
				nskip += 1
				continue
			mkey = ykey + '_' + monf.name.strip().lower().replace('_','#')
			monInfo = CurrBoxClient.folder(folder_id=monf.id).get(fields=['modified_at'])
			
			try: 
				mbo = BoxID.objects.get(name=mkey)
				prevMonModDT = mbo.boxModDT
			except ObjectDoesNotExist:
				
				mbo = BoxID()
				mbo.name = mkey
				mbo.froot = parsePL.name2froot(mkey)		
				mbo.boxidx = int(monf.id)
				mbo.boxModDT = monInfo.modified_at
				mbo.save()
				newChanges.add(mbo.idx)
				ybo.kids.add(mbo)
				ybo.save()
				newChanges.add(ybo.idx)
				
				prevMonModDT = None

				logger.info('updateBoxID: including month %s (boxidx=%s) modified %s' , mbo.name,mbo.boxidx,mbo.boxModDT)					

			monModDT = dateutil.parser.parse(monInfo.modified_at)
				
			if prevMonModDT is not None and not (monModDT > prevMonModDT and monModDT > lastUpdate):
				if verbose:
					logger.info('updateBoxID: skipping month %s (id=%s %s) monModDT=%s prevMonModDT=%s lastUpdate=%s' , \
						monf.name,monf.id,monf.type,monModDT,prevMonModDT,lastUpdate)
				nskip += 1
				continue
			
			if verbose:
				logger.info('updateBoxID: updating month folder %s %s modified %s' , mbo.name,mbo.boxidx,mbo.boxModDT)		

			for dayf in monf.get_items():
				if dayf.type != 'file':
					logger.info('updateBoxID: skipping day non-file in month %s / %s (%s %s)' , \
						mkey,dayf.name,dayf.id,dayf.type)
					nskip += 1
					continue
				dkey = mkey + '_' + dayf.name.strip().lower().replace('_','#')
				dayInfo = CurrBoxClient.file(file_id=dayf.id).get(fields=['modified_at'])

				try: 
					dbo = BoxID.objects.get(name=dkey)
					prevDayModDT = dbo.boxModDT
				except ObjectDoesNotExist:
					
					dbo = BoxID()
					dbo.name = dkey
					dbo.froot = parsePL.name2froot(dkey)		
					dbo.boxidx = int(dayf.id)
					dbo.boxModDT = dayInfo.modified_at
					dbo.save()
					newChanges.add(dbo.idx)
					mbo.kids.add(dbo)
					mbo.save()
					newChanges.add(mbo.idx)
														
					logger.info('updateBoxID: including day %s (boxidx=%s) modified %s' , dbo.name,dbo.boxidx,dbo.boxModDT)					
	chgList = list(newChanges)
	logger.info('updateBoxID: NChanged BoxID=%s',len(chgList))
	return chgList
	
def postBoxTbl2DB(currTbl,lastModDate):
	'''initialize BoxID model objects based on currTbl
		lastModDate used if no modify date specified
	'''
	
	BoxID.objects.all().delete()
	
	for name,info in currTbl.items():
		try: 
			boxObj = BoxID.objects.get(name=name)
		except ObjectDoesNotExist:
			boxObj = BoxID()
			boxObj.name = name
			boxObj.boxidx = int(info['id'])
			
			boxObj.froot = parsePL.name2froot(name)
			
			if 'mdate' in info:
				mdatestr = info['mdate']
				# HACK: 190825
				# mdatestr = 2017-01-10T15:18:15-08:00
				mdatestr = mdatestr[:-6]
				mdate = awareDT(datetime.strptime(mdatestr,BoxDateTimeFmt))
			else:
				mdate = lastModDate
			boxObj.boxModDT = mdate 
			boxObj.save()
			
		except Exception as e: # # BoxID.DoesNotExist: # ObjectDoesNotExist:
			logger.warning('postBoxTbl2DB: exception1?! name=%s except=%s',name,e)
			continue
			
			# NB: need to save boxObj before we can add kids
			# ValueError: "<BoxID: BoxID object>" needs to have a value for field "idx" before this many-to-many relationship can be used.
				
		if 'kids' in info:
			for kidname in info['kids']:
				kidInfo = currTbl[kidname]
				kidid = kidInfo['id']
				try:
					kidObj = BoxID.objects.get(boxidx=kidid)
				except ObjectDoesNotExist:
					kidObj = BoxID()
					kidObj.name = kidname
					kidObj.boxidx = kidid
					kidObj.froot = parsePL.name2froot(kidname)
					if 'mdate' in kidInfo:
						mdatestr = kidInfo['mdate']
						# HACK: 190825
						# mdatestr = 2017-01-10T15:18:15-08:00
						mdatestr = mdatestr[:-6]
						mdate = awareDT(datetime.strptime(mdatestr,BoxDateTimeFmt))
					else:
						mdate = lastModDate
					kidObj.boxModDT = mdate
					kidObj.save()
				except Exception as e: 
					logger.warning('postBoxTbl2DB: exception?! kidname=%s except=%s',kidname,e)
					continue

				boxObj.kids.add(kidObj)
				
			# NB: final save to include added kids
			boxObj.save()			

	logger.info('postBoxTbl2DB: NBoxID=%d' , BoxID.objects.count())
	
def createBoxTblFromDB():
	'''convert all BoxID model objects into python dictionary with name keys
		ala {'root': {'id': "16382272441","mdate": "2016-08-09T04:08:13-07:00", 'kids': []} }
	'''
	qs = BoxID.objects.all()
	currTbl = {}
	for boxObj in qs:
		boxPO = {'id': boxObj.boxidx, 'name': boxObj.name, 'mdate': boxObj.boxModDT, 'kids': []}
		for kidObj in boxObj.kids.all():
			boxPO['kids'].append(kidObj.name)
		currTbl[boxObj.name] = boxPO
	
	logger.info('createBoxTblFromDB: NBoxID=%d' , len(currTbl))
	return currTbl

class Command(BaseCommand):
	help = '''harvest updates from OPD PatrolLogs from Box 
			if lastCheck, recover since %Y-%m-%d lastCheck date, 
				else since most recent boxModDT across BoxID records
			Compare cache to current database
			Parse PDF of newly harvested
			Merge against existing dailyIncid
			'''
	
	def add_arguments(self, parser):
		parser.add_argument(
			'--lastCheck',
			default='',
			help='harvest only those with modified_at > startDate %Y-%m-%d'
		)

	def handle(self, *args, **options):
		# ASSUME logging handled in settings
		# .basicConfig(level=logging.INFO)

		logging.getLogger("boxsdk").setLevel(logging.WARNING)
		logging.getLogger("pdfminer").setLevel(logging.WARNING)

		lastCheck = options['lastCheck']
		logger.info('harvestPatrolLog: lastCheck=%s' , lastCheck)

		verbose = None
		initAll = False 
		HarvestOverlapBuffer = 2
		
		beginDT = datetime.now()
		runDate = awareDT(beginDT)
		dateStr = datetime.strftime(runDate,'%y%m%d')

		summRpt = '' # summary report for email

		if lastCheck == '':
			## Compare cache to current database
			lastTouchedBoxID = BoxID.objects.latest('boxModDT')
			lastBoxDT = lastTouchedBoxID.boxModDT
			
			logger.info('BOXMOD lastBoxDT=%s' ,lastBoxDT)
			
			# NB: HarvestOverlapBuffer to avoid missing any in the gap!
			lastBoxDT -= timedelta(days=HarvestOverlapBuffer)
			lastDLogDate = lastBoxDT.date()
			logger.info('%s DB last updated with PatrolLogs >= (%d days earlier than) %s' , \
				dateStr,HarvestOverlapBuffer,lastDLogDate)
		else:
			lastBoxDT = datetime.strptime(lastCheck,'%Y-%m-%d')
			lastBoxDT = OaklandTimeZone.localize(lastBoxDT)
			logger.info('FIXED lastBoxDT=%s',lastBoxDT)
		
		## Check current files @ Box
		makeBoxConnection() # sets CurrBoxClient
			
		topf = CurrBoxClient.folder(folder_id=OPDPatrolFolderID)
		topfInfo = topf.get(fields=['modified_at'])
		topModDTStr = topfInfo.modified_at
		summRpt += 'updateBoxID: OPDPatrolFolder modifiedDT=%s\n' % (topModDTStr)
					
		chgList = updateBoxID(lastBoxDT)
		elapTime = datetime.now() - beginDT
		logger.info('updateBoxID DONE elapTime=%s' , elapTime.total_seconds())	
		summRpt += 'updateBoxID: NChanged BoxID=%s\n' % len(chgList)

		## identify those not yet reflected in local cache under HarvestRootDir
		missingList = compBox2Dir(chgList)	
		elapTime = datetime.now() - beginDT
		logger.info('compBox2Dir DONE elapTime=%s' , elapTime.total_seconds())
	
		## harvest these to local cache under HarvestRootDir
		harvestedFiles = []
		for boxidx in missingList:
			if getMiss(boxidx):
				harvestedFiles.append(boxidx)
		logger.info('NFilesHarvested=%d' ,len(harvestedFiles))
		elapTime = datetime.now() - beginDT
		logger.info('getMiss DONE elapTime=%s' , elapTime.total_seconds())	
		summRpt += 'NFilesHarvested=%d\n'  % len(harvestedFiles)

		## Parse PDF of recently harvested, unparsed files

		parseSinceDT = beginDT - timedelta(days=HarvestOverlapBuffer)
		qs = BoxID.objects.filter(harvestDT__gte=parseSinceDT).filter(parseDT__isnull=True)
		unParsed = [boxid.idx for boxid in qs]
		logger.info('NUparsed=%d since %s',len(unParsed),parseSinceDT)
						
		# dpIdxList = list of all DailyParse indices produced as part of parse
		dpIdxList = parsePL.parseLogFiles(unParsed,HarvestRootDir,verbose=True)
		elapTime = datetime.now() - beginDT
		logger.info('parseLogFiles DONE elapTime=%s' , elapTime.total_seconds())			
		summRpt += 'parseLogFiles: NIncidParsed=%d\n'  % len(dpIdxList)

		## Regularize attributes from PDF fields, including geotagging
		
		parsePL.regularizeIncidTbl(dpIdxList)
		elapTime = datetime.now() - beginDT
		logger.info('regularizeIncidTbl DONE elapTime=%s' , elapTime.total_seconds())			
		
		CurrGClient = makeGConnection()  # sets CurrGClient
				
		parsePL.addGeoCode2(dpIdxList, CurrGClient,verbose=20)
		elapTime = datetime.now() - beginDT
		logger.info('addGeoCode DONE elapTime=%s' , elapTime.total_seconds())			

		# dlogMatchTbl: 	cid -> OakCrime UNSAVED and 
		# dlogUnmatchTbl: 	dlogCID -> OakCrime UNSAVED					
		dlMatchTbl, unMatchTbl = postPL.findSimIncid(dpIdxList,dateStr)
		elapTime = datetime.now() - beginDT
		logger.info('findSimIncid DONE NMatch=%d NUnMatch=%d elapTime=%s' , \
			len(dlMatchTbl),len(unMatchTbl),elapTime.total_seconds())	
		summRpt += 'findSimIncid: NMatch=%d NUnMatch=%d\n'  % (len(dlMatchTbl),len(unMatchTbl))
		
		allCID = list(dlMatchTbl.keys())
		allCID.sort()
		nupdate =0
		nerr=0
		for i,cid in enumerate(allCID):
			if verbose != None and (i % verbose)==0:
				logger.info('%s Matches saved %d NUpdate=%d NErr=%d' , dateStr,i,nupdate,nerr)
			newOC = dlMatchTbl[cid]
						
			try:
				# NB: newOC.idx set in mergDLog2Incid, forcing update vs insert
				assert bool(newOC.idx) == True, 'harvestDLog: No idx for update?! %s\n%s' % (cid,pprintOC(newOC))
				newOC.save()
				nupdate += 1
			except Exception as e:
				logger.warning('cant save merge?! %s %s\n\t%s' , cid,e,pprintOC(newOC) )
				nerr += 1
				continue
		logger.info('%s Matches saved FINAL NUpdate=%d NErr=%d' , dateStr,nupdate,nerr)
		summRpt += 'Match NUpdate=%d NErr=%d\n'  % (nupdate,nerr)

		allCID = list(unMatchTbl.keys())
		allCID.sort()
		
		nupdate =0
		nerr=0
		for i,cid in enumerate(allCID):
			if verbose != None and (i % verbose)==0:
				logger.info('%s Unmatched saved %d NUpdate=%d NErr=%d' , dateStr,i,nupdate,nerr)
			newOC = unMatchTbl[cid]
			# NB: findSimIncid() returns None in unMatchTbl for cid's without any best match
			
			try:
				assert bool(newOC.idx) == False, 'Idx for insert?! %s\n%s' % (cid,pprintOC(newOC))
				newOC.save()
				nupdate += 1
			except Exception as e:
				logger.warning('cant save new?! %s %s\n\t%s' , cid,e,pprintOC(newOC) )
				nerr += 1
				continue
			
		logger.info('%s Unmatched saved FINAL NUpdate=%d NErr=%d' , dateStr,nupdate,nerr)
		summRpt += 'UnMatch NUpdate=%d NErr=%d\n'  % (nupdate,nerr)
		
		elapTime = datetime.now() - beginDT
		rptMsg = ' DONE elapTime=%s' % elapTime.total_seconds()
		logger.info(rptMsg)			
		
		summRpt = summRpt + rptMsg + '\n'

		send_mail('PatrolLog @ Box harvest', summRpt, 'rik@electronicArtifacts.com', \
				['rik@electronicArtifacts.com'], fail_silently=False)

	
