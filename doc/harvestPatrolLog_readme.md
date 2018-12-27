% HarvestPatrolLog


A utility capturing daily patrol logs provided by OPD and integrating
them with other data maintained as part of OakCrime.org.

That probably doesn't *seem* like a complicated thing to do, but in
fact this django command encapsulates a multi-stage process:

1. Preliminaries: authenticate connection with Box server, get date of
   last database update including patrol logs
   
1. `getBoxIDs(), updateBoxIDTbl()` Check current files @ Box.  Box
   makes use of their own folder/file IDs, and these are required for
   downloading.  Maintain the current mapping in  `MEDIA_ROOT/PLHarvest/boxIDTbl.json`

1. `compBox2Dir()`: Compare current Box inventory to cache contents.
   OPD PatrolLog files from Box are *cached locally* under
   `MEDIA_ROOT/PLHarvest/`.  

1. `getMiss()`: harvest any new PDF files

1. `modifiedSince()`: identify (just-harvested) PDF files not included
   since last database update, to be parsed
   
1. `parsePatrolLog.collectDailyLogs(), parsePatrolLog.mergeDailyLogs()
   parsePatrolLog.regularizeIncidTbl() parsePatrolLog.addGeoCode2()`:
   parse individual days' PDF files, merge them together, regularized the
   entry fields, and geotag their addresses.

1. `postPatrolLog.findSimIncid()`: compare the patrol log entries to
   existing incidents from daily log data, merging incidents sharing
   the same OPD_RD key.  Attempt to also match others that "nearly"
   match (i.e., near the same time and address).  Post any unmatched
   patrol logs as independent incidents.
   
(draft documentation, 26 Dec 18)
