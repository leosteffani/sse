"""Cliente SSE (lado confiável): cifra, gera rótulos, busca e decifra.

Construção (relatório, Seção 2.3): índice invertido dinâmico com contador por
palavra mantido no cliente. Na busca, o cliente envia os rótulos L(w,1..n) e
nunca a chave K_w, o que dá forward privacy e permite checar a completude.
"""
import random

from . import crypto
from .crypto import ErroIntegridade  # noqa: F401  (reexportado)
from .entidades import ENTIDADES
from .vault import Cofre


class ResultadoIncompleto(Exception):
    """O servidor não devolveu todas as entradas esperadas para a palavra."""


class ClienteSSE:
    def __init__(self, cofre: Cofre, store, bloco_entradas: int = 8):
        self.cofre = cofre
        self.store = store
        self.bloco = bloco_entradas
        self.ultima_busca = []  # o que foi enviado ao servidor (para demonstração)

    # -------------------------------------------------------------- inserção
    def inserir(self, tabela: str, campos: dict) -> str:
        if tabela not in ENTIDADES:
            raise ValueError(f"tabela desconhecida: {tabela}")
        ent = ENTIDADES[tabela]
        k = self.cofre.chaves
        registro_id = crypto.novo_id()
        dados = {"tabela": tabela, **{c: str(v) for c, v in campos.items()}}
        ct = crypto.cifrar_registro(k.k_doc, registro_id, dados)

        # o nome da tabela lógica também é uma palavra de busca
        textos = [tabela] + [campos.get(c, "") for c in ent["indexados"]]
        todas = []
        for t in textos:
            for w in crypto.palavras(t):
                if w not in todas:
                    todas.append(w)

        novas = dict(self.cofre.contagens)
        entradas = []
        for w in todas:
            novas[w] = novas.get(w, 0) + 1
            entradas.append(crypto.criar_entrada(k.k_idx, w, novas[w], registro_id))
        entradas += crypto.entradas_de_preenchimento(len(entradas), self.bloco)
        random.SystemRandom().shuffle(entradas)

        self.store.inserir(registro_id, ct, entradas)  # transação única no servidor
        self.cofre.contagens = novas  # só confirma o estado após o commit
        self.cofre.salvar()
        return registro_id.hex()

    # ----------------------------------------------------------------- busca
    def _ids_da_palavra(self, w: str) -> set:
        n = self.cofre.contagens.get(w, 0)
        if n == 0:
            return set()
        k_w = crypto.chave_palavra(self.cofre.chaves.k_idx, w)
        rotulos = [crypto.rotulo(k_w, c) for c in range(1, n + 1)]
        self.ultima_busca.append({"palavra": w, "rotulos": rotulos})
        achados = self.store.buscar_indice(rotulos)
        if set(achados) != set(rotulos):
            raise ResultadoIncompleto(
                f"esperadas {n} entradas para a palavra, recebidas {len(achados)}"
            )
        return {crypto.abrir_valor(k_w, r, achados[r]) for r in rotulos}

    def buscar(self, termo: str) -> list:
        """Busca por uma ou mais palavras (interseção, feita no cliente)."""
        self.ultima_busca = []
        ws = crypto.palavras(termo)
        if not ws:
            return []
        ids = None
        for w in ws:
            achados = self._ids_da_palavra(w)
            ids = achados if ids is None else ids & achados
            if not ids:
                return []
        cts = self.store.obter_registros(sorted(ids))
        if set(cts) != ids:
            raise ResultadoIncompleto("registro referenciado pelo índice não foi devolvido")
        saida = []
        for rid in sorted(ids):
            dados = crypto.decifrar_registro(self.cofre.chaves.k_doc, rid, cts[rid])
            saida.append({"id": rid.hex(), **dados})
        return saida
