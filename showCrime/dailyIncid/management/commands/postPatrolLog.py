""" postPatrolLog:

    uses findSimIncident() to attempt matches of DLogs to incidents
    ASSUME geotagging already done

@date 181218
@author: rik
"""

from datetime import datetime, time, timedelta

import editdistance
import pytz
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.core.exceptions import ObjectDoesNotExist

from dailyIncid.models import *

# Constants
SRS_default = 4326  # WGS84
SRS_10N = 26910  # UTM zone 10N

MaxCIDDiff = 3  # max allowable difference between PatrolLog Report# and opd_rd
DefaultNDays = 7
DateOnlyStrFormat = '%Y-%m-%d'
Socrata_date_format = '%Y-%m-%dT%H:%M:%S'  # 2013-12-04T19:00:00
DLogDateTimeFmt = "%Y-%m-%d %H:%M:%S"

MZDefaultOaklandCoord = [-122.197811, 37.785199]

# 171026:  Most frequent pairs from pc2ccTbl_171006.ods
MajorCrimes = ['ASSAULT' 'DOM-VIOL', 'HOMICIDE', 'ROBBERY']

PC2CrimeCatTbl = {'211': 'ROBBERY',
                  '245(a)(1)': 'ASSAULT',
                  '245(a)(2)': 'ASSAULT',
                  '664': 'ROBBERY',
                  '246.3': 'ASSAULT',
                  '215': 'ROBBERY',
                  '246': 'ASSAULT',
                  '212.5': 'ROBBERY',
                  '(211': 'ROBBERY',
                  '187': 'HOMICIDE',
                  '247(b)': 'ASSAULT',
                  '273.5': 'DOM-VIOL',
                  '211pc-armed': 'ROBBERY',
                  '247': 'ASSAULT'}


def awareDT(naiveDT):
    utc = pytz.UTC
    return utc.localize(naiveDT)


def classify(ctype, desc):
    try:
        cco1 = CrimeCat.objects.get(ctypeDesc=ctype)
        cc = cco1.crimeCat
    except ObjectDoesNotExist:
        try:
            cco2 = CrimeCat.objects.get(ctypeDesc=desc)
            cc = cco2.crimeCat
        except ObjectDoesNotExist:
            cc = ''
    return cc


def classifyPC(pclist):
    '''return first match found in PC2CrimeCatTbl
    '''

    for pc in pclist:
        if pc in PC2CrimeCatTbl:
            return PC2CrimeCatTbl[pc]
    return ''


