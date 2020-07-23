#!/bin/bash

USERNAME=mark
EMAIL_ADDRESS=markhedleyjones@gmail.com
PASSWORD=password
RESTORE=_with_transport

cd website

rm -rf tourbuilder/migrations/*
rm db.sqlite3

if [[ "${RESTORE}" != "" ]]; then
  cp 0001_initial.py${RESTORE} tourbuilder/migrations/0001_initial.py
  cp db.sqlite3${RESTORE} db.sqlite3
else
  python3 manage.py makemigrations tourbuilder
  python3 manage.py migrate
  echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('${USERNAME}', '${EMAIL_ADDRESS}', '${PASSWORD}')" | python3 manage.py shell
fi

cd -
python3 ./generate_database_fixtures.py
echo "Built the fixtures, starting to import"
python3 ./website/manage.py loaddata django_db_fixtures.json
echo "Finised importing fixtures"
