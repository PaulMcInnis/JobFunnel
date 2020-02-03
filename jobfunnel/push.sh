#!/bin/bash
rm -rf build.zip
cd ../
if [ $? -eq 0 ]; then
 regions=( "us-east-1" "us-east-2" "us-west-1" "us-west-2" "ap-south-1"
      "ap-northeast-2" "ap-southeast-1" "ap-southeast-2" "ap-northeast-1"
      "ca-central-1" "eu-central-1" "eu-west-1" "eu-west-2" "eu-west-3" "sa-east-1" )
    for i in "${regions[@]}"
    do
        aws lambda update-function-code --region $i --function-name "$1" --zip-file fileb://build.zip
        if [ $? -eq 1 ]; then
            return 1
        fi
    done
fi