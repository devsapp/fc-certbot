# -*- coding: utf-8 -*-

import os
import time
import sys

from alidns.index import (
    insert_rr,
    get_domain_rr,
    get_domain_name,
)

try:
    domainName = get_domain_name()
    rr = get_domain_rr()
    validation = os.environ.get("CERTBOT_VALIDATION", "")
    current_domain = os.environ.get("CERTBOT_DOMAIN", os.environ.get("DEVS_DOMAIN", "unknown"))
    
    print(f"[Authenticator] Processing domain: {current_domain}")
    print(f"[Authenticator] Base domain: {domainName}")
    print(f"[Authenticator] RR: {rr}")
    print(f"[Authenticator] Validation: {validation[:20]}...")
    
    # 始终新增记录，不要更新已有记录！
    # 原因：*.example.com 和 example.com 共用同一个 _acme-challenge RR 名，
    # 但 ACME 验证需要两条不同值的 TXT 记录同时存在。
    # DNS 允许同名多条 TXT 记录，所以每次都应该 insert 而不是 update。
    insert_rr(domainName, rr)
    print("[Authenticator] DNS record added.")
    
    # 等待 DNS 记录传播（重要！）
    # Certbot 会为每个域名分别调用此脚本，所以每个域名都会等待
    # 阿里云 DNS 通常在 10-30 秒内生效
    # 注意：多域名证书的总等待时间 = 域名数量 × 等待时间
    wait_time = int(os.environ.get("DNS_PROPAGATION_WAIT", "30"))
    print(f"[Authenticator] Waiting {wait_time} seconds for DNS propagation...")
    time.sleep(wait_time)
    print("[Authenticator] DNS propagation wait completed.")
    
except Exception as e:
    print(f"[Authenticator] ERROR: {str(e)}")
    sys.exit(1)
