# coding: utf-8
"""Persistência do catálogo de sequências de acordes em SQLite.

Uma única tabela ``sequencias``; as seis sequências originais entram por um seed
idempotente no boot. A conexão é aberta por operação (e fechada no ``finally``),
o que é seguro sob múltiplos workers do gunicorn.
"""
import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone

from matching import chave_de

DB_PADRAO = 'var/catalogo.db'

# Timestamp fixo do seed: mantém a primeira carga determinística.
SEED_CRIADO_EM = '2026-11-07T00:00:00+00:00'

# Ordem original do dicionário de main.py:40-45; nomes de
# data/mapeamento_sequencias_famosas.txt.
SEQUENCIAS_ORIGINAIS = [
    ('Sequência de Bm', ['Bm', 'G', 'D', 'A']),
    ('Sequência de C', ['C', 'G', 'Am', 'F']),
    ('Sequência Em', ['Em', 'G']),
    ('Sequência de C (Samba)', ['C', 'A7', 'Dm', 'G7']),
    ('Sequência de Gm', ['Gm', 'F']),
    ('Sequência de C (Samba cont.)', ['C', 'C7', 'F', 'Fm']),
]

CRIAR_TABELA = """
CREATE TABLE IF NOT EXISTS sequencias (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nome      TEXT    NOT NULL,
    acordes   TEXT    NOT NULL,   -- JSON array, grafia como digitada
    chave     TEXT    NOT NULL UNIQUE,  -- ';'.join(minúsculas)
    criado_em TEXT    NOT NULL    -- ISO-8601 UTC
)
"""


class SequenciaDuplicada(Exception):
    """A chave já existe no catálogo; carrega o id da sequência existente."""

    def __init__(self, id_existente):
        super().__init__('sequencia ja cadastrada')
        self.id = id_existente


def caminho_db():
    """Caminho do banco, lido do ambiente a cada operação (facilita testes)."""
    return os.environ.get('CIFRAME_DB', DB_PADRAO)


def conectar():
    """Abre uma conexão nova; quem chama é responsável por fechá-la."""
    caminho = caminho_db()
    diretorio = os.path.dirname(caminho)
    if diretorio:
        os.makedirs(diretorio, exist_ok=True)

    conexao = sqlite3.connect(caminho)
    conexao.row_factory = sqlite3.Row
    conexao.execute('PRAGMA journal_mode=WAL')
    conexao.execute('PRAGMA busy_timeout=5000')
    return conexao


def init_db():
    """Cria a tabela e semeia as seis originais sem duplicar nem sobrescrever."""
    with closing(conectar()) as conexao:
        conexao.execute(CRIAR_TABELA)
        for indice, (nome, acordes) in enumerate(SEQUENCIAS_ORIGINAIS, start=1):
            conexao.execute(
                'INSERT OR IGNORE INTO sequencias '
                '(id, nome, acordes, chave, criado_em) VALUES (?, ?, ?, ?, ?)',
                (indice, nome, json.dumps(acordes, ensure_ascii=False),
                 chave_de(acordes), SEED_CRIADO_EM),
            )
        conexao.commit()


def _linha_para_dict(linha):
    return {
        'id': linha['id'],
        'nome': linha['nome'],
        'acordes': json.loads(linha['acordes']),
        'criado_em': linha['criado_em'],
    }


def listar():
    """Catálogo inteiro, ordenado por id."""
    with closing(conectar()) as conexao:
        linhas = conexao.execute(
            'SELECT id, nome, acordes, criado_em FROM sequencias ORDER BY id'
        ).fetchall()
    return [_linha_para_dict(linha) for linha in linhas]


def buscar(id_sequencia):
    """Sequência pelo id, ou None."""
    with closing(conectar()) as conexao:
        linha = conexao.execute(
            'SELECT id, nome, acordes, criado_em FROM sequencias WHERE id = ?',
            (id_sequencia,),
        ).fetchone()
    return _linha_para_dict(linha) if linha is not None else None


def _buscar_por_chave(chave):
    with closing(conectar()) as conexao:
        linha = conexao.execute(
            'SELECT id, nome, acordes, criado_em FROM sequencias WHERE chave = ?',
            (chave,),
        ).fetchone()
    return _linha_para_dict(linha) if linha is not None else None


def criar(nome, acordes):
    """Insere uma sequência; em duplicata levanta SequenciaDuplicada(id)."""
    chave = chave_de(acordes)
    criado_em = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    try:
        with closing(conectar()) as conexao:
            cursor = conexao.execute(
                'INSERT INTO sequencias (nome, acordes, chave, criado_em) '
                'VALUES (?, ?, ?, ?)',
                (nome, json.dumps(acordes, ensure_ascii=False), chave, criado_em),
            )
            conexao.commit()
            id_novo = cursor.lastrowid
    except sqlite3.IntegrityError:
        existente = _buscar_por_chave(chave)
        if existente is None:
            raise
        raise SequenciaDuplicada(existente['id'])

    return buscar(id_novo)


def resolver_legado(chave_sem_separador):
    """Resolve a chave antiga (``BmGDA``) para uma sequência do catálogo."""
    alvo = chave_sem_separador.replace(',', '').strip().lower()
    with closing(conectar()) as conexao:
        linha = conexao.execute(
            "SELECT id, nome, acordes, criado_em FROM sequencias "
            "WHERE REPLACE(chave, ';', '') = ?",
            (alvo,),
        ).fetchone()
    return _linha_para_dict(linha) if linha is not None else None
