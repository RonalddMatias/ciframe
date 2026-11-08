# Pesquisa — Sequências de Acordes Customizadas

Baseline: branch `feat/sequencias-customizadas`, HEAD `fb97001`. Medições de
2026-11-07, executadas localmente (Python 3.9.6 do `.venv`). Documento de apoio
com todas as evidências, referências de linha e reprodutibilidade:
[`research/sequencias-customizadas-codebase.md`](../../../research/sequencias-customizadas-codebase.md).
Script de comparação de regras:
[`research_compare.py`](research_compare.py).

## 1. Algoritmo de matching

**O que existe hoje.** Não há cálculo de matching. `GET /similares?sequencia=`
remove as vírgulas do parâmetro (`main.py:191`), procura a string resultante
num dicionário literal de 6 chaves (`main.py:40-45`) e devolve as músicas cuja
coluna pré-computada `SEQ_FAMOSA` contém aquele índice
(`get_similares_por_sequencia`, `main.py:203-223`, teste em `main.py:209`).
Uma chave desconhecida devolve `[]` com HTTP 200 — sem erro, sem normalização
de caixa (`cgamf` → 0 itens, medido).

**Como a tag foi gerada.** `scripts/generate_data_set.py:7-24` aplica **duas**
condições à cifra da música, ambas necessárias:

- **(a) contiguidade na ordem** — a sequência é substring contígua da cifra
  (`'bm;g;d;a' in acorde`), de modo que ordem e repetição importam;
- **(b) contenção de vocabulário** — **todo** acorde da música pertence ao
  conjunto de acordes da sequência (`for l in acorde.split(';'): if l not in
  s.split(';')`).

A cifra usada é a coluna 8 tokenizada por `limpa_cifra` (`main.py:11-23`), que
descarta vazios e trata tablatura (`|`). `Musica` mantém `cifra` como lista
ordenada com repetições e deriva `acordes = list(set(cifra))`
(`musica.py:17`) — ou seja, `acordes` **não** preserva ordem nem repetição.

**Validação (pergunta 2).** Rodando (a)+(b) em tempo real sobre os 67.585
objetos carregados, para as 6 sequências, o conjunto de `id_unico_musica`
coincide **exatamente** com o conjunto marcado pela tag: `True` nas seis, 0
faltando e 0 sobrando.

| sequência | acordes | tag | (a) contíguo | (b) vocabulário | (a)+(b) | conjunto invertido |
|---|---|---|---|---|---|---|
| `BmGDA` | Bm G D A | 199 | 866 | 9.014 | **199** | 5.768 |
| `CGAmF` | C G Am F | 296 | 1.216 | 9.099 | **296** | 6.894 |
| `EmG` | Em G | 4 | 3.110 | 8.165 | **4** | 14.160 |
| `CA7DmG7` | C A7 Dm G7 | 5 | 96 | 8.194 | **5** | 582 |
| `GmF` | Gm F | 7 | 1.039 | 8.159 | **7** | 3.847 |
| `CC7FFm` | C C7 F Fm | 3 | 132 | 8.198 | **3** | 365 |

Nenhuma condição isolada reproduz a tag: só (a) infla de 3× a ~780×; só (b)
infla de ~30× a ~2.700×; exigir apenas que os acordes da sequência existam na
música ("conjunto invertido") também não (5.768 contra 199 em `BmGDA`).

**Fatos de dados que afetam qualquer regra.**

- A tag cobre **514 de 67.585 linhas (0,76%)** e **nenhuma linha tem mais de
  uma tag**.
- As 6 sequências usam 4, 4, 2, 4, 2 e 4 acordes; a de 2 acordes (`EmG`)
  casa com 4 músicas porque a condição (b) é restritiva: a música inteira não
  pode ter acorde fora de `{Em, G}`.
- O vocabulário de acordes do dataset tem 6.653 tokens, incluindo formas como
  `E/G#`, `D#5-` e `Bb9`; não há normalização de grafia em nenhum ponto do
  backend.
- Custo medido de (a)+(b) em Python puro: 1,23 s para as 6 sequências sobre
  67.585 músicas (≈205 ms por sequência), contra 0,54 s de carga do CSV. O
  handler atual responde em 1–15 ms porque só lê a tag.

## 2. Validação da hipótese

Ver §1: a regra (a)+(b) reproduz a tag nas 6 sequências, por igualdade de
conjunto de `id_unico_musica`. Duas ressalvas medidas:

