'''  crimeCat (was statute)
Statute, UCR, DOJ crime category-related analysis, pulled from opd_130305
Created on Mar 26, 2013

@author: rik
'''

import csv

def freqHist(tbl):
    "Assuming values are frequencies, returns sorted list of (val,freq) items in descending freq order"
    def cmpd1(a,b):
        "decreasing order of frequencies"
        return cmp(b[1], a[1])

    
    flist = tbl.items()
    flist.sort(cmpd1)
    return flist

# 2do: share in common __init__
import socket
host = socket.gethostname()
if host.startswith('vb-hancock'):
    DataDir = '/media/sf_sharedData/c4a_oakland/OAK_data/'
elif host.startswith('hancock'):
    DataDir = '/Data/sharedData/c4a_oakland/OAK_data/'
elif host.startswith('mjq'):
    DataDir = '/home/Data/c4a_oakland/OAK_data/'

PlotDir = DataDir+'plots/'    
LogDir = DataDir+'logs/'    

Stat2UCRThresh = 0.95

StatuteTbl = {}
UCRTbl = {}


class UCR_Code():
    def __init__(self,idStr): 
        self.id = idStr
        self.desc = ''
        self.statList = []
        self.parent = None
        self.kids = []

def ppUCRTbl(outf):
        
    outs = open(outf,'w')
    outs.write('UCR,Desc,Stats\n')
    ucrList = UCRTbl.keys()
    ucrList.sort()
    for ucr in ucrList:
        currUCR = UCRTbl[ucr]
        outs.write('%s,"%s","%s"\n' % (ucr,currUCR.desc,currUCR.statList))
    outs.close()
  
class CrimeCat():

    def __init__(self,ccid,rent=None): 
        self.ccid = ccid
        self.desc = ''
        self.opdCtypeList = []
        self.statList = []
        self.UCRList = []
        self.attrib = {}
        self.kids = []
        self.sibPos = None
        if rent:
            self.parent = rent
            rent.kids.append(self)
            self.sibPos = len(rent.kids)
        else:
            self.sibPos = 0
            self.parent = None
    
    def getHierIdx(self):
        hidx = '%d' % self.sibPos
        rent = self.parent
        while rent and rent.ccid != HeadLbl:
            hidx = ('%d.' % rent.sibPos) + hidx
            rent = rent.parent
        return hidx         

HeadLbl = '000_head'
    
class Statute():

    def __init__(self,idStr): 
        self.statIDStr = idStr
        self.normStat = ''
        self.desc = ''
        self.UCRList = []
        self.attrib = {}
        self.parent = None
        self.kids = []    

def ppStatTbl(outf):
        
    outs = open(outf,'w')
    outs.write('Stat,Desc,UCR,Attrib\n')
    statList = StatuteTbl.keys()
    statList.sort()
    for stat in statList:
        currStat = StatuteTbl[stat]
        outs.write('%s,"%s","%s","%s","%s"\n' % (stat,currStat.desc,currStat.UCRList,currStat.attrib))
    outs.close()

def ppCrimeCatTbl(ccTbl,outf):
        
    outs = open(outf,'w')
    outs.write('CatIdx,Cat,CTypes,Stats,Kids\n')
    catList = ccTbl.keys()
    catList.sort()
    for cat in catList:
        currCat = ccTbl[cat]
        catIdx= currCat.getHierIdx()
        kidStr = ''
        for kid in currCat.kids:
            kidx = kid.getHierIdx()
            kidStr += '%s:%s,' % (kidx,kid.ccid)
        outs.write('"%s","%s","%s","%s","%s"\n' % (catIdx,cat,currCat.opdCtypeList,currCat.statList,kidStr))
    outs.close()
    
