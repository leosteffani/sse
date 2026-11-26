"""Visão do SERVIDOR (atacante curioso): lê o banco SEM nenhuma chave.
Este arquivo NÃO importa o cofre nem as funções de chave: só a camada do banco.

Rodar (qualquer computador; usa o papel sse_view, somente leitura):
    streamlit run server_view.py --server.port 8502
"""
import os

import pandas as pd
import streamlit as st

from sse.store import PgStore

st.set_page_config(page_title="Visão do servidor", layout="wide")
st.title("O que o servidor enxerga (sem chaves)")

with st.sidebar:
    host = st.text_input("Host", os.environ.get("PGHOST", "localhost"))
    banco = st.text_input("Banco", os.environ.get("PGDATABASE", "sse_db"))
    usuario = st.text_input("Usuário (somente leitura)", os.environ.get("PGUSER", "sse_view"))
    senha = st.text_input("Senha", type="password", value=os.environ.get("PGPASSWORD", ""))
    sslmode = st.selectbox("sslmode", ["verify-full", "verify-ca", "require"])
    cert = st.text_input("Certificado da CA", os.environ.get("PGSSLROOTCERT", "certs/ca.crt"))
    limite = st.slider("Linhas por tabela", 5, 100, 20)
    st.button("Atualizar")

try:
    args = dict(host=host, dbname=banco, user=usuario, password=senha, sslmode=sslmode,
                connect_timeout=10)
    if cert:
        args["sslrootcert"] = cert
    store = PgStore(**args)
    c = store.contagens()
except Exception as e:
    st.error(f"Sem conexão: {e}")
    st.stop()

col1, col2, col3 = st.columns(3)
col1.metric("Registros cifrados", c["registros"])
col2.metric("Entradas do índice", c["entradas_indice"])
col3.metric("Rótulos distintos", c["rotulos_distintos"])
if c["entradas_indice"] == c["rotulos_distintos"]:
    st.success("Nenhum rótulo se repete: o índice em repouso não revela frequência por palavra.")
else:
    st.warning("Há rótulos repetidos (inesperado).")

st.subheader("Tabela registros")
st.dataframe(pd.DataFrame([
    {"id (hex)": rid.hex(), "bytes": len(ct), "ciphertext (hex, início)": ct.hex()[:64] + "…"}
    for rid, ct in store.amostra_registros(limite)
]))
st.subheader("Tabela indice")
st.dataframe(pd.DataFrame([
    {"label (hex)": l.hex(), "valor (hex, início)": v.hex()[:48] + "…", "bytes do valor": len(v)}
    for l, v in store.amostra_indice(limite)
]))
st.caption("Nada aqui é legível: sem as chaves (que só existem na memória do cliente) "
           "não há texto, palavra, tipo de registro nem relação entre registros.")
