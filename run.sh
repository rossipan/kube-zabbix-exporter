#!/bin/sh

SERVER="$ZBX_SERVER_HOST"
METADATA="$ZBX_METADATA"
HOST="$ZBX_HOSTNAME"

if [ -z "$SERVER" ]; then
    echo "Server address is missing"
    exit 1
fi

if [ -z "$METADATA" ]; then
    echo "Host metadata is missing"
    exit 1
fi

if [ -z "$HOST" ]; then
    #MACHINEID=$(cat /rootfs/etc/machine-id)
    HOST="$METADATA-$HOSTNAME"
fi

sed -i "s/^Server\=.*/Server\=$SERVER/" /etc/zabbix/zabbix_agentd.conf
sed -i "s/^ServerActive\=.*/ServerActive\=$SERVER/" /etc/zabbix/zabbix_agentd.conf
sed -i "s/^Hostname\=.*/Hostname\=$HOST/" /etc/zabbix/zabbix_agentd.conf
sed -i "s/^HostMetadata\=.*/HostMetadata\=$METADATA/" /etc/zabbix/zabbix_agentd.conf

if [ -f "/etc/zabbix/$HOST.conf" ]; then
    cat "/etc/zabbix/$HOST.conf" >> /etc/zabbix/zabbix_agentd.conf
fi

exec /usr/sbin/zabbix_agentd -c /etc/zabbix/zabbix_agentd.conf -f
