"""T8 - desempenho: tempo de inserção, de busca e tamanho do índice.
Compara a busca cifrada com uma busca em claro (índice invertido sem cifra, SQLite).
Uso:  python -m scripts.bench --tamanhos 1000 5000 10000 --saida resultados.csv
(SQLite local; para medir no PostgreSQL remoto use --pg com um banco vazio.)
"""
import argparse
import csv
import os
import sqlite3
import statistics
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sse import crypto  # noqa: E402
from sse.client import ClienteSSE  # noqa: E402
from sse.store import PgStore, SqliteStore  # noqa: E402
from sse.sintetico import gerar  # noqa: E402
from sse.vault import criar_cofre, gerar_arquivo_chave  # noqa: E402

PALAVRAS_BUSCA = ["joinville", "ferramentas", "metalurgia", "franquias", "aurora"]


def medir_busca(f, repeticoes=20):
    tempos = []
    for _ in range(repeticoes):
        for p in PALAVRAS_BUSCA:
            t0 = time.perf_counter()
            r = f(p)
            tempos.append((time.perf_counter() - t0) * 1000)
    return statistics.median(tempos), len(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tamanhos", type=int, nargs="+", default=[1000, 5000, 10000])
    ap.add_argument("--saida", default="resultados.csv")
    ap.add_argument("--pg", action="store_true")
    a = ap.parse_args()
    linhas = []
    for n in a.tamanhos:
        d = tempfile.mkdtemp()
        cofre = criar_cofre(os.path.join(d, "c.sse"), "bench-senha", gerar_arquivo_chave())
        store = PgStore() if a.pg else SqliteStore(os.path.join(d, "b.db"))
        cli = ClienteSSE(cofre, store)
        # baseline em claro
        claro = sqlite3.connect(":memory:")
        claro.executescript(
            "CREATE TABLE doc(id INTEGER PRIMARY KEY, txt TEXT);"
            "CREATE TABLE idx(palavra TEXT, id INTEGER);"
            "CREATE INDEX i ON idx(palavra);")
        dados = gerar(n)
        t0 = time.perf_counter()
        for tabela, campos in dados:
            cli.inserir(tabela, campos)
        t_ins = (time.perf_counter() - t0) / n * 1000
        t0 = time.perf_counter()
        for i, (tabela, campos) in enumerate(dados):
            claro.execute("INSERT INTO doc VALUES (?,?)", (i, str(campos)))
            ws = {w for v in [tabela] + list(campos.values()) for w in crypto.palavras(v)}
            claro.executemany("INSERT INTO idx VALUES (?,?)", [(w, i) for w in ws])
        t_ins_claro = (time.perf_counter() - t0) / n * 1000
        t_busca, _ = medir_busca(cli.buscar)
        t_busca_claro, _ = medir_busca(lambda p: claro.execute(
            "SELECT d.txt FROM idx x JOIN doc d ON d.id = x.id WHERE x.palavra=?", (p,)).fetchall())
        c = store.contagens()
        tam = None
        if not a.pg:
            tam = sum(len(x[1]) for x in store.conn.execute("SELECT id, ciphertext FROM registros")) \
                + sum(len(x[0]) + len(x[1]) for x in store.conn.execute("SELECT label, valor FROM indice"))
        linhas.append({"registros": n, "ins_cifrado_ms": round(t_ins, 3),
                       "ins_claro_ms": round(t_ins_claro, 3),
                       "busca_cifrada_ms_mediana": round(t_busca, 3),
                       "busca_claro_ms_mediana": round(t_busca_claro, 3),
                       "entradas_indice": c["entradas_indice"], "bytes_cifrados": tam})
        print(linhas[-1])
    with open(a.saida, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0]))
        w.writeheader()
        w.writerows(linhas)
    print(f"salvo em {a.saida}")


if __name__ == "__main__":
    main()
