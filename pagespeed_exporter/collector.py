import asyncio

import aiohttp
from aioprometheus import Registry
from multidict import MultiDict

from .utils import camel_to_snake, get_or_create_gauge

from enum import IntEnum


class PageSpeedCollector:
    PREFIX = "pagespeed"
    STRATEGIES = ("desktop", "mobile")
    CATEGORIES = ("accessibility", "best-practices", "performance", "pwa", "seo")

    API_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

    def __init__(self, apikey=None, aiohttp_client=None):
        self._apikey = apikey
        self._aiohttp_client = aiohttp_client or aiohttp.ClientSession()

    async def collect(self, target):
        self.registry = Registry()

        await asyncio.gather(
            *[self._collect_strategy(target, strategy) for strategy in self.STRATEGIES]
        )

        return self.registry

    async def _collect_strategy(self, target, strategy):
        query_params = MultiDict()
        for category in self.CATEGORIES:
            query_params.add("category", category)
        query_params.add("url", target)
        query_params.add("strategy", strategy)
        if self._apikey:
            query_params.add("key", self._apikey)

        async with self._aiohttp_client.get(self.API_URL, params=query_params) as r:
            data = await r.json()

        labels = dict(strategy=strategy)

        self._handle_lighthouse(data["lighthouseResult"], labels)

        for lexp_type in ("loadingExperience", "originLoadingExperience"):
            if lexp_type in data and "metrics" in data[lexp_type]:
                self._handle_loading_experience(
                    data[lexp_type], labels, origin=lexp_type.startswith("origin")
                )

    def _fqname(self, *kwargs):
        return "_".join((self.PREFIX,) + kwargs)

    def _handle_lighthouse(self, data, labels):
        lh_audits = data["audits"]
        lh_metrics = lh_audits["metrics"]["details"]["items"][0].items()
        for metric, value in lh_metrics:
            if not metric.startswith("observed"):
                metric_name = camel_to_snake(metric)

                metric_fqname = self._fqname(
                    "lighthouse", metric_name, "duration", "seconds"
                )
                gauge = get_or_create_gauge(
                    self.registry,
                    metric_fqname,
                    lh_audits[metric_name.replace("_", "-")]["description"],
                )
                gauge.add(labels, value / 1000)

        lh_categories = data["categories"].items()
        for category, value in lh_categories:
            metric_fqname = self._fqname(
                "lighthouse", category.replace("-", "_"), "score"
            )

            gauge = get_or_create_gauge(
                self.registry, metric_fqname, "Lighthouse score for {}".format(category)
            )
            gauge.add(labels, value["score"])

    def _handle_loading_experience(self, data, labels, origin=False):
        metric_prefix = "{}loading_experience".format("origin_" if origin else "")

        for metric, value in data["metrics"].items():
            metric_name = metric.lower()
            if metric_name.endswith("_ms"):
                metric_name = metric_name[:-3]

            metric_fqname = self._fqname(
                metric_prefix, metric_name, "duration", "seconds"
            )

            if metric_name == "first_contentful_paint":
                metric_fqname += "_90p"
            elif metric_name == "first_input_delay":
                metric_fqname += "_95p"

            metric_labels = labels.copy()
            metric_labels.update(dict(category=value["category"]))

            gauge = get_or_create_gauge(
                self.registry,
                metric_fqname,
                "Loading experience percentile metric for {}".format(metric_name),
            )
            gauge.add(labels, value["percentile"] / 1000)

        if "overall_category" in data:
            metric_name = self._fqname(metric_prefix, "overall_category")

            metric_labels = labels.copy()
            metric_labels.update(dict(category=data["overall_category"]))

            gauge = get_or_create_gauge(
                self.registry,
                metric_name,
                "Loading experience overall category",
            )
            gauge.add(metric_labels, 1)
