import argparse
import http.server

from prometheus_client import REGISTRY
from prometheus_client.exposition import MetricsHandler

from .collector import PageSpeedCollector

parser = argparse.ArgumentParser(
    'pagespeed_exporter',
    description='Google PageSpeed metrics exporter for Prometheus')
parser.add_argument('-k', '--api-key', required=True)
parser.add_argument('-t', '--target', action='append', required=True)

args = parser.parse_args()

collector = PageSpeedCollector(api_key=args.api_key, targets=args.target)
REGISTRY.register(collector)

httpd = http.server.HTTPServer(('0.0.0.0', 9271), MetricsHandler)
httpd.serve_forever()
