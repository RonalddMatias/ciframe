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
