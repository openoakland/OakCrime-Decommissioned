''' dropSource4django: hack for import of CSV into postgresql database underlying showCrime django
Created on Nov 2, 2016

@author: rik
'''

import csv


def modCol(inf, outf):

    inflds = ['Idx','OPD_RD','OIdx','Date','Time','CType','Desc','Beat','Addr','Lat','Lng','Src','UCR','Statute','CrimeCat']
    outflds = ['idx','opd_rd','oidx','date','time','ctype','desc','beat','addr','lat','lng','ucr','statute','crimeCat', 'latlng']
    dropFld = 'Src'
    nonQuoteFlds = ['Idx', 'OIdx', 'Lat', 'Lng']
    outs = open(outf, 'w')
    hdrLine = ','.join(outflds) + '\n'
    outs.write(hdrLine)

# 	inStr = open(inf)
# 	for il,line in enumerate(inStr.readlines()):
# 		if il == 0:
# 			continue
# 		flds = line[:-1].split(',')
# 		nflds = len(flds)
# 		if nflds != len(inflds):
# 			nbad += 1
# 			continue
# 		del flds[dropFldIdx]

    reader = csv.DictReader(open(inf))
    for i, entry in enumerate(reader):
        flds = []
        for fname in inflds:
            if fname == dropFld:
                continue
            if fname in nonQuoteFlds:
                flds.append(entry[fname])
            else:
                flds.append('"'+entry[fname]+'"')

        flds.append('')

        outline = ','.join(flds) + '\n'
        outs.write(outline)
    outs.close()


if __name__ == '__main__':
    inf = 'OPD_161101.csv'
    outf = 'OPD_161101_showCrime.csv'
    modCol(inf, outf)
