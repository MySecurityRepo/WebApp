#!/bin/bash

LOGFILE="/home/webserver/logs/cpu_monitor.log"
THRESHOLD=90

while true; do
    CPU=$(top -bn1 | grep "%Cpu(s)" | \
        awk -F'[, ]+' '{
            for (i=1; i<=NF; i++) {
                if ($i == "id" || $i == "id,") {
                    idle = $(i-1)
                }
            }
            if (idle == "") idle = 0
            print 100 - idle
        }')

    CPU_INT=${CPU%.*}   # drop decimal part, e.g. 89.7 -> 89

    if [ "$CPU_INT" -gt "$THRESHOLD" ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') CPU at ${CPU}%" >> "$LOGFILE"
    fi

    sleep 2
done
