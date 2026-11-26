"""Testes de validação (relatório, Seção 3.6). Rodar: python -m unittest -v

Usam SqliteStore (mesma interface do PgStore) para rodar sem banco.
Há um teste de integração com PostgreSQL, ativado com SSE_TEST_PG=1.
"""
import os
import tempfile
import unittest

from sse import crypto
from sse.client import ClienteSSE, ResultadoIncompleto
from sse.crypto import ErroIntegridade
from sse.store import PgStore, SqliteStore
from sse.vault import ErroCredenciais, abrir_cofre, criar_cofre, gerar_arquivo_chave

SENHA = "senha-de-teste-forte"


def novo_cliente(store=None, bloco=8):
    d = tempfile.mkdtemp()
    chave = gerar_arquivo_chave()
    cofre = criar_cofre(os.path.join(d, "cofre.sse"), SENHA, chave)
    return ClienteSSE(cofre, store or SqliteStore(), bloco), chave


def popular(c):
    ids = {}
    ids["r1"] = c.inserir(
        "produtos",
        {"nome": "Furadeira Industrial", "categoria": "ferramentas",
         "descricao": "uso profissional", "codigo_interno": "1001", "preco": "2000", "estoque": "15"},
    )
    ids["r2"] = c.inserir(
        "clientes",
        {"razao_social": "Metalúrgica Aurora", "ramo": "metalurgia", "cidade": "Joinville",
         "codigo_interno": "2001"},
    )
    ids["r3"] = c.inserir(
        "franquias",
        {"nome_da_loja": "Loja Centro", "cidade": "Joinville", "codigo_interno": "3001"},
    )
    return ids


class TestFuncional(unittest.TestCase):
    def test_busca_basica_e_sem_acento(self):
        c, _ = novo_cliente()
        ids = popular(c)
        achados = {r["id"] for r in c.buscar("joinville")}
        self.assertEqual(achados, {ids["r2"], ids["r3"]})
        self.assertEqual({r["id"] for r in c.buscar("METALURGICA")}, {ids["r2"]})
        self.assertEqual({r["id"] for r in c.buscar("metalúrgica aurora")}, {ids["r2"]})
        self.assertEqual(c.buscar("inexistente"), [])

    def test_busca_pelo_tipo_da_tabela_logica(self):
        c, _ = novo_cliente()
        ids = popular(c)
        self.assertEqual({r["id"] for r in c.buscar("franquias")}, {ids["r3"]})

    def test_campos_cifrados_nao_sao_pesquisaveis(self):
        c, _ = novo_cliente()
        popular(c)
        self.assertEqual(c.buscar("2000"), [])  # preço não é indexado
        rec = c.buscar("furadeira")[0]
        self.assertEqual(rec["preco"], "2000")  # mas volta decifrado

    def test_cofre_senha_ou_chave_erradas(self):
        c, chave = novo_cliente()
        caminho = c.cofre.caminho
        abrir_cofre(caminho, SENHA, chave)  # ok
        with self.assertRaises(ErroCredenciais):
            abrir_cofre(caminho, "outra-senha", chave)
        with self.assertRaises(ErroCredenciais):
            abrir_cofre(caminho, SENHA, gerar_arquivo_chave())

    def test_estado_persiste(self):
        c, chave = novo_cliente()
        popular(c)
        cofre2 = abrir_cofre(c.cofre.caminho, SENHA, chave)
        c2 = ClienteSSE(cofre2, c.store)
        self.assertEqual(len(c2.buscar("joinville")), 2)


