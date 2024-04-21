#!/bin/bash
set -e

usage() { echo "Usage: $0 COMMAND" 1>&2; exit 1; }

# Find aws profile env variable
echo "evertz.io CD profile = ${AWS_EIO_CD_PROFILE}"
if [ -z "${AWS_EIO_CD_PROFILE}" ]; then
    echo "Make sure the environment variable AWS_EIO_CD_PROFILE is set correctly with a profile name for evertz.io build account" 1>&2; exit 1
fi

# Parse COMMAND
pipenv_cmd=$1
shift
pipenv_args=$@

echo "command = ${pipenv_cmd}"
if [ "${pipenv_args}" ]; then
    echo "args = ${pipenv_args}"
fi

# Are we in a virtual env?
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Run 'pipenv shell' before ${pipenv_cmd}ing" 1>&2; exit 1
fi

# Get CodeArtifact token
export CODEARTIFACT_AUTH_TOKEN=`aws codeartifact get-authorization-token --domain evertz-io --domain-owner 737710810646 \
                        --query authorizationToken --output text --region us-east-1 --profile $AWS_EIO_CD_PROFILE`
echo "CodeArtifact token = `echo $CODEARTIFACT_AUTH_TOKEN | sed -r 's/^(.{8}).*(.{8})$/\1****************\2/'`"

# Call pipenv
echo "Running pipenv $pipenv_cmd $@"
pipenv $pipenv_cmd $@
