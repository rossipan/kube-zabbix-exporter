FROM python:2.7.15-stretch

ENV DEBIAN_FRONTEND noninteractive
ENV ZABBIX_AGENT_PACKAGE zabbix-agent_3.0.17+dfsg-1_amd64.deb

COPY files/${ZABBIX_AGENT_PACKAGE} /root/
COPY etc/zabbix/ /etc/zabbix/
COPY run.sh /
COPY files/dumb-init_1.2.0_amd64 /usr/local/bin/dumb-init

RUN groupadd zabbix && useradd -g zabbix zabbix  && \
    apt-get update && \
    apt-get -y install locales && \
    dpkg-reconfigure locales && \
    locale-gen C.UTF-8 && \
    /usr/sbin/update-locale LANG=C.UTF-8 && \
    echo 'en_US.UTF-8 UTF-8' >> /etc/locale.gen && \
    locale-gen
ENV LC_ALL C.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US.UTF-8
ENV TERM xterm

RUN apt-get update && \
    apt-get -y install \
        procps \
        iproute && \
    apt-get -y install --no-install-recommends \
        jq \
        libcurl3-gnutls \
        libldap-2.4-2 \
        netcat-openbsd \
        pciutils \
        sudo && \
    dpkg -i /root/${ZABBIX_AGENT_PACKAGE} && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* && \
    mkdir -p /var/lib/zabbix && \
    chmod 700 /var/lib/zabbix && \
    chown zabbix:zabbix /var/lib/zabbix && \
    chown zabbix:zabbix -R /etc/zabbix && \
    usermod -d /var/lib/zabbix zabbix && \
    usermod -a -G adm zabbix && \
    chmod +x /run.sh && \
    chmod +x /usr/local/bin/dumb-init && \
    rm -f /root/${ZABBIX_AGENT_PACKAGE} && \
    pip install -r /etc/zabbix/exporter/res/requirements.txt

COPY etc/sudoers.d/zabbix /etc/sudoers.d/zabbix
RUN chmod 400 /etc/sudoers.d/zabbix

EXPOSE 10050

USER zabbix
ENTRYPOINT ["/usr/local/bin/dumb-init","/run.sh"]
