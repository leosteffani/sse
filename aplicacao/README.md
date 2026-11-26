# Aplicação (cliente, CONFIÁVEL) — Python + Streamlit

Tudo o que usa chaves está aqui: derivação de chaves (senha + arquivo de chave), cifra dos
registros, rótulos do índice, busca e decifragem. As chaves só existem na memória.

| Caminho | Função |
|---|---|
| `sse/crypto.py` | scrypt + HKDF, rótulos, entradas do índice, AES-256-GCM, preenchimento |
| `sse/vault.py` | Cofre local cifrado (salt + contadores); arquivo de chave separado |
| `sse/client.py` | Inserir e buscar (forward privacy, completude) |
| `sse/store.py` | `PgStore` (PostgreSQL) e `SqliteStore` (testes); só bytes |
| `sse/entidades.py` | Campos de produtos, clientes e franquias (indexados × só cifrados) |
| `sse/sintetico.py` | Dados sintéticos |
| `app.py` | Interface (criar registro, buscar) |
| `server_view.py` | Visão do servidor: lê o banco **sem chaves** (não importa o cofre) |
| `tests/test_sse.py` | Testes T1 a T5 |
| `scripts/seed.py`, `scripts/bench.py` | Carga de dados e medições (T8) |

## Passo a passo (Windows PowerShell, computador A)

```powershell
cd aplicacao
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
mkdir certs        # coloque aqui o ca.crt copiado do computador B

$env:PGHOST="192.168.0.10"          # IP do computador B
$env:PGUSER="sse_app"
$env:PGPASSWORD="<SSE_APP_PASSWORD do .env do banco>"
$env:PGSSLMODE="verify-full"
$env:PGSSLROOTCERT="certs/ca.crt"
streamlit run app.py --server.address 127.0.0.1
```

No primeiro uso o app cria o cofre e gera o **arquivo de chave**: baixe e guarde (sem ele
e sem a senha os dados não podem ser recuperados). Depois, informe senha + arquivo de
chave. As chaves são descartadas por inatividade (10 min) ou em "Sair".

Dados de exemplo: `$env:SSE_SENHA="<senha do cofre>"; python -m scripts.seed 300 --pg`

Visão do servidor (sem chaves; use o papel somente leitura):
```powershell
$env:PGUSER="sse_view"; $env:PGPASSWORD="<SSE_VIEW_PASSWORD>"
streamlit run server_view.py --server.port 8502
```

## Testes e medições

```powershell
python -m unittest -v                         # T1 a T5 (SQLite, sem banco)
$env:SSE_TEST_PG="1"; python -m unittest -v   # inclui o teste de integração no PostgreSQL
python -m scripts.bench --tamanhos 1000 5000 10000 --saida ..\evidencias\resultados.csv
```

| Teste | Esperado |
|---|---|
| T1 Adulteração de um byte | rejeitado (`ErroIntegridade`) |
| T2 Troca de registros ou de valores do índice | rejeitado (AAD) |
| T3 Omissão de entrada do índice | `ResultadoIncompleto` |
| T4 Forward privacy | o rótulo novo nunca foi enviado ao servidor antes |
| T5 Índice em repouso | todos os rótulos distintos |

(T6 a T8: ver `banco/README.md` e a tabela do relatório.)

## Decisões de segurança

AES-256-GCM com nonce aleatório e AAD = id; preenchimento de registros em faixas; ids
aleatórios; entradas de preenchimento no índice (blocos de 8) e lote embaralhado;
scrypt + arquivo de chave (dois fatores) + HKDF com separação de domínio; busca envia
rótulos `L(w,1..n)` e nunca `K_w`; TLS `verify-full`, SCRAM e privilégio mínimo.

## Limitações assumidas

Servidor "honesto, mas curioso"; vazam padrão de busca, padrão de acesso e tamanho do
resultado; busca só por palavra exata; um único usuário; sem proteção contra *rollback*
do banco ou do cofre; sem remoção de registros (só inserção).
