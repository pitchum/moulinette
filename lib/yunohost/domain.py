# -*- coding: utf-8 -*-

""" License

    Copyright (C) 2013 YunoHost

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published
    by the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program; if not, see http://www.gnu.org/licenses

"""

""" yunohost_domain.py

    Manage domains
"""
import os
import sys
import datetime
import re
import shutil
import json
import yaml
from urllib import urlopen

from moulinette.core import MoulinetteError


def domain_list(auth, filter=None, limit=None, offset=None):
    """
    List domains

    Keyword argument:
        filter -- LDAP filter used to search
        offset -- Starting number for domain fetching
        limit -- Maximum number of domain fetched

    """
    result_list = []

    # Set default arguments values
    if offset is None:
        offset = 0
    if limit is None:
        limit = 1000
    if filter is None:
        filter = 'virtualdomain=*'

    result = auth.search('ou=domains,dc=yunohost,dc=org', filter, ['virtualdomain'])

    if len(result) > offset and limit > 0:
        for domain in result[offset:offset+limit]:
            result_list.append(domain['virtualdomain'][0])
    return { 'domains': result_list }


def domain_add(auth, domains, main=False, dyndns=False):
    """
    Create a custom domain

    Keyword argument:
        domains -- Domain name to add
        main -- Is the main domain
        dyndns -- Subscribe to DynDNS

    """
    attr_dict = { 'objectClass' : ['mailDomain', 'top'] }
    ip = str(urlopen('http://ip.yunohost.org').read())
    now = datetime.datetime.now()
    timestamp = str(now.year) + str(now.month) + str(now.day)
    result = []

    if not isinstance(domains, list):
        domains = [ domains ]

    for domain in domains:
        if domain in domain_list(auth)['domains']:
            continue

        # DynDNS domain
        if dyndns:
            if len(domain.split('.')) < 3:
                raise MoulinetteError(22, _("Invalid domain '%s' for DynDNS" % domain))
            import requests
            from yunohost.dyndns import dyndns_subscribe

            r = requests.get('http://dyndns.yunohost.org/domains')
            dyndomains = json.loads(r.text)
            dyndomain  = '.'.join(domain.split('.')[1:])
            if dyndomain in dyndomains:
                if os.path.exists('/etc/cron.d/yunohost-dyndns'):
                    raise MoulinetteError(22, _("You already have a DynDNS domain"))
                dyndns_subscribe(domain=domain)
            else:
                raise MoulinetteError(22, _("Unknown DynDNS domain '%s'" % dyndomain))

        # Commands
        ssl_dir = '/usr/share/yunohost/yunohost-config/ssl/yunoCA'
        ssl_domain_path  = '/etc/yunohost/certs/'+ domain
        with open(ssl_dir +'/serial', 'r') as f:
            serial = f.readline().rstrip()
        try: os.listdir(ssl_domain_path)
        except OSError: os.makedirs(ssl_domain_path)

        command_list = [
            'cp '+ ssl_dir +'/openssl.cnf '+ ssl_domain_path,
            'sed -i "s/yunohost.org/' + domain + '/g" '+ ssl_domain_path +'/openssl.cnf',
            'openssl req -new -config '+ ssl_domain_path +'/openssl.cnf -days 3650 -out '+ ssl_dir +'/certs/yunohost_csr.pem -keyout '+ ssl_dir +'/certs/yunohost_key.pem -nodes -batch',
            'openssl ca -config '+ ssl_domain_path +'/openssl.cnf -days 3650 -in '+ ssl_dir +'/certs/yunohost_csr.pem -out '+ ssl_dir +'/certs/yunohost_crt.pem -batch',
            'ln -s /etc/ssl/certs/ca-yunohost_crt.pem   '+ ssl_domain_path +'/ca.pem',
            'cp '+ ssl_dir +'/certs/yunohost_key.pem    '+ ssl_domain_path +'/key.pem',
            'cp '+ ssl_dir +'/newcerts/'+ serial +'.pem '+ ssl_domain_path +'/crt.pem',
            'chmod 755 '+ ssl_domain_path,
            'chmod 640 '+ ssl_domain_path +'/key.pem',
            'chmod 640 '+ ssl_domain_path +'/crt.pem',
            'chmod 600 '+ ssl_domain_path +'/openssl.cnf',
            'chown root:metronome '+ ssl_domain_path +'/key.pem',
            'chown root:metronome '+ ssl_domain_path +'/crt.pem'
        ]

        for command in command_list:
            if os.system(command) != 0:
                raise MoulinetteError(17, _("An error occurred during certificate generation"))

        try:
            auth.validate_uniqueness({ 'virtualdomain': domain })
        except MoulinetteError:
            raise MoulinetteError(17, _("Domain already created"))


        attr_dict['virtualdomain'] = domain

        try:
            with open('/var/lib/bind/'+ domain +'.zone') as f: pass
        except IOError as e:
            zone_lines = [
             '$TTL    38400',
             domain +'.      IN   SOA   ns.'+ domain +'. root.'+ domain +'. '+ timestamp +' 10800 3600 604800 38400',
             domain +'.      IN   NS    ns.'+ domain +'.',
             domain +'.      IN   A     '+ ip,
             domain +'.      IN   MX    5 '+ domain +'.',
             domain +'.      IN   TXT   "v=spf1 mx a -all"',
             'ns.'+ domain +'.   IN   A     '+ ip,
             '_xmpp-client._tcp.'+ domain +'.  IN   SRV   0  5   5222  '+ domain +'.',
             '_xmpp-server._tcp.'+ domain +'.  IN   SRV   0  5   5269  '+ domain +'.',
             '_jabber._tcp.'+ domain +'.       IN   SRV   0  5   5269  '+ domain +'.',
            ]
            if main:
                zone_lines.extend([
                    'pubsub.'+ domain +'.   IN   A     '+ ip,
                    'muc.'+ domain +'.      IN   A     '+ ip,
                    'vjud.'+ domain +'.     IN   A     '+ ip
                ])
            with open('/var/lib/bind/' + domain + '.zone', 'w') as zone:
                for line in zone_lines:
                    zone.write(line + '\n')

            os.system('chown bind /var/lib/bind/' + domain + '.zone')

        else:
            raise MoulinetteError(17, _("Zone file already exists for ") + domain)

        conf_lines = [
            'zone "'+ domain +'" {',
            '    type master;',
            '    file "/var/lib/bind/'+ domain +'.zone";',
            '    allow-transfer {',
            '        127.0.0.1;',
            '        localnets;',
            '    };',
            '};'
        ]
        with open('/etc/bind/named.conf.local', 'a') as conf:
            for line in conf_lines:
               conf.write(line + '\n')

        os.system('service bind9 reload')

        # XMPP
        try:
            with open('/etc/metronome/conf.d/'+ domain +'.cfg.lua') as f: pass
        except IOError as e:
            conf_lines = [
                'VirtualHost "'+ domain +'"',
                '  ssl = {',
                '        key = "'+ ssl_domain_path +'/key.pem";',
                '        certificate = "'+ ssl_domain_path +'/crt.pem";',
                '  }',
                '  authentication = "ldap2"',
                '  ldap = {',
                '     hostname      = "localhost",',
                '     user = {',
                '       basedn        = "ou=users,dc=yunohost,dc=org",',
                '       filter        = "(&(objectClass=posixAccount)(mail=*@'+ domain +'))",',
                '       usernamefield = "mail",',
                '       namefield     = "cn",',
                '       },',
                '  }',
            ]
            with open('/etc/metronome/conf.d/' + domain + '.cfg.lua', 'w') as conf:
                for line in conf_lines:
                    conf.write(line + '\n')

        os.system('mkdir -p /var/lib/metronome/'+ domain.replace('.', '%2e') +'/pep')
        os.system('chown -R metronome: /var/lib/metronome/')
        os.system('chown -R metronome: /etc/metronome/conf.d/')
        os.system('service metronome restart')


        # Nginx
        os.system('cp /usr/share/yunohost/yunohost-config/nginx/template.conf /etc/nginx/conf.d/'+ domain +'.conf')
        os.system('mkdir /etc/nginx/conf.d/'+ domain +'.d/')
        os.system('sed -i s/yunohost.org/'+ domain +'/g /etc/nginx/conf.d/'+ domain +'.conf')
        os.system('service nginx reload')

        if auth.add('virtualdomain=' + domain + ',ou=domains', attr_dict):
            result.append(domain)
            continue
        else:
            raise MoulinetteError(169, _("An error occurred during domain creation"))


    os.system('yunohost app ssowatconf > /dev/null 2>&1')

    msignals.display(_("Domain(s) successfully created."), 'success')
    return { 'domains': result }


