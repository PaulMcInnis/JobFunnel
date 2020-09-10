#!/bin/bash
DUMP=~/Documents/jobfunnel
LOCATIONS=(*/)

for location in "${LOCATIONS[@]}"
do
if [ -d "$DUMP/$location" ] && echo "funnel scaping job for $location @ $(date +"%T")"
then
cd $DUMP/$location &&
~/.local/bin/funnel load -s settings.yaml > cronjob.log 2>&1
fi
done