# Codes primarily from CA_DOJ_codes.pdf
# a few others (with ?) added  to accomodate additional ones found
CA_DOJ_CodeTbl = \
    {'BP': 'Business and Professions Code',
    'CC': 'Corporations Code',
    'CI': 'Civil Code',
    'EC': 'Education Code',
    'FA': 'Food and Agriculture Code',
    'FC': 'Financial Code',
    'FG': 'Fish and Game Code',
    'GC': 'Government Code',
    'HN': 'Harbors and Navigation Code',
    'HS': 'Health and Safety Code',
    'IC': 'Insurance Code',
    'LC': 'Labor Code',
    'MV': 'Military and Veterans Code',
    'OM': 'OM??',
    'PC': 'Penal Code',
    'PR': 'Public Resources Code',
    'RT': 'Revenue and Taxation Code',
    'SC': 'SC??',
    'SH': 'Streets and Highways Code',
    'UI': 'Unemployment Insurance Code',
    'US': 'U.S. Code?',
    'VC': 'Vehicle Code',
    'WI': 'Welfare and Institutions Code'}

CA_DOJ_Codes = CA_DOJ_CodeTbl.keys()

def normStat(s):
    # 2do: handle slashes?!
    
    s = s.strip().upper()
    if s[0:2] in CA_DOJ_Codes:
        news = s[0:2]+'_'+s[2:]
    else:
        news = 'XX_'+s
    news = news.replace('.','_')
    news = news.replace(' (','_')
    news = news.replace('(','_')
    news = news.replace(')','')
    news = news.replace(' ','_')
    return news

HierBreakChar = '_'

def initAncestors(ccTbl,rentName):
    'fill in any necessary ancestors starting with rent'
    
    ancList = rentName.split(HierBreakChar)
    prevAnc = None
    for anc in enumerate(ancList):
        if prevAnc:
            newCC = CrimeCat(anc,prevAnc)
        else:
            newCC = CrimeCat(anc,ccTbl[HeadLbl])
        prevAnc = newCC
    return newCC   
    
def addOPDCat(ccTbl,newCatf):
    'add new categories from newCat, USC-encoded'

    ## begin CrimeCatTbl with any new categories in newCrimeCat
    print 'bld_USC_StatInfo: loading newCat from %s ...' % (newCatf)
    csvDictReader = csv.DictReader(open(newCatf))
    # NewCat,UCR,Statutes
    for ri,entry in enumerate(csvDictReader):
        cat = entry['NewCat']
                
        if cat in ccTbl:
            # might have already been introduced as ancestor
            currCat = ccTbl[cat]
        else:
            if HierBreakChar in cat:
                bpos = cat.index(HierBreakChar)
                rentName = cat[:bpos]
                if rentName not in ccTbl:
                    rent = initAncestors(ccTbl,rentName)
                else:
                    rent = ccTbl[rentName]
            
            currCat = CrimeCat(cat,rent)   
        
        statListStr = entry['Statutes']
        for stat in statListStr.split(','):
            currCat.statList.append( normStat(stat) )
        UCRListStr = entry['Statutes']
        for ucr in statListStr.split(','):
            currCat.UCRList.append(ucr)
            
    print 'addOPDCat: done. NCat=%d' % (len(ccTbl))
    return ccTbl

def bldCTypeEncodeTbl(uscef):
    ## next load OPD friendly category encodings
    encodeTbl = {}
    print 'bldCTypeEncodeTbl: loading category encodings from %s ...' % (uscef)
    
    csvDictReader = csv.DictReader(open(uscef))
    # Raw,Encoded
    for ri,entry in enumerate(csvDictReader):
        raw = entry['Raw']
        encode = entry['Encoded']
        encodeTbl[raw] = encode
    print 'bldCTypeEncodeTbl:  done.  NEncode=%d' % (len(encodeTbl))    
    
    return encodeTbl
    
