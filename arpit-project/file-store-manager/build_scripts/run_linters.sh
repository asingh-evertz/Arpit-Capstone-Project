##!/bin/bash -xe
#
#echo "Run linters and tests from script"
#export PIPENV_PYUP_API_KEY=""
#export VIRTUALENV_PIP=21.1.1
#pipenv sync --dev --pre
#pipenv run cfn-lint ${TEMPLATE_FOLDER}/* -f parseable
#pipenv run bandit -r ${PACKAGE_DIR}
#pipenv run black --check .
#pipenv run pylint ${PACKAGE_DIR}
#pipenv run isort --check-only .
#PYTHONPATH=${PYTHONPATH}:${PWD}/${PACKAGE_DIR} pipenv run pytest ${UNIT_TEST_RESULTS}
