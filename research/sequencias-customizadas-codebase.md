# Research — Sequências de Acordes Customizadas (estado atual do código)

> Fase 1 (RePPIT) da feature `docs/features/sequencias-customizadas/`.
> Escopo: **descrever o que existe hoje**, com evidência executada. Sem
> recomendações, sem desenho de solução.
>
> Baseline: branch `feat/sequencias-customizadas`, HEAD `fb97001`
> (`Update 00-enunciado.md`), que é o mesmo commit indexado pelo DeepWiki
> (`fb970019`).
>
> Data das medições: 2026-11-07.

## Sumário

O backend é um único `main.py` (280 linhas) que, no import, lê
`data/top/dataset_final.csv` (67.586 linhas, sem cabeçalho), descarta a
primeira linha e materializa 67.585 objetos `Musica` em memória
(`main.py:49-98`). Não existe banco de dados, migração, nem camada de
persistência: todo o estado nasce do CSV a cada start e morre com o processo.
A busca por sequência é um dicionário literal de 6 chaves
(`main.py:40-45`) cotejado contra uma coluna pré-computada do CSV
(`SEQ_FAMOSA`), preenchida fora do runtime por
`scripts/generate_data_set.py:7-24`. Reimplementar as **duas** condições desse
script em tempo real sobre `musica.cifra` reproduz, para as 6 sequências, o
mesmo conjunto de músicas que a tag — medido, não suposto (199/296/4/5/7/3,
igualdade de conjuntos `True` nas seis). Nenhuma das duas condições isolada
reproduz a tag. O frontend (`#/porsequencia`) tem um catálogo de 4 sequências
hardcoded em JavaScript, diferente das 6 do backend, não tem formulário de
cadastro, e envia `GET /similares?sequencia=<acordes com vírgula>`, que o
backend reduz a uma chave sem separadores (`main.py:191`).

## 1. Forma do repositório e do runtime

| Arquivo | Papel |
|---|---|
| `main.py` | aplicação Flask inteira: carga do CSV, índices em memória, 9 rotas |
| `musica.py` | entidade `Musica` (25 linhas), derivada do CSV |
| `Dockerfile` | `python:3.9-slim`, `gunicorn --bind 0.0.0.0:8080 main:app` |
| `requirements.txt` | só `Flask==3.1.3` e `gunicorn==23.0.0` |
| `static/` | SPA AngularJS 1.4.9 servida pelo próprio Flask, sem build |
| `data/top/dataset_final.csv` | base de músicas (67.586 linhas) |
| `data/mapeamento_sequencias_famosas.txt` | nome legível das 6 sequências |
| `scripts/generate_data_set.py` | gerador histórico da coluna `SEQ_FAMOSA` |
| `docs/adr/` | 3 ADRs (deploy local-only, persistência [template], fim do freeze do frontend) |

O `Dockerfile` é single-stage, copia o repo inteiro (`COPY . .`), não declara
`VOLUME` e não tem `docker-compose`. `docker run -p 8080:8080 ciframe` não
monta nada: qualquer arquivo escrito em runtime vive só no filesystem do
container.

Ambiente local verificado: `.venv` com Python 3.9.6, `pytest 8.4.2`,
`sqlite3 3.54.0`.

Container verificado depois de o daemon ser iniciado (`docker 29.9.2`):
`python:3.9-slim` traz Python **3.9.25** e o módulo `sqlite3` da stdlib com
SQLite **3.46.1** (`docker run --rm python:3.9-slim python -c "import
sqlite3; print(sqlite3.sqlite_version)"`).

## 2. Carga do CSV e modelo em memória

`main.py:47-98` roda no import do módulo — não é uma função chamada por
request:

1. `open('data/top/dataset_final.csv')` e `f.readline()` (`main.py:49-50`).
   O arquivo **não tem cabeçalho** (a linha 1 já é dado:
   `14-bis,a-qualquer-tempo,14 Bis,...`). Logo, `readline()` descarta a
   música `14-bis / A Qualquer Tempo`. Verificado: `14-bis_a-qualquer-tempo`
   não existe em `main.musicas_dict`; `14-bis_adoraveis-criaturas` (linha 2)
   existe.
2. `line.replace('"','').replace('NA','')[:-1]` (`main.py:53`) e
   `line.split(',')`. O `replace('NA','')` é global na linha, não só na coluna
   de tag. Efeito colateral medido: 7 títulos são mutilados, entre eles
   `DNA → D`, `JULIANA → JULIA`, `CABANA → CABA`, `ROTINA DE POBRE → ROTI DE
   POBRE`. Todas as 67.585 linhas restantes têm exatamente 9 campos após esse
   tratamento.
