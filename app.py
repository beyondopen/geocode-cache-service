import os
import time

import requests
from flask import Flask, abort, request
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
    __table_args__ = (
        db.UniqueConstraint(
            "city", "county", "state", "country", name="location_index"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    country = db.Column(db.Text(), nullable=False)
    state = db.Column(db.Text(), nullable=False)
    county = db.Column(db.Text())
    city = db.Column(db.Text())
    latitude = db.Column(db.Float(), nullable=False)
    longitude = db.Column(db.Float(), nullable=False)
    provider = db.Column(db.Text(), nullable=False)
    result_district = db.Column(db.Text())
    result_city = db.Column(db.Text())
    result_county = db.Column(db.Text())


@app.cli.command()
def resetdb():
    db.drop_all()
    print("resetdb successful!")
    db.create_all()


db.create_all()


def geocode_here(q):
    qq = ";".join([f"{k}={v}" for k, v in q.items() if v != None and k != "city"])
    q_city = q["city"]

    url = f"https://geocode.search.hereapi.com/v1/geocode?q={q_city}&qq={qq}&apiKey={api_key}&lang=de-de&in=countryCode:DEU&limit=1"
    print(url)

    r = requests.get(url)
    r.raise_for_status()

    items = r.json()["items"]
    if len(items) == 0:
        return None
    item = items[0]
    if item["resultType"] != "locality":
        return None

    if item["localityType"] == "district":
        return (
            *item["position"].values(),
            item["address"]["county"],
            item["address"]["city"],
            item["address"]["district"],
        )
    else:
        return (
            *item["position"].values(),
            item["address"]["county"],
            item["address"]["city"],
            None,
        )


def geocode(q, p):
    if p == "here":
        return geocode_here(q)
    return None


def get_location(q, p):
    location = (
        Location.query.filter(Location.city == q["city"])
        .filter(Location.county == q["county"])
        .filter(Location.state == q["state"])
        .filter(Location.country == q["country"])
        .filter(Location.provider == p)
        .first()
    )

    if location is None:
        geocode_result = geocode(q, p)

        if geocode_result is None:
            return None

        latitude, longitude, r_county, r_city, r_district = geocode_result
        location = Location(
            **q,
            latitude=latitude,
            longitude=longitude,
            result_county=r_county,
            result_city=r_city,
            result_district=r_district,
            provider=p,
        )
        db.session.add(location)
        db.session.commit()
    return location


@app.route("/", methods=["GET"])
def index_get():
    city = request.args.get("city")
    county = request.args.get("county")
    state = request.args.get("state")
    country = request.args.get("country")
    provider = request.args.get("provider")
    # city & county are optional
    if None in [state, country, provider]:
        abort(
            400,
            "please construct your requests as follows /?provider=here&city=Haldensleben&county=Börde&state=Sachsen-Anhalt&country=Deutschland",
        )

    query = {"state": state, "country": country, "city": city, "county": county}

    provider = provider.lower()

    location = get_location(query, provider)
    if location is None:
        abort(400, f"geolocation failed for `{query}` and `{provider}`")

    return {
        "latitude": location.latitude,
        "longitude": location.longitude,
        "county": location.result_county,
        "city": location.result_city,
        "district": location.result_district,
    }


@app.route("/", methods=["POST"])
def index_post():
    data = request.get_json()

    if data is None or "locations" not in data or len(data["locations"]) == 0:
        abort(
            400,
            'post data like this: `{"provider": "here", "locations": [{"query": {"city":"Haldensleben", "county": "Börde", "state": "Sachsen-Anhalt", "country": "Deutschland"}}]}`',
        )

    provider = data["provider"].lower()

    for x in data["locations"]:
        location = get_location(x["query"], provider)
        if location is not None:
            x["latitude"] = location.latitude
            x["longitude"] = location.longitude
            x["county"] = location.result_county
            x["city"] = location.result_city
            x["district"] = location.result_district
    return data
