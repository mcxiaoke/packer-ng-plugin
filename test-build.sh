#!/usr/bin/env bash
./deploy-local.sh
echo "test clean build"
./gradlew clean assemblePaidRelease --stacktrace $1 $2