3. Colunas por índice (`main.py:25-35`): `0` slug artista, `1` slug música,
   `2` nome artista, `3` nome música, `4` gênero, `5` popularidade (pontos
   removidos, `int`), `6` tom, `7` `SEQ_FAMOSA`, `8` cifra.
4. `limpa_cifra` (`main.py:11-23`) quebra a coluna 8 em tokens: split por
   `;` (feito no chamador, `main.py:59`), descarte de vazios, tratamento de
   tablatura (`|` → primeiro token antes do `|`) e de acordes separados por
   espaço.
5. `musica[SEQ_FAMOSA].split(";")` (`main.py:63`) → sempre uma lista; sem tag
   o CSV traz `NA`, que já virou `''` no passo 2, então a lista é `['']`.
6. Índices construídos: `generos` (set → list), `acordes` (set global),
   `genero_musicas` (gênero → lista já ordenada por popularidade),
   `musicas_dict` (id único → objeto) e `musicas` (`OrderedDict` ordenado por
   popularidade desc, `main.py:88-89`).

Medições: carga em **0,54 s**; 3.505.331 tokens de cifra (média 51,9 por
música, máximo 2.065); 52 gêneros; 6.653 acordes distintos; 67.585 ids
únicos (sem colisão de `id_unico_musica`).

`Musica` (`musica.py:1-25`) guarda `cifra` (lista ordenada, com repetições) e
deriva `acordes = list(set(cifra))` (`musica.py:17`) — ou seja, **a ordem e as
repetições existem em `cifra` e são perdidas em `acordes`**. `seqs_famosas` é
a lista da coluna 7. `id_unico_musica` é `"{id_artista}_{id_musica}"`
(`musica.py:20`) e `url` é montada como `cifraclub.com.br/{artista}/{musica}`
(`musica.py:22`).

## 3. Superfície HTTP

Todas as rotas devolvem `json.dumps(...)` como string (`Content-Type:
text/html; charset=utf-8`), nunca `jsonify`. CORS `*` em todas as respostas
(`main.py:274-277`).

| Rota | Handler | Parâmetros | Observado |
|---|---|---|---|
| `/` | `index` (`main.py:101-103`) | — | serve `static/index.html` |
| `/<path>` | `static_proxy` (`main.py:109-112`) | — | assets e templates |
| `/search` | `busca` (`main.py:114-142`) | `key` (obrigatório), `generos`, `pagina` | tokens de `key` têm de estar **todos** em `artista + título` normalizados; `key` ausente → 500 (`None.lower()`) |
| `/musicas` | `get_musicas` (`main.py:154-156`) | — | 67.585 objetos completos, ~695 ms, **sem paginação** apesar do docstring |
| `/generos` | `get_generos` (`main.py:158-160`) | — | 52 strings; ordem varia por `PYTHONHASHSEED` |
| `/acordes` | `get_acordes` (`main.py:162-164`) | — | 6.653 tokens, ordem variável |
| `/musica/<m_id>/` | `get_musica` (`main.py:166-168`) | path | `KeyError` → 500 se o id não existe |
| `/similares` | `get_similares` (`main.py:170-201`) | `acordes` \| `id_unico_musica` \| `sequencia`, mais `generos`, `pagina` | ver §4 |

Precedência em `/similares` (`main.py:184-197`): `acordes` vence
`id_unico_musica`, que vence `sequencia`. Testado:
`/similares?sequencia=BmGDA&acordes=C` devolve o resultado do ramo `acordes`
(100 itens).

Paginação: `get_pagina` (`main.py:226-228`) fatia `[(p-1)*100 : (p-1)*100+100]`
com `TAM_PAGINA = 100` (`main.py:35`). Nenhum controller do frontend envia
`pagina`, então a UI só vê os 100 primeiros itens.

## 4. A busca por sequência hoje

`main.py:40-45` define o catálogo como um dicionário literal de 6 chaves sem
separador:

```python
sequencias = {'BmGDA': 0, 'CGAmF': 1, 'EmG': 2, 'CA7DmG7': 3, 'GmF': 4, 'CC7FFm': 5}
```

O ramo `sequencia` (`main.py:190-197`):

```python
acordes = sequencia_tag.replace(',','')
similares = []
if acordes in sequencias:
    id_seq = sequencias[acordes]
    similares = get_pagina(get_similares_por_sequencia(id_seq, generos_key), pagina_tag)
return json.dumps(similares)
```

Três consequências medidas:

- **Chave desconhecida → `[]` com HTTP 200.** `XYZ` e `cgamf` devolvem 0
  itens; não há erro, nem normalização de caixa.
- **A vírgula é decorativa.** `Bm,G,D,A`, `BmGDA` e `CG,Am,F` produzem o
  mesmo resultado que `BmGDA`/`CGAmF`, porque `replace(',','')` colapsa tudo
  na mesma chave. `C,G,Am` (3 acordes) → 0 itens.