def bld_USC_StatInfo():
    '''build StatuteTbl, CrimeCatTbl from USC_UCR_and_Statutes
       augment with category encodings in USC_UCR_CatEncoding and new crimeCat in newOPD_Categories
    '''
    
    # ASSUME all global tables initialized prior to call

    global StatuteTbl
    global CrimeCatTbl
    
    ## begin CrimeCatTbl with any new categories in newCrimeCat
    inf = DataDir + 'OAK_data/newOPD_Categories.csv'
    print 'bld_USC_StatInfo: loading newCat from %s ...' % (inf)
    
    csvDictReader = csv.DictReader(open(inf))
    # NewCat,UCR,Statutes
    for ri,entry in enumerate(csvDictReader):
        cat = entry['NewCat']
        encode = 'OPD_'+cat
        statListStr = entry['Statutes']
        nstatList = []
        for stat in statListStr.split(','):
            nstatList.append( normStat(stat) )
        CrimeCatTbl[encode] = nstatList
    

    ## next load OPD friendly category encodings
    USC_UCR_EncodeTbl = {}
    inf = DataDir + 'OAK_data/USC_UCR_CatEncoding.csv'
    print 'bld_USC_StatInfo: loading category encodings from %s ...' % (inf)
    
    csvDictReader = csv.DictReader(open(inf))
    # Raw,Encoded
    for ri,entry in enumerate(csvDictReader):
        raw = entry['Raw']
        encode = entry['Encoded']
        USC_UCR_EncodeTbl[raw] = encode
    
    
    inf = DataDir + 'OAK_data/USC_UCR_and_Statutes.csv'
    print 'bld_USC_StatInfo: loading USC categories from %s ...' % (inf)
    
    csvDictReader = csv.DictReader(open(inf), delimiter='\t')
    # Sta_UCR_Cat_Cd, Sta_UCR_Cat, Sta_Statute_Code, Sta_Statute_Desc
    for ri,entry in enumerate(csvDictReader):
        stat = entry['Sta_Statute_Code']
        nstat = normStat(stat)
        desc = entry['Sta_Statute_Desc'].strip()
        ucr = entry['Sta_UCR_Cat_Cd'].strip()
        ucrDesc = entry['Sta_UCR_Cat'].strip()
       
        if len(ucr)==0:
            # missing UCR info
            if nstat.startswith('VC'):
                encode = 'OPD_OTHER_TRAFFIC'
            else:
                encode = 'OPD_OTHER_NON_USC'
        else:
            # conventionalize UCR desc to be compatabile with OPD categories
            if ucrDesc not in USC_UCR_EncodeTbl:
                print 'bld_USC_StatInfo: unencoded UCR desc?!'
                continue
            
            encode = 'OPD_'+USC_UCR_EncodeTbl[ucrDesc]

        if encode in CrimeCatTbl:
            if nstat not in CrimeCatTbl[encode]:
                CrimeCatTbl[encode].append(nstat)
        else:
            CrimeCatTbl[encode] = [nstat]

                    
        if nstat in StatuteTbl:
#            if stat != StatuteTbl[nstat].statIDStr:
#                print 'add_USC_StatInfo: nonNormID?!',nstat,StatuteTbl[nstat].statIDStr,stat
            stato = StatuteTbl[nstat]
        else:
            stato = Statute(stat)
            stato.normStat = nstat
            stato.desc = desc
            
        StatuteTbl[nstat] = stato         
        
    print 'add_USC_StatInfo: NStat=%d NUCR=%d NCat=%d'  % (len(StatuteTbl),len(UCRTbl),len(CrimeCatTbl))

def add_UCR_stats():
    'read stat -> (UCR, prob, freq) from file produced in opd.bld_usc_statuteMaps()'
    
    global StatuteTbl
    global UCRTbl
    
    addStatThresh = 5
    
    s2uf = DataDir + 'OAK_data/stat2ucr.csv'
    print 'add_UCR_info: reading USC_Statute -> UCR info from',s2uf
    s2us = open(s2uf)
    
    csvDictReader = csv.DictReader(open(s2uf))
    nadd = 0
    ntp = 0
    ntn = 0
    nfp = 0
    nfn = 0
    trueFreq=0
    falseFreq=0
    for ri,entry in enumerate(csvDictReader):    
        # 'Statute,UCR,Freq,Prob'
        ucr = entry['UCR'].strip()
        if len(ucr)==0:
            continue

        stat = entry['Statute']
        nstat = normStat(stat)
        freq = int(entry['Freq'])
        prob = float(entry['Prob'])
        
    
        if nstat in StatuteTbl:
