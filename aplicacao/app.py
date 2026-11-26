"""Aplicação cliente (lado CONFIÁVEL): cria registros e busca por palavra-chave
sobre uma base PostgreSQL cifrada. Chaves só em memória (st.session_state).

Rodar (no computador cliente):
    python -m streamlit run app.py --server.address 127.0.0.1
"""
import os
import time

import pandas as pd
import streamlit as st

from sse.client import ClienteSSE, ResultadoIncompleto
from sse.crypto import ErroIntegridade
from sse.entidades import ENTIDADES
from sse.store import ErroDuplicado, PgStore
from sse.vault import ErroCredenciais, abrir_cofre, criar_cofre, gerar_arquivo_chave

TIMEOUT_SESSAO = 600  # segundos sem uso -> as chaves são descartadas

st.set_page_config(page_title="Busca em dados cifrados (SSE)", layout="wide")
st.title("Busca em base de dados cifrada (SSE)")


def sair(motivo=None):
    cli = st.session_state.pop("cliente", None)
    if cli is not None:
        try:
            cli.store.fechar()
        except Exception:
            pass
    st.session_state.pop("ultimo_uso", None)
    if motivo:
        st.session_state["aviso"] = motivo


def conectar(params):
    args = dict(
        host=params["host"], port=int(params["porta"]), dbname=params["banco"],
        user=params["usuario"], password=params["senha_banco"], sslmode=params["sslmode"],
        connect_timeout=10,
    )
    if params["sslrootcert"]:
        args["sslrootcert"] = params["sslrootcert"]
    return PgStore(**args)


# -------------------------------------------------------------------- sessão
if "cliente" in st.session_state:
    if time.time() - st.session_state.get("ultimo_uso", 0) > TIMEOUT_SESSAO:
        sair("Sessão encerrada por inatividade; as chaves foram descartadas da memória.")
    else:
        st.session_state["ultimo_uso"] = time.time()
if "aviso" in st.session_state:
    st.warning(st.session_state.pop("aviso"))

# ------------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("Servidor (PostgreSQL)")
    params = {
        "host": st.text_input("Host", os.environ.get("PGHOST", "localhost")),
        "porta": st.text_input("Porta", os.environ.get("PGPORT", "5432")),
        "banco": st.text_input("Banco", os.environ.get("PGDATABASE", "sse_db")),
        "usuario": st.text_input("Usuário", os.environ.get("PGUSER", "sse_app")),
        "senha_banco": st.text_input("Senha do banco", type="password",
                                     value=os.environ.get("PGPASSWORD", "")),
        "sslmode": st.selectbox("sslmode", ["verify-full", "verify-ca", "require"], index=0),
        "sslrootcert": st.text_input("Certificado da CA (ca.crt)",
                                     os.environ.get("PGSSLROOTCERT", "certs/ca.crt")),
    }
    st.header("Cofre local")
    caminho_cofre = st.text_input("Arquivo do cofre", "cofre.sse")
    if "cliente" in st.session_state:
        if st.button("Sair (descartar chaves)"):
            sair()
            st.rerun()
    if "keyfile_novo" in st.session_state:
        st.warning("Guarde o arquivo de chave agora. Sem ele (e sem a senha) os dados não podem ser recuperados.")
        st.download_button("Baixar arquivo de chave", st.session_state["keyfile_novo"],
                           file_name="chave.bin")
        if st.button("Já guardei o arquivo de chave"):
            st.session_state.pop("keyfile_novo")
            st.rerun()

