#!/usr/bin/env bash
echo "deploy plugin artifacts to local repo"
rm -rf /tmp/repo/
./gradlew -PbuildNum=2013 -PRELEASE_REPOSITORY_URL=file:///tmp/repo -PSNAPSHOT_REPOSITORY_URL=file:///tmp/repo/ :plugin:clean :plugin:build :plugin:uploadArchives --stacktrace $1