#            if stat != StatuteTbl[nstat].statIDStr:
#                print 'add_UCR_stats: nonNormID?!',nstat,StatuteTbl[nstat].statIDStr,stat
            currStat = StatuteTbl[nstat]
        else:
            # print 'add_UCR_stats: missing stat?!',ri,stat,nstat
            if freq > addStatThresh:
                nadd += 1
                currStat = Statute(stat)
                currStat.normStat = nstat
                StatuteTbl[nstat] = currStat
                
                if ucr not in UCRTbl:
                    currUCR = UCR_Code(ucr)
                    currUCR.statList.append(nstat)
                else:
                    currUCR = UCRTbl[ucr]
                    if nstat not in currUCR.statList:
                        currUCR.statList.append(nstat)
                UCRTbl[ucr] = currUCR

            else:
                continue
        
        if prob < Stat2UCRThresh:
            if ucr in currStat.UCRList:
                nfn += 1
                print 'add_UCR_stats: FN: %s %s %f' % (nstat,ucr,prob)
                falseFreq += freq
            else: 
                ntn += 1
                trueFreq += freq
        else:
            if ucr in currStat.UCRList:
                ntp += 1
                trueFreq += freq
            else: 
                nfp += 1           
                print 'add_UCR_stats: FP: %s %s %f' % (nstat,ucr,prob)
                falseFreq += freq
               
    s2us.close()
    iacc = float(trueFreq) / (falseFreq+trueFreq)
    acc = float(ntp+ntn) / (ntp+ntn+nfp+nfn)
    print 'add_UCR_stats: NAdd=%d NStat=%d NUCR=%d IncidAcc=%f TP=%d TN=%d FP=%d FN=%d CatAcc=%f'  % \
        (nadd,len(StatuteTbl),len(UCRTbl),iacc,ntp,ntn,nfp,nfn,acc)

UCR_AnnRpt2CA_DOJTbl = {'Violent crime total': None,
                  'Murder and nonnegligent Manslaughter': 'Homicide',  # ??
                  'Forcible rape': 'Forcible Rape',
                  'Robbery': 'Robbery',
                  'Aggravated assault': 'Assault',                     # too broad!
                  'Property crime total': None,
                  'Burglary': 'Burglary',
                  'Larceny-theft': 'Theft',
                  'Motor vehicle theft': 'Motor Vehicle Theft'}

def rptUCRTopCat(outf):
    
    outs = open(outf,'w')
    outs.write('TopCat,Statutes,UCR\n')
    for tcatLbl,cadojLbl in UCR_AnnRpt2CA_DOJTbl.items():
        if not cadojLbl:
            continue
        
        ccat = 'FELONY_'+cadojLbl
        if ccat not in CrimeCatTbl:
            print 'missing category?!', ccat
            continue
        
        statList = CrimeCatTbl[ccat]
        ucrList = []
        for nstat in statList:
            ulist = StatuteTbl[nstat].UCRList
            for ucr in ulist:
                if ucr not in ucrList:
                    ucrList.append(ucr)
        
        statStr = str(statList)
        ucrStr = str(ucrList)
        outs.write('"%s","%s","%s"\n' % (tcatLbl,statStr,ucrStr))

