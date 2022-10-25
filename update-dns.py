"""Cloudflare API code - example"""

import os
import sys
import requests
import CloudFlare
import json


def read_config():
    with open('dns-config.json', 'r') as data_file:
        record_data = json.load(data_file)
        #print(record_data)

    token = record_data["api_key"]
    zone = record_data["zone"]
    return token, zone
    #exit(0)


sys.path.insert(0, os.path.abspath('..'))


def my_ip_address():
    """Cloudflare API code - example"""

    # This list is adjustable - plus some v6 enabled services are needed
    # url = 'http://myip.dnsomatic.com'
    # url = 'http://www.trackip.net/ip'
    # url = 'http://myexternalip.com/raw'
    url = 'https://api.ipify.org'
    try:
        ip_address = requests.get(url).text
    except:
        exit('%s: failed' % (url))
    if ip_address == '':
        exit('%s: failed' % (url))

    if ':' in ip_address:
        ip_address_type = 'AAAA'
    else:
        ip_address_type = 'A'

    #
    #ip_address = '192.168.1.100'
    return ip_address, ip_address_type


def do_dns_update(cf, zone_id, dns_name, ip_address, ip_address_type, ttl):
    """Cloudflare API code - example"""

    try:
        params = {'name': dns_name, 'match': 'all', 'type': ip_address_type}
        dns_records = cf.zones.dns_records.get(zone_id, params=params)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit('/zones/dns_records %s - %d %s - api call failed' % (dns_name, e, e))

    updated = False

    # update the record - unless it's already correct
    for dns_record in dns_records:
        old_ip_address = dns_record['content']
        old_ip_address_type = dns_record['type']

        if ip_address_type not in ['A', 'AAAA']:
            # we only deal with A / AAAA records
            continue

        if ip_address_type != old_ip_address_type:
            # only update the correct address type (A or AAAA)
            # we don't see this becuase of the search params above
            print('IGNORED: %s %s ; wrong address family' % (dns_name, old_ip_address))
            continue

        if ip_address == old_ip_address:
            print('UNCHANGED: %-*s %s' % (30, dns_name, ip_address))
            updated = True
            continue

        proxied_state = dns_record['proxied']
        if proxied_state:
            ttl = 1

        # Yes, we need to update this record - we know it's the same address type
        dns_record_id = dns_record['id']
        dns_record = {
            'ttl': ttl,
            'name': dns_name,
            'type': ip_address_type,
            'content': ip_address,
            'proxied': proxied_state
        }

        try:
            dns_record = cf.zones.dns_records.put(zone_id, dns_record_id, data=dns_record)
        except CloudFlare.exceptions.CloudFlareAPIError as e:
            exit('/zones.dns_records.put %s - %d %s - api call failed' % (dns_name, e, e))
        print('UPDATED: %-*s %s -> %s' % (30, dns_name, old_ip_address, ip_address))
        updated = True

    if updated:
        return

    # no exsiting dns record to update - so create dns record
    dns_record = {
        'ttl': ttl,
        'name': dns_name,
        'type': ip_address_type,
        'content': ip_address,
        'proxied': True
    }
    try:
        dns_record = cf.zones.dns_records.post(zone_id, data=dns_record)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit('/zones.dns_records.post %s - %d %s - api call failed' % (dns_name, e, e))
    print('CREATED: %s %s' % (dns_name, ip_address))


def main():
    """Cloudflare API code - example"""
    api_token, zone_name = read_config()
    print(api_token,zone_name)

    if zone_name == "":
        try:
            zone_name = sys.argv[1]
        except IndexError:
            exit('usage: example-update-dynamic-dns.py fqdn-hostname')

    ip_address, ip_address_type = my_ip_address()
    print("Current public IP: " + ip_address)
    r_ttl = 1
    cf = CloudFlare.CloudFlare(token=api_token,)

    # query for the zone name and expect only one value back
    try:
        zones = cf.zones.get(params={'name': zone_name, 'per_page': 1})
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit('/zones.get %d %s - api call failed' % (e, e))
    except Exception as e:
        exit('/zones.get - %s - api call failed' % (e))
    if len(zones) == 0:
        exit('No zones found')

    # extract the zone_id which is needed to process that zone
    zone = zones[0]
    zone_id = zone['id']

    # request the DNS records from that zone
    try:
        dns_records = cf.zones.dns_records.get(zone_id)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit('/zones/dns_records.get %d %s - api call failed' % (e, e))

    # print the results - first the zone name
    print("FOUND: zone_id=%s zone_name=%s \n" % (zone_id, zone_name))

    # then all the DNS records for that zone
    for dns_record in dns_records:
        r_name = dns_record['name']
        r_type = dns_record['type']
        r_content = dns_record['content']
        r_id = dns_record['id']
        r_ttl = dns_record['ttl']
        #print('\t', r_id, r_name, r_type, r_content)

        if r_type in ['A', 'AAAA']:
            do_dns_update(cf, zone_id, r_name, ip_address, ip_address_type, r_ttl)
    exit(0)


if __name__ == '__main__':
    main()
