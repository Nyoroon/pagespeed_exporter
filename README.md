# pagespeed_exporter
Google PageSpeed metrics exporter for Prometheus.

## Usage
1. Install dependencies: `$ pip install -r requiremets.txt`
2. Run
   `$ python -m pagespeed_exporter`

### Example prometheus config
```yaml
  - job_name: pagespeed
    metrics_path: /scrape
    scrape_interval: 300s
    scrape_timeout: 150s
    static_configs:
      - targets:
          - https://www.google.com
          - https://www.ya.ru
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: localhost:9271
```