def add_CA_DOJ_statutes():
    'Add labels to CrimeCatTbl; crimeCat, Felony/Misdimeanor flags to StatuteTbl'
    dojf = DataDir + 'CA_DOJ_codes.txt'
    print 'add_CA_DOJ_statutes: reading CA_DOJ  from',dojf
    inStr = open(dojf)

    global CrimeCatTbl
    global StatuteTbl
    
    #* FELONY
    #Homicide - 128, 187(a), 189, 192(a), 192(b), 193(a), 193(b), 273ab, 399, 12310(a)
    #Forcible Rape - 220, 220(a), 220(b), 261, 261(a)(1), 261(a)(2), 261(a)(3), 261(a)(4), 261(a)(4)(a), 261(a)(4)(b), 261(a)(4)(c), 261(a)(4)(d), 261(a)(5), 261(a)(6), 261(a)(7), 262(a)(1), 262(a)(2), 262(a)(3), 262(a)(4), 262(a)(5), 264.1, 266c, 269(a)(1), 269(a)(2), 288.7(a), 288.7(b), 664/261
    nline=0
    currCat = ''
    nhit = 0
    nmiss = 0
    
    for line in inStr.readlines():
        nline = nline+1
        line = line[:-1] # strip \n
        line.strip()
        if line.startswith('*'):
            currCat = 'CADOJ_'+line[2:]
            continue
        hpos = line.index(' - ')
        subcat = line[:hpos].strip()
        cat = currCat+HierBreakChar+subcat
        statListStr = line[hpos+3:]
        statList = statListStr.split(',')
        for stat in statList:
            if currCat.startswith('CADOJ_FELONY'):
                fm = 'FELONY'
            elif currCat.startswith('CADOJ_MISDEMEANOR'):
                fm = 'MISDEMEANOR'
            stat = stat.strip()
            if stat.endswith('*'):
                fm = 'both'
                stat = stat[:-1]
                
            if stat[-2:].isalpha():
                statCode = stat[-2:]
                stat = stat[:-2]
            else:
                statCode = 'PC'
            stat = statCode+stat
            
            nstat = normStat(stat)
            
            if nstat not in StatuteTbl:
                nmiss += 1
                continue
            
            nhit += 1
            currStat = StatuteTbl[nstat]
            currStat.attrib['FelMis'] = fm
            currStat.attrib['CADOJ'] = cat
            StatuteTbl[nstat] = currStat
            
            if cat in CrimeCatTbl:
                if nstat not in CrimeCatTbl[cat]:
                    CrimeCatTbl[cat].append(nstat)
            else:
                CrimeCatTbl[cat] = [nstat]

    print 'add_CA_DOJ_statutes: NHit=%d NMiss=%d NCrimeCat=%d' % (nhit,nmiss,len(CrimeCatTbl))

    
def bldStatuteTbl():
    global StatuteTbl,UCRTbl,CrimeCatTbl
    StatuteTbl = {}
    # UCRTbl = {}
    CrimeCatTbl = {}
    bld_USC_StatInfo()
    # add_UCR_stats()
    add_CA_DOJ_statutes()
    # ppUCRTbl(DataDir+'UCRTbl_130419.csv')
    ppStatTbl(DataDir+'statTbl_130419.csv')
    ppCrimeCatTbl(DataDir+'CrimeCatTbl_130419.csv')

def addCMCat(ccTbl,cmf):
    'augment crimeCatTbl with any CrimeMapper OPD_CType-based categories in cmf'
    
    csvDictReader = csv.DictReader(open(cmf,"r"))
    # Idx,CrimeCat,Desc,PD_ID,Addr,PD,Date,Time
    for ri,entry in enumerate(csvDictReader):
        crimeCat=entry['CrimeCat']
        crimeCat = crimeCat.upper()
        desc=entry['Desc']
        headCat = ccTbl[HeadLbl]
        if crimeCat not in ccTbl:
            # all CM categories are at top level
            currCat = CrimeCat(crimeCat,headCat)
            currCat.attrib['Source']='CrimeMapper'
            ccTbl[crimeCat] = currCat
            
        else:
            currCat = ccTbl[crimeCat]
        if desc not in currCat.opdCtypeList:
            currCat.opdCtypeList.append(desc)
            
    print 'addCMCat: done. NCat=%d' % (len(ccTbl))
    return ccTbl
    
