Python asyncio iterator tools
=============================

The library provides a bunch of functions for working with async iterators.

.. image:: https://travis-ci.com/popravich/asyncio_iter_tools.svg?branch=master
    :target: https://travis-ci.com/popravich/asyncio_iter_tools


The following tools are implemented:

Mix several streams into one
----------------------------

.. code-block:: python

   import asyncio
   import asyncio_iter_tools as aiter

   async def simple_stream(seq, delay=0):
       for obj im seq:
           yield await asyncio.sleep(delay, obj)

   async def main():
       streamA = simple_stream('abc', 0.05)
       streamB = simple_stream('def', 0.07)

       res = [
           obj async for obj in aiter.mix(streamA, streamB)]

       assert res == ['a', 'd', 'b', 'e', 'c', 'f']
   asyncio.run(main())


Split stream into two
---------------------
   
.. code-block:: python

   import asyncio
   import asyncio_iter_tools as aiter

   async def main():
       # simple_stream func from above
       stream = simple_stream('abc')

       streamA, streamB = aiter.split(stream, buffer_size=3)

       resA = [obj async for obj in streamA]
       resB = [obj async for obj in streamA]

       assert resA == ['a', 'b', 'c']
       assert resB == ['a', 'b', 'c']
   asyncio.run(main())

Chain several streams into one
------------------------------

.. code-block:: python

   import asyncio
   import asyncio_iter_tools as aiter

   async def main():
       # simple_stream func from above
       streamA = simple_stream('abc')
       streamB = simple_stream(range(3))

       res = [
           obj async for obj in aiter.chain(streamA, streamB)]

       assert res == ['a', 'b', 'c', 0, 1, 2]
   asyncio.run(main())


Filter stream with function or coroutine
----------------------------------------

.. code-block:: python

   import asyncio
   import asyncio_iter_tools as aiter

   async def main():
       # simple_stream func from above
       stream = simple_stream('ab0cde23')

       res = [
           obj async for obj in aiter.filter(str.isnumeric, stream)]

       assert res == ['0', '2', '3']
   asyncio.run(main())


Map stream with function or coroutine
-------------------------------------

.. code-block:: python

   import asyncio
   import asyncio_iter_tools as aiter

   async def main():
       # simple_stream func from above
       stream = simple_stream('123')

       res = [
           obj async for obj in aiter.map(int, stream)]

       assert res == [1, 2, 3]
   asyncio.run(main())
