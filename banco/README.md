# Banco de dados (servidor, NÃO confiável) — PostgreSQL com TLS

Guarda apenas bytes: `registros(id, ciphertext)` e `indice(label, valor)`.
Sem datas, sem colunas de tipo ou ordem, sem chaves. Privilégio mínimo:
`sse_app` (INSERT/SELECT) usado pela aplicação e `sse_view` (SELECT) para a visão do servidor.

| Arquivo | Função |
|---|---|
| `sql/schema.sql` | Tabelas e privilégios |
| `docker-compose.yml` | PostgreSQL 16 com `ssl=on`, SCRAM e log de comandos ligado |
| `initdb/01-init.sh` | Cria os papéis e aplica o esquema (1ª inicialização) |
| `initdb/02-hba.sh` | `pg_hba.conf`: só `hostssl` + `scram-sha-256`, só do IP do cliente |
| `gen_certs.sh` | Gera a CA própria e o certificado do servidor (com SAN) |
| `.env.example` | Senhas e IP do cliente (copiar para `.env`) |

## Passo a passo (Windows, computador B)

Requisitos: Docker Desktop. Para gerar os certificados use o **Git Bash** (vem com o Git
for Windows e inclui o OpenSSL) ou o WSL.

1. Descubra o IP do computador B e o do computador A (`ipconfig`).
2. Nesta pasta, no Git Bash: `./gen_certs.sh 192.168.0.10` (IP do computador B).
3. `copy .env.example .env` e edite as três senhas e o `CLIENT_CIDR` (IP do A, ex.: `192.168.0.20/32`).
4. `docker compose up -d`
5. Confira: `docker compose exec db psql -U postgres -d sse_db -c "SHOW ssl;"` → `on`.
6. Firewall do Windows (PowerShell como administrador), liberando a porta só para o cliente:
   `New-NetFirewallRule -DisplayName "PostgreSQL SSE" -Direction Inbound -Protocol TCP -LocalPort 5432 -RemoteAddress 192.168.0.20 -Action Allow`
7. Copie **somente** `certs/ca.crt` para o computador A (em `aplicacao/certs/ca.crt`).

## Para a demonstração e as evidências

- Consultas que chegam ao servidor: `docker compose logs db` (procure `FROM indice`).
- T7 (o banco só tem bytes):
  `docker compose exec db psql -U postgres -d sse_db -c "SELECT encode(id,'hex'), length(ciphertext) FROM registros LIMIT 3;"`
- Dump: `docker compose exec db pg_dump -U postgres sse_db`
- T6 (rede): capture a porta 5432 com o Wireshark durante uma busca; deve aparecer só TLS.

Se o contêiner reclamar de `\r` em `.sh`, os scripts foram salvos com fim de linha do Windows:
reconverta para LF (o `.gitattributes` já força LF no Git).