def mergeDLog2Incid(dlogDict, ocResult, nowDate):
    '''Combine dlog dictionary with OakCrime match including existing ocResult incident
    PREFER ocResult fields
    if ocResult==None, fill only fields available in dlog
    '''

    newOC = OakCrime()

    # NB: include froot as part of dlogSrc
    dlogSrc = 'DLog_' + nowDate + '_' + dlogDict['froot']

    if ocResult is None:
        # New incident indicated to save() by null idx
        newOC.idx = None
        # NB: missing existing ocResult, use cid from dlog
        newOC.opd_rd = dlogDict['rptno']
        # NB:  oidx must be non-null! - 171205
        newOC.oidx = 0

        # NB: parseOPDLog_PDForm.regularizeIncidTbl() can't regularize bad dates!
        dlogDate = dlogDict['reg_date']
        # NB: parse_OPDLog_PDForm.regularizeIncidTbl() only includes good times
        if 'reg_time' not in dlogDict or dlogDict['reg_time'] == '':
            dlogTime = time()
        else:
            dlogTime = dlogDict['reg_time']

        newDateTime = awareDT(datetime.combine(dlogDate, dlogTime))
        newOC.cdateTime = newDateTime

        newOC.desc = ''  # NB: no description in logs, nature used for pclist
        newOC.ctype = ''
        if 'reg_pc' in dlogDict:
            newOC.crimeCat = classifyPC(dlogDict['reg_pc'])
        else:
            newOC.crimeCat = ''

        newOC.beat = dlogDict['reg_beat']
        newOC.addr = dlogDict['location1'].upper()

        newOC.xlng = float(dlogDict['XLng']) if dlogDict['XLng'] != '' else None
        newOC.ylat = float(dlogDict['YLat']) if dlogDict['YLat'] != '' else None

        if newOC.xlng is not None and newOC.ylat is not None:
            try:
                newpt = Point(newOC.xlng, newOC.ylat, srid=SRS_default)
                newpt.transform(SRS_10N)
                newOC.point = newpt
            except Exception as e:
                print('mergeDLog2Incid: cant make point for dlog?! %s %s %s\n\t%s' % (
                    newOC.opd_rd, newOC.xlng, newOC.ylat, e))
                newOC.point = None

        newOC.source = dlogSrc

    else:
        incid = ocResult['incid']
        # NB: existing ocResult, use cid from it
        # 		and make sure to steal its primary key!
        newOC.idx = incid.idx
        newOC.opd_rd = incid.opd_rd
        newOC.oidx = incid.oidx

        # PREFER all ocResult fields

        newOC.cdateTime = incid.cdateTime

        if incid.desc != '':
            newOC.desc = incid.desc
        else:
            newOC.desc = ''

        if newOC.ctype != '':
            newOC.ctype = incid.ctype
        else:
            newOC.ctype = ''

        if incid.beat != '':
            newOC.beat = incid.beat
        else:
            newOC.beat = dlogDict['reg_beat']

        if incid.addr != '':
            newOC.addr = incid.addr
        else:
            newOC.addr = dlogDict['location1'].upper()

        if incid.xlng is not None:
            newOC.xlng = incid.xlng
        elif dlogDict['XLng'] != '':
            newOC.xlng = float(dlogDict['XLng'])
        else:
            newOC.xlng = None

        if incid.ylat is not None:
            newOC.ylat = incid.ylat
        elif dlogDict['YLat'] != '':
            newOC.ylat = float(dlogDict['YLat'])
        else:
            newOC.ylat = None

        if incid.point is not None:
            newOC.point = incid.point
        elif newOC.xlng is not None and newOC.ylat is not None:
            try:
                newpt = Point(newOC.xlng, newOC.ylat, srid=SRS_default)
                newpt.transform(SRS_10N)
                newOC.point = newpt
            except Exception as e:
                print('mergeDLog2Incid: cant add point from dlog?! %s %s %s\n\t%s' % (
                    incid.opd_rd, newOC.xlng, newOC.ylat, e))
                newOC.point = None
        else:
            newOC.point = None

        # 2do: new classify(newOC.ctype,newOC.desc, PC)

        # NB: prefer previous crimeCat, then (re-)try to classify based on ctype,desc
        # 		finally exploit dlog reg_pc

        if incid.crimeCat != '':
            newOC.crimeCat = incid.crimeCat
        elif incid.ctype != '' or incid.desc != '':
            cc = classify(incid.ctype, incid.desc)
            if cc == '' and 'reg_pc' in dlogDict:
                cc = classifyPC(dlogDict['reg_pc'])
            newOC.crimeCat = cc
        else:
            newOC.crimeCat = ''

        newOC.source = incid.source + '+' + dlogSrc

    # 2do: Retrain to produce pseudo-UCR, pseudo-PC
    newOC.ucr = ''

    # 2do: Geo-locate wrt/ zip, beat, census tract
    newOC.zip = None
    newOC.geobeat = None
    newOC.ctractGeoID = None

    # add dlog features
    newOC.dlogData = True
    # 2do HACK: parse_OPDLog_PDForm.regularizeIncidTbl() doesn't always provide these fields(:
    newOC.lossList = dlogDict['reg_loss'] if ('reg_loss' in dlogDict) else []
    # NB: parse_OPDLog_PDForm.regularizeIncidTbl() only includes 'reg_gsw' from some injuries
    newOC.gswP = 'reg_gsw' in dlogDict
    newOC.weapon = dlogDict['reg_weapon'] if ('reg_weapon' in dlogDict) else ''
    newOC.callout = dlogDict['reg_callout'] if ('reg_callout' in dlogDict) else 'no'
    newOC.ncustody = dlogDict['reg_ncustody'] if ('reg_ncustody' in dlogDict) else 0
    newOC.nsuspect = dlogDict['reg_nsuspect'] if ('reg_nsuspect' in dlogDict) else 0
    newOC.nvictim = dlogDict['reg_nvictim'] if ('reg_nvictim' in dlogDict) else 0
    newOC.nhospital = dlogDict['reg_nhospital'] if ('reg_nhospital' in dlogDict) else 0
    # 2do HACK: parse_OPDLog_PDForm.regularizeIncidTbl()  WHY WOULD reg_ro and reg_pc be missing?!
    newOC.roList = dlogDict['reg_ro'] if ('reg_ro' in dlogDict) else []
    newOC.pcList = dlogDict['reg_pc'] if ('reg_pc' in dlogDict) else []

    return newOC


