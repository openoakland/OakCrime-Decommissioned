This version of the OPD crime data set should be the last ad hoc publication; from now on I intend to publish a new one approximately every month.  This version captures Oakland Police Department department data for the period 2007 – Mar’14.  The number of unique case IDs (NumberCID)  is 486663 and the number of indicents associated with these (NIncid) is 805187. Three formats are available:

* OPD_140403.csv.zip (23.2 MB, zipped) comma separated with a header line showing these fields:
    * `Idx, OPD_RD, OIdx, Date, Time, CType, Desc, Beat, Addr, Lat, Long, UCR, Statute, CrimeCat`
     
* OPD_140403_5.json(19.8 MB zipped) JSON for a dictionary
	* `cid – > [date,time,beat,addr,lat,long, [ctype,desc,ucr,statute,cc]+ ]`
    
* OPD_140403.db.zip (34.1 MB zipped) a SqlLite database created via
	* `CREATE TABLE INCIDENT (incididx int, rd text, date text, beat text, addr text, lat real, long real)`
	* `CREATE TABLE CHARGE (chgidx int, rd text, rdchgidx int, ctype text, desc text, ucr text, statute text, crimeCat text)`
