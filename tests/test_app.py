from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from app import Location, db, geocode, geocode_here, get_location


def _here_response(items):
    mock = MagicMock()
    mock.json.return_value = {"items": items}
    mock.raise_for_status.return_value = None
    return mock


SAMPLE_ITEM = {
    "resultType": "locality",
    "position": {"lat": 52.52, "lng": 13.405},
    "address": {
        "county": "Berlin",
        "city": "Berlin",
        "district": "Mitte",
        "street": "Unter den Linden",
        "postalCode": "10117",
        "houseNumber": "1",
    },
}


# -- Model tests --


def test_location_creation(db_session):
    loc = Location(
        city="Berlin", county="Berlin", state="Berlin", country="Deutschland",
        latitude=52.52, longitude=13.405, provider="here",
    )
    db_session.add(loc)
    db_session.commit()

    assert loc.id is not None
    assert loc.city == "Berlin"


def test_location_unique_constraint(db_session):
    # Fill all constraint columns so SQLite can enforce uniqueness (NULLs are always distinct in SQLite)
    kwargs = dict(
        city="Berlin", county="Berlin", state="Berlin", country="Deutschland",
        district="Mitte", street="Str", postal_code="10117", house_number="1",
        latitude=52.52, longitude=13.405, provider="here",
    )
    db_session.add(Location(**kwargs))
    db_session.commit()

    db_session.add(Location(**kwargs))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_location_nullable_fields(db_session):
    loc = Location(
        state="Berlin", country="Deutschland",
        latitude=52.52, longitude=13.405, provider="here",
    )
    db_session.add(loc)
    db_session.commit()

    assert loc.city is None
    assert loc.county is None
    assert loc.district is None
    assert loc.street is None
    assert loc.postal_code is None
    assert loc.house_number is None


# -- geocode_here tests --


@patch("app.requests.get")
def test_geocode_here_success(mock_get, app):
    mock_get.return_value = _here_response([SAMPLE_ITEM])

    with app.app_context():
        result = geocode_here({"city": "Berlin", "state": "Berlin", "country": "Deutschland"})

    assert result is not None
    lat, lng, county, city, district, street, postal_code, house_number = result
    assert lat == 52.52
    assert lng == 13.405
    assert county == "Berlin"
    assert city == "Berlin"
    assert district == "Mitte"


@patch("app.requests.get")
def test_geocode_here_no_results(mock_get, app):
    mock_get.return_value = _here_response([])

    with app.app_context():
        result = geocode_here({"city": "Nowhere", "state": "X", "country": "X"})

    assert result is None


@patch("app.requests.get")
def test_geocode_here_filters_non_county_admin_area(mock_get, app):
    item = {
        "resultType": "administrativeArea",
        "administrativeAreaType": "state",
        "position": {"lat": 52.0, "lng": 13.0},
        "address": {"county": "X"},
    }
    mock_get.return_value = _here_response([item])

    with app.app_context():
        result = geocode_here({"city": "X", "state": "X", "country": "X"})

    assert result is None


@patch("app.requests.get")
def test_geocode_here_allows_county_admin_area(mock_get, app):
    item = {
        "resultType": "administrativeArea",
        "administrativeAreaType": "county",
        "position": {"lat": 52.0, "lng": 13.0},
        "address": {"county": "Börde"},
    }
    mock_get.return_value = _here_response([item])

    with app.app_context():
        result = geocode_here({"city": "X", "state": "X", "country": "X"})

    assert result is not None
    assert result[2] == "Börde"


@patch("app.requests.get")
def test_geocode_here_filters_invalid_result_type(mock_get, app):
    item = {
        "resultType": "intersection",
        "position": {"lat": 52.0, "lng": 13.0},
        "address": {"county": "X"},
    }
    mock_get.return_value = _here_response([item])

    with app.app_context():
        result = geocode_here({"city": "X", "state": "X", "country": "X"})

    assert result is None


@patch("app.requests.get")
def test_geocode_here_url_with_city(mock_get, app):
    mock_get.return_value = _here_response([])

    with app.app_context():
        geocode_here({"city": "Berlin", "state": "Berlin", "country": "Deutschland"})

    url = mock_get.call_args[0][0]
    assert "q=Berlin" in url
    assert "qq=" in url


@patch("app.requests.get")
def test_geocode_here_url_without_city(mock_get, app):
    mock_get.return_value = _here_response([])

    with app.app_context():
        geocode_here({"state": "Berlin", "country": "Deutschland"})

    url = mock_get.call_args[0][0]
    assert "q=" not in url or "qq=" in url


