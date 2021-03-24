# cache-geocode-service

Flask app to geocode locations and cache the results.

Using <https://developer.here.com/documentation/geocoding-search-api/dev_guide/index.html>.


https://developer.here.com/documentation/geocoding-search-api/api-reference-swagger.html

```bash
curl -u username:password https://geocode.app.vis.one/q=Berlin
```

## API

Two endpoints:

### GET
```
GET https://geocode.app.vis.one/?provider=here&city=Haldensleben&county=B%C3%B6rde&state=Sachsen-Anhalt&country=Deutschland
```
Return 400 if no location was found.

### POST
```
POST https://geocode.app.vis.one/
```

with data in body:

```json
{"provider": "here", "locations": [{"query": {"city":"Haldensleben", "county": "Börde", "state": "Sachsen-Anhalt", "country": "Deutschland"}}]}
```

NB: Returns 200 even if no location wasn't found (for one item). Iterate over the responding array to verify if matching geo coords were found.

## Development

Create `keys.txt` and store a HERE API key in it.

```bash
docker-compose up
```


## Deployment

Deploy with Dokku.


```bash
sudo dokku run geocode flask resetdb
```

## License

MIT.