- **A ordem dos resultados não é estável hoje.** `get_similares_por_sequencia`
  itera sobre `apply_filtro(musicas.values(), generos_key)`
  (`main.py:203-205`) e `generos` é `list(set)` (`main.py:92`); com
  `PYTHONHASHSEED=1` e `=42` os primeiros itens de
  `/similares?sequencia=BmGDA` e de `/generos` mudam. Comparar a regressão por
  **conjunto de ids**, não por ordem, é o único critério estável hoje.
- **Paginação corta em 100** (`TAM_PAGINA`, `main.py:35`; `get_pagina`,
  `main.py:226-228`). `BmGDA` tem 199 músicas: página 1 → 100, página 2 → 99,
  página 3 → 0. Nenhum controller envia `pagina`, então a UI vê só 100.

## 3. Banco de dados

**Estado atual: não existe persistência.** Nenhum `sqlite3`, `dbm`, ORM ou
`json.dump` no código; nenhum arquivo de dados além do CSV versionado. Todo o
estado nasce do CSV no import (`main.py:47-98`) e morre com o processo.

**Restrições dadas.** `docs/adr/0001-local-only-docker-deploy.md`: container
único, local, sem serviço externo. `Dockerfile`: `python:3.9-slim`, single
stage, `COPY . .`, sem `VOLUME`, sem compose; roda `gunicorn` em `:8080`.

**Opções embarcadas disponíveis no runtime atual (sem dependência nova).**

| Opção | Disponível? | Persistência entre reinícios |
|---|---|---|
| `sqlite3` (stdlib) | sim — `3.54.0` no `.venv` (Python 3.9.6) | só se o arquivo `.db` sobreviver: volume nomeado/bind mount, ou caminho fora do container |
| `dbm`/`shelve` (stdlib) | sim | mesma condição: arquivo em volume |
| arquivo JSON em disco | sim (stdlib) | idem |
| banco embarcado de terceiros (TinyDB etc.) | exigiria nova linha em `requirements.txt` | idem |

Fatos que delimitam a escolha:

- Sem volume, `docker rm`/`docker run` novo zera o filesystem do container —
  o `Dockerfile` atual não declara `VOLUME` e o comando documentado em
  `AGENTS.md` (`docker run -p 8080:8080 ciframe`) não monta nada.
- Com gunicorn, há múltiplos workers/processos possíveis sobre o mesmo
  arquivo; `sqlite3` da stdlib aceita concorrência de escrita com
  serialização, `dbm`/JSON não têm controle de concorrência embutido.
- `python:3.9-slim` já traz `sqlite3` (SQLite 3.46.1), então a opção não
  adiciona dependência nem muda o `Dockerfile` além do volume.
- Semântica de persistência medida no container real: um arquivo escrito em
  `/catalogo.db` **sobrevive** a `docker restart` e **desaparece** no
  `docker run` seguinte; o `Dockerfile` não declara `VOLUME` (0 ocorrências).
  Ou seja, "reiniciar" preserva, "recriar o container" não.

## 4. Frontend existente

`#/porsequencia` (`routes.js:17-21`) usa `templates/sequencia.html` +
`SequenciaController` (`controllerAs: "Sequencia"`). O que já existe:

- **Catálogo hardcoded de 4 sequências** (`sequencia.js:2-37`): `Bm-G-D-A`,
  `C-G-Am-F`, `Gm-F`, `C-C7-F-Fm`. O backend tem 6; `Em-G` e `C-A7-Dm-G7`
  nunca aparecem na tela.
- **Busca** (`sequencia.js:63-90`): monta `"similares?sequencia=" +
  acordes.join(',')` (`createChordsString`, `sequencia.js:55-61`) e faz
  `$http.get` em URL **relativa** (`apiUrl = ""`, `sequencia.js:72`). O
  `?sequencia=` resultante é `Bm,G,D,A` — que o backend reduz a `BmGDA`.
- **Filtro de gênero**: `<select>` com a constante `GENEROS`
  (`sequencia.js:43`), **51 gêneros literais** em `app.js:6-58`. O backend
  expõe 52 (o extra é `R&B;`, que carrega um `;` do dado). `/generos` nunca é
  chamado pelo frontend.
- **Constante morta**: `RESTAPI = { url: 'http://localhost:5003' }`
  (`app.js:3-5`) não é usada por nenhum controller.
