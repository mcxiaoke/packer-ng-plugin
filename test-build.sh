#!/usr/bin/env bash
./deploy-local.sh
echo "test clean build"
./gradlew clean build --stacktrace $1 $2
