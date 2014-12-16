#!/usr/bin/env bash
./deploy-local.sh
echo "test clean build"
cd sample
../gradlew clean build --stacktrace $1 $2
cd ..
