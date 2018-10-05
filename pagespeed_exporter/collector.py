from apiclient.discovery import build as api_client_build
from prometheus_client.core import GaugeMetricFamily
from cachetools import TTLCache, cachedmethod
from functools import partial
from .utils import camel_to_snake
import operator


class PageSpeedCollector(object):
    def __init__(self, api_key: str, targets: list, cache_ttl: int = 100):
        self._api_client = api_client_build(
            'pagespeedonline', 'v4', developerKey=api_key)
        self._pagespeed_api = self._api_client.pagespeedapi()
        self._cache = TTLCache(maxsize=50, ttl=cache_ttl)
        self.strategies = ('desktop', 'mobile')
        self.targets = targets

    PAGESTATS_HELP = dict(
        numberResources='Number of HTTP resources loaded by the page.',
        numberHosts='Number of unique hosts referenced by the page.',
        totalRequestBytes='Total size of all request bytes sent by the page.',
        numberStaticResources='Number of static (i.e. cacheable) resources'
                              ' on the page.',
        htmlResponseBytes='Number of uncompressed response bytes for the main'
                          ' HTML document and all iframes on the page.',
        textResponseBytes='Number of uncompressed response bytes for'
                          ' text resources not covered by other statistics'
                          ' (i.e non-HTML, non-script, non-CSS resources)'
                          ' on the page.',
        overTheWireResponseBytes='Number of over-the-wire bytes, uses the'
                                 ' default gzip compression strategy as'
                                 ' an estimation.',
        cssResponseBytes='Number of uncompressed response bytes for CSS'
                         ' resources on the page.',
        imageResponseBytes='Number of response bytes for image resources'
                           ' on the page.',
        javascriptResponseBytes='Number of uncompressed response bytes for'
                                ' JS resources on the page.',
        flashResponseBytes='Number of response bytes for flash resources'
                           ' on the page.',
        otherResponseBytes='Number of response bytes for other resources'
                           ' on the page.',
        numberJsResources='Number of JavaScript resources referenced'
                          ' by the page.',
        numberCssResources='Number of CSS resources referenced by the page.',
        numberRobotedResources='Number of roboted resources.',
        numberTransientFetchFailureResources='Number of transient-failed'
                                             ' resources.',
        numTotalRoundTrips='The needed round trips to load the full page.',
        numRenderBlockingRoundTrips='The needed round trips to load render'
                                    ' blocking resources.')

    LOADEXP_HELP = dict(
        first_contentful_paint='Time when the browser renders the first bit'
                               ' of content from the DOM.',
        dom_content_loaded_event_fired='Time when DOMContentLoaded event is'
                                       ' fired.')

    def _create_metrics(self):
        score_metrics = dict(
            score=GaugeMetricFamily(
                f'pagespeed_score',
                'The score (0-100), which indicates how much better a page'
                ' could be in that category.',
                labels=('target', 'strategy', 'category')))

        pagespeed_metrics = dict()
        for metric, desc in self.PAGESTATS_HELP.items():
            pagespeed_metrics[metric] = GaugeMetricFamily(
                f'pagespeed_pagestats_{camel_to_snake(metric)}',
                desc,
                labels=('target', 'strategy'))

        loadexp_metrics = dict()
        for metric, desc in self.LOADEXP_HELP.items():
            loadexp_metrics[metric] = GaugeMetricFamily(
                f'pagespeed_loadingexpeience_{metric}_seconds',
                desc,
                labels=('target', 'strategy', 'category'))

        return {**score_metrics, **pagespeed_metrics, **loadexp_metrics}

    @cachedmethod(operator.attrgetter('_cache'))
    def collect(self):
        def _handle_pagespeed(strategy, request_id, response, exception):
            if exception:
                return None

            target = response['id']

            for category, group in response['ruleGroups'].items():
                metrics['score'].add_metric((target, strategy, category),
                                            group['score'])

            for metric, value in response['pageStats'].items():
                if metric not in metrics:
                    continue

                metrics[metric].add_metric((target, strategy), int(value))

            loadexp = response['loadingExperience']
            if 'metrics' in loadexp:
                for metric, values in loadexp['metrics'].items():
                    metric = metric.lower()
                    value = values['median']
                    if metric.endswith('_ms'):
                        metric = metric[:-3]
                        value = value / 1000
                    metrics[metric].add_metric(
                        (target, strategy, values['category']), value)

        metrics = self._create_metrics()
        batch = self._api_client.new_batch_http_request()

        for strategy in self.strategies:
            _handle_pagespeed_strategy = partial(_handle_pagespeed, strategy)
            for target in self.targets:
                pagespeed_req = self._pagespeed_api.runpagespeed(url=target)
                batch.add(pagespeed_req, callback=_handle_pagespeed_strategy)

        batch.execute()
        return metrics.values()

    def describe(self):
        return self._create_metrics().values()
