import asyncio

__all__ = [
    'get_running_loop',
]

if hasattr(asyncio, 'get_running_loop'):
    get_running_loop = asyncio.get_running_loop
else:
    get_running_loop = asyncio.get_event_loop