- **Não há cálculo de matching.** `get_similares_por_sequencia`
  (`main.py:203-223`) só faz `str(id_seq) in musica.seqs_famosas`, sobre a
  coleção já filtrada por gênero (`apply_filtro`, `main.py:266-272`).

Formato de cada item devolvido (`main.py:210-220`): `id_unico_musica`,
`id_artista`, `id_musica`, `nome_artista`, `nome_musica`, `popularidade`,
`acordes`, `genero`, `url`. **Não** há `diferenca`/`intersecao` (essas chaves
só existem no ramo `acordes`, `main.py:246-258`).

Ordem: a iteração é sobre `apply_filtro(musicas.values(), generos)`, e
`generos` é `list(set)` (`main.py:92`), portanto a ordem dos itens depende de
`PYTHONHASHSEED`. Verificado com seed 1 e 42: primeiros ids de
`/similares?sequencia=BmGDA` foram `wesley-safadao_sou-ciumento...`,
`wesley-safadao_segunda-opcao`, ... contra `soja_not-done-yet`,
`maneva_segura-som`, ...; `/generos` começou em `Forró` contra `Reggae`. Isso
é dívida pré-existente, não da feature.

Paginação observada em `BmGDA` (199 músicas): página 1 → 100, página 2 → 99,
página 3 → 0.

## 5. De onde vem a tag `SEQ_FAMOSA`

`scripts/generate_data_set.py:7-24`:

```python
seqs = ['bm;g;d;a','c;g;am;f','em;g','c;a7;dm;g7','gm;f','c;c7;f;fm']
def get_famosas(acorde):
    ...
    if s in acorde:            # (a) substring contígua na cifra minúscula
        for l in acorde.split(';'):   # (b) vocabulário da música
            if l not in s.split(';'): #     contido no da sequência
                achou = False
```

Duas condições simultâneas:

- **(a) contiguidade na ordem**: a sequência aparece como substring
  contígua da cifra (`'bm;g;d;a' in 'bm;g;d;a;bm;g;...'`), então ordem e
  repetição importam;
- **(b) contenção de vocabulário**: **todo** acorde da música pertence ao
  conjunto da sequência (`set(musica.acordes) ⊆ set(sequencia)`).

A tag é gravada como índice (`0`..`5`) na coluna 7 e o runtime a lê como
lista (`main.py:63`, `main.py:209`).

### Verificação das regras contra os dados

Script: `docs/features/sequencias-customizadas/research_compare.py`
(`.venv/bin/python .../research_compare.py`; parser idêntico a
`main.py:49-63`). Número de músicas casadas por regra:

| sequência | acordes | tag | (a) contíguo | (b) vocabulário | (a)+(b) | conjunto invertido | subsequência |
|---|---|---|---|---|---|---|---|
| `BmGDA` | Bm G D A | 199 | 866 | 9.014 | **199** | 5.768 | 4.763 |
| `CGAmF` | C G Am F | 296 | 1.216 | 9.099 | **296** | 6.894 | 5.887 |
| `EmG` | Em G | 4 | 3.110 | 8.165 | **4** | 14.160 | 13.643 |
| `CA7DmG7` | C A7 Dm G7 | 5 | 96 | 8.194 | **5** | 582 | 427 |
| `GmF` | Gm F | 7 | 1.039 | 8.159 | **7** | 3.847 | 3.641 |
| `CC7FFm` | C C7 F Fm | 3 | 132 | 8.198 | **3** | 365 | 280 |

(colunas `(a)`, `(b)` e `conjunto invertido` isoladas **não** reproduzem a
tag; `subsequência` = ordem importa, mas aceita acordes no meio.)

Igualdade de conjunto de `id_unico_musica` entre tag e regra (a)+(b):
`True` nas 6 sequências, com 0 faltando e 0 sobrando.

Distribuição da tag no CSV: 514 de 67.585 linhas (0,76%); valores possíveis
`0`..`5`; **nenhuma linha tem mais de uma tag** (o gerador concatena índices
sem separador, mas o caso não ocorre na base atual).

Custo: aplicar (a)+(b) às 6 sequências sobre 67.585 músicas levou 1,23 s
(≈205 ms por sequência) em Python puro, single-thread, sem índice. A carga do
CSV custa 0,54 s.

## 6. Frontend: `#/porsequencia`

- Rota: `static/assets/js/routes.js:17-21` → `templates/sequencia.html` +
  `SequenciaController` (`controllerAs: "Sequencia"`).
- Catálogo: **4 sequências literais** em `sequencia.js:2-37`
  (`Bm-G-D-A`, `C-G-Am-F`, `Gm-F`, `C-C7-F-Fm`). O backend tem 6; `Em-G` e
  `C-A7-Dm-G7` não aparecem na UI.
