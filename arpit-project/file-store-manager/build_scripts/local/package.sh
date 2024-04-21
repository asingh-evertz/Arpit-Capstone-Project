#!/bin/bash
set -e

usage() { # Function: Print a help message.
  echo "Usage: $0 [ -p AWS Deployment Profile Name ]" 1>&2
}

OUTPUT_DIR="./build_scripts/local/output_dir"

OPTS=`getopt -o p: --long profile: -n 'parse-options' -- "$@"`

if [ $? != 0 ] ; then echo "Failed parsing options." >&2 ; exit 1 ; fi

eval set -- "$OPTS"

while true; do
  case "$1" in
    -p | --profile ) PROFILE="$2"; shift; shift ;;
    -- ) shift; break ;;
    * ) break ;;
  esac
done

if [ -z ${PROFILE+x} ] ; then usage ; exit 1; fi

# Find aws profile env variable
echo "evertz.io CD profile = ${AWS_EIO_CD_PROFILE}"
if [ -z "${AWS_EIO_CD_PROFILE}" ]; then
    echo "Make sure the environment variable AWS_EIO_CD_PROFILE is set correctly with a profile name for evertz.io build account" 1>&2;
    exit 1
fi

REGION=$(aws configure get region --profile $PROFILE)
export CODEARTIFACT_AUTH_TOKEN=`aws codeartifact get-authorization-token --domain evertz-io \
  --domain-owner 737710810646 --query authorizationToken --output text --region us-east-1 --profile ${AWS_EIO_CD_PROFILE}`

mkdir -p $OUTPUT_DIR
rm -rf $OUTPUT_DIR/*
cp ./buildspec.yaml $OUTPUT_DIR/buildspec.yaml

sed -i "/export CODEARTIFACT_AUTH_TOKEN=/d" $OUTPUT_DIR/buildspec.yaml

echo "AWS_DEFAULT_PROFILE=$PROFILE" > $OUTPUT_DIR/codebuild-package.env
echo "PROJECT=file-store-manager-$USER" >> $OUTPUT_DIR/codebuild-package.env
echo "CODEARTIFACT_AUTH_TOKEN=$CODEARTIFACT_AUTH_TOKEN" >> $OUTPUT_DIR/codebuild-package.env
echo "S3_BUCKET=dev-templates-$REGION" >> $OUTPUT_DIR/codebuild-package.env

./build_scripts/local/codebuild_build.sh  -a $OUTPUT_DIR/ -i aws/codebuild/standard:5.0 -e $OUTPUT_DIR/codebuild-package.env -b $OUTPUT_DIR/buildspec.yaml -c

echo "container finished"
cd $OUTPUT_DIR
unzip artifacts.zip
cd -

echo "All done"
