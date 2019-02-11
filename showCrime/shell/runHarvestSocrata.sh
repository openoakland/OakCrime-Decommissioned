# ASSUME crontab entry ala (daily @ 4:08p)

# > crontab -l
# # run once a day at 16:08
# 8 16 * * * .../showCrime/shell/runHarvestSocrata.sh

# ASSUME environment variables provided to this shell

datestr=`date +"%y-%m-%d-%H:%M"`
logFile="/home/rik/bak/showCrimeLogs/harvestSocrata/harvestSocrata_"$datestr".log"
echo "<harvestSocrata "$datestr" >"  > $logFile
cd /home/rik/webapps/django10/showCrime/

python3 manage.py harvestSocrata >> $logFile

bakFile="/home/rik/bak/djdb10/dailyIncid_oakcrime_"$datestr".json"
ionice -c2 -n6 python3 manage.py dumpdata dailyIncid.OakCrime --indent 1 > $bakFile
gzip $bakFile
datestr=`date +"%y-%m-%d-%H:%M"`
echo "</harvestSocrata "$datestr" >"  >> $logFile
# 180201: also capture access, error/INFO logs                                                               
errLogFile="/home/rik/bak/showCrimeLogs/error_access/errInfoLog_"$datestr".log"
# NB: use log.1 to ensure it's not partially created; perhaps ~ 1 day lag?                                   
# only capture INFO lines                                                                                    
grep INFO /home/rik/logs/user/error_django10.log.1 > $errLogFile
accessLogFile="/home/rik/bak/showCrimeLogs/error_access/accessLog_"$datestr".log"
cp /home/rik/logs/user/access_django10.log.1 $accessLogFile