def domain_remove(auth, domains):
    """
    Delete domains

    Keyword argument:
        domains -- Domain(s) to delete

    """
    result = []
    domains_list = domain_list(auth)['domains']

    if not isinstance(domains, list):
        domains = [ domains ]

    for domain in domains:
        if domain not in domains_list:
            raise MoulinetteError(22, _("Unknown domain '%s'") % domain)

        # Check if apps are installed on the domain
        for app in os.listdir('/etc/yunohost/apps/'):
            with open('/etc/yunohost/apps/' + app +'/settings.yml') as f:
                try:
                    app_domain = yaml.load(f)['domain']
                except:
                    continue
                else:
                    if app_domain == domain:
                        raise MoulinetteError(1, _("One or more apps are installed on this domain, please uninstall them before proceed to domain removal"))

        if auth.remove('virtualdomain=' + domain + ',ou=domains'):
            try:
                shutil.rmtree('/etc/yunohost/certs/'+ domain)
                os.remove('/var/lib/bind/'+ domain +'.zone')
                shutil.rmtree('/var/lib/metronome/'+ domain.replace('.', '%2e'))
                os.remove('/etc/metronome/conf.d/'+ domain +'.cfg.lua')
                shutil.rmtree('/etc/nginx/conf.d/'+ domain +'.d')
                os.remove('/etc/nginx/conf.d/'+ domain +'.conf')
            except:
                pass
            with open('/etc/bind/named.conf.local', 'r') as conf:
                conf_lines = conf.readlines()
            with open('/etc/bind/named.conf.local', 'w') as conf:
                in_block = False
                for line in conf_lines:
                    if re.search(r'^zone "'+ domain, line):
                        in_block = True
                    if in_block:
                        if re.search(r'^};$', line):
                            in_block = False
                    else:
                        conf.write(line)
            result.append(domain)
            continue
        else:
            raise MoulinetteError(169, _("An error occurred during domain deletion"))

    os.system('yunohost app ssowatconf > /dev/null 2>&1')
    os.system('service nginx reload')
    os.system('service bind9 reload')
    os.system('service metronome restart')

    msignals.display(_("Domain(s) successfully deleted."), 'success')
    return { 'domains': result }
