# pagespeed_exporter

Prometheus exporter for Google PageSpeed metrics.

## Building and running

With pipenv:
```sh
pipenv install
pipenv run python -m pagespeed_exporter --api-key {API_KEY} --target {TARGET}
```

Or with pip:
```sh
pip install -r requirements.txt
python -m pagespeed_exporter --api-key {API_KEY} --target {TARGET}
```