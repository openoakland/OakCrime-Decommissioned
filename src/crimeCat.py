'''
Created on Sep 23, 2014

@author: rik
'''

import csv

DescOnly2CatTbl = None
CTypeOnly2CatTbl = None
DescCType2CatTbl = None

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

def bldCrimeCatList(inf):
    'list of all crimeCat including implicit interior categories'
    
    allCat = []
    
    print 'bldCrimeCatList: reading categories from',inf
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

    return allCat
 
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