def addStatCat(ccTbl,statCatf,catPrefix='OPD'):
    'augment ccTbl with categories from statCatf; return stat2catTbl'
    
    csvDictReader = csv.DictReader(open(statCatf))
    s2cTbl = {} # catLbl -> {nstat:1}
    plen = len(catPrefix)
    ndup=0
    # Cat,Stats
    for ri,entry in enumerate(csvDictReader):
        cat = entry['Cat']

        if cat in ccTbl:
            # might have already been introduced as ancestor
            currCat = ccTbl[cat]
        else:
            if HierBreakChar in cat:
                bpos = cat.index(HierBreakChar)
                rentName = cat[:bpos]
                if rentName not in ccTbl:
                    rent = initAncestors(ccTbl,rentName)
                else:
                    rent = ccTbl[rentName]
            
            currCat = CrimeCat(cat,rent)   
        
        statListStr = entry['Stats']
        for stat in statListStr.split(','):
            nstat = normStat(stat)
            currCat.statList.append(nstat)
            if stat in s2cTbl:
                print 'addStatCat: mult cat/stat?!',stat,s2cTbl[stat],nstat
                ndup += 1
            else:
                s2cTbl[stat] = nstat
                
    print 'addStatCat: done. NCat=%d' % (len(ccTbl))
    return ccTbl,s2cTbl
    
# 2do NEXT...
#def addCTypeCat(ccTbl,csvFile,cteTbl):
#    
#    csvDictReader = csv.DictReader(open(csvFile),delimiter='\t')
#    # Idx,OPD_RD,OIdx,Date,CType,Beat,Addr,Lat,Long,UCR,Statute
#    for ri,entry in enumerate(csvDictReader):
#        ctype = entry['CType']
#        
#        if ctype in cteTbl:
#            ctype = cteTbl[ctype]
#        
#        
#        
#        
#        stat = entry['Statute']

    
def bldCrimeCat():
    
    ccTbl = {}
    ccHead = CrimeCat(HeadLbl)
    ccHead.desc = 'AllCrimes'
    ccTbl[HeadLbl] = ccHead

    cmf = DataDir + 'crimeMapping/CrimeMapping_130418-130501.csv'
    ccTbl = addCMCat(ccTbl,cmf)
    
    newCatf = DataDir + 'newOPD_Categories.csv'
    ccTbl = addOPDCat(ccTbl,newCatf)
    
    uscef = DataDir + 'USC_UCR_CatEncoding.csv'
    cteTbl = bldCTypeEncodeTbl(uscef)
    
    statCatf = '/Data/sharedData/c4a_oakland/CrimeCatTbl_130419.csv'
    ccTbl, stat2CatTbl = addStatCat(ccTbl,statCatf)
    
    csvFile = DataDir+'OPD_combined_130417.csv'
    ccTbl = addCTypeCat(ccTbl,csvFile,cteTbl)
    
    outf = DataDir + 'crimeCat_130503.csv'
    ppCrimeCatTbl(ccTbl,outf)
    return ccTbl
    
def formNewCatFile(inf,outf):   
    'utility routine to consume hand-formed list of categories'
    print "Loading %s ..." % inf
    nline=0
    
    inStr = open(inf,'r')
    currHeading = ''
    typeTbl = {}
    for line in inStr.readlines():
        nline = nline+1
        line = line[:-1].strip()
        if len(line)==0:
            continue
        if line.startswith('*'):
            currHeading = line[2:]
            continue
        desc = ''
        ctype = ''
        if currHeading not in typeTbl:
            typeTbl[currHeading] = []
        ppos = line.find('+')
        if ppos != -1:
            ctype = line[ppos+1:]
            if ppos==0:
                typeTbl[currHeading].append( (ctype,'') )
            else:
                desc = line[:ppos]
                typeTbl[currHeading].append( (ctype,desc) )
        else:
            desc = line
            typeTbl[currHeading].append( ('',desc) )
    inStr.close()
    print "formNewCatFile: done. NLines read=",nline
    outs = open(outf,'w')
    outs.write('Category,CType,Desc\n')
    catKeys = typeTbl.keys()
    catKeys.sort()
    nline = 0
    for cat in catKeys:
        for ct,d in typeTbl[cat]:
            outs.write('%s,%s,"%s"\n' % (cat,ct,d))
            nline += 1
    outs.close()
    print "formNewCatFile: done. NLines output=",nline

