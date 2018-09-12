#!/usr/bin/bash

if [ -d ./socapp/migrations/ ]; then
    rm -r ./socapp/migrations/
fi

if [ -d ./socapp_auth/migrations/ ]; then
    rm -r ./socapp_auth/migrations/
fi

if [ -f ./db.sqlite3 ]; then
    rm ./db.sqlite3
fi

python manage.py makemigrations
python manage.py makemigrations socapp socapp_auth
python manage.py migrate
python manage.py loaddata tournaments teams_champ_lg games_champ_lg