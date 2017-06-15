#!/usr/bin/env bash
./deploy-local.sh
echo "------ build for markets running..."
./gradlew -Pchannels=@channels/channels.txt clean apkRelease $1 $2
echo "------ build for markets finished!"