def getCrimeCat(inf):
    'return hierarchic tables capturing crimeCat'
    
    catTbl = {'TOP': {} }
    
    print 'getCrimeCat: reading categories from',inf
    csvDictReader = csv.DictReader(open(inf,"r"))
    # Category,CType,Desc
    for ri,entry in enumerate(csvDictReader):
        fullCat = entry['Category']
        
        path = fullCat.split('_')
        parent = catTbl['TOP']
        while len(path)>0:
            cat = path.pop(0)  # treat as queue
            if cat not in parent:
                parent[cat] = {}
            parent = parent[cat]
                
    return catTbl            
  
def listCrimeCat(inf):
    'produce doubles list of crimeCat required for showCrime/forms.py'
    
    allCat = []
    
    print 'getCrimeCat: reading categories from',inf
    csvDictReader = csv.DictReader(open(inf,"r"))
    # Category,CType,Desc
    for ri,entry in enumerate(csvDictReader):
        fullCat = entry['Category']
        prefix = ''
        path = fullCat.split('_')
        while len(path)>0:
            cat = path.pop(0)  # treat as queue
            if prefix != '':
                prefix += '_'
            newPref = prefix+cat
            if newPref not in allCat:
                allCat.append(newPref)
            prefix = newPref
            
    print 'CrimeCatChoices = ( ',
    for cat in allCat:
        print '\t("%s","%s"),' % (cat,cat)
    print ')'
  
DescOnly2CatTbl = None
CTypeOnly2CatTbl = None
DescCType2CatTbl = None

def bldClassTbls(inf):
    '''use data from new_cat file to build DescOnly2CatTbl, CTypeOnly2CatTbl 
        and DescCType2CatTbl, for use by classCrime()'''

    global DescOnly2CatTbl
    global CTypeOnly2CatTbl 
    global DescCType2CatTbl
    DescOnly2CatTbl = {}
    CTypeOnly2CatTbl = {}
    DescCType2CatTbl = {}    
    
    print 'bldClassTbls: reading categories from',inf
    csvDictReader = csv.DictReader(open(inf,"r"))
    # Category,CType,Desc
    for ri,entry in enumerate(csvDictReader):
        cat = entry['Category']
        ct = entry['CType']
        d = entry['Desc']
        if len(ct)==0:
            # assert d not in DescOnly2CatTbl, 'duplicate desc?! %s' % d
            if d in DescOnly2CatTbl:
                print 'duplicate desc?! %s' % d
            DescOnly2CatTbl[d] = cat
        elif len(d)==0:
            # assert ct not in CTypeOnly2CatTbl, 'duplicate ctype?! %s' % ct
            if ct in CTypeOnly2CatTbl:
                print 'duplicate ctype?! %s' % ct
            CTypeOnly2CatTbl[ct] = cat
        else:
            t = (ct,d)
            # assert t not in DescCType2CatTbl, 'duplicate ctype+desc?! %s' % t
            if t in DescCType2CatTbl:
                print 'duplicate ctype+desc?! %s' % (t,)
            DescCType2CatTbl[t] = cat
    print 'bldClassTbls: done. DescOnly2CatTbl=%d CtypeOnly2CatTbl=%d DescCType2CatTbl=%d' % \
            (len(DescOnly2CatTbl), len(CTypeOnly2CatTbl), len(DescCType2CatTbl))
  
def classCrime(ctype,desc):
    'use DescOnly2CatTbl, CTypeOnly2CatTbl and DescCType2CatTbl'
    if ctype in CTypeOnly2CatTbl:
        return CTypeOnly2CatTbl[ctype]
    if desc in DescOnly2CatTbl:
        return DescOnly2CatTbl[desc]
    t = (ctype,desc)
    if t in DescCType2CatTbl:
        return DescCType2CatTbl[t]
    else:
        return ''

