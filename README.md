# README #

Shab Publications Scraper installation
Python 3.6+
### Install dependences

```
pip install -r requirements.txt
```

### run database

run on command line in the project folder:

```
docker-compose up -d
```

you need to create database. Run on command line:
```
docker-compose exec postgresql bash
```
next step:
```
su - postgres
```
next step:
```
psql
```
next step (you can create your own user, change password and other data):
```
CREATE DATABASE parsing; 
CREATE USER parsing_admin WITH PASSWORD 'parsing_adminparsing_admin';
ALTER ROLE parsing_admin SET client_encoding TO 'utf8';
ALTER ROLE parsing_admin SET default_transaction_isolation TO 'read committed';
ALTER ROLE parsing_admin SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE parsing TO parsing_admin;
ALTER USER parsing_admin CREATEDB;

```

to create tables run file:
```
create_db.py
```

### Run Command ###

```
python run.py --output-path=results/
```
