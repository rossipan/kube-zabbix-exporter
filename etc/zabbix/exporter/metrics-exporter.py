#!/usr/bin/env python
"""
Zabbix monitoring template for kube-apiserver node metrics.
for example:

fetch apiserver metrics    
$ ./metrics-exporter.py -u https://10.0.0.222:443/healthz -t healthz
$ ./metrics-exporter.py -u https://10.0.0.222:443/metrics -t counter -q apiserver_request_count -v LIST:total_count
$ ./metrics-exporter.py -u https://10.0.0.222:443/metrics -t counter -q apiserver_request_count -v LIST:error_count
$ ./metrics-exporter.py -u https://10.0.0.222:443/metrics -t summary -q apiserver_request_latencies_summary -v LIST

fetch kubelet metrics 
$ ./metrics-exporter.py -u https://10.0.0.222:10250/metrics -t gauge -q kubelet_running_pod_count
$ ./metrics-exporter.py -u https://10.0.0.222:10250/healthz -t healthz

fetch leader
$ ./metrics-exporter.py -u https://10.0.0.222:443 -t get_leader -q kube-controller-manager
$ ./metrics-exporter.py -u https://10.0.0.222:443 -t get_leader -q kube-scheduler
"""
from parser import text_string_to_metric_families
import sys, os, time
import requests
import re
import json
import argparse
import numpy as np
from base64 import b16encode
from sys import exit, stderr
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

stats_cache_file_tmpl = '/tmp/zbx_metrics_exporter_stats_{router}.txt'


def connect(router, timeout=60):

    # generate path for cache file
    cache_file = stats_cache_file_tmpl.format(router=b16encode(router))

    # get the age of the cache file
    if os.path.exists(cache_file):
        cache_age = int(time.time() - os.path.getmtime(cache_file))
    else:
        cache_age = timeout

    # read stats from cache if it's still valid
    if cache_age < timeout:
        with open(cache_file, 'r') as c:
            raw = c.read()

    # if not get, get the fresh stats from the apiserver
    else:
        # get the service account token
        token_file = '/var/run/secrets/kubernetes.io/serviceaccount/token'
        with open(token_file, 'r') as t:
            token = 'Bearer ' + t.read()

        try:
            requests.packages.urllib3.disable_warnings()
            raw = requests.get(router, headers={"Authorization": token}, verify=False).content

        except requests.exceptions.RequestException as e:
            return "Error: " + str(e)

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

def get_version(router):

    parsed_uri = urlparse(router)
    base_url = '{uri.scheme}://{uri.netloc}/'.format(uri=parsed_uri)
    raw_json = connect(base_url + 'version')

    # finally return the parsed response
    try:
        version_result = json.loads(raw_json)
    except Exception as e:  # improve this...
        print >> stderr, e
        return None

    version = version_result['major'] + '.' + version_result['minor']
    return version

def get_leader(router, endpoint):

    parsed_uri = urlparse(router)
    base_url = '{uri.scheme}://{uri.netloc}/'.format(uri=parsed_uri)
    raw_json = connect(base_url + 'api/v1/namespaces/kube-system/endpoints/' + endpoint)

    # finally return the parsed response
    try:
        leader_result = json.loads(raw_json)
        annotations_str = json.loads(leader_result['metadata']['annotations']['control-plane.alpha.kubernetes.io/leader'])
        holderIdentity = annotations_str['holderIdentity']
    except Exception as e:
        print >> stderr, e
        return None

    return holderIdentity

def num(s):
    # parse a string to a float
    try:
        return float(s)
    except ValueError:
        return float('0.0')

def counter(router, query_label_name, query_label_verb):

    parsed_query = query_label_verb.split(':')
    if len(parsed_query) != 2:
        print >> stderr, "Wrong query_label_verb syntax (%s)" % query_label_verb
        return None

    verb = parsed_query[0]
    count_by = parsed_query[1]

    total_count, error_count = 0.0, 0.0
    metrics = connect(router)
    api_version = get_version(router)

    for family in text_string_to_metric_families(metrics):
        for sample in family.samples:

            item = "{0}".format(*sample)

            if item == query_label_name:
                key = "{1}".format(*sample)
                value = "{2}".format(*sample)
                metric_label_name = key.replace('{', '').replace('}', '').replace(':', '=').replace('u\'', '').replace('\'', '').replace(' ', '')

                if api_version == '1.7':
                    hit_err_regex = r"^code=5..,.*verb=" + re.escape(verb) + r",.*"
                    hit_tal_regex = r"^code=.*verb=" + re.escape(verb) + r",.*"
                else:
                    hit_err_regex = r"^verb=" + re.escape(verb) + r",code=5..,.*"
                    hit_tal_regex = r"^verb=" + re.escape(verb) + r",code=.*"

                if count_by == 'total_count':
                    if re.match(hit_tal_regex, metric_label_name):
                        total_count += num(value)

                elif count_by == 'error_count':
                    if re.match(hit_err_regex, metric_label_name):
                        error_count += num(value)

    if count_by == 'total_count':
        return total_count
    elif count_by == 'error_count':
        return error_count

def summary(router, query_label_name, query_label_verb):

    data = []
    metrics = connect(router)
    api_version = get_version(router)

    for family in text_string_to_metric_families(metrics):
        for sample in family.samples:

            item = "{0}".format(*sample)

            if item == query_label_name:
                key = "{1}".format(*sample)
                value = "{2}".format(*sample)
                metric_label_name = key.replace('{', '').replace('}', '').replace(':', '=').replace('u\'', '').replace('\'', '').replace(' ', '')

                if api_version == '1.7':
                    hit_verb_regex = r"^quantile=0.99,verb=" + re.escape(query_label_verb) + r",.*"
                else:
                    hit_verb_regex = r"^scope=.*,quantile=0.99,verb=" + re.escape(query_label_verb) + r",.*"

                if re.match(hit_verb_regex, metric_label_name) and value != 'nan':
                    data.append(num(value))

    if len(data) > 0:
        np_arr = np.asarray(data)
        return np.mean(np_arr)
    else:
        return 0

def gauge(router, query_label_name):
    metrics = connect(router)

    for family in text_string_to_metric_families(metrics):
        for sample in family.samples:
            item = "{0}".format(*sample)
            if item == query_label_name:
                value = "{2}".format(*sample)
                break

    return value

def main():
    parser = argparse.ArgumentParser(description='Fetch apiserver metric')
    parser.add_argument('-u',dest='url',action='store',help='url',required='true')
    parser.add_argument('-t',dest='query_type',action='store',help='[healthz|counter|summary|gauge|get_leader]',required='true')
    parser.add_argument('-q',dest='query_label_name',action='store',help='[apiserver_request_count|apiserver_request_latencies_summary|kubelet_running_pod_count]',nargs='?')
    parser.add_argument('-v',dest='query_label_verb',action='store',help='[DELETE|LIST|PUT|POST|PATCH|GET]',nargs='?')

    args = parser.parse_args()

    url = args.url
    query_type = args.query_type
    query_label_name = args.query_label_name
    query_label_verb = args.query_label_verb

    if query_type == 'healthz':
        result = connect(url)

    elif query_type == 'gauge':
        result = gauge(router=url, query_label_name=query_label_name)

    elif query_type == 'counter':
        result = counter(router=url, query_label_name=query_label_name, query_label_verb=query_label_verb)

    elif query_type == 'summary':
        result = summary(router=url, query_label_name=query_label_name, query_label_verb=query_label_verb)

    elif query_type == 'get_leader':
        result = get_leader(router=url, endpoint=query_label_name)

    print result

if __name__ == "__main__":
    main()
