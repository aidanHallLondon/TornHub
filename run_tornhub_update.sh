#!/bin/bash

# Get the current date and time and store it in a variable
timestamp=$(date +"%Y-%m-%d %H:%M:%S") 
echo "$timestamp - Running new.py" >> ~/Documents/code/TornHub/reports/logs/cron.log 2>&1

cd ~/Documents/code/TornHub
source ~/Documents/code/TornHub/.venv/bin/activate
~/Documents/code/TornHub/.venv/bin/python daily_update.py >> ~/Documents/code/TornHub/reports/logs/cron.log 2>&1
echo >> ~/Documents/code/TornHub/reports/logs/cron.log 2>&1
exit