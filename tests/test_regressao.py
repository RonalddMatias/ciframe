# coding: utf-8
from collections import defaultdict

import pytest

import main
from matching import casa, prepara_alvo
from conftest import corpo, ids_da_api

SEQUENCIAS = list(enumerate(main.catalogo.SEQUENCIAS_ORIGINAIS, start=1))
CONTAGENS_DA_TAG = [199, 296, 4, 5, 7, 3]


@pytest.fixture(scope='module')
def musicas_por_genero():
    por_genero = defaultdict(set)
    for musica in main.musicas.values():
        por_genero[musica.genero].add(musica.id_unico_musica)
    return por_genero


@pytest.fixture(scope='module')
def calculado():
    """Resultado da regra (a)+(b) em tempo real, uma vez por sequência."""
    resultado = {}
    for id_seq, (_, acordes) in SEQUENCIAS:
        alvo_norm, alvo_set = prepara_alvo(acordes)
        resultado[id_seq] = {
            musica.id_unico_musica
            for musica in main.musicas.values()
            if casa(musica.cifra_norm, musica.acordes_norm, alvo_norm, alvo_set)
        }
    return resultado


def ids_da_tag(indice_tag):
    return {
        musica.id_unico_musica
        for musica in main.musicas.values()
        if str(indice_tag) in musica.seqs_famosas
    }


def test_contagens_da_tag_sao_o_oraculo_esperado():
    assert [len(ids_da_tag(indice)) for indice in range(6)] == CONTAGENS_DA_TAG


def test_conjunto_por_sequencia_igual_a_tag(cliente, calculado):
    for id_seq, (_, acordes) in SEQUENCIAS:
        tag = ids_da_tag(id_seq - 1)
        assert calculado[id_seq] == tag, 'regra diverge da tag em %s' % (acordes,)

        pela_api = ids_da_api(cliente, id_seq)
        assert pela_api == tag, 'endpoint diverge da tag em %s' % (acordes,)


def test_conjunto_por_sequencia_e_genero_igual_a_tag(calculado, musicas_por_genero):
    for id_seq, (_, acordes) in SEQUENCIAS:
        tag = ids_da_tag(id_seq - 1)
        generos_com_tag = {
            musica.genero
            for musica in main.musicas.values()
            if str(id_seq - 1) in musica.seqs_famosas
        }

        for genero in generos_com_tag:
            esperado = tag & musicas_por_genero[genero]
            obtido = calculado[id_seq] & musicas_por_genero[genero]
            assert obtido == esperado, '%s / %s diverge' % (acordes, genero)

        # Não pode sobrar resultado em gênero que a tag não marca.
        for genero, ids_do_genero in musicas_por_genero.items():
            if genero not in generos_com_tag:
                assert not (calculado[id_seq] & ids_do_genero)


def test_endpoint_com_filtro_de_genero(cliente, musicas_por_genero):
    for id_seq, (_, acordes) in SEQUENCIAS:
        tag = ids_da_tag(id_seq - 1)
        generos_com_tag = {
            musica.genero
            for musica in main.musicas.values()
            if str(id_seq - 1) in musica.seqs_famosas
        }
        # Gênero com mais músicas marcadas: exercita o filtro de verdade.
        genero = max(generos_com_tag, key=lambda g: len(tag & musicas_por_genero[g]))

        obtidos = ids_da_api(cliente, id_seq, genero)
        assert obtidos == tag & musicas_por_genero[genero], acordes


def test_contagens_de_pagina_em_bmgda(cliente):
    tamanhos = []
    for pagina in (1, 2, 3):
        itens = corpo(cliente.get(
            '/similares?sequencia_id=1&pagina=%d' % pagina))
        tamanhos.append(len(itens))
    assert tamanhos == [100, 99, 0]
