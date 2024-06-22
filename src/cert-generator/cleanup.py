# -*- coding: utf-8 -*-

from alidns.index import get_domain_record_id, get_domain_rr, get_domain_name, delete_rr

domainName = get_domain_name()
rr = get_domain_rr()

record_id = get_domain_record_id(domainName, rr)

if record_id:
    delete_rr(record_id)
    print("dns record delted.")