def distWgt(dist, maxDist):
    '''linear ramp weight from 1.0 to 0.0 at maxDist
    '''

    dist = max([0, min([dist, maxDist])])

    return (maxDist - dist) / maxDist


def dateDiffWgt(dayDiff, maxDays):
    '''linear ramp weight from 1.0 to 0.0 at maxDays
    '''

    return (float(maxDays) - abs(dayDiff)) / maxDays


def getBestMatch(dlog, dlogCID, logStream, cidFilter=False, requireMajorCrime=True):
    '''query existing OakCrime database for exact opd_rd match,
    then approx dateTime+location similarity
      - logStream: non-None is a stream to write matching detailed log
      - cidFilter: pre-filter against matches with CID > MaxCIDDiff
      - requireMajorCrime: only consider incidents with ctype in MajorCrimes list
    ASSUME dlog contains date and xlng,ylat
    '''

    CloseRadius = 1000  # 1km
    DateRange = 7

    LocationScale = 0.5
    DateScale = 0.5

    if 'reg_date' not in dlog or dlog['reg_date'] is None:
        # nmissDate += 1
        return 'missDate'
    else:
        dlogDate = dlog['reg_date']

    if 'reg_time' not in dlog or dlog['reg_time'] == '':
        dlogTime = time()
    else:
        dlogTime = dlog['reg_time']

    dlogDateTime = awareDT(datetime.combine(dlogDate, dlogTime))

    # ASSUME 4am cutoff ala 29 Sept 17 "0400hrs / Friday (29SEP17) - 0400hrs / Saturday (30SEP17)"
    # 		ie goes 4 hours into next day's incidents
    if dlogTime.hour <= 4:
        dlogDateTime += timedelta(days=1)

    minDate = (dlogDateTime - timedelta(days=DateRange))
    maxDate = (dlogDateTime + timedelta(days=DateRange))

    if not ('location1' in dlog and dlog['location1'] != '' and 'XLng' in dlog and dlog['XLng'] != ''):
        # nmissGC += 1
        return 'missGC'

    dlXLng = dlog['XLng']
    dlYLat = dlog['YLat']

    dlPt = Point(dlXLng, dlYLat, srid=SRS_default)

    result = OakCrime.objects.filter(cdateTime__gte=minDate) \
        .filter(cdateTime__lte=maxDate) \
        .exclude(point__isnull=True) \
        .filter(point__distance_lte=(dlPt, D(m=CloseRadius)))

    matchTbl = {}
    for i, incid in enumerate(result):

        opd_rd = incid.opd_rd
        match = {'cid': opd_rd}

        idDist = editdistance.eval(opd_rd, dlogCID)

        if cidFilter and idDist > MaxCIDDiff:
            continue

        match['idDist'] = idDist
        cdateTime = incid.cdateTime
        # match['cdate'] = cdate
        dateDiff = cdateTime - dlogDateTime
        dateDiffSeconds = dateDiff.total_seconds()
        dayDiff = float(dateDiffSeconds) / 60 / 60 / 24
        match['dayDiff'] = dayDiff

        XLng = incid.xlng
        YLat = incid.ylat

        if XLng is None or YLat is None:
            print('getBestMatch: missing coord in matching incid?! dlog: %s %s %s ; %s %s %s' %
                  (dlogCID, dlXLng, dlYLat, opd_rd, XLng, YLat))
            continue

        incidPt = incid.point

        distDegree = incidPt.distance(dlPt)  # degrees!

        # EarthEquatorialRadius = 6378000
        Degree2Meter = 111195  # EarthEquatorialRadius * Pi / 180
        distMeter = distDegree * Degree2Meter

        distw = distWgt(distMeter, CloseRadius)

        match['dist'] = distMeter

        datew = dateDiffWgt(dayDiff, DateRange)

        matchScore = LocationScale * distw + DateScale * datew

        # 181223: PatrolLogs generally only report crimes in PC2CrimeCatTbl
        # NB: only keeping first PCode in match
        majorCrime = False
        for pc in dlog['reg_pc']:
            if incid.ctype in MajorCrimes:
                majorCrime = True
                break
        match['majorCrime'] = majorCrime

        match['mscore'] = matchScore

        # include all of OakCrime incident features
        match['incid'] = incid

        matchTbl[opd_rd] = match

        if logStream:
            # dRptNo,dLoc,dxlng,dylat,dDT,dPC,iCID,iAddr,ixlng,iylat,iDT,iCC,iCType,iDesc,matchScore,idDist,distMeter,dayDiff,majorCrime

            logFlds = [dlog['rptno'], dlog['location1'], dlXLng, dlYLat, dlogDateTime, dlog['reg_pc'],
                       incid.opd_rd, incid.addr, incid.xlng, incid.ylat, incid.cdateTime, incid.crimeCat, incid.ctype,
                       incid.desc, matchScore, idDist, distMeter, dayDiff, majorCrime]
            logStrFlds = ['"' + str(f) + '"' for f in logFlds]
            outline = ','.join(logStrFlds)
            logStream.write(outline + '\n')

    allMatch = list(matchTbl.keys())
    bestMatch = None
    bestMatchScore = 0.

    # select exact match CID result,
    for opd_rd in allMatch:
        match = matchTbl[opd_rd]
        # NB: parse_OPDLoPDF.mergeDailyLogs() adds suffix to cid for duplicate rptno
        # exact match of either allowed
        if opd_rd == dlogCID or opd_rd == dlog['rptno']:
            bestMatch = match
            break

    # or best-matching
    if not bestMatch:
        majorCrimes = []
        if requireMajorCrime:
            for opd_rd in allMatch:
                match = matchTbl[opd_rd]
                if match['majorCrime']:
                    majorCrimes.append(opd_rd)

            # NB: only match against majorCrime if it is unique
            if len(majorCrimes) > 1:
                # print('getBestMatch: multiple majorCrime match!',majorCrimes)
                pass
            elif len(majorCrimes) == 1:
                bestMatch = matchTbl[majorCrimes[0]]
        else:
            for opd_rd in allMatch:
                match = matchTbl[opd_rd]
                if match['mscore'] > bestMatchScore:
                    bestMatch = match
                    bestMatchScore = match['mscore']

    if bestMatch and logStream:
        # dRptNo,dLoc,dxlng,dylat,dDT,dPC,iCID,iAddr,ixlng,iylat,iDT,iCC,iCType,iDesc,matchScore,idDist,distMeter,dayDiff,majorCrime
        incid = bestMatch['incid']
        # NB: prefix best's CID with star!
        logFlds = [dlog['rptno'], dlog['location1'], dlXLng, dlYLat, dlogDateTime, dlog['reg_pc'],
                   incid.opd_rd, incid.addr, incid.xlng, incid.ylat, incid.cdateTime, incid.crimeCat, incid.ctype,
                   incid.desc, matchScore, idDist, distMeter, dayDiff, majorCrime]
        logStrFlds = ['"' + str(f) + '"' for f in logFlds]
        outline = ','.join(logStrFlds)
        logStream.write(outline + '\n')

    return bestMatch


