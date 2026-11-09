# Relatório de testes — Sequências de Acordes Customizadas

## Cobertura

A suíte tem 71 testes (`pytest -q`: 71 passed em 15,55 s), distribuídos assim:

- `tests/test_matching.py` — a regra pura de `matching.py`: janela contígua
  respeitando ordem e repetição, contenção de vocabulário (nenhum acorde da
  música fora da sequência), normalização de caixa/espaços, sequência vazia e
  cifra mais curta que o alvo.
- `tests/test_api.py` — `GET /sequencias` traz os 6 seeds na ordem; `POST
  /sequencias` cria (nome padrão e nome informado), devolve 409 com o id da
  existente em duplicata e 400 para corpo não-objeto, 0/13 acordes, acorde
  vazio, acorde com mais de 20 caracteres, `;`/`,`, tipo errado e nome com mais
  de 120 caracteres; `GET /similares?sequencia_id=` devolve exatamente o
  conjunto da regra; `?acordes=` mantém a ordenação por diferença/intersecção;
  `?id_unico_musica=` não inclui a própria música; ids inexistentes, fora do
  intervalo do SQLite e páginas inválidas devolvem 404/400 em vez de 500;
  página além do fim devolve `[]`; respostas continuam `text/html` por serem
  `json.dumps` (contrato legado) e não expõem `cifra_norm`/`acordes_norm`.
- `tests/test_persistencia.py` — sequência criada é visível em outra conexão
  SQLite (simula outro worker), seed repetido não duplica, seed não sobrescreve
  sequência do usuário e `criar` duplicado levanta `SequenciaDuplicada` com o
  id existente.
- `tests/test_legado.py` — `?sequencia=BmGDA`, `Bm,G,D,A` e `bm,g,d,a`
  devolvem o mesmo conjunto; `cgamf` passou a funcionar; chave desconhecida
  devolve `[]`.
- `tests/test_regressao.py` — compara a tag `SEQ_FAMOSA` com a regra em tempo
  real e com o endpoint, por sequência e por gênero, além das contagens de
  página.

Cobertura medida com `coverage run -m pytest`:

| arquivo | cobertura | linhas não cobertas |
| --- | --- | --- |
| `main.py` | 98% | `/`, proxy estático, `/generos`, `/acordes` e `app.run` |
| `catalogo.py` | 98% | só o `raise` de fallback após `IntegrityError` |
| `matching.py` | 100% | — |
| `musica.py` | 95% | `__str__`, não usada pelo app |

Total: 98%.

## Teste de regressão obrigatório

As 6 sequências originais (agora `catalogo.SEQUENCIAS_ORIGINAIS`, antes o
dicionário literal de `main.py`) precisam devolver exatamente os mesmos
resultados de antes da migração para SQLite.

A tag `SEQ_FAMOSA` do `dataset_final.csv` — gerada pelo script antigo — é o
oráculo: `tests/test_regressao.py` calcula a regra real de matching para cada
sequência e compara com a tag, e também percorre todas as páginas de
`/similares?sequencia_id=`, exigindo **0 faltando / 0 sobrando**. O mesmo é
feito com filtro de gênero. Resultado: igual para as 6 sequências, com as
contagens esperadas `199 / 296 / 4 / 5 / 7 / 3`, e `?sequencia=BmGDA`
(paginação inclusive) devolve o mesmo conjunto de `?sequencia_id=1`.

## Números medidos na implementação

- Tag vs regra/endpoint, por sequência (0 faltando / 0 sobrando): `Bm-G-D-A`
  199; `C-G-Am-F` 296; `Em-G` 4; `C-A7-Dm-G7` 5; `Gm-F` 7; `C-C7-F-Fm` 3.
- Contagens de página em `BmGDA`: 100 / 99 / 0.
- Latência de `/similares?sequencia_id=1` (1 chamada de aquecimento + 20
  chamadas, Flask test client, código final): mín. 209 ms, mediana 211 ms,
  p95 222 ms, máx. 226 ms.
- Container (`python:3.9-slim`, build refeito nesta fase com o `.dockerignore`
  novo): a imagem não contém `docs/`, `research/` nem `tests/`; `GET /generos`
  200 (52 gêneros) → `POST` 201 (id 7) → `docker restart` → sequência presente
  → `docker rm` + `docker run` com o mesmo volume → sequência presente;
  duplicata devolve 409 com o id existente. Dentro do container, `pagina=abc`
  devolve 400, `sequencia_id` gigante devolve 404 e `/musica/nope/` devolve 404.
- Render de `#/porsequencia` em Chrome headless: 6 sequências (20 hexágonos),
  incluindo `Em-G` e `C-A7-Dm-G7`; formulário presente; `GET /sequencias` 200.
- `pytest -q`: 71 passed em 15,55 s.

## Correções feitas na revisão de código

Depois da revisão, e antes da medição acima, foram corrigidos os pontos que
podiam virar 500 ou degradar a entrega: `pagina` não inteira/negativa agora
devolve 400 (em `/similares` e `/search`), `sequencia_id` acima do limite do
SQLite devolve 404 em vez de `OverflowError`, `?id_unico_musica=` e
`/musica/<id>/` inexistentes devolvem 404, `nome` tem limite de 120 caracteres,
o catálogo ganhou acesso por teclado (`tabindex` + Enter/Espaço), o template
deixou de depender do campo `diferenca` que a API por sequência não devolvia,
o `.dockerignore` exclui `docs/`, `research/` e `tests/` da imagem, o diretório
temporário de import do `conftest.py` é limpo no fim, e `coverage`/`pytest-cov`
entraram em `requirements-dev.txt`. Cada correção veio com teste.

## Como rodar

```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest -q
coverage run -m pytest -q && coverage report -m
```

## O que ficou de fora

- A imagem não foi enxugada além do `.dockerignore`: `Dockerfile`, `LICENSE`,
  `requirements-dev.txt` e `scripts/` ainda entram no contexto (345 MB,
  dominados pela base `python:3.9-slim`). Não era objetivo desta fase.
- Sem teste de concorrência real entre dois workers inserindo a mesma chave ao
  mesmo tempo: o caminho `IntegrityError` é coberto pela duplicata sequencial,
  mas o `raise` de fallback (quando o SELECT também não acha a chave) fica sem
  teste e é inalcançável sem simular falha do banco.
- Endpoints legados `/`, proxy estático, `/generos`, `/acordes` e `app.run`
  continuam sem teste; `__str__` de `Musica` também não é usada.
- O smoke de render em Chrome headless foi manual, não há teste E2E de
  navegador no repositório.
- Limites de payload do gunicorn (corpo HTTP gigante) não foram testados;
  `valida_sequencia` cobre só o domínio (acordes, nome e formato do JSON).
