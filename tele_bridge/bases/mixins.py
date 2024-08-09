import asyncio
import inspect
import queue
from typing import Any, Awaitable, TypeAlias, Union, Callable, Coroutine

ClientValue: TypeAlias = Union[str, asyncio.Queue, queue.Queue]
Autofill: TypeAlias = Union[
    ClientValue,
    Callable[[], ClientValue],
    Callable[[], Awaitable[ClientValue]],
    Coroutine[Any, Any, ClientValue],
]


class SetAttribute:

    _set_attr_timeout: int
    _attribute_cache: dict[str, Any]

    async def set_unfilled_attribute(self, attr_name: str) -> ClientValue | None:
        async with asyncio.timeout(self._set_attr_timeout):
            return await self._set_unfilled_attribute(attr_name)

    async def _set_unfilled_attribute(self, attr_name: str) -> ClientValue | None:
        attr = getattr(self, attr_name, None)
        if attr is None:
            return None
        # logger.info(f"attr: {attr}")
        if cache_attr := self._attribute_cache.get(attr_name):
            if isinstance(cache_attr, (str, int)):
                return None
            attr = cache_attr

        while (inspect.isfunction(attr)
               or inspect.iscoroutinefunction(attr)
               or inspect.isawaitable(attr)):
            self._attribute_cache.setdefault(attr_name, attr)
            if inspect.iscoroutinefunction(attr):
                attr = await attr()
            elif inspect.isawaitable(attr):
                attr = await attr
            elif inspect.isfunction(attr):
                attr = await asyncio.to_thread(attr)

        if isinstance(attr, (str, int)):
            attr = attr

        elif isinstance(attr, asyncio.Queue):
            val = await attr.get()
            attr.task_done()
            attr = val
        elif isinstance(attr, queue.Queue):
            val = await asyncio.to_thread(attr.get)
            attr.task_done()
            attr = val
        return attr