# --------------------------------------------------------------------- login
if "cliente" not in st.session_state:
    if not os.path.exists(caminho_cofre):
        st.subheader("Primeiro uso: criar cofre")
        s1 = st.text_input("Senha", type="password", key="s1")
        s2 = st.text_input("Confirmar senha", type="password", key="s2")
        if st.button("Criar cofre e arquivo de chave"):
            if len(s1) < 12 or s1 != s2:
                st.error("Use uma senha de pelo menos 12 caracteres e confirme-a corretamente.")
            else:
                try:
                    chave = gerar_arquivo_chave()
                    cofre = criar_cofre(caminho_cofre, s1, chave)
                    st.session_state["cliente"] = ClienteSSE(cofre, conectar(params))
                    st.session_state["keyfile_novo"] = chave
                    st.session_state["ultimo_uso"] = time.time()
                    st.rerun()
                except Exception as e:  # erro de conexão, permissão etc.
                    st.error(f"Não foi possível criar/conectar: {e}")
    else:
        st.subheader("Entrar")
        senha = st.text_input("Senha", type="password")
        arq = st.file_uploader("Arquivo de chave", type=None)
        if st.button("Entrar"):
            if not senha or arq is None:
                st.error("Informe a senha e o arquivo de chave.")
            else:
                try:
                    cofre = abrir_cofre(caminho_cofre, senha, arq.getvalue())
                    st.session_state["cliente"] = ClienteSSE(cofre, conectar(params))
                    st.session_state["ultimo_uso"] = time.time()
                    st.rerun()
                except ErroCredenciais:
                    st.error("Senha ou arquivo de chave incorretos.")
                except Exception as e:
                    st.error(f"Erro de conexão com o servidor: {e}")
    st.stop()

# ---------------------------------------------------------------- aplicação
cli: ClienteSSE = st.session_state["cliente"]
aba_criar, aba_buscar = st.tabs(["Criar registro", "Buscar"])

with aba_criar:
    tabela = st.selectbox("Tipo de registro", list(ENTIDADES),
                          format_func=lambda t: ENTIDADES[t]["rotulo"])
    ent = ENTIDADES[tabela]
    with st.form("novo_registro", clear_on_submit=True):
        valores = {}
        for campo in ent["indexados"]:
            valores[campo] = st.text_input(f"{campo}  (pesquisável)", key=f"{tabela}_{campo}")
        for campo in ent["cifrados"]:
            valores[campo] = st.text_input(f"{campo}  (apenas cifrado)", key=f"{tabela}_{campo}")
        enviado = st.form_submit_button("Cifrar e gravar")
    if enviado:
        if not valores[ent["indexados"][0]].strip():
            st.error(f"Preencha ao menos o campo '{ent['indexados'][0]}'.")
        else:
            try:
                rid = cli.inserir(tabela, valores)
                st.success(f"Registro gravado de forma cifrada (id {rid[:12]}…).")
            except ErroDuplicado:
                st.error("Conflito no índice: o estado local pode estar desatualizado.")
            except Exception as e:
                st.error(f"Falha ao gravar: {e}")

with aba_buscar:
    with st.form("busca"):
        termo = st.text_input("Palavra(s) a buscar (várias palavras = todas devem casar)")
        buscar = st.form_submit_button("Buscar")
    if buscar and termo.strip():
        try:
            achados = cli.buscar(termo)
            st.write(f"{len(achados)} registro(s) encontrado(s) e decifrado(s) localmente.")
            for r in achados:
                ent = ENTIDADES[r["tabela"]]
                titulo = r.get(ent["indexados"][0], "")
                with st.expander(f"{ent['rotulo']} · {titulo} · id {r['id'][:8]}"):
                    st.json({k: v for k, v in r.items() if k not in ("tabela", "id")})
            with st.expander("O que o servidor recebeu nesta busca"):
                if cli.ultima_busca:
                    linhas = [
                        {"consulta": i + 1, "rótulo (hex, 16 primeiros bytes)": r.hex()[:32] + "…"}
                        for i, b in enumerate(cli.ultima_busca) for r in b["rotulos"]
                    ]
                    st.dataframe(pd.DataFrame(linhas))
                    st.caption("Só rótulos pseudoaleatórios: o servidor não recebe a palavra "
                               "nem a chave da palavra.")
                else:
                    st.caption("Nenhuma consulta ao índice (palavra sem ocorrências).")
        except ResultadoIncompleto as e:
            st.error(f"Resultado incompleto: o servidor omitiu dados. {e}")
        except ErroIntegridade as e:
            st.error(f"Integridade violada: {e}")
        except Exception as e:
            st.error(f"Falha na busca: {e}")
