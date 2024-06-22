# -*- coding: utf-8 -*-

import os

from alibabacloud_alidns20150109.client import Client as Alidns20150109Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_alidns20150109 import models as alidns_20150109_models
from alibabacloud_tea_util import models as util_models


def get_domain_rr():
    tokens = os.environ["DEVS_DOMAIN"].split(".")
    del tokens[-2:]
    if tokens[0] == "*":
        tokens.pop(0)
    tokens.insert(0, "_acme-challenge")
    return ".".join(tokens)


def get_domain_name():
    tokens = os.environ["DEVS_DOMAIN"].split(".")
    return ".".join(tokens[-2:])


def check_if_valid_domain():
    client.describe_domain_info_with_options(
        alidns_20150109_models.DescribeDomainInfoRequest(domain_name=get_domain_name()),
        runtime,
    )


def insert_rr(domainName, rr):
    print(os.environ["CERTBOT_VALIDATION"])
    client.add_domain_record_with_options(
        alidns_20150109_models.AddDomainRecordRequest(
            domain_name=domainName,
            rr=rr,
            type="TXT",
            value=os.environ["CERTBOT_VALIDATION"],
        ),
        runtime,
    )


def delete_rr(record_id):
    client.delete_domain_record_with_options(
        alidns_20150109_models.DeleteDomainRecordRequest(record_id=record_id), runtime
    )


def update_rr(record_id, rr):
    client.update_domain_record_with_options(
        alidns_20150109_models.UpdateDomainRecordRequest(
            record_id=record_id,
            rr=rr,
            type="TXT",
            value=os.environ["CERTBOT_VALIDATION"],
        ),
        runtime,
    )


def get_domain_record_id(domainName, rr):
    records = client.describe_domain_records_with_options(
        alidns_20150109_models.DescribeDomainRecordsRequest(
            domain_name=domainName, type_key_word="TXT", rrkey_word=rr
        ),
        runtime,
    )
    record_id = None
    for record in records.body.domain_records.record:
        if record.rr == rr:
            record_id = record.record_id
            break
    return record_id


def get_alidns_endpoint():
    if os.environ["FC_REGION"] == "ap-southeast-1":
        return "alidns.ap-southeast-1.aliyuncs.com"
    else:
        return "alidns.cn-hangzhou.aliyuncs.com"


runtime = util_models.RuntimeOptions()

client = Alidns20150109Client(
    open_api_models.Config(
        access_key_id=os.environ["ALIBABA_CLOUD_ACCESS_KEY_ID"],
        access_key_secret=os.environ["ALIBABA_CLOUD_ACCESS_KEY_SECRET"],
        security_token=os.environ["ALIBABA_CLOUD_SECURITY_TOKEN"],
        endpoint=get_alidns_endpoint(),
        read_timeout=1000000,
        connect_timeout=1000000,
    )
)
