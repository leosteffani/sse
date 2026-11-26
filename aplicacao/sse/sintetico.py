"""Gerador de dados SINTÉTICOS (nada real): produtos, clientes e franquias."""
import random

CIDADES = ["Joinville", "Florianópolis", "Blumenau", "Itajaí", "Chapecó", "Criciúma",
           "Lages", "Balneário Camboriú", "São José", "Jaraguá do Sul"]
CATEGORIAS = ["ferramentas", "eletrica", "hidraulica", "pintura", "fixacao", "seguranca",
              "jardinagem", "iluminacao"]
PRODUTOS = ["Furadeira", "Parafusadeira", "Serra Circular", "Esmerilhadeira", "Martelete",
            "Lixadeira", "Chave Inglesa", "Alicate", "Trena", "Nível a Laser", "Compressor",
            "Soldador", "Capacete", "Luva", "Lanterna", "Cortador de Grama"]
ADJ = ["Industrial", "Profissional", "Compacto", "Reforçado", "Bivolt", "Portátil", "Premium"]
USOS = ["uso profissional", "uso residencial", "alta potência", "baixo consumo",
        "obra pesada", "acabamento fino", "uso intenso"]
RAMOS = ["metalurgia", "construção", "varejo", "logística", "alimentos", "agronegócio",
         "têxtil", "tecnologia", "automotivo"]
EMPRESAS = ["Aurora", "Horizonte", "Vale Verde", "Atlântico", "Pioneira", "Serra Azul",
            "Delta", "Estrela do Sul", "Nova Era", "Cascata"]
TIPOS = ["Metalúrgica", "Construtora", "Distribuidora", "Comercial", "Indústria", "Agro"]
BAIRROS = ["Centro", "Norte", "Sul", "Praça", "Shopping", "Marginal", "Industrial", "Beira-Mar"]
NOMES = ["Ana Souza", "Bruno Lima", "Carla Dias", "Diego Rocha", "Elisa Prado", "Fábio Nunes"]


def gerar(n: int, semente: int = 42):
    """Devolve n tuplas (tabela, campos), 1/3 de cada entidade, em ordem embaralhada."""
    rnd = random.Random(semente)
    itens = []
    for i in range(n):
        t = i % 3
        if t == 0:
            itens.append(("produtos", {
                "nome": f"{rnd.choice(PRODUTOS)} {rnd.choice(ADJ)}",
                "categoria": rnd.choice(CATEGORIAS),
                "descricao": rnd.choice(USOS),
                "codigo_interno": str(1000 + i), "preco": str(rnd.randint(20, 5000)),
                "estoque": str(rnd.randint(0, 300))}))
        elif t == 1:
            itens.append(("clientes", {
                "razao_social": f"{rnd.choice(TIPOS)} {rnd.choice(EMPRESAS)}",
                "ramo": rnd.choice(RAMOS), "cidade": rnd.choice(CIDADES),
                "codigo_interno": str(2000 + i), "contato_ficticio": rnd.choice(NOMES),
                "observacoes": rnd.choice(["pagamento em 30 dias", "cliente preferencial", "novo"]),
                "franquia_atendente": str(3000 + rnd.randint(0, max(1, n // 3)))}))
        else:
            itens.append(("franquias", {
                "nome_da_loja": f"Loja {rnd.choice(BAIRROS)}", "cidade": rnd.choice(CIDADES),
                "codigo_interno": str(3000 + i), "responsavel_ficticio": rnd.choice(NOMES),
                "endereco": f"Rua {rnd.choice(EMPRESAS)}, {rnd.randint(1, 999)}",
                "produtos_vendidos": ",".join(str(1000 + rnd.randint(0, max(1, n // 3)))
                                              for _ in range(3))}))
    rnd.shuffle(itens)
    return itens
