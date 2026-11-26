# Busca em base de dados cifrada (SSE) — Python + PostgreSQL

Trabalho de implementação de esquemas criptográficos (UFSC). Guarda **produtos,
clientes (empresas) e franquias** (dados sintéticos) cifrados em um PostgreSQL e
permite **buscar por palavra-chave sem que o servidor veja o conteúdo nem a palavra
buscada** (Searchable Symmetric Encryption com índice dinâmico, contador no cliente,
*forward privacy* e checagem de completude).

```
trabalho final sec/
├── banco/        LADO NÃO CONFIÁVEL  → computador B (servidor): PostgreSQL + TLS
├── aplicacao/    LADO CONFIÁVEL      → computador A (cliente): chaves, cifra, busca
└── evidencias/   capturas de rede, prints, resultados dos testes e do benchmark
```

```
Computador A (aplicacao/)                     Computador B (banco/)
┌─────────────────────────────┐   TLS (rede)  ┌─────────────────────────────┐
│ app.py (Streamlit, local)   │ ────────────▶ │ PostgreSQL (Docker)         │
│ senha + arquivo de chave    │ ◀──────────── │  registros(id, ciphertext)  │
│ chaves só em memória        │               │  indice(label, valor)       │
│ cofre.sse (contadores)      │               │ (sem chaves, só bytes)      │
└─────────────────────────────┘               └─────────────────────────────┘
```

A pasta `banco/` **não contém nenhuma chave nem código de criptografia**: só o esquema,
o Docker e a configuração de TLS/autenticação. Toda a criptografia está em `aplicacao/`.

Ordem: 1) `banco/README.md` (subir o servidor) → 2) `aplicacao/README.md` (rodar o
cliente, os testes e o benchmark) → 3) guardar as provas em `evidencias/`.

Não versione: `cofre.sse`, `chave.bin`, `banco/.env`, `banco/certs/` (ver `.gitignore`).
