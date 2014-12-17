#!/usr/bin/env bash
echo "test clean build"
cd sample
../gradlew clean build --refresh-dependencies --stacktrace $1 $2
cd ..
