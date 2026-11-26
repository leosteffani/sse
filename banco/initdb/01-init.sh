#!/bin/bash
# Executado uma única vez, na primeira inicialização do banco.
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
  CREATE ROLE sse_app  LOGIN PASSWORD '${SSE_APP_PASSWORD}';
  CREATE ROLE sse_view LOGIN PASSWORD '${SSE_VIEW_PASSWORD}';
  \i /sql/schema.sql
EOSQL
