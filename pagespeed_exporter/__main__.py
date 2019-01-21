import asyncio

import aiohttp
from aiohttp import web
from aiohttp.hdrs import ACCEPT
from aioprometheus import render

from .collector import PageSpeedCollector


async def handle_scrape(request):
    if not "target" in request.query:
        return web.HTTPBadRequest()

    collector = PageSpeedCollector(aiohttp_client=request.app.aiohttp_client)
    registry = await collector.collect(request.query.get("target"))
    content, http_headers = render(registry, request.headers.getall(ACCEPT, []))
    return web.Response(body=content, headers=http_headers)


async def dispose_aiohttp_client(app):
    await app.aiohttp_client.close()


async def make_app():
    app = web.Application()

    app.aiohttp_client = aiohttp.ClientSession()

    app.add_routes([web.get("/scrape", handle_scrape)])

    app.on_cleanup.append(dispose_aiohttp_client)

    return app


if __name__ == "__main__":
    web.run_app(make_app(), port=9271)
