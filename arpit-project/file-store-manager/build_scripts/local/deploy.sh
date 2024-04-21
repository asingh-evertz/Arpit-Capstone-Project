#!/bin/bash -x
set -e
OUTPUT_DIR="./build_scripts/local/output_dir"
OPTS=$(getopt -o p: --long profile: -n 'parse-options' -- "$@")

if [ $? != 0 ]; then
  echo "Failed parsing options." >&2
  exit 1
fi

echo "$OPTS"
eval set -- "$OPTS"
#set deletion_policy as Delete for dev env
DELETION_POLICY="Delete"
PROFILE=''
USER='amane'

while true; do
  case "$1" in
    -p | --profile ) PROFILE="$2"; shift; shift ;;
    -- ) shift; break ;;
    * ) break ;;
  esac
done

echo "Start deploying stack"
aws --profile $PROFILE cloudformation deploy --template-file $OUTPUT_DIR/template-export.yaml \
    --capabilities CAPABILITY_AUTO_EXPAND CAPABILITY_NAMED_IAM --stack-name capstone-project-$USER --parameter-overrides \
    DeletionPolicyParam="$DELETION_POLICY" Project=capstone-project-$USER Owner=$USER@evertz.com Name=capstone-project-$USER BasePath=capstone-project-$USER
echo "All done"