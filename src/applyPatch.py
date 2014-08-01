def applyPatch(matchTblFile,newDataFile,ct2statTbl,stat2ucrTbl,missAddrFile,diffFile):
	'''Incorporate new data into existing data set
		Extrapolate previously geo-coded addresses to new incidents
		Extrapolate hi-probability UCR and Statute codes
	'''
	
	matchTbl = json2matchTbl(matchTblFile)
	
	# rptYearDist(matchTbl,'applyPatch_initial')
	
	newDataTbl  = loadDataSlice(newDataFile)
	
	# rptYearDist(newDataTbl,'applyPatch_newData')
	
	addrTbl = {}
	for cid,info in matchTbl.items():
		cdate,beat,addr,lat,long,incidList = info
		if lat != '' and long != '' and addr not in addrTbl:
			addrTbl[addr] = (lat,long)
	print 'applyPatch: addrTbl built NAddr=%d' % (len(addrTbl))
	
	mas = open(missAddrFile,'w')
	mas.write('CID,Addr\n')

	diffs = open(diffFile,'w')
	diffs.write('CID,Prev,Curr\n')
	
	nupdate = 0
	ndup = 0
	nmult = 0
	nnew = 0
	nincid = 0
	nambigCC = 0
	nmatchAddr=0
	nmissAddr=0
	for newCID in newDataTbl:
		(new_cdate,new_beat,new_addr,fooLat,barLong,incidList) = newDataTbl[newCID]
		if newCID in matchTbl:
			(prev_cdate,prev_beat,prev_addr,prev_lat,prev_long,prev_incid) = matchTbl[newCID]
			
			# NB: CType+Desc the only guaranteed commonality with new data
			allPrevCTD = [ctype+':'+desc for (ctype,desc,ucr,statute,cc) in prev_incid]
			
			if ((prev_cdate==new_cdate and \
			   	 prev_beat==new_beat and \
			     prev_addr==new_addr) or \
			   (prev_beat=='' and new_beat != '')):
				
				if (prev_beat=='' and new_beat != ''):
					# 2do: allow update of bad date/time, address
					nupdate += 1

				for baseInfo in incidList:
					ctype,desc = baseInfo
					ctd = ctype+':'+desc
					if ctd in allPrevCTD:
						ndup += 1
					else:
						ucr = ''
						statute = ''
						if ctype in ct2statTbl:
							(likelyStat,freq,prob) = ct2statTbl[ctype]
							if prob >= CT2StatThresh:
								statute = likelyStat+'(~)'
								if ucr=='' and likelyStat in stat2ucrTbl:
									(likelyUCR,freq,prob) = stat2ucrTbl[likelyStat]
									if prob >= Stat2UCRThresh:
										ucr = likelyUCR+'(~)'

						cc = crimeCat.classCrime(ctype, desc)
						if cc=='':
							nambigCC += 1
						
						newInfo = (ctype,desc,ucr,statute,cc)
						prev_incid.append( newInfo )
						nmult += 1
					
				newDataTbl[newCID] = (new_cdate,new_beat,new_addr,prev_incid)
				
			else:
				prev_dates = prev_cdate.strftime(C4A_dateTime_string2)
				prevTuple = tuple([prev_dates,prev_beat,prev_addr])
				dates  = new_cdate.strftime(C4A_dateTime_string2)
				newTuple = tuple([dates,new_beat,new_addr])
				diffs.write('%s,"%s","%s"\n' % (newCID, str(prevTuple), str(newTuple)))
		else:

			## try to get lat, long for new_addr
			addrFnd = new_addr in addrTbl
			if addrFnd:
				nmatchAddr += 1
				lat,long = addrTbl[new_addr]
			else:
				nmissAddr += 1
				mas.write('%s,%s\n' % (newCID,new_addr))
				lat = ''
				long = ''
			
			# NB: new_incid elements only have basic ctype,desc here
			new_incid = []
			for ctype,desc in incidList:
					
				statute = ''
				ucr = ''
				## Supplement missing statutes, UCR from highly probable
				if ctype in ct2statTbl:
					(likelyStat,freq,prob) = ct2statTbl[ctype]
					if prob >= CT2StatThresh:
						statute = likelyStat+'(~)'
						if likelyStat in stat2ucrTbl:
							(likelyUCR,freq,prob) = stat2ucrTbl[likelyStat]
							if prob >= Stat2UCRThresh:
								ucr = likelyUCR+'(~)'
								
				cc = crimeCat.classCrime(ctype, desc)
				if cc=='':
					nambigCC += 1
			
				newInfo = (ctype,desc,ucr,statute,cc)
				new_incid.append(newInfo)
			
			matchTbl[newCID] = (new_cdate,new_beat,new_addr,lat,long, new_incid )
			nincid += len(new_incid)
			nnew += 1

	mas.close()
	diffs.close()
	print "applyPatch: NData=%d NNew=%d NIncid=%d,NDup=%d NMult=%d NAmbigCC=%d NMatchAddr=%d NMissAddr=%d" % \
		 (len(newDataTbl),nnew,nincid,ndup,nmult,nambigCC,nmatchAddr,nmissAddr)

	# rptYearDist(matchTbl,'applyPatch_final')
	
	return matchTbl