@patch("app.requests.get")
def test_geocode_here_maps_snake_case_keys(mock_get, app):
    mock_get.return_value = _here_response([])

    with app.app_context():
        geocode_here({"postal_code": "10117", "house_number": "1", "state": "Berlin", "country": "Deutschland"})

    url = mock_get.call_args[0][0]
    assert "postalCode=10117" in url
    assert "houseNumber=1" in url


def test_geocode_unknown_provider(app):
    with app.app_context():
        assert geocode({"city": "X"}, "unknown") is None


# -- get_location / cache tests --


@patch("app.geocode")
def test_get_location_cache_miss_then_hit(mock_geocode, app, db_session):
    mock_geocode.return_value = (52.52, 13.405, "Berlin", "Berlin", "Mitte", "Str", "10117", "1")
    q = {"city": "Berlin", "state": "Berlin", "country": "Deutschland"}

    loc1 = get_location(q, "here")
    loc2 = get_location(q, "here")

    assert loc1.id == loc2.id
    assert mock_geocode.call_count == 1


@patch("app.geocode")
def test_get_location_geocode_returns_none(mock_geocode, app, db_session):
    mock_geocode.return_value = None
    q = {"city": "Nowhere", "state": "X", "country": "X"}

    assert get_location(q, "here") is None
    assert db_session.execute(db.select(Location)).scalars().all() == []


@patch("app.geocode")
def test_get_location_stores_result_fields(mock_geocode, app, db_session):
    mock_geocode.return_value = (52.52, 13.405, "Berlin", "Berlin", "Mitte", "Str", "10117", "1")
    q = {"city": "Berlin", "state": "Berlin", "country": "Deutschland"}

    loc = get_location(q, "here")

    assert loc.result_county == "Berlin"
    assert loc.result_city == "Berlin"
    assert loc.result_district == "Mitte"
    assert loc.result_street == "Str"
    assert loc.result_postal_code == "10117"
    assert loc.result_house_number == "1"


@patch("app.geocode")
def test_get_location_filters_unknown_keys(mock_geocode, app, db_session):
    mock_geocode.return_value = (52.52, 13.405, "Berlin", "Berlin", None, None, None, None)
    q = {"city": "Berlin", "state": "Berlin", "country": "Deutschland", "address": "should be ignored"}

    loc = get_location(q, "here")
    assert loc is not None
    assert not hasattr(loc, "address")


# -- Endpoint tests --


@patch("app.geocode")
def test_get_missing_provider(mock_geocode, client):
    resp = client.get("/")
    assert resp.status_code == 400


@patch("app.geocode")
def test_get_success(mock_geocode, client, db_session):
    mock_geocode.return_value = (52.52, 13.405, "Berlin", "Berlin", "Mitte", "Str", "10117", "1")

    resp = client.get("/?provider=here&city=Berlin&state=Berlin&country=Deutschland")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["latitude"] == 52.52
    assert data["longitude"] == 13.405
    assert data["state"] == "Berlin"
    assert data["country"] == "Deutschland"


@patch("app.geocode")
def test_get_geocode_failure(mock_geocode, client, db_session):
    mock_geocode.return_value = None

    resp = client.get("/?provider=here&city=Nowhere&state=X&country=X")
    assert resp.status_code == 400


@patch("app.geocode")
def test_post_success(mock_geocode, client, db_session):
    mock_geocode.return_value = (52.52, 13.405, "Berlin", "Berlin", "Mitte", "Str", "10117", "1")

    resp = client.post("/", json={
        "provider": "here",
        "locations": [
            {"query": {"city": "Berlin", "state": "Berlin", "country": "Deutschland"}},
        ],
    })

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["locations"][0]["latitude"] == 52.52


@patch("app.geocode")
def test_post_empty_body(mock_geocode, client):
    resp = client.post("/", data="", content_type="application/json")
    assert resp.status_code == 400


@patch("app.geocode")
def test_post_no_locations(mock_geocode, client):
    resp = client.post("/", json={"provider": "here", "locations": []})
    assert resp.status_code == 400


@patch("app.geocode")
def test_post_partial_failure(mock_geocode, client, db_session):
    mock_geocode.side_effect = [
        (52.52, 13.405, "Berlin", "Berlin", "Mitte", "Str", "10117", "1"),
        None,
    ]

    resp = client.post("/", json={
        "provider": "here",
        "locations": [
            {"query": {"city": "Berlin", "state": "Berlin", "country": "Deutschland"}},
            {"query": {"city": "Nowhere", "state": "X", "country": "X"}},
        ],
    })

    assert resp.status_code == 200
    data = resp.get_json()
    assert "latitude" in data["locations"][0]
    assert "latitude" not in data["locations"][1]
