# -*- coding: utf-8 -*-

import os


from alidns.index import get_domain_record_id_by_value, get_domain_rr, get_domain_name, delete_rr

try:
    domainName = get_domain_name()
    rr = get_domain_rr()
    validation = os.environ.get("CERTBOT_VALIDATION", "")
    
    print(f"[Cleanup] Domain: {domainName}")
    print(f"[Cleanup] RR: {rr}")
    print(f"[Cleanup] Validation: {validation[:20]}...")
    
    # 按 RR + value 精确匹配删除，避免误删同名的其他 ACME challenge 记录
    # （*.example.com 和 example.com 共用同一个 _acme-challenge RR 名）
    record_id = get_domain_record_id_by_value(domainName, rr, validation)
    
    if record_id:
        delete_rr(record_id)
        print(f"[Cleanup] DNS record {record_id} deleted.")
    else:
        print("[Cleanup] No matching DNS record found to delete.")
        
except Exception as e:
    print(f"[Cleanup] WARNING: {str(e)}")
    # cleanup 失败不影响证书生成，只记录警告
    pass
