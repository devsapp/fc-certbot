# -*- coding: utf-8 -*-
import logging
import json
import certbot.main
import os
import subprocess
import datetime
from cas.index import upload_cert, get_cert_by_name
from alidns.index import check_if_valid_domain


def check_if_less_than_seven_days(x):
    d = datetime.datetime.strptime(x, "%Y-%m-%d")
    now = datetime.datetime.now()
    return (d - now).days < 7


def handler(event, context):
    evt = json.loads(event)
    domainName = evt.get("domainName")
    if domainName is not None:
        if domainName.startswith("https://") or domainName.startswith("http://"):
            domainName = domainName.split("://")[1]
        os.environ["DEVS_DOMAIN"] = domainName
    certName = evt.get("certName")
    certificate_id = None
    if certName is not None:
        cert = get_cert_by_name(certName)
        if cert is not None:
            if cert.common != domainName:
                raise Exception("domainName and cert common name do not match")
            if check_if_less_than_seven_days(cert.end_date):
                certificate_id = cert.id
            else:
                print("Cert will not expire in 7 days")
                return cert.id
    if domainName is None:
        raise Exception("no domainName provided")
    check_if_valid_domain()
    certbot_args = [
        "certonly",
        "--manual",
        "--quiet",
        "--non-interactive",
        "--agree-tos",
        "--manual-auth-hook",
        "/code/scripts/authenticator.sh",
        "--manual-cleanup-hook",
        "/code/scripts/cleanup.sh",
        "--preferred-challenges",
        "dns",
        "--key-type",
        "rsa",
        "--cert-name",
        domainName,
        "--email",
        "your_mail@mail.com",
        "--server",
        "https://acme-v02.api.letsencrypt.org/directory",
        "--domains",
        domainName,
    ]
    certbot.main.main(certbot_args)
    print("cert generated")
    exitCode = subprocess.call("/code/scripts/upload-certs.sh")
    if exitCode == 0:
        cert, key, cert_id = upload_cert(
            "/etc/letsencrypt/live/" + domainName + "/fullchain.pem",
            "/etc/letsencrypt/live/" + domainName + "/privkey.pkcs1.pem",
            domainName,
            certName,
            certificate_id,
        )
        print("cert uploaded to cas successfully")
        return cert_id
    else:
        raise Exception("failed to upload certs")
