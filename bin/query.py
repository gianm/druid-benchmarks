#!/usr/bin/env python3

import aiohttp
import argparse
import asyncio
import json
import sys
import time

def load_query(query_name):
  with open(query_name, 'r') as f:
    return json.loads(f.read())

async def do_query(session, args, query_obj):
  async with session.post(args.url, data=json.dumps(query_obj), headers={'Content-Type': 'application/json'}) as response:
    if response.status != 200 and response.status != 500:
      raise Exception("Oops, got status {0}: {1}".format(response.status, await response.read()))
    return await response.read()

async def wait_for_data(session, args):
  while True:
    try:
      result = await do_query(session, args, {
        'queryType': 'timeseries',
        'dataSource': 'tpch_lineitem_small',
        'intervals': '1000/3000',
        'aggregations': [{'type': 'count', 'name': 'count'}],
        'granularity': 'all'
      })
      result = json.loads(result.decode('utf-8'))
      if int(result[0]['result']['count']) > 0:
        return
      else:
        raise Exception("Zero count")
    except Exception as e:
      sys.stderr.write('Still waiting ({0})...\n'.format(str(e)))
      await asyncio.sleep(1)

async def time_query(session, args, query_obj):
  start_time = time.perf_counter()
  response_content = await do_query(session, args, query_obj)
  end_time = time.perf_counter()

  response_obj = json.loads(response_content.decode('utf-8'))

  if len(response_content) > 100:
    response_content = str(response_content[0:96]) + " ..."
  sys.stderr.write("Got response: {0}\n".format(response_content))

  if type(response_obj) is dict:
    # Error object
    return -1
  else:
    return end_time - start_time

async def time_queries(session, args, query_obj):
  times = []

  # Wait for data
  await wait_for_data(session, args)

  # Warmup queries
  for i in range(0, args.num_warmup_queries):
    await time_query(session, args, query_obj)

  # Actual test queries
  for i in range(0, args.num_queries):
    times.append(await time_query(session, args, query_obj))

  return times

###
# main
###

parser = argparse.ArgumentParser()
parser.add_argument('--url', metavar='url', type=str, default='http://localhost:8082/druid/v2/')
parser.add_argument('--query', metavar='name', type=str, required=True)
parser.add_argument('--num-queries', metavar='n', type=int, default=3)
parser.add_argument('--num-warmup-queries', metavar='n', type=int, default=2)
args = parser.parse_args()

loop = asyncio.get_event_loop()
with aiohttp.ClientSession(loop=loop) as session:
  times = loop.run_until_complete(time_queries(session, args, load_query(args.query)))
  print("{0},{1}".format(args.query, ','.join(map(str, times))))
