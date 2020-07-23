#!/bin/bash

USERNAME=mark
EMAIL_ADDRESS=markhedleyjones@gmail.com
PASSWORD=password
RESTORE=${RESTORE:=""}

cd website

if [[ $# -eq 2 ]]; then
  echo "Params"
  echo "${1}"
  if [[ "${1}" == "--save" ]]; then
    name=${2}
    echo "Saving migrations and database as ${name}"
    cp tourbuilder/migrations/0001_initial.py ./0001_initial_${name}.py
    cp db.sqlite3 ./db_${name}.sqlite3
  elif [[ "${1}" == "--restore" ]]; then
    name=${2}
    echo "Restoring migrations and database from ${name}"
    rm -rf tourbuilder/migrations/*
    rm db.sqlite3
    cp ./0001_initial_${name}.py tourbuilder/migrations/0001_initial.py
    cp ./db_${name}.sqlite3 db.sqlite3
  else
    echo "Unrecognised option"
  fi
elif [[ $# -eq 1 ]]; then
  if [[ "${1}" == "--clear" ]]; then
    echo "Deleting database"
    rm -rf tourbuilder/migrations/*
    rm db.sqlite3
    python3 manage.py makemigrations tourbuilder
    python3 manage.py migrate
    echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('${USERNAME}', '${EMAIL_ADDRESS}', '${PASSWORD}')" | python3 manage.py shell
  elif [[ "${1}" == "--update" ]]; then
    echo "Updating database"
    cd -
    python3 ./generate_database_fixtures.py
    echo "Built the fixtures, starting to import"
    python3 ./website/manage.py loaddata django_db_fixtures.json
    echo "Finised importing fixtures"
  else
    echo "Unrecognised option"
  fi
else
  echo "Usage: --save NAME"
  echo "Usage: --restore NAME"
  echo "Usage: --clear"
  echo "Usage: --update"
fi
