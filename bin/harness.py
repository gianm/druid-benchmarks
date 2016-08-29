#!/usr/bin/env python3

import argparse
import os
import re
import subprocess
import sys
import yaml

###
# main
###

parser = argparse.ArgumentParser()
parser.add_argument('--directory', metavar='path', type=str, required=True)
parser.add_argument('--benchmark', metavar='file', type=str, required=True)
parser.add_argument('--supervise-log', metavar='file', type=str, default='supervise.log')
parser.add_argument('--out', metavar='file', type=str, default='out')
args = parser.parse_args()

benchmark = {0}
with open(args.benchmark, 'r') as f:
  benchmark = yaml.load(f)

# Load replacements (default: no replacements)
replacements = benchmark.get('replacements', [])

# Load cases (default: 1 case with no variables)
cases = benchmark.get('cases', [[]])

# Load queries (default: no queries)
queries = benchmark.get('queries', [])

if not queries:
  raise Exception("No queries in benchmark file")

if not os.path.isdir(args.directory):
  raise Exception("Not a directory: {0}".format(args.directory))

# Chdir to druid-benchmarks base
mydir = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..')
os.chdir(mydir)

with open(args.out, 'w') as fout:
  for case in cases:
    with open(args.supervise_log, 'w') as flog:
      # Copy config, perform replacements
      subprocess.check_call(['rm', '-fr', 'conf-tmp'])
      subprocess.check_call(['cp', '-R', 'conf', 'conf-tmp'])

      for replacement in replacements:
        file_path = os.path.join('conf-tmp/druid', replacement['file'])
        file_contents = None
        with open(file_path, 'r') as f:
          file_contents = f.read()
        repl = replacement['repl']
        for i, val in enumerate(case):
          repl = repl.replace('@' + str(i) + '@', str(val))
        file_contents = re.sub(replacement['pattern'], repl, file_contents)
        with open(file_path, 'w') as f:
          f.write(file_contents)

      # Symlink conf-tmp into Imply distro
      symlink_path = '{0}/conf-benchmark'.format(args.directory)
      if os.path.lexists(symlink_path):
        os.unlink(symlink_path)
      os.symlink('{0}/conf-tmp'.format(mydir), symlink_path)

      # Run Imply services
      supervise = subprocess.Popen(['{0}/bin/supervise'.format(args.directory), '-c', '{0}/conf-benchmark/supervise/benchmark.conf'.format(args.directory)], stdout=flog, stderr=subprocess.STDOUT)

      try:
        for query in queries:
          timings = subprocess.check_output(['bin/query.py', '--query', query]).decode('utf-8').strip()
          outline = ''
          if case:
            outline = '{0},'.format(','.join(map(str, case)))
          outline = '{0}{1}\n'.format(outline, timings)
          sys.stderr.write('writing: {0}'.format(outline))
          fout.write(outline)
        subprocess.check_call(['{0}/bin/service'.format(args.directory), '--down'])
      except:
        supervise.terminate()
        raise
      finally:
        exit_code = supervise.wait()
        if exit_code != 0:
          raise Exception("Nonzero exit code: {0}".format(str(exit_code)))
