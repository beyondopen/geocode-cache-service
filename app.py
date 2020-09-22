import os
import time

import requests
from flask import Flask, request, abort
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

if app.debug:
    url = "postgresql+psycopg2://postgres:password@db:5432/postgres"
    time.sleep(10)
    from pathlib import Path

    api_key = Path("keys.txt").read_text()
else:
    url = os.environ["DATABASE_URL"]
    api_key = os.environ["HERE_KEY"]


app.config["SQLALCHEMY_DATABASE_URI"] = url

db = SQLAlchemy(app)


class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    q = db.Column(db.Text(), unique=True, nullable=False)
    latitude = db.Column(db.Float(), nullable=False)
    longitude = db.Column(db.Float(), nullable=False)
    provider = db.Column(db.Text(), nullable=False)


@app.cli.command()
def resetdb():
    db.drop_all()
    print('resetdb successful!')


db.create_all()


def geocode_here(q):
    print(f'need to lookup {q}')

    q = eval(q)
    print(f'evaluated {q}')


    qq = []
    for x in q:
        if len(x) == 2:
            qq .append(x[0] + '=' + x[1])
    qq = ';'.join(qq)

    r = requests.get(
        f"https://geocode.search.hereapi.com/v1/geocode?qq={qq}&apiKey={api_key}&lang=de-de&in=countryCode:DEU&limit=1"
    )
    r.raise_for_status()
    
    items = r.json()["items"]
    if len(items) > 0:
        return items[0]["position"].values()
    return None


def geocode(q, p):
    if p == 'here':
        return geocode_here(q)
    return None


def get_location(q, p):
    location = Location.query.filter(Location.q == q).filter(Location.provider == p).first()

    if location is None:
        geocode_result = geocode(q, p)

        if geocode_result is None:
            return None

        latitude, longitude = geocode_result
        location = Location(q=q, latitude=latitude, longitude=longitude, provider=p)
        db.session.add(location)
        db.session.commit()
    return location


@app.route("/", methods=["GET"])
def index_get():
    q = request.args.get("q")
    if q is None:
        return 'choose q such as /?q=[["city", "Haldensleben"], ["county", "Börde"], ["state", "Sachsen-Anhalt"], ["country", "Deutschland"]]'

    provider = request.args.get("p")
    if provider is None:
        return "choose provider such as /?p=here"
    provider = provider.lower()

    location = get_location(q, provider)
    if location is None:
        abort(400, f"geolocation failed for `{q}` and `{provider}`")
    return {"latitude": location.latitude, "longitude": location.longitude}


@app.route("/", methods=["POST"])
def index_post():
    data = request.get_json()

    if data is None or "qs" not in data or len(data["qs"]) == 0:
        return 'post data like this: `{"p": "here", "qs": [{"q": [["city", "Haldensleben"], ["county", "Börde"], ["state", "Sachsen-Anhalt"], ["country", "Deutschland"]]}]}`'
    
    provider = data["p"].lower()

    for x in data["qs"]:
        location = get_location(x["q"], provider)
        if location is not None:
            x["latitude"] = location.latitude
            x["longitude"] = location.longitude

    return data