class TestSeguranca(unittest.TestCase):
    def test_T1_adulteracao_de_registro(self):
        c, _ = novo_cliente()
        popular(c)
        rid, ct = c.store.amostra_registros(1)[0]
        ruim = bytearray(ct)
        ruim[20] ^= 1
        c.store.conn.execute("UPDATE registros SET ciphertext=? WHERE id=?", (bytes(ruim), rid))
        with self.assertRaises(ErroIntegridade):
            for p in ("produtos", "clientes", "franquias"):
                c.buscar(p)  # um deles devolve o registro adulterado

    def test_T2_troca_de_registros(self):
        c, _ = novo_cliente()
        popular(c)
        (id1, ct1), (id2, ct2) = c.store.amostra_registros(2)
        c.store.conn.execute("UPDATE registros SET ciphertext=? WHERE id=?", (ct2, id1))
        c.store.conn.execute("UPDATE registros SET ciphertext=? WHERE id=?", (ct1, id2))
        with self.assertRaises(ErroIntegridade):
            for p in ("produtos", "clientes", "franquias"):
                c.buscar(p)

    def test_T2b_troca_de_valores_do_indice(self):
        c, _ = novo_cliente()
        popular(c)
        # troca os valores de dois rótulos reais da palavra 'joinville'
        k_w = crypto.chave_palavra(c.cofre.chaves.k_idx, "joinville")
        l1, l2 = crypto.rotulo(k_w, 1), crypto.rotulo(k_w, 2)
        a = c.store.buscar_indice([l1, l2])
        c.store.conn.execute("UPDATE indice SET valor=? WHERE label=?", (a[l2], l1))
        c.store.conn.execute("UPDATE indice SET valor=? WHERE label=?", (a[l1], l2))
        with self.assertRaises(ErroIntegridade):
            c.buscar("joinville")

    def test_T3_omissao_no_indice(self):
        c, _ = novo_cliente()
        popular(c)
        k_w = crypto.chave_palavra(c.cofre.chaves.k_idx, "joinville")
        c.store.conn.execute("DELETE FROM indice WHERE label=?", (crypto.rotulo(k_w, 2),))
        with self.assertRaises(ResultadoIncompleto):
            c.buscar("joinville")

    def test_T4_forward_privacy(self):
        c, _ = novo_cliente()
        popular(c)
        c.buscar("joinville")
        enviados = {r for b in c.ultima_busca for r in b["rotulos"]}
        c.inserir("franquias", {"nome_da_loja": "Loja Norte", "cidade": "Joinville"})
        k_w = crypto.chave_palavra(c.cofre.chaves.k_idx, "joinville")
        novo = crypto.rotulo(k_w, 3)
        self.assertNotIn(novo, enviados)  # o servidor nunca recebeu esse rótulo
        self.assertEqual(len(enviados), 2)
        self.assertIn(novo, c.store.buscar_indice([novo]))  # mas ele existe no índice
        self.assertEqual(len(c.buscar("joinville")), 3)  # e a busca continua correta

    def test_T5_indice_em_repouso(self):
        c, _ = novo_cliente()
        for i in range(30):
            c.inserir("franquias", {"nome_da_loja": f"Loja {i}", "cidade": "Joinville"})
        n = c.store.contagens()
        self.assertEqual(n["entradas_indice"], n["rotulos_distintos"])  # nada se repete
        # 'joinville' aparece em 30 registros, mas o servidor não vê agrupamento
        self.assertEqual(n["entradas_indice"] % 8, 0)  # preenchimento em blocos

    def test_preenchimento_de_registros_em_faixas(self):
        c, _ = novo_cliente()
        popular(c)
        tamanhos = {len(ct) - crypto.NONCE_LEN - crypto.TAG_LEN
                    for _, ct in c.store.amostra_registros(10)}
        for t in tamanhos:
            self.assertGreaterEqual(t, crypto.FAIXA_MIN)
            self.assertEqual(t & (t - 1), 0)  # potência de 2

    def test_servidor_nao_ve_texto_em_claro(self):
        c, _ = novo_cliente()
        popular(c)
        bruto = b"".join(ct for _, ct in c.store.amostra_registros(10))
        bruto += b"".join(l + v for l, v in c.store.amostra_indice(1000))
        for termo in (b"joinville", b"Aurora", b"Furadeira", b"franquias"):
            self.assertNotIn(termo, bruto)


@unittest.skipUnless(os.environ.get("SSE_TEST_PG") == "1", "defina SSE_TEST_PG=1 e as variáveis PG*")
class TestPostgres(unittest.TestCase):
    def test_roundtrip_no_postgres(self):
        store = PgStore()  # usa PGHOST, PGUSER, PGPASSWORD, PGSSLMODE...
        c, _ = novo_cliente(store)
        ids = popular(c)
        self.assertIn(ids["r2"], {r["id"] for r in c.buscar("joinville")})


if __name__ == "__main__":
    unittest.main()
