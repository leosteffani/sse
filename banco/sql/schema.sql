-- Esquema do servidor. O banco guarda apenas bytes: nada legível, sem datas,
-- sem colunas de tipo ou ordem (o tipo do registro vai dentro do conteúdo cifrado).

CREATE TABLE IF NOT EXISTS registros (
    id         BYTEA PRIMARY KEY,   -- 16 bytes aleatórios
    ciphertext BYTEA NOT NULL       -- nonce || AES-256-GCM(registro preenchido; AAD = id)
);

CREATE TABLE IF NOT EXISTS indice (
    label BYTEA PRIMARY KEY,        -- HMAC-SHA256 (pseudoaleatório) ou preenchimento
    valor BYTEA NOT NULL            -- nonce || AES-GCM(id do registro; AAD = label)
);

-- Privilégio mínimo (os papéis são criados em server/initdb/01-init.sh)
REVOKE ALL ON registros, indice FROM PUBLIC;
GRANT SELECT, INSERT ON registros, indice TO sse_app;   -- aplicação: só insere e lê
GRANT SELECT          ON registros, indice TO sse_view; -- visão do servidor: só lê
