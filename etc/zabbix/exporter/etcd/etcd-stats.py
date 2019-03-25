#!/usr/bin/env python
"""
Zabbix Monitoring template for etcd node stats.

Examples:
$ ./etcd-stats.py -m v2/stats/leader:followers/node.domain.tld/counts/fail
$ ./etcd-stats.py -m v2/stats/self:recvAppendRequestCnt
$ ./etcd-stats.py -m v2/stats/store:watchers
$ ./etcd-stats.py -m v2/members

"""
import json
import os
import urllib2
import urllib2_ssl
import time
import StringIO
import argparse
import ConfigParser
from base64 import b16encode
from sys import exit, stderr

stats_cache_file_tmpl = '/tmp/zbx_etcd_stats_{type}_{url}.txt'
rootfs_path = '/rootfs'
etcd_config_file = rootfs_path + '/etc/etcd-environment'

config = StringIO.StringIO()
config.write('[dummysection]\n')
config.write(open(etcd_config_file).read())
config.seek(0, os.SEEK_SET)
cp = ConfigParser.ConfigParser()
cp.readfp(config)
node_url = cp.get('dummysection', 'ETCD_ADVERTISE_CLIENT_URLS')
key_file = rootfs_path + '/etc/ssl/certs/etcd-client-key.pem'
cert_file = rootfs_path + '/etc/ssl/certs/etcd-client.pem'
ca_certs = rootfs_path + '/etc/ssl/certs/etcd-trusted-ca.pem'

def get_stats(stats, timeout=60):
    '''Get the specified stats from the etcd (or from cached data) and return JSON.'''

    # generate path for cache file
    cache_file = stats_cache_file_tmpl.format(type=stats, url=b16encode(node_url))

    # get the age of the cache file
    if os.path.exists(cache_file):
        cache_age = int(time.time() - os.path.getmtime(cache_file))
    else:
        cache_age = timeout

    # read stats from cache if it's still valid
    if cache_age < timeout:
        with open(cache_file, 'r') as c:
            raw_json = c.read()

    # if not get, get the fresh stats from the etcd server
    else:
        try:
            opener = urllib2.build_opener(urllib2_ssl.HTTPSHandler(
                    key_file=key_file,
                    cert_file=cert_file,
                    ca_certs=ca_certs))
            raw_json = opener.open('%s/%s' % (node_url, stats)).read()
        except (urllib2.URLError, ValueError) as e:
            if e.code == 403:
                raw_json = e.read()
            else:
                print >> stderr, '%s (%s)' % (e, node_url)
                return None

        try:
            # save the contents to cache_file
            cache_file_tmp = open(cache_file + '.tmp', "w")
            cache_file_tmp.write(raw_json)
            cache_file_tmp.flush()
            cache_file_tmp.close()
            os.rename(cache_file + '.tmp', cache_file)
        except:
            pass

    # finally return the parsed response
    try:
        response = json.loads(raw_json)
    except Exception as e:  # improve this...
        print >> stderr, e
        return None

    return response

def members(metric):
    data= []
    member_list = get_stats(metric)
    for member in member_list['members']:
        name = member['name']
        nember_id = member['id']
        data += [{'{#NAME}':name, '{#ID}':nember_id}]

    return json.dumps({'data':data},indent=4)

def get_metric(metric):
    '''Get the specified metric from the stats dict and return it's value.'''

    parsed_metric = metric.split(':')

    if len(parsed_metric) != 2:
        print >> stderr, "Wrong metric syntax (%s)" % metric
        return None

    mtype  = parsed_metric[0].lower()
    mlookup = parsed_metric[1].split('/')

    # get fresh stats
    stats = get_stats(mtype)
    if type(stats) is not dict:
        print >> stderr, "Response is not dict: (%s)" % stats
        return None

    # leaders can't have counts/latency metrics,
    # return 0 if stats for leader were requested
    if mtype == 'v2/stats/leader':
        h = mlookup[1]

        if 'leader' in stats:
            l = stats['leader']
            if h == l:
                return '0'

        if 'message' in stats:
            if stats['message'] == 'not current leader':
                return '-1'

    # get metric value and return it
    return reduce(lambda parent, child: parent.get(child, None), mlookup, stats)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Fetch etcd server metric')
    parser.add_argument('-m',dest='metric',action='store',help='metric',required='true')

    args = parser.parse_args()
    metric = args.metric

    if metric == 'v2/members':
        result = members(metric)
    else:
        result = get_metric(metric)

    if result is not None:
        print result
    else:
        print "ZBX_NOTSUPPORTED"
        exit(1)
