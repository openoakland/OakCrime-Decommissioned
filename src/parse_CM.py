#===============================================================================
# parse_CM: simple parser for CrimeMapper html pages
#    Usage : python parse_CM.py HTML_ROWS_FILE CSV_FILE
#    
#    @author rik@electronicArtifacts.com
#    @date 31 Mar 14
#    @version 1.0
#===============================================================================

import sys
import re

def parseLine(line):
    mp0 = r'report-grid-alt-row'
    nl0 = re.sub(mp0,'',line)
    mp1 = r'<tr .*\);\"><td class=\"\"\><img src=\"images/map/crime-types/legend/'
    nl1 = re.sub(mp1,'"',nl0)
    mp2 = r'\.png\" /></td><td class=\"\"><span>'
    nl2=re.sub(mp2,'","',nl1)
    # NB: next regexp matches twice, substitutes on both
    mp3 = r'</span></td><td class=\"\"><span>'
    nl3=re.sub(mp3,'","',nl2) 
    mp4 = r'</span></td><td class=" no-wrap"><span>'
    nl4 = re.sub(mp4,'",',nl3)
    mp5 = r'(\d+\/\d+\/\d+) (\d+:\d+ [A|P]M)<\/span><\/td><\/tr>'
    nl5 = re.sub(mp5,r'"\1","\2"',nl4)
    
    data = [s.strip('"') for s in nl5.split(',') ]

    return data

def parseFile(inf,outf):

    # ASSUME inf html file that has been trimmed to only <tr> lines
    # </tr> -> </tr>\n
    # 2do: remove this requirement

    print "parseFile: Loading from %s, writing to %s:" % (inf,outf)
    nout=0
    nonOPD = 0
    nbadCID=0
    nline=0
    inStr = open(inf,'r')
    outs = open(outf,'w')
    outs.write('Idx,CrimeCat,Desc,PD_ID,Addr,PD,Date,Time\n')
    
    for line in inStr.readlines():
        line = line[:-1].strip()
        if len(line)==0:
            continue
        
        nline += 1
        
        lineData = parseLine(line)
        
        if lineData[4] != 'Oakland Police':
            nonOPD += 1
            continue
                    
        nout = nout+1
        outs.write('%d,' % (nout))
        for fld in lineData[:-1]:
            outs.write('%s,' % fld)
        outs.write('%s\n' % lineData[-1])   
        
    inStr.close()
    outs.close()
    print "parseFile: done. NLine=%d NNonOPD=%d NBadCID=%d NOut=%d" % (nline,nonOPD,nbadCID,nout)

# inf = DataDir + 'crimeMapping/crimeMapping_1_1_2014-1_10_2014_rowsOnly.html'
# outf = DataDir + 'crimeMapping/crimeMapping_1_1_2014-1_10_2014.csv'

if __name__ == "__main__":
    inf = sys.argv[1]
    outf = sys.argv[2]
    sys.exit(parseFile(inf,outf))


