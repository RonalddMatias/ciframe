# coding: utf-8
import pytest

import main
from matching import casa, prepara_alvo
from conftest import corpo, ids_da_api

SEQUENCIA_NOVA = ['Am', 'F', 'C', 'G']


def test_get_sequencias_traz_os_seis_seeds(cliente):
    resposta = cliente.get('/sequencias')
    assert resposta.status_code == 200

    sequencias = corpo(resposta)
    assert [sequencia['id'] for sequencia in sequencias] == [1, 2, 3, 4, 5, 6]
    assert [sequencia['acordes'] for sequencia in sequencias] == [
        acordes for _, acordes in main.catalogo.SEQUENCIAS_ORIGINAIS
    ]
    for sequencia in sequencias:
        assert set(sequencia) == {'id', 'nome', 'acordes', 'criado_em'}


def test_post_valido_cria_e_aparece_no_get(cliente):
    resposta = cliente.post('/sequencias', json={'acordes': SEQUENCIA_NOVA})
    assert resposta.status_code == 201

    criada = corpo(resposta)
    assert criada['id'] == 7
    assert criada['acordes'] == SEQUENCIA_NOVA
    assert criada['nome'] == 'Sequência de Am - F - C - G'

    sequencias = corpo(cliente.get('/sequencias'))
    assert sequencias[-1] == criada


def test_post_com_nome_usa_o_nome_informado(cliente):
    resposta = cliente.post(
        '/sequencias', json={'nome': '  Minha progressão  ', 'acordes': ['Am', 'F']})
    assert resposta.status_code == 201
    assert corpo(resposta)['nome'] == 'Minha progressão'


def test_post_duplicado_devolve_409_com_id_existente(cliente):
    primeira = corpo(cliente.post('/sequencias', json={'acordes': ['Am', 'F', 'C', 'G']}))

    resposta = cliente.post('/sequencias', json={'acordes': ['am', 'f', 'c', 'g']})
    assert resposta.status_code == 409
    assert corpo(resposta) == {'erro': 'sequencia ja cadastrada', 'id': primeira['id']}


@pytest.mark.parametrize('corpo_bruto', ['[]', '"texto"', 'null', '1'])
def test_post_com_corpo_nao_objeto_devolve_400(cliente, corpo_bruto):
    resposta = cliente.post(
        '/sequencias', data=corpo_bruto, content_type='application/json')
    assert resposta.status_code == 400
    assert 'erro' in corpo(resposta)


@pytest.mark.parametrize('payload', [
    {'acordes': []},
    {'acordes': ['A'] * 13},
    {'acordes': ['']},
    {'acordes': ['   ']},
    {'acordes': ['A;B']},
    {'acordes': ['A,B']},
    {'acordes': ['A' * 21]},
    {'acordes': ['A', 1]},
    {'acordes': 'A,B'},
    {'nome': 1, 'acordes': ['A']},
    {},
])
def test_post_invalido_devolve_400(cliente, payload):
    resposta = cliente.post('/sequencias', json=payload)
    assert resposta.status_code == 400
    assert 'erro' in corpo(resposta)


def test_busca_por_sequencia_nova(cliente):
    criada = corpo(cliente.post('/sequencias', json={'acordes': SEQUENCIA_NOVA}))

    obtidos = ids_da_api(cliente, criada['id'])

    alvo_norm, alvo_set = prepara_alvo(SEQUENCIA_NOVA)
    esperados = {
        musica.id_unico_musica
        for musica in main.musicas.values()
        if casa(musica.cifra_norm, musica.acordes_norm, alvo_norm, alvo_set)
    }
    assert obtidos == esperados
    assert obtidos  # a sequência de teste precisa casar com alguma música


def test_sequencia_id_inexistente_devolve_404(cliente):
    resposta = cliente.get('/similares?sequencia_id=999')
    assert resposta.status_code == 404
    assert 'erro' in corpo(resposta)


def test_sequencia_id_nao_inteiro_devolve_400(cliente):
    resposta = cliente.get('/similares?sequencia_id=abc')
    assert resposta.status_code == 400
    assert 'erro' in corpo(resposta)


@pytest.mark.parametrize('sequencia_id', ['0', '-1', '9' * 40])
def test_sequencia_id_fora_do_intervalo_devolve_404(cliente, sequencia_id):
    # 2**63-1 é o maior INTEGER do SQLite; acima disso o binding estoura.
    resposta = cliente.get('/similares?sequencia_id=' + sequencia_id)
    assert resposta.status_code == 404
    assert 'erro' in corpo(resposta)


