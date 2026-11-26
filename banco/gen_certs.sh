#!/bin/bash
# Gera uma CA própria e o certificado do servidor (com SAN) para TLS verify-full.
# Uso: ./gen_certs.sh 192.168.0.10     (IP ou nome DNS do computador servidor)
set -euo pipefail
HOST="${1:?uso: ./gen_certs.sh <IP ou nome do servidor>}"
mkdir -p certs && cd certs
openssl genrsa -out ca.key 4096
openssl req -x509 -new -key ca.key -sha256 -days 365 -subj "/CN=SSE Demo CA" -out ca.crt
openssl genrsa -out server.key 2048
openssl req -new -key server.key -subj "/CN=${HOST}" -out server.csr
if [[ "$HOST" =~ ^[0-9.]+$ ]]; then SAN="IP:${HOST}"; else SAN="DNS:${HOST}"; fi
printf "subjectAltName=%s\n" "$SAN" > san.ext
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
        -out server.crt -days 365 -sha256 -extfile san.ext
chmod 600 server.key ca.key
rm -f server.csr san.ext
echo "OK. Copie SOMENTE certs/ca.crt para o computador cliente."
