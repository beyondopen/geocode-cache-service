# cache-geocode-service

Flask app to geocode locations and cache the results.

Using <https://developer.here.com/documentation/geocoding-search-api/dev_guide/index.html>.

```bash
curl -u username:password https://geocode.app.vis.one/q=Berlin
```

## API

Two endpoints:

### GET
```
GET https://geocode.app.vis.one/q=Berlin
```

Return 400 if no location was found.

### POST
```
POST https://geocode.app.vis.one/
```

with data in body:

```json
{'locations': [{'location': 'Berlin'}]}
```

NB: Returns 200 even if no location wasn't found (for one item). Iterate over the responding array to verify if maching geo coords were found.

## Development

Create `keys.txt` and store a HERE API key in it.

```
docker-compose up
```

## Deployment

Deploy with Dokku.
`

## License

MIT.
