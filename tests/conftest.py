# coding: utf-8
import atexit
import os
import shutil
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

# main.py chama catalogo.init_db() no import. Aponta o banco para um arquivo
# temporário antes do import para não criar var/catalogo.db no repositório.
_IMPORT_DIR = tempfile.mkdtemp(prefix='ciframe-import-')
atexit.register(shutil.rmtree, _IMPORT_DIR, ignore_errors=True)
_IMPORT_DB = os.path.join(_IMPORT_DIR, 'catalogo.db')
os.environ['CIFRAME_DB'] = _IMPORT_DB

import pytest  # noqa: E402

import catalogo  # noqa: E402
import main  # noqa: E402


@pytest.fixture()
def cliente(tmp_path, monkeypatch):
    """Test client com um catálogo SQLite novo e isolado por teste."""
    monkeypatch.setenv('CIFRAME_DB', str(tmp_path / 'catalogo.db'))
    catalogo.init_db()
    main.app.config['TESTING'] = True
    return main.app.test_client()


def corpo(resposta):
    import json
    return json.loads(resposta.data)


def ids_da_api(cliente, id_sequencia, genero=None):
    """Percorre todas as páginas de /similares e devolve o conjunto de ids."""
    ids = set()
    pagina = 1
    while True:
        url = '/similares?sequencia_id=%d&pagina=%d' % (id_sequencia, pagina)
        if genero is not None:
            url += '&generos=' + genero
        itens = corpo(cliente.get(url))
        if not itens:
            break
        ids.update(item['id_unico_musica'] for item in itens)
        pagina += 1
    return ids
