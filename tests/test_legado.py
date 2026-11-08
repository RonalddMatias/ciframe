# coding: utf-8
from conftest import corpo


def test_grafias_do_legado_devolvem_o_mesmo_conjunto(cliente):
    sem_separador = ids_da_api_legado(cliente, 'BmGDA')
    com_virgulas = ids_da_api_legado(cliente, 'Bm,G,D,A')
    minusculas = ids_da_api_legado(cliente, 'bm,g,d,a')

    assert sem_separador == com_virgulas == minusculas
    assert len(sem_separador) == 199


def test_cgamf_passa_a_funcionar(cliente):
    # Mudança intencional: antes o dicionário literal era case-sensitive e
    # devolvia [] para 'cgamf'; agora a chave é resolvida no catálogo.
    obtidos = ids_da_api_legado(cliente, 'cgamf')
    canonicos = ids_da_api_legado(cliente, 'C,G,Am,F')

    assert obtidos == canonicos
    assert len(obtidos) == 296


def test_chave_desconhecida_devolve_lista_vazia(cliente):
    resposta = cliente.get('/similares?sequencia=nao-existe')
    assert resposta.status_code == 200
    assert corpo(resposta) == []


def ids_da_api_legado(cliente, chave):
    ids = set()
    pagina = 1
    while True:
        resposta = cliente.get(
            '/similares?sequencia=%s&pagina=%d' % (chave, pagina))
        itens = corpo(resposta)
        if not itens:
            break
        ids.update(item['id_unico_musica'] for item in itens)
        pagina += 1
    return ids
