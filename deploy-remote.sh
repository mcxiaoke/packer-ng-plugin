#!/usr/bin/env bash
echo "build and deploy plugin artifacts to remote repo..."
./gradlew clean uploadArchives --stacktrace $1