def findSimIncid(dlogTbl, nowString, logStr=None, verbose=None):
    '''build ranked list of dailyIncid 'similar' to each dailyLog
    return dlogMatchTbl: 	cid -> OakCrime() and
           dlogUnmatchTbl: 	dlogCID -> OakCrime()
    '''

    allCID = list(dlogTbl.keys())
    allCID.sort()

    nhit = 0
    nmissGC = 0
    nmissDate = 0
    nmissTime = 0
    ncidMatch = 0
    nnearMatch = 0
    nunmatch = 0
    nbadTransform = 0
    ndrop = 0
    dlMatchTbl = {}
    unMatchTbl = {}

    for i, dlogCID in enumerate(allCID):
        if verbose is not None and i % verbose == 0:
            print(
                'findSimIncid: i=%d %s NHit=%d NDrop=%d NMissGC=%d NMissDate=%d NBadTran=%d NMissTime=%d NCIDMatch=%d '
                'NNearMatch=%d NMatch=%d NUnmatch=%d/%d (%d)' %
                (i, dlogCID, nhit, ndrop, nmissGC, nmissDate, nbadTransform, nmissTime, ncidMatch, nnearMatch,
                 len(dlMatchTbl),
                 len(unMatchTbl), nunmatch, (len(dlMatchTbl) + len(unMatchTbl))))

        dlog = dlogTbl[dlogCID]

        # first try using cid directly
        if dlogCID.find('_') != -1:
            dlcid, suf = dlogCID.split('_')
        else:
            dlcid = dlogCID
        try:
            sameCIDIncid = OakCrime.objects.filter(opd_rd=dlcid)
        except Exception as e:
            sameCIDIncid = []

        # not uncommon to have multiple incident records sharing same OPD_RD
        if len(sameCIDIncid) >= 1:
            # NB: arbitrarily pick FIRST; all should share same date, location
            incid = sameCIDIncid[0]
            nhit += 1
            # HACK: create dictionary for use in mergeDLog2Incid()
            opd_rd = incid.opd_rd
            match = {'cid': opd_rd}
            match['incid'] = incid
            newOC = mergeDLog2Incid(dlog, match, nowString)
            dlMatchTbl[dlogCID] = newOC
            continue

        # Can't find approximate match without date and location
        # drop those missing either
        if not ('reg_date' in dlog and 'location1' in dlog and 'XLng' in dlog and 'YLat' in dlog):
            ndrop += 1
            continue

        # Next try heuristic matching based on date,
        bestMatch = getBestMatch(dlog, dlogCID, logStr)

        if bestMatch == 'missGC':
            nmissGC += 1
            bestMatch = None
        elif bestMatch == 'missDate':
            nmissDate += 1
            bestMatch = None
        elif bestMatch == 'cantTransformPt':
            nbadTransform += 1
            bestMatch = None

        if bestMatch is None:
            nunmatch += 1
            newOC = mergeDLog2Incid(dlog, None, nowString)
            unMatchTbl[dlogCID] = newOC

        else:

            # NB: parse_OPDLoPDF.mergeDailyLogs() adds suffix to cid for duplicate rptno
            # exact match of either allowed
            if bestMatch['cid'] == dlogCID or bestMatch['cid'] == dlog['rptno']:
                ncidMatch += 1
                newOC = mergeDLog2Incid(dlog, bestMatch, nowString)
                dlMatchTbl[dlogCID] = newOC

            elif bestMatch['majorCrime'] and bestMatch['mscore'] > 0.5:
                nnearMatch += 1
                newOC = mergeDLog2Incid(dlog, bestMatch, nowString)
                dlMatchTbl[dlogCID] = newOC

            else:
                nunmatch += 1
                newOC = mergeDLog2Incid(dlog, None, nowString)
                unMatchTbl[dlogCID] = newOC

        # import pdb; pdb.set_trace()

    # Interpretting log lines
    #
    # 	NHit=289	nhit	NHit	query on CID returns >= 1
    # 	NDrop=0	ndrop	NDrop	no date or no time
    # 	NMissGC=4	nmissGC	NMissGC	getBestMatch: no location, X, Y
    # 	NMissDate=0	nmissDate	NMissDate	getBestMatch: no reg_date
    # 	NBadTran=27	nbadTransform	NBadTran	getBestMatch: dlPt.transform(SRS_10N) exception
    # 	NMissTime=0	nmissTime	NMissTime	N/A!
    # 	NCIDMatch=0	ncidMatch	NCIDMatch	exact CID match
    # 	NNearMatch=19	nnearMatch	NNearMatch	match above sim thresh
    # 	NMatch=308	len(dlMatchTbl)	NMatch
    # 	NUnmatch=60/60	len(unMatchTbl)	NUnmatch
    # 	nunmatch	“ / Nunmatch”	no best nor ncidMatch nor above match thresh
    # 	(368)	(len(dlMatchTbl)+len(unMatchTbl))	“( )”

    print(
        'findSimIncid: FINAL NHit=%d NDrop=%d NMissGC=%d NMissDate=%d NBadTran=%d NMissTime=%d NCIDMatch=%d '
        'NNearMatch=%d NMatch=%d NUnmatch=%d/%d (%d)' %
        (nhit, ndrop, nmissGC, nmissDate, nbadTransform, nmissTime, ncidMatch, nnearMatch, len(dlMatchTbl),
         len(unMatchTbl), nunmatch, (len(dlMatchTbl) + len(unMatchTbl))))

    return dlMatchTbl, unMatchTbl
