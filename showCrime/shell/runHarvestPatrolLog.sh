# ASSUME crontab entry ala (daily @ 4:20p)

# > crontab -l
# # run once a day at 16:20
# 20 16 * * * .../showCrime/dailyIncid/management/commands/harvestPatrolLog.py

# ASSUME environment variables provided to this shell

python3 manage.py harvestPatrolLog
