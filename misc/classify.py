def classify(incid):
	''' classification into CrimeCat based on:
			1. PC code
			2. match ctype, desc against match rules in CTypeDesc2CCTbl
	'''

	if incid.pcList is not None and len(incid.pcList) > 0:
		pcList = eval(incid.pcList)
		for pc in pcList:
			try:
				pco = PC2CC.objects.get(pc=pc)
				# NB: some PC codes are 'qualifiers'
				if pco.crimeCat.startswith('('):
					continue
				return pco.crimeCat
			except ObjectDoesNotExist:
				continue
			except Exception as e:
				print('classify: bad PC?!',pc,e)
				continue
				
	if incid.ctype =='' and incid.desc == '':
		return ''
	
	qs = CrimeCatMatch.objects.filter(matchType='cd') \
							  .filter(ctype=incid.ctype) \
							  .filter(desc=incid.desc)
	if qs.exists():
		cc = qs[0].crimeCat
		return cc
	
	# NB: match first against MORE SPECIFIC descriptions
	
	# NB: desc limited to first 100 char in CrimeCatMatch
	desc = incid.desc[:99]
	qs = CrimeCatMatch.objects.filter(matchType='d') \
							  .filter(desc=desc)
	if qs.exists():
		cc = qs[0].crimeCat
		return cc

	qs = CrimeCatMatch.objects.filter(matchType='c') \
							  .filter(ctype=incid.ctype)
	if qs.exists():
		cc = qs[0].crimeCat
		return cc
	return ''

