#!/bin/bash
# Só aceita conexões TLS (hostssl) dos dois papéis, a partir do endereço do cliente.
set -e
cat > "$PGDATA/pg_hba.conf" <<EOCONF
local all all trust
hostssl ${POSTGRES_DB} sse_app  ${CLIENT_CIDR} scram-sha-256
hostssl ${POSTGRES_DB} sse_view ${CLIENT_CIDR} scram-sha-256
EOCONF
