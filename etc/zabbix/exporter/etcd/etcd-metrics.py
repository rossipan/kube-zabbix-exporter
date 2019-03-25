#!/usr/bin/env python
"""
Monitoring the health of etcd with metrics api.

Examples:
$ ./etcd-metrics.py -t gauge -q etcd_server_has_leader
$ ./etcd-metrics.py -t counter -q etcd_server_leader_changes_seen_total
$ ./etcd-metrics.py -t gauge -q process_max_fds
$ ./etcd-metrics.py -t gauge -q process_open_fds
$ ./etcd-metrics.py -t counter -q etcd_server_proposals_failed_total
$ ./etcd-metrics.py -t gauge -q etcd_server_proposals_committed_total
$ ./etcd-metrics.py -t gauge -q etcd_server_proposals_applied_total
$ ./etcd-metrics.py -t gauge -q etcd_server_proposals_pending
$ ./etcd-metrics.py -t histogram -q etcd_disk_backend_commit_duration_seconds_sum
$ ./etcd-metrics.py -t histogram -q etcd_disk_backend_commit_duration_seconds_count
$ ./etcd-metrics.py -t histogram -q etcd_disk_wal_fsync_duration_seconds_sum
$ ./etcd-metrics.py -t histogram -q etcd_disk_wal_fsync_duration_seconds_count
"""
import json
import os, sys
import urllib2
import urllib2_ssl
import time
import StringIO
import argparse
import ConfigParser
from base64 import b16encode
from sys import exit, stderr

# this will let the script to import parent modules when execute directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
from prometheus_client.parser import text_string_to_metric_families

stats_cache_file_tmpl = '/tmp/zbx_etcd_stats_{url}.txt'
rootfs_path = '/rootfs'
etcd_config_file = rootfs_path + '/etc/etcd-environment'

config = StringIO.StringIO()
config.write('[dummysection]\n')
config.write(open(etcd_config_file).read())
config.seek(0, os.SEEK_SET)
cp = ConfigParser.ConfigParser()
cp.readfp(config)
node_url = cp.get('dummysection', 'ETCD_ADVERTISE_CLIENT_URLS') + '/metrics'
key_file = rootfs_path + '/etc/ssl/certs/etcd-client-key.pem'
cert_file = rootfs_path + '/etc/ssl/certs/etcd-client.pem'
ca_certs = rootfs_path + '/etc/ssl/certs/etcd-trusted-ca.pem'

def connect(timeout=60):
    '''Get the specified stats from the etcd (or from cached data).'''

    # generate path for cache file
    cache_file = stats_cache_file_tmpl.format(url=b16encode(node_url))

    # get the age of the cache file
    if os.path.exists(cache_file):
        cache_age = int(time.time() - os.path.getmtime(cache_file))
    else:
        cache_age = timeout

    # read stats from cache if it's still valid
    if cache_age < timeout:
        with open(cache_file, 'r') as c:
            raw = c.read()

    # if not get, get the fresh stats from the etcd server
    else:
        try:
            opener = urllib2.build_opener(urllib2_ssl.HTTPSHandler(
                    key_file=key_file,
                    cert_file=cert_file,
                    ca_certs=ca_certs))
            raw = opener.open('%s' % (node_url)).read()
        except (urllib2.URLError, ValueError) as e:
            if e.code == 403:
                raw = e.read()
            else:
                print >> stderr, '%s (%s)' % (e, node_url)
                return None

        try:
            # save the contents to cache_file
            cache_file_tmp = open(cache_file + '.tmp', "w")
            cache_file_tmp.write(raw)
            cache_file_tmp.flush()
            cache_file_tmp.close()
            os.rename(cache_file + '.tmp', cache_file)
        except:
            pass

    # finally return the parsed response
    try:
        response = raw
    except Exception as e:
        print >> stderr, e
        return None

    return response

def gauge(query_label_name):
    metrics = connect()

    for family in text_string_to_metric_families(metrics):
        for sample in family.samples:
            item = "{0}".format(*sample)
            if item == query_label_name:
                value = "{2}".format(*sample)
                break

    return value

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Fetch etcd server metric')
    parser.add_argument('-t',dest='query_type',action='store',help='[gauge|histogram]',required='true')
    parser.add_argument('-q',dest='query_label_name',action='store',required='true')

    args = parser.parse_args()
    query_type = args.query_type
    query_label_name = args.query_label_name

    if query_type == 'gauge' or query_type == 'histogram':
        result = gauge(query_label_name=query_label_name)
    elif query_type == 'counter':
        #Make counter metric name not have _total internally.
        #With OpenMetrics the _total is a suffix on a sample
        #for a counter, so the convention that Counters should end
        #in total is now enforced. If an existing counter is
        #missing the _total, it'll now appear on the /metrics.
        #https://github.com/prometheus/client_python/commit/a4dd93bcc6a0422e10cfa585048d1813909c6786
        if not query_label_name.endswith('_total'):
            query_label_name = query_label_name + '_total'

        result = gauge(query_label_name=query_label_name)

    if result is not None:
        print result
    else:
        print "ZBX_NOTSUPPORTED"
        exit(1)
