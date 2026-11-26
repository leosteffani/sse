"""Camada do servidor: só guarda e devolve bytes. Não tem acesso a nenhuma chave.

PgStore     -> PostgreSQL (usado na demonstração, em outro computador, com TLS)
SqliteStore -> mesma interface, para testes e benchmarks locais sem banco
"""
import sqlite3


class ErroDuplicado(Exception):
    """Rótulo ou id já existente (ex.: estado do cliente desatualizado)."""


class SqliteStore:
    def __init__(self, caminho=":memory:"):
        self.conn = sqlite3.connect(caminho)
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS registros (id BLOB PRIMARY KEY, ciphertext BLOB NOT NULL);
            CREATE TABLE IF NOT EXISTS indice (label BLOB PRIMARY KEY, valor BLOB NOT NULL);
            """
        )

    def inserir(self, registro_id, ciphertext, entradas):
        try:
            with self.conn:
                self.conn.execute(
                    "INSERT INTO registros(id, ciphertext) VALUES (?, ?)",
                    (registro_id, ciphertext),
                )
                self.conn.executemany(
                    "INSERT INTO indice(label, valor) VALUES (?, ?)", entradas
                )
        except sqlite3.IntegrityError as e:
            raise ErroDuplicado(str(e)) from e

    def buscar_indice(self, rotulos):
        achados = {}
        for i in range(0, len(rotulos), 500):
            lote = rotulos[i : i + 500]
            q = ",".join("?" * len(lote))
            for lab, val in self.conn.execute(
                f"SELECT label, valor FROM indice WHERE label IN ({q})", lote
            ):
                achados[bytes(lab)] = bytes(val)
        return achados

    def obter_registros(self, ids):
        achados = {}
        for i in range(0, len(ids), 500):
            lote = ids[i : i + 500]
            q = ",".join("?" * len(lote))
            for rid, ct in self.conn.execute(
                f"SELECT id, ciphertext FROM registros WHERE id IN ({q})", lote
            ):
                achados[bytes(rid)] = bytes(ct)
        return achados

    def amostra_registros(self, limite=20):
        return [
            (bytes(r), bytes(c))
            for r, c in self.conn.execute(
                "SELECT id, ciphertext FROM registros LIMIT ?", (limite,)
            )
        ]

    def amostra_indice(self, limite=20):
        return [
            (bytes(a), bytes(b))
            for a, b in self.conn.execute("SELECT label, valor FROM indice LIMIT ?", (limite,))
        ]

    def contagens(self):
        n_reg = self.conn.execute("SELECT count(*) FROM registros").fetchone()[0]
        n_idx = self.conn.execute("SELECT count(*) FROM indice").fetchone()[0]
        n_dist = self.conn.execute("SELECT count(DISTINCT label) FROM indice").fetchone()[0]
        return {"registros": n_reg, "entradas_indice": n_idx, "rotulos_distintos": n_dist}

    def fechar(self):
        self.conn.close()


class PgStore:
    """Usa psycopg 3. Os parâmetros (host, dbname, user, password, sslmode,
    sslrootcert...) vêm como argumentos ou das variáveis PG* do ambiente."""

    def __init__(self, **conexao):
        import psycopg  # importado aqui para não ser exigido nos testes locais

        self._psycopg = psycopg
        self.conn = psycopg.connect(autocommit=True, **conexao)

    def inserir(self, registro_id, ciphertext, entradas):
        try:
            with self.conn.transaction():
                with self.conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO registros(id, ciphertext) VALUES (%s, %s)",
                        (registro_id, ciphertext),
                    )
                    cur.executemany(
                        "INSERT INTO indice(label, valor) VALUES (%s, %s)", entradas
                    )
        except self._psycopg.errors.UniqueViolation as e:
            raise ErroDuplicado(str(e)) from e

    def buscar_indice(self, rotulos):
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT label, valor FROM indice WHERE label = ANY(%s)", (list(rotulos),)
            )
            return {bytes(a): bytes(b) for a, b in cur.fetchall()}

    def obter_registros(self, ids):
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id, ciphertext FROM registros WHERE id = ANY(%s)", (list(ids),)
            )
            return {bytes(a): bytes(b) for a, b in cur.fetchall()}

    def amostra_registros(self, limite=20):
        with self.conn.cursor() as cur:
            cur.execute("SELECT id, ciphertext FROM registros LIMIT %s", (limite,))
            return [(bytes(a), bytes(b)) for a, b in cur.fetchall()]

    def amostra_indice(self, limite=20):
        with self.conn.cursor() as cur:
            cur.execute("SELECT label, valor FROM indice LIMIT %s", (limite,))
            return [(bytes(a), bytes(b)) for a, b in cur.fetchall()]

    def contagens(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM registros")
            n_reg = cur.fetchone()[0]
            cur.execute("SELECT count(*), count(DISTINCT label) FROM indice")
            n_idx, n_dist = cur.fetchone()
        return {"registros": n_reg, "entradas_indice": n_idx, "rotulos_distintos": n_dist}

    def fechar(self):
        self.conn.close()
