import time
import os

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import requests

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
        f"https://geocode.search.hereapi.com/v1/geocode?q={q}&apiKey={api_key}&lang=de-de&in=de"
    )
    if r.ok:
        return r.json()["items"][0]["position"].values()


@app.route("/", methods=["GET"])
def index():
    q = request.args.get("q")

    location = Location.query.filter(Location.q == q).first()

    if location is None:
        latitude, longitude = geocode(q)
        location = Location(q=q, latitude=latitude, longitude=longitude)
        db.session.add(location)
        db.session.commit()

    return jsonify({"latitude": location.latitude, "longitude": location.longitude})