def test_id_unico_musica_inexistente_devolve_404(cliente):
    resposta = cliente.get('/similares?id_unico_musica=nao-existe')
    assert resposta.status_code == 404
    assert 'erro' in corpo(resposta)


def test_musica_inexistente_devolve_404(cliente):
    resposta = cliente.get('/musica/nao-existe/')
    assert resposta.status_code == 404
    assert 'erro' in corpo(resposta)


def test_musica_existente_devolve_o_dict(cliente):
    id_musica = next(iter(main.musicas))
    resposta = cliente.get('/musica/%s/' % id_musica)
    assert resposta.status_code == 200
    assert corpo(resposta)['id_unico_musica'] == id_musica


def test_search_filtra_por_genero(cliente):
    itens = corpo(cliente.get('/search?key=a&generos=Rock'))
    assert itens
    assert all(item['genero'] == 'Rock' for item in itens)


@pytest.mark.parametrize('pagina', ['abc', '1.5', '', '0', '-1'])
def test_pagina_invalida_devolve_400(cliente, pagina):
    for url in ('/similares?sequencia_id=1&pagina=' + pagina,
                '/search?key=am&pagina=' + pagina):
        resposta = cliente.get(url)
        assert resposta.status_code == 400, url
        assert 'erro' in corpo(resposta)


def test_pagina_alem_do_fim_devolve_lista_vazia(cliente):
    resposta = cliente.get('/similares?sequencia_id=1&pagina=999')
    assert resposta.status_code == 200
    assert corpo(resposta) == []


def test_post_com_nome_no_limite_e_aceito(cliente):
    resposta = cliente.post(
        '/sequencias', json={'nome': 'n' * 120, 'acordes': ['Am', 'F']})
    assert resposta.status_code == 201


def test_post_com_nome_longo_demais_devolve_400(cliente):
    resposta = cliente.post(
        '/sequencias', json={'nome': 'n' * 121, 'acordes': ['Am', 'F']})
    assert resposta.status_code == 400
    assert 'erro' in corpo(resposta)


def test_similares_por_acordes_legado_ordena_por_diferenca(cliente):
    acordes = {'Am', 'F', 'C', 'G'}
    itens = corpo(cliente.get('/similares?acordes=' + ','.join(sorted(acordes))))
    assert itens

    for item in itens:
        assert item['intersecao']
        assert set(item['intersecao']) == set(item['acordes']) & acordes
        assert set(item['diferenca']) == set(item['acordes']) - acordes

    chaves = [(len(item['diferenca']), -len(item['intersecao'])) for item in itens]
    assert chaves == sorted(chaves)


def test_similares_por_id_de_musica_nao_inclui_a_propria_musica(cliente):
    id_musica = next(iter(main.musicas))
    itens = corpo(cliente.get('/similares?id_unico_musica=' + id_musica))
    assert itens  # a música mais popular precisa ter similares

    ids = {item['id_unico_musica'] for item in itens}
    assert id_musica not in ids


def test_similares_por_sequencia_inclui_diferenca_e_intersecao(cliente):
    sequencia = corpo(cliente.get('/sequencias'))[0]
    itens = corpo(cliente.get('/similares?sequencia_id=%d' % sequencia['id']))
    assert itens

    for item in itens:
        assert set(item) >= {'diferenca', 'intersecao'}
        assert isinstance(item['diferenca'], list)
        assert isinstance(item['intersecao'], list)
        assert item['diferenca'] == sorted(item['diferenca'])
        assert item['intersecao'] == sorted(item['intersecao'])
        assert set(item['intersecao']) <= set(sequencia['acordes'])


def test_similares_sem_parametros_devolve_lista_vazia(cliente):
    resposta = cliente.get('/similares')
    assert resposta.status_code == 200
    assert corpo(resposta) == []


def test_respostas_continuam_sendo_json_dumps_como_string(cliente):
    for url in ('/sequencias', '/similares?sequencia_id=1'):
        resposta = cliente.get(url)
        assert resposta.mimetype == 'text/html'
        assert isinstance(resposta.data, bytes)


def test_musicas_nao_expoe_campos_derivados_do_matching(cliente):
    musicas = corpo(cliente.get('/musicas'))
    assert 'cifra_norm' not in musicas[0]
    assert 'acordes_norm' not in musicas[0]
