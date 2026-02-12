# -*- coding: utf-8 -*-
import logging
import json
import certbot.main
import os
import subprocess
import datetime
from cas.index import upload_cert, get_cert_by_name
from alidns.index import check_if_valid_domain

try:
    from certbot.crypto_util import get_names_from_cert
except ImportError:
    get_names_from_cert = None


def check_if_less_than_seven_days(x):
    d = datetime.datetime.strptime(x, "%Y-%m-%d")
    now = datetime.datetime.now()
    return (d - now).days < 7


def handler(event, context):
    evt = json.loads(event)
    domainName = evt.get("domainName")
    
    # 支持 domainName 为字符串或数组
    if domainName is not None:
        # 如果是字符串，转换为列表
        if isinstance(domainName, str):
            domainName = domainName.strip()
            if not domainName:
                raise Exception("domainName must be a non-empty string")
            if domainName.startswith("https://") or domainName.startswith("http://"):
                domainName = domainName.split("://", 1)[1].strip()
                if not domainName:
                    raise Exception("domainName must be a non-empty string after normalization")
            domainNames = [domainName]
        # 如果是列表，清理每个域名
        elif isinstance(domainName, list):
            if not domainName:
                raise Exception("domainName list must be non-empty")
            domainNames = []
            for d in domainName:
                if not isinstance(d, str):
                    raise Exception("all domainName items must be non-empty strings")
                d = d.strip()
                if not d:
                    raise Exception("all domainName items must be non-empty strings")
                if d.startswith("https://") or d.startswith("http://"):
                    d = d.split("://", 1)[1].strip()
                    if not d:
                        raise Exception("all domainName items must be non-empty strings after normalization")
                domainNames.append(d)
        else:
            raise Exception("domainName must be a string or array")
        
        # 使用第一个域名作为主域名（用于 DNS 验证和证书存储路径）
        if not domainNames:
            raise Exception("no valid domainName provided")
        primary_domain = domainNames[0]
        os.environ["DEVS_DOMAIN"] = primary_domain
    else:
        raise Exception("no domainName provided")
    
    certName = evt.get("certName")
    certificate_id = None
    if certName is not None:
        cert = get_cert_by_name(certName)
        if cert is not None:
            # 从证书内容中解析所有 SAN 域名（使用 certbot/acme 模块）
            existing_domains = []
            if hasattr(cert, 'cert') and cert.cert:
                try:
                    if get_names_from_cert is None:
                        raise ImportError("certbot.crypto_util not available")
                    # 使用 certbot 的方法从 PEM 格式证书中提取所有域名（CN + SAN）
                    cert_bytes = cert.cert.encode('utf-8')
                    all_names = get_names_from_cert(cert_bytes)
                    existing_domains = all_names
                    print(f"Parsed {len(all_names)} domain(s) from certificate: {', '.join(all_names)}")
                    
                    # 方案二：补充检查 CN 是否在列表中（双重保险）
                    if hasattr(cert, 'common') and cert.common:
                        if cert.common not in existing_domains:
                            existing_domains.insert(0, cert.common)
                            print(f"Added CN '{cert.common}' to domain list")
                except Exception as e:
                    print(f"Warning: Failed to parse SAN from certificate: {e}")
                    # 降级方案：从 API 字段中解析域名
                    if hasattr(cert, 'common') and cert.common:
                        existing_domains.append(cert.common)
                    
                    # 解析 sans 字段
                    if hasattr(cert, 'sans') and cert.sans:
                        print(f"DEBUG: sans field type: {type(cert.sans)}, value: {cert.sans}")
                        # sans 可能是字符串（逗号/空格/换行分隔）或列表
                        if isinstance(cert.sans, str):
                            # 尝试多种分隔符：逗号、空格、换行
                            sans_str = cert.sans.replace('\n', ',').replace(' ', ',')
                            sans_list = [s.strip() for s in sans_str.split(',') if s.strip()]
                        elif isinstance(cert.sans, list):
                            sans_list = cert.sans
                        else:
                            sans_list = []
                        
                        # 添加所有SAN域名，去重
                        for san in sans_list:
                            if san and san not in existing_domains:
                                existing_domains.append(san)
                    
                    if existing_domains:
                        print(f"Using fallback method, parsed domains: {', '.join(existing_domains)}")
            
            if existing_domains:
                # 使用现有证书的域名列表，保持顺序一致
                domainNames = existing_domains
                primary_domain = domainNames[0]
                os.environ["DEVS_DOMAIN"] = primary_domain
                print(f"Using domains from existing certificate: {', '.join(domainNames)}")
            
            # 检查证书是否需要更新
            if check_if_less_than_seven_days(cert.end_date):
                certificate_id = cert.id
            else:
                print("Cert will not expire in 7 days")
                return cert.id
    
    # 对所有请求的域名执行域名有效性检查，避免仅校验主域名
    original_devs_domain = os.environ.get("DEVS_DOMAIN")
    try:
        for domain in domainNames:
            os.environ["DEVS_DOMAIN"] = domain
            check_if_valid_domain()
    finally:
        # 恢复为主域名，保持后续逻辑的兼容性
        if original_devs_domain is not None:
            os.environ["DEVS_DOMAIN"] = original_devs_domain
        else:
            os.environ["DEVS_DOMAIN"] = primary_domain
    
    # 构建 certbot 参数，支持多域名
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
        primary_domain,
        "--email",
        "your_mail@mail.com",
        "--server",
        "https://acme-v02.api.letsencrypt.org/directory",
    ]
    
    # 为每个域名添加 -d 参数（注意：用 -d 而不是 --domains）
    for domain in domainNames:
        certbot_args.extend(["-d", domain])
    
    print(f"Requesting certificate for domains: {', '.join(domainNames)}")
    certbot.main.main(certbot_args)
    print("cert generated")
    exitCode = subprocess.call("/code/scripts/upload-certs.sh")
    if exitCode == 0:
        cert, key, cert_id = upload_cert(
            "/etc/letsencrypt/live/" + primary_domain + "/fullchain.pem",
            "/etc/letsencrypt/live/" + primary_domain + "/privkey.pkcs1.pem",
            primary_domain,
            certName,
            certificate_id,
        )
        print("cert uploaded to cas successfully")
        return cert_id
    else:
        raise Exception("failed to upload certs")
