`opdata.py` contains all methods required for basic data updates.  It references `opdUtil, opdConstant` and `crimeCat` modules.

There is a `DataDir` variable that should be changed from `/Data/sharedData/c4a_oakland/OAK_data/` to a path in the local file system where the OPData will be.

Run from the command line, it expects three arguments:

* **lastRunDate** the date of the last compiled data file.  For example, as of this writing,  the [OpenOakland data repository](http://data.openoakland.org/dataset/crime-reports) contains `OPD_161101_2.json`.  Download this file to `DataDir`.  *(NB: you'll need to remove the `_2` suffix!)*
	
* **currDate** the date to be associated with the updated data file being constructed
	
* **updateList** a list of one or more data files from the Oakland Police Department.  For example, as of this writing, OPD's FTP site (ftp://crimewatchdata.oaklandnet.com/) contains a `crimePublicData.csv` file dated 11/16/16.  To incorporate just this update, after downloading this file to the file `161116.csv` in a sub-drectory `DataDir/ftp_CrimePublicData/`, this parameter should be `"['161116']"`.  (Careful with the single and double quotes!)
	
Three ancillary files (supporting addresses and crime categories) are also necessary.  These should be downloaded, also from the [OpenOakland data repository](http://data.openoakland.org/dataset/crime-reports/resource/80455b8a-e225-4c27-8f6e-23c815c0243c), unzipped and placed in the `DataDir`.