def classCrimeAll(ctype,desc):
    'use DescOnly2CatTbl, CTypeOnly2CatTbl and DescCType2CatTbl'
    fnd = []
    if ctype in CTypeOnly2CatTbl:
        fnd.append(CTypeOnly2CatTbl[ctype])
    if desc in DescOnly2CatTbl:
        fnd.append(DescOnly2CatTbl[desc])
    t = (ctype,desc)
    if t in DescCType2CatTbl:
        fnd.append(DescCType2CatTbl[t])
    return fnd

def analOPDClass(crimeCatf,allCrimef):
    
    bldClassTbls(crimeCatf)
    
    print 'analOPDClass: reading from',allCrimef
    csvReader = csv.reader(open(allCrimef, "r"))

    classTbl = {}
    missTbl = {}
    dupTbl = {} # (c,t) -> {
    nredun = 0
    nmiss = 0
    for ri,row in enumerate(csvReader):
        # OPD
        # "OTHER",2010-09-28 00:00:00,"01-053413","GRAND THEFT","",""
        # "MISDEMEANOR WARRANT",2007-03-01 10:40:00,"03-025334","MISDEMEANOR BENCH WARRANT - LOCAL","99X","O/S"
        
        if ri % 50000 == 0:
            print 'anal_OPD_CTypeDesc',ri
            
        (crimeType,dateStr,cid,desc,beat,addr) = row
        
        ct = crimeType.upper().strip()
        d = desc.upper().strip()
        t = (ct,d)
        fnd = classCrimeAll(ct,d)
        if len(fnd)>1:
#            nambig +=1 
#            print ('dup: %s,%s: ' % (ct,d)),
#            for c in fnd:
#                print ('"%s",' % c),
#            print

            first = fnd[0]
            if all(e==first for e in fnd[1:]):
                nredun += 1
                continue
            if t in dupTbl:
                dupTbl[t][1] += 1
            else:
                dupTbl[t] = [fnd,1]            
            
        elif len(fnd)==0:
            nmiss += 1
            if t in missTbl:
                missTbl[t] += 1
            else:
                missTbl[t] = 1
        else:
            cat = fnd[0]
            if cat in classTbl:
                classTbl[cat] += 1
            else:
                classTbl[cat] = 1

    print 'analOPDClass: done. NMiss=%d NRedun=%d' % (nmiss,nredun)
    cHist = freqHist(classTbl)
    print '\n# Class'
    print 'Class,Freq'
    for cat,freq in cHist:
        print '"%s",%d' % (cat,freq)

    missHist = freqHist(missTbl)
    print '\n# Misses'
    print 'CType,Desc,Freq'
    for t,freq in missHist:
        print '"%s","%s",%d' % (t[0],t[1],freq)

    
    dupFreqTbl = {}
    for k,v in dupTbl.items():
        dupFreqTbl[k] = dupTbl[k][1]
        
    dupHist = freqHist(dupFreqTbl)
    print '\n# Duplicates'
    print 'CType,Desc,Freq,Found'
    for t,freq in dupHist:
        print '"%s","%s",%d,"%s"' % (t[0],t[1],freq,dupTbl[t][0])
    

# bldStatuteTbl()
  
# ccTbl = bldCrimeCat()

# rawCatFile = DataDir + 'new_ctype4cat.txt'
# formNewCatFile(rawCatFile,newCatFile)  

# NB: make sure to comment out these executables; crimeCat imported!

#opd_file = DataDir+'OPD_PublicCrimeData_2007-12.csv'
#analOPDClass(newCatFile,opd_file)

CurrCatFile = DataDir + 'crimeCat_130528.csv'

# bldClassTbls(CurrCatFile)

ccTbl = getCrimeCat(CurrCatFile)
import pprint,json
pprint.pprint(ccTbl['TOP'])
# print json.dumps(ccTbl['TOP'])
# listCrimeCat(CurrCatFile)

