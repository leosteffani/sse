"""Cofre local do cliente: guarda o salt e o estado (contador por palavra),
cifrado com AES-GCM (K_state). O arquivo de chave fica separado do cofre."""
import json
import os
import secrets
from dataclasses import dataclass, field

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .crypto import NONCE_LEN, Chaves, derivar_chaves

MAGIC = b"SSE1"
SALT_LEN = 16


class ErroCredenciais(Exception):
    """Senha ou arquivo de chave incorretos (ou cofre corrompido)."""


@dataclass
class Cofre:
    caminho: str
    salt: bytes
    chaves: Chaves
    contagens: dict = field(default_factory=dict)

    def salvar(self) -> None:
        nonce = os.urandom(NONCE_LEN)
        blob = json.dumps(self.contagens, sort_keys=True).encode("utf-8")
        ct = AESGCM(self.chaves.k_state).encrypt(nonce, blob, MAGIC + self.salt)
        tmp = self.caminho + ".tmp"
        with open(tmp, "wb") as f:
            f.write(MAGIC + self.salt + nonce + ct)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.caminho)  # troca atômica


def gerar_arquivo_chave(caminho: str = None) -> bytes:
    chave = secrets.token_bytes(32)
    if caminho:
        fd = os.open(caminho, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(chave)
    return chave


def criar_cofre(caminho: str, senha: str, arquivo_chave: bytes) -> Cofre:
    if os.path.exists(caminho):
        raise FileExistsError(caminho)
    salt = secrets.token_bytes(SALT_LEN)
    cofre = Cofre(caminho, salt, derivar_chaves(senha, salt, arquivo_chave))
    cofre.salvar()
    return cofre


def abrir_cofre(caminho: str, senha: str, arquivo_chave: bytes) -> Cofre:
    with open(caminho, "rb") as f:
        dados = f.read()
    if dados[:4] != MAGIC:
        raise ErroCredenciais("arquivo de cofre inválido")
    salt = dados[4 : 4 + SALT_LEN]
    nonce = dados[4 + SALT_LEN : 4 + SALT_LEN + NONCE_LEN]
    ct = dados[4 + SALT_LEN + NONCE_LEN :]
    chaves = derivar_chaves(senha, salt, arquivo_chave)
    try:
        blob = AESGCM(chaves.k_state).decrypt(nonce, ct, MAGIC + salt)
    except InvalidTag as e:
        raise ErroCredenciais("senha ou arquivo de chave incorretos") from e
    return Cofre(caminho, salt, chaves, json.loads(blob.decode("utf-8")))