- Disparo: `pesquisarPorSequencia` (`sequencia.js:63-90`) monta
  `"similares?sequencia=" + acordes.join(',')` (`createChordsString`,
  `sequencia.js:55-61`) e faz `$http.get` em URL relativa (`apiUrl = ""`,
  `sequencia.js:72`).
- A constante `RESTAPI` (`app.js:3-5`, `http://localhost:5003`) **não é usada
  por nenhum controller** — todos usam `""`.
- Filtro de gênero: `<select>` alimentado pela constante `GENEROS`
  (`sequencia.js:43`), 51 gêneros literais em `app.js:6-58`. O backend tem 52
  (`R&B;` só existe lá, por causa do `;` no dado).
- Não há formulário de cadastro, nem chamada a `/generos` ou `/acordes`; a
  paleta de acordes de `#/poracordes` (`acordes.js:2-53`, 51 acordes com cor)
  é outro array literal, não vem do backend.
- Resultados: cards `ng-repeat` com `ng-hide="music.diferenca.length"`
  (`sequencia.html:40-59`). O ramo `sequencia` não devolve `diferenca`, então
  a expressão é `undefined` → todos os itens aparecem. Não há paginação na
  UI.
- Visual do acorde: diretiva `dfHex` (`df-hex.js:1-12` +
  `templates/directives/df-hex.html`), entrada `acorde`/`acorde-color` por
  atributo.

## 7. Fluxo ponta a ponta (hoje)

```
clique na sequência (sequencia.js:63)
  → GET /similares?sequencia=Bm,G,D,A[&generos=X]
  → get_similares (main.py:171)
  → sequencia_tag.replace(',','')  (main.py:191)
  → dict lookup em `sequencias` (main.py:40-45)
  → get_similares_por_sequencia (main.py:203)
  → apply_filtro por gênero (main.py:266)
  → `str(id_seq) in musica.seqs_famosas` (main.py:209)   [tag do CSV]
  → get_pagina(..., 100) (main.py:226)
  → json.dumps(lista)  (main.py:197)
  → cards no template (sequencia.html:40-59)
```

Não existe caminho que calcule matching em tempo real, nem endpoint de
escrita (nenhuma rota aceita `POST`; só `GET`).

## 8. Persistência e testes: o que existe hoje

- **Persistência**: nenhuma. Nenhum `sqlite3`, `dbm`, `json.dump` ou ORM no
  código; nenhum arquivo de dados fora do CSV versionado. `Dockerfile` sem
  `VOLUME`; reiniciar o container reconstrói tudo do CSV.
- **Testes**: não existe diretório `tests/`, nem `pytest.ini`, nem CI. A
  verificação usada neste documento foi feita com `pytest` disponível no
  `.venv` e com os dois scripts de sonda descritos abaixo.
- **Como rodar**: `python main.py` (porta 5000, `debug=True`,
  `main.py:279-280`) ou `docker run -p 8080:8080 ciframe`.

## 9. Reprodução das evidências

| Evidência | Como reproduzir |
|---|---|
| contagens por regra, igualdade com a tag, custo | `.venv/bin/python docs/features/sequencias-customizadas/research_compare.py` |
| comportamento dos endpoints, ordem, paginação | `PYTHONPATH=. .venv/bin/python <sonda>` (test client do Flask) |
| primeira linha descartada, `NA` mutilando títulos | inspeção linha a linha do CSV com `split(',')` após `replace('"','')` |

## 10. Conferência com o DeepWiki

Fonte usada para orientação: `https://deepwiki.com/joaoarthurbm/ciframe`
(índice do commit `fb970019`, o mesmo do HEAD). O acesso direto é bloqueado
pelo *Vercel Security Checkpoint* (HTTP 429); o conteúdo foi lido via
`https://r.jina.ai/<url>` e salvo em `research/deepwiki/`.

| Página | Confere com o código? |
|---|---|
| `2.2 REST API Endpoints` | sim: rotas, parâmetros, `TAM_PAGINA`, formatos |
| `2.3 Search and Similarity Algorithms` | sim: normalização NFD, tokenização de `/search`, ordenação de `get_similares` |
| `4.4 dataset_final.csv Schema` | colunas sim; a descrição da tag está **incompleta** (fala só de "ordered intervals", omite a condição de vocabulário que o §5 mede) |
| `5.1 / 5.2` | descrevem ADRs e o enunciado/templates; não há implementação da feature |

Duas afirmações do DeepWiki não se sustentam no código e foram corrigidas
aqui: (i) `/musicas` "paginado" — o docstring promete paginação, o handler não
pagina; (ii) a origem da tag descrita como só contiguidade.
