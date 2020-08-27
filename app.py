import os
import time

import requests
from flask import Flask, request
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


db.create_all()


def geocode(q):
    r = requests.get(
        f"https://geocode.search.hereapi.com/v1/geocode?q={q}&apiKey={api_key}&lang=de-de&in=countryCode:DEU&limit=1"
    )
    if r.ok:
        return r.json()["items"][0]["position"].values()


def get_location(q):
    location = Location.query.filter(Location.q == q).first()

    if location is None:
        latitude, longitude = geocode(q)
        location = Location(q=q, latitude=latitude, longitude=longitude)
        db.session.add(location)
        db.session.commit()
    return location


@app.route("/", methods=["GET"])
def index_get():
    q = request.args.get("q")
    if q is None:
        return "choose q such as /?q=Berlin"

    location = get_location(q)

    return {"latitude": location.latitude, "longitude": location.longitude}


@app.route("/", methods=["POST"])
def index_post():
    data = request.get_json()

    if data is None or "locations" not in data or len(data["locations"]) == 0:
        return "post data like this: `{'locations': [{'location': 'Berlin'}]}`"

    for x in data["locations"]:
        location = get_location(x["location"])
        x["latitude"] = location.latitude
        x["longitude"] = location.longitude

    return data
