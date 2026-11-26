"""Entidades lógicas da aplicação (Seção 3.1 do relatório).

Campos 'indexados' geram palavras de busca (e ficam cifrados no registro).
Campos 'cifrados' ficam só no conteúdo cifrado, sem índice.
As relações entre entidades são referências por código interno, dentro do
conteúdo cifrado: o servidor não vê as relações.
"""

ENTIDADES = {
    "produtos": {
        "rotulo": "Produto",
        "indexados": ["nome", "categoria", "descricao"],
        "cifrados": ["codigo_interno", "preco", "estoque"],
    },
    "clientes": {
        "rotulo": "Cliente (empresa)",
        "indexados": ["razao_social", "ramo", "cidade"],
        "cifrados": ["codigo_interno", "contato_ficticio", "observacoes", "franquia_atendente"],
    },
    "franquias": {
        "rotulo": "Franquia (loja)",
        "indexados": ["nome_da_loja", "cidade"],
        "cifrados": ["codigo_interno", "responsavel_ficticio", "endereco", "produtos_vendidos"],
    },
}
