import aiohttp

timeout = aiohttp.ClientTimeout(total=10)
aiohttp_session = aiohttp.ClientSession(timeout=timeout)
