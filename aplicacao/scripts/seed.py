"""Popula o banco com dados sintéticos.
Uso (PostgreSQL, variáveis PG* definidas):
    SSE_SENHA=... python -m scripts.seed 300 --cofre cofre.sse --chave chave.bin
Sem --pg usa SQLite local (arquivo demo.db) apenas para experimentar.
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sse.client import ClienteSSE  # noqa: E402
from sse.store import PgStore, SqliteStore  # noqa: E402
from sse.sintetico import gerar  # noqa: E402
from sse.vault import abrir_cofre, criar_cofre, gerar_arquivo_chave  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("n", type=int)
    ap.add_argument("--cofre", default="cofre.sse")
    ap.add_argument("--chave", default="chave.bin")
    ap.add_argument("--pg", action="store_true", help="usar PostgreSQL (variáveis PG*)")
    a = ap.parse_args()
    senha = os.environ.get("SSE_SENHA") or input("Senha: ")
    if not os.path.exists(a.chave):
        gerar_arquivo_chave(a.chave)
        print(f"arquivo de chave criado: {a.chave} (guarde em local seguro)")
    chave = open(a.chave, "rb").read()
    cofre = abrir_cofre(a.cofre, senha, chave) if os.path.exists(a.cofre) else criar_cofre(a.cofre, senha, chave)
    store = PgStore() if a.pg else SqliteStore("demo.db")
    cli = ClienteSSE(cofre, store)
    t0 = time.perf_counter()
    for tabela, campos in gerar(a.n):
        cli.inserir(tabela, campos)
    dt = time.perf_counter() - t0
    print(f"{a.n} registros inseridos em {dt:.2f}s ({1000 * dt / a.n:.1f} ms/registro)")
    print(store.contagens())


if __name__ == "__main__":
    main()
