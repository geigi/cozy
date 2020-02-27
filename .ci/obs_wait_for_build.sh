#!/bin/bash

echo $(osc r)
osc r | grep -E "building|blocked|scheduled"
builds_in_progress=$?
counter=0

while [[ $builds_in_progress != [1] ]]
do
	echo "Build(s) in progress."
	sleep 5
	echo $(osc r)
	osc r | grep building
	builds_in_progress=$?
	counter=$((counter+5))
	if (( counter > 3600 )); then
		echo "Build longer than 60min, failing!"
		exit 1
	fi
done

echo $(osc r)
osc r | grep -E "broken|failed"
build_successful=$?
if (( $build_successful != 1 )); then
	echo "At least one build failed."
	exit 1
fi

echo "Builds succeeded."
exit 0
