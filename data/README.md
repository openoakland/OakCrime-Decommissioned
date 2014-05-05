OPD DATA
Version 140505

This version captures Oakland Police Department department data for the period 2007 — April 2014.  The number of unique case IDs (NumberCID)  is 489448 and the number of incidents associated with these (NIncid) is 808355. Three formats are available:

* OPD_140505_1.csv.zip (23.1 MB, zipped) comma separated with a header line showing these fields:
    * `Idx, OPD_RD, OIdx, Date, Time, CType, Desc, Beat, Addr, Lat, Long, UCR, Statute, CrimeCat`
     
* OPD_140505_1.json(19.7 MB zipped) JSON for a dictionary
	* `cid —> [date,time,beat,addr,lat,long, [ctype,desc,ucr,statute,cc]+ ]`
    
* OPD_140505_1.db.zip (34.5 MB zipped) a SqlLite database created via
	* `CREATE TABLE INCIDENT (incididx int, rd text, date text, beat text, addr text, lat real, long real)`
	* `CREATE TABLE CHARGE (chgidx int, rd text, rdchgidx int, ctype text, desc text, ucr text, statute text, crimeCat text)`
