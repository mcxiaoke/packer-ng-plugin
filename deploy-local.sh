#!/usr/bin/env bash
echo "deploy plugin artifacts to local repo"
# rm -rf /tmp/repo/
./gradlew -PRELEASE_REPOSITORY_URL=file:///tmp/repo -PSNAPSHOT_REPOSITORY_URL=file:///tmp/repo/ clean uploadArchives --stacktrace $1
