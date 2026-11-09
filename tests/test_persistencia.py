# coding: utf-8
import sqlite3

import pytest

import catalogo


def test_nova_sequencia_visivel_em_outra_conexao(tmp_path, monkeypatch):
    caminho = tmp_path / 'catalogo.db'
    monkeypatch.setenv('CIFRAME_DB', str(caminho))
    catalogo.init_db()

    criada = catalogo.criar('Persistida', ['Am', 'F', 'C', 'G'])
    assert criada['id'] == 7

    # Conexão nova no mesmo arquivo simula outro processo/worker.
    conexao = sqlite3.connect(str(caminho))
    try:
        linha = conexao.execute(
            'SELECT nome, acordes, chave FROM sequencias WHERE id = ?',
            (criada['id'],),
        ).fetchone()
    finally:
        conexao.close()

    assert linha is not None
    assert linha[0] == 'Persistida'
    assert linha[2] == 'am;f;c;g'


def test_criar_duplicada_levanta_com_id_existente(tmp_path, monkeypatch):
    monkeypatch.setenv('CIFRAME_DB', str(tmp_path / 'catalogo.db'))
    catalogo.init_db()

    primeira = catalogo.criar('Minha', ['Am', 'F', 'C', 'G'])
    with pytest.raises(catalogo.SequenciaDuplicada) as excinfo:
        # A chave ignora grafia e espaços, então a UNIQUE barra a segunda.
        catalogo.criar('Outra', [' am', 'f ', 'C', 'g'])

    assert excinfo.value.id == primeira['id']
    assert len(catalogo.listar()) == 7


def test_init_db_repetido_nao_duplica_o_seed(tmp_path, monkeypatch):
    caminho = tmp_path / 'catalogo.db'
    monkeypatch.setenv('CIFRAME_DB', str(caminho))

    catalogo.init_db()
    catalogo.init_db()
    catalogo.init_db()

    sequencias = catalogo.listar()
    assert len(sequencias) == 6
    assert [sequencia['id'] for sequencia in sequencias] == [1, 2, 3, 4, 5, 6]


def test_init_db_nao_sobrescreve_sequencia_do_usuario(tmp_path, monkeypatch):
    monkeypatch.setenv('CIFRAME_DB', str(tmp_path / 'catalogo.db'))
    catalogo.init_db()

    catalogo.criar('Minha', ['Am', 'F'])
    catalogo.init_db()

    nomes = [sequencia['nome'] for sequencia in catalogo.listar()]
    assert nomes.count('Minha') == 1
    assert len(nomes) == 7
