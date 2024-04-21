## Development environment setup

### Install Python 3.9 (This step is required if you are using ubuntu 20.04 or below)
1. Install pyenv dependencies  
    `sudo apt-get install make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev python-openssl git`
2. Install pyenv  
    `curl https://pyenv.run | bash`  
   Add pyenv to the bashrc and export env variable in this session
   1. Add pyenv to the bashrc and export env variable in this session
       1. To add this in bashrc
        ``` 
          PYENV_ROOT="$HOME/.pyenv"
          PATH="$PYENV_ROOT/bin:$HOME/.local/bin:$PATH"
          
          if command -v pyenv 1>/dev/null 2>&1; then
             eval "$(pyenv init -)"
          fi
       ```
      2. To reload bashrc
        `source ~/.bashrc`
3. Install python 3.9.12
    `pyenv install 3.9.12`


### Get codebuild docker image

```shell
git clone https://github.com/aws/aws-codebuild-docker-images.git
cd aws-codebuild-docker-images/ubuntu/standard/5.0
docker build -t aws/codebuild/standard:5.0 .
```

### Get credentials for your evertzio test user in the evertz-test tenant
If you are making an API you will need to authenticate first. You may want to ask your team lead to generate an evertz.io user for you.
### Login to your evertz.io dev account in the evertz-tv/ evertz-test tenant
1. First make sure you are logged into dev account using SSO.
2. If you are making an API you will need to authenticate first. You may want to ask your team lead to generate an evertz.io user for you.


### How to test 
The package stage runs tests in a fresh reproducible codebuild environment, but it takes time. You may want to run any of the following commands from the root of the project.

```shell
pipenv run safety check --full-report
pipenv run cfn-lint templates/*.yaml -f parseable
pipenv run bandit -r file_store_manager
pipenv run isort --check-only .
pipenv run black --check .
pipenv run pylint file_store_manager
PYTHONPATH=${PYTHONPATH}:${PWD}/file_store_manager pipenv run pytest
```

### How to build and package 
```shell
./build_scripts/local/package.sh -p eio-dev
```

### How to deploy your isolated development stack
For development every evertz.io developer launches their on isolated stack which can be done using
```shell
./build_scripts/local/deploy.sh -p eio-dev
```

### How to cleanup your isolated development stack
To delete the sample application that you created, use the AWS CLI. Assuming you used your project name for the stack name, you can run the following:
```shell
aws cloudformation delete-stack --stack-name file-store-manager-${USER}
```


## TODO
Get code deploy credentials so Jenkins can push code to AWS
```
def repository_credentials = "eio-file-store-manager-project-private-key"
def us_east_1 = "ssh://APKA2XQX5UYLLBVOV2OG@git-codecommit.us-east-1.amazonaws.com/v1/repos/file-store-manager-repository"
```
