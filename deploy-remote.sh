#!/usr/bin/env bash
echo "build and deploy plugin artifacts to remote repo..."
./gradlew :plugin:clean :plugin:build :plugin:uploadArchives --stacktrace $1
