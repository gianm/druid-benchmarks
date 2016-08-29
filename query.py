#!/usr/bin/env python3

import aiohttp
import argparse
import asyncio
import json
import logging
import sys
import time

def load_query(query_name):
  with open('queries/{0}.json'.format(query_name), 'r') as f:
    return json.loads(f.read())

async def time_query(session, query_url, query_obj):
  start_time = time.perf_counter()
  async with session.post(query_url, data=json.dumps(query_obj), headers={'Content-Type': 'application/json'}) as response:
    if response.status != 200:
      raise Exception("Oops, got status {0}: {1}".format(response.status, await response.read()))
    response_content = await response.read()
    sys.stderr.write("Got response: {0}\n".format(response_content))
    end_time = time.perf_counter()
    return end_time - start_time

async def time_queries(session, query_url, query_obj):
  num_warmup_queries = 2
  num_queries = 3
  times = []

  # Warmup queries
  for i in range(0, num_warmup_queries):
    await time_query(session, query_url, query_obj)

  # Actual test queries
  for i in range(0, num_queries):
    times.append(await time_query(session, query_url, query_obj))

  return times

###
# main
###

parser = argparse.ArgumentParser(description='Become a service.')
parser.add_argument('--url', metavar='url', type=str, default='http://localhost:8082/druid/v2/')
parser.add_argument('--query', metavar='name', type=str, required=True)
args = parser.parse_args()

loop = asyncio.get_event_loop()
with aiohttp.ClientSession(loop=loop) as session:
  times = loop.run_until_complete(time_queries(session, args.url, load_query(args.query)))
  print(times)
  print(sum(times) / len(times))
