"""Primitivas criptográficas do esquema SSE (busca em dados cifrados).

Resumo do esquema (ver relatório, Seção 2.3):
  K_w      = HMAC(K_idx, w)                      chave própria de cada palavra
  rótulo   = HMAC(K_w, 'L' || c)                 c = contador da palavra (começa em 1)
  valor    = AES-GCM(HMAC(K_w, 'V'), id; AAD = rótulo)
  registro = AES-256-GCM(K_doc, JSON preenchido; AAD = id do registro)
O servidor só enxerga rótulos, valores e textos cifrados.
"""
import hashlib
import hmac
import json
import os
import re
import secrets
import struct
import unicodedata
from dataclasses import dataclass

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

NONCE_LEN = 12
ID_LEN = 16
LABEL_LEN = 32
TAG_LEN = 16
VALOR_LEN = NONCE_LEN + ID_LEN + TAG_LEN  # tamanho fixo de um valor do índice
FAIXA_MIN = 256  # menor tamanho de registro (bytes) após o preenchimento
SCRYPT_N = 2 ** 15
SCRYPT_R = 8
SCRYPT_P = 1


class ErroIntegridade(Exception):
    """Dado adulterado, trocado ou decifrado com chave errada."""


@dataclass(frozen=True)
class Chaves:
    k_doc: bytes
    k_idx: bytes
    k_state: bytes


# ---------------------------------------------------------------- normalização
def normalizar(texto) -> str:
    t = unicodedata.normalize("NFD", str(texto).lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def palavras(texto) -> list:
    """Palavras normalizadas (minúsculas, sem acento), sem repetição, em ordem."""
    vistas, saida = set(), []
    for w in re.split(r"[^a-z0-9]+", normalizar(texto)):
        if len(w) >= 2 and w not in vistas:
            vistas.add(w)
            saida.append(w)
    return saida


# ----------------------------------------------------------------------- chaves
def derivar_chaves(senha: str, salt: bytes, arquivo_chave: bytes) -> Chaves:
    """Senha (scrypt) + arquivo de chave aleatório (dois fatores) -> chaves
    independentes, por separação de domínio com HKDF."""
    if len(arquivo_chave) < 32:
        raise ValueError("arquivo de chave inválido (mínimo de 32 bytes)")
    mestra = Scrypt(salt=salt, length=32, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P).derive(
        senha.encode("utf-8")
    )

    def sub(info: bytes) -> bytes:
        return HKDF(
            algorithm=hashes.SHA256(), length=32, salt=arquivo_chave, info=info
        ).derive(mestra)

    return Chaves(sub(b"sse/doc/v1"), sub(b"sse/idx/v1"), sub(b"sse/state/v1"))


def _hmac(chave: bytes, msg: bytes) -> bytes:
    return hmac.new(chave, msg, hashlib.sha256).digest()


def chave_palavra(k_idx: bytes, palavra: str) -> bytes:
    return _hmac(k_idx, palavra.encode("utf-8"))


def rotulo(k_w: bytes, c: int) -> bytes:
    return _hmac(k_w, b"L" + struct.pack(">I", c))


# ------------------------------------------------------------ entradas do índice
def criar_entrada(k_idx: bytes, palavra: str, c: int, registro_id: bytes):
    k_w = chave_palavra(k_idx, palavra)
    lab = rotulo(k_w, c)
    nonce = os.urandom(NONCE_LEN)
    val = nonce + AESGCM(_hmac(k_w, b"V")).encrypt(nonce, registro_id, lab)
    return lab, val


def abrir_valor(k_w: bytes, lab: bytes, valor: bytes) -> bytes:
    try:
        return AESGCM(_hmac(k_w, b"V")).decrypt(valor[:NONCE_LEN], valor[NONCE_LEN:], lab)
    except InvalidTag as e:
        raise ErroIntegridade("entrada do índice adulterada ou trocada") from e


def entradas_de_preenchimento(qtd_reais: int, bloco: int):
    """Pares aleatórios para que o número de entradas por inserção seja múltiplo
    de `bloco` (esconde o número exato de palavras distintas do registro)."""
    faltam = (-qtd_reais) % bloco
    return [(os.urandom(LABEL_LEN), os.urandom(VALOR_LEN)) for _ in range(faltam)]


# ------------------------------------------------------------------- registros
def _proxima_faixa(n: int) -> int:
    p = FAIXA_MIN
    while p < n:
        p *= 2
    return p


def cifrar_registro(k_doc: bytes, registro_id: bytes, dados: dict) -> bytes:
    pt = json.dumps(dados, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    enquadrado = struct.pack(">I", len(pt)) + pt
    preenchido = enquadrado.ljust(_proxima_faixa(len(enquadrado)), b"\x00")
    nonce = os.urandom(NONCE_LEN)
    return nonce + AESGCM(k_doc).encrypt(nonce, preenchido, registro_id)


def decifrar_registro(k_doc: bytes, registro_id: bytes, blob: bytes) -> dict:
    try:
        pt = AESGCM(k_doc).decrypt(blob[:NONCE_LEN], blob[NONCE_LEN:], registro_id)
    except InvalidTag as e:
        raise ErroIntegridade("registro adulterado, trocado ou chave incorreta") from e
    (tam,) = struct.unpack(">I", pt[:4])
    return json.loads(pt[4 : 4 + tam].decode("utf-8"))


def novo_id() -> bytes:
    return secrets.token_bytes(ID_LEN)
