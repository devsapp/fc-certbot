#!/bin/bash

privkeyPath=/etc/letsencrypt/live/$DEVS_DOMAIN/privkey.pem
if [ -e "$privkeyPath" ]; then
    openssl rsa -in $privkeyPath -out /etc/letsencrypt/live/$DEVS_DOMAIN/privkey.pkcs1.pem
fi