- **Sem cadastro**: não há formulário, input de acordes, nem `POST`. A paleta
  de acordes existe só em `#/poracordes` (`acordes.js:2-53`, 51 acordes com
  cor), também literal.
- **Resultados**: cards `ng-repeat` com `ng-hide="music.diferenca.length"`
  (`sequencia.html:40-59`); o ramo `sequencia` não devolve `diferenca`, então
  a expressão é `undefined` e todos aparecem. Sem paginação na UI.
- **Visual**: diretiva `dfHex` (`df-hex.js:1-12`,
  `templates/directives/df-hex.html`) recebe `acorde`, `acorde-color`,
  `acorde-checked`, `small`.

## Trade-offs identificados

Opções reais para a fase de proposta; nenhuma decisão tomada aqui.

**Algoritmo**

| Opção | Prós | Contras |
|---|---|---|
| (a)+(b), igual à geração da tag | regressão exata das 6 sequências (medido); uma única regra para antigas e novas | a condição (b) é contraintuitiva para sequência arbitrária: a música não pode ter **nenhum** acorde fora da sequência, então sequências curtas casam pouco (2 acordes → 4 músicas) |
| só contiguidade (a) | intuitivo ("a sequência aparece na música") | 3× a ~780× mais resultados que hoje; quebra a regressão exigida |
| só vocabulário (b) | independe de ordem | 30× a 2.700× mais resultados; não distingue sequência de conjunto |
| acordes da sequência contidos na música ("conjunto invertido") | é o que `/similares?acordes=` já faz | 5.768 contra 199 em `BmGDA`; ignora ordem e não reproduz a tag |
| regra diferente para as 6 antigas (tag) e para as novas (tempo real) | regressão trivial | duas semânticas para o mesmo botão; o catálogo passa a ter sequências de primeira e de segunda classe |

**Banco**

| Opção | Prós | Contras |
|---|---|---|
| `sqlite3` stdlib | zero dependência nova; SQL, transação e concorrência de escrita; já presente no runtime | exige volume para sobreviver a `docker rm`; arquivo binário no repo/volume |
| `dbm`/`shelve` stdlib | zero dependência; chave-valor simples | sem consulta/ordenação, sem concorrência embutida; exige volume do mesmo jeito |
| JSON em disco | legível e trivial | reescreve o arquivo inteiro a cada escrita; sem concorrência |
| embarcado de terceiros (TinyDB) | API simples | nova dependência em `requirements.txt` e no build |

**Persistência no container** (transversal à escolha acima): volume nomeado,
bind mount, ou caminho dentro da imagem (que não sobrevive a `docker rm`).

**Frontend**

| Opção | Prós | Contras |
|---|---|---|
| catálogo vem de um `GET` do backend e o cadastro é `POST` | uma fonte de verdade; as 6 antigas aparecem | exige endpoint novo e estado de carregamento/erro na tela |
| manter as 6/4 no JS e só acrescentar as novas | menos mudança | duas fontes de verdade; a divergência 6 × 4 que já existe hoje continua |
| reusar a paleta de `acordes.js` no formulário | consistência visual | a paleta é literal (51 acordes) e não cobre o vocabulário real (6.653 tokens) |

## Decisões que fecharam esta fase

Confirmadas pelo autor do projeto em 2026-11-07, depois da entrevista:

1. **A tag `SEQ_FAMOSA` é especificação, não artefato histórico.** A regra
   (a)+(b) de `scripts/generate_data_set.py:7-24` vale para **todas** as
   sequências, antigas e novas — uma única semântica: "músicas construídas
   sobre essa progressão" (contígua na ordem **e** sem acorde fora dela).
   Consequência aceita: sequências curtas rendem pouco (`Em-G` → 4 músicas).
2. **Regressão = mesmo conjunto de `id_unico_musica`, ordem ignorada**, por
   sequência e por sequência+gênero, mais as contagens de página
   (100/99/0 em `BmGDA`) como verificação separada. A ordem fica fora do
   critério porque já varia com `PYTHONHASHSEED` antes da feature.
3. **Evidência de container coletada nesta fase**, depois de o daemon ser
   iniciado: `python:3.9-slim` → Python 3.9.25 + `sqlite3` 3.46.1; arquivo
   criado em runtime sobrevive a `docker restart` e desaparece no
   `docker run` seguinte; `Dockerfile` sem `VOLUME`. A decisão sobre volume
   continua em aberto para a fase de proposta.
