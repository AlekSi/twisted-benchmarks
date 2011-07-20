
"""
Evaluate one or more benchmarks and upload the results to a Speedcenter server.
"""

from __future__ import division

from sys import argv, stdout
from os import uname
from sys import executable
from datetime import datetime
from urllib import urlopen, urlencode

import twisted
from twisted.python.filepath import FilePath
from twisted.python.usage import UsageError

from all import allBenchmarks
from benchlib import BenchmarkOptions, Driver

# Unfortunately, benchmark name is the primary key for speedcenter
SPEEDCENTER_NAMES = {
    'tcp_connect': 'TCP Connections',
    'tcp_throughput': 'TCP Throughput',
    'ssh_connect': 'SSH Connections',
    'ssh_throughput': 'SSH Throughput',
    'ssl_connect': 'SSL Connections',
    'ssl_throughput': 'SSL Throughput',
    'sslbio_connect': 'SSL (Memory BIO) Connections',
    'sslbio_throughput': 'SSL (Memory BIO) Throughput',
    }


class SpeedcenterOptions(BenchmarkOptions):
    optParameters = [
        ('url', None, None, 'Location of Speedcenter to which to upload results.'),
        ]

    def postOptions(self):
        if not self['url']:
            raise UsageError("The Speedcenter URL must be provided.")



class SpeedcenterDriver(Driver):
    def benchmark_report(self, acceptCount, duration, name):
        print name, acceptCount, duration
        stdout.flush()
        self.results.setdefault(name, []).append((acceptCount, duration))



def reportEnvironment():
    revision = twisted.version.short().split('r', 1)[1]

    packageDirectory = FilePath(twisted.__file__).parent()

    try:
        import pysvn
    except ImportError:
        entries = packageDirectory.child('.svn').child('entries').getContent()
        lines = entries.splitlines()
        revision = lines[3]
        date = lines[9][:20].replace('T', ' ')
    else:
        client = pysvn.Client()
        [entry] = client.log(
            packageDirectory.path,
            pysvn.Revision(pysvn.opt_revision_kind.number, int(revision)),
            limit=1)
        date = str(datetime.fromtimestamp(entry['date']))

    return {
        'project': 'Twisted',
        'executable': executable,
        'environment': uname()[1],
        'commitid': revision,
        'revision_date': date,
        'result_date': str(datetime.now()),
        }



def main():
    options = SpeedcenterOptions()
    try:
        options.parseOptions(argv[1:])
    except UsageError, e:
        raise SystemExit(str(e))

    driver = SpeedcenterDriver()
    driver.results = {}
    driver.run_jobs(
        allBenchmarks,
        options['duration'], options['iterations'], options['warmup'])

    environment = reportEnvironment()

    for (name, results) in sorted(driver.results.items()):
        rates = [count / duration for (count, duration) in results]
        totalCount = sum([count for (count, duration) in results])
        totalDuration = sum([duration for (count, duration) in results])

        name = SPEEDCENTER_NAMES.get(name, name)
        stats = environment.copy()
        stats['benchmark'] = name
        stats['result_value'] = totalCount / totalDuration
        stats['min'] = min(rates)
        stats['max'] = max(rates)

        # Please excuse me.
        fObj = urlopen(options['url'], urlencode(stats))
        print name, fObj.read()
        fObj.close()


if __name__ == '__main__':
    main()
