# Proposta — Sequências de Acordes Customizadas

## Contexto

- **Pedido:** qualquer visitante cadastra uma sequência de acordes (sem login) e
  busca músicas por ela, exatamente como as 6 sequências de hoje; o catálogo
  passa a viver num banco de dados e a página `#/porsequencia` passa a refletir
  o catálogo real.
- **Fonte de pesquisa:** [`01-research.md`](01-research.md) — §1 (algoritmo e
  custo medido), §2 (validação e critério de regressão), §3 (opções de banco e
  semântica de volume no container), §4 (frontend), "Trade-offs identificados" e
  "Decisões que fecharam esta fase" — mais o documento de apoio
  [`research/sequencias-customizadas-codebase.md`](../../../research/sequencias-customizadas-codebase.md)
  (§4, §5, §6, §8). Baseline `fb97001`.
- **Restrições fixas (enunciado):** músicas/gêneros continuam vindo do CSV em
  memória; um único `Dockerfile`, local-only (ADR 0001); as 6 sequências
  originais produzem o mesmo conjunto de resultados; respostas continuam sendo
  `json.dumps(...)`, não `jsonify`.
- **Decisões já fechadas na pesquisa:** a tag `SEQ_FAMOSA` é especificação, não
  artefato — a regra (a)+(b) de `scripts/generate_data_set.py:7-24` vale para
  sequências antigas e novas; regressão é igualdade de **conjunto de
  `id_unico_musica`** (ordem ignorada) mais as contagens de página (100/99/0 em
  `BmGDA`).

## As duas abordagens candidatas

As duas compartilham a mesma regra de matching e o mesmo banco (SQLite); a
diferença é **quando** o matching é calculado e, por consequência, quanta coisa
derivada existe para manter.

### Proposta 1 — SQLite + matching em tempo real (recomendada)

- **Visão geral:** o catálogo de sequências é uma única tabela no SQLite. Cada
  `GET /similares?sequencia_id=` lê a sequência do banco e aplica a regra
  (a)+(b) sobre as cifras em memória, música a música, reusando
  `apply_filtro` (`main.py:266-272`) e `get_pagina` (`main.py:226-228`). Nada
  derivado é gravado.
- **Mudanças principais:**
  - `matching.py` (novo): funções puras `normaliza`, `chave_de` e `casa`
    (janela de tokens + contenção de vocabulário), sem importar `main.py`.
  - `catalogo.py` (novo): schema, seed das 6 originais, `listar`, `buscar`,
    `criar`; conexão SQLite por request.
  - `musica.py`: pré-computar `cifra_norm` (minúsculas) e `acordes_norm` (set)
    no `__init__`, para não pagar o custo por request.
  - `main.py`: `GET /sequencias`, `POST /sequencias`, ramo
    `sequencia_id` em `/similares`; o dict literal de `main.py:40-45` sai.
  - `Dockerfile`: `CIFRAME_DB=/data/catalogo.db`, `VOLUME ["/data"]`.
  - Frontend: catálogo via `GET`, formulário de cadastro via `POST`, busca por
    `id` (`sequencia.js:2-37`, `63-90`; `sequencia.html`).
- **Trade-offs:**
  - *Prós:* uma única fonte de verdade (não há índice para invalidar); a
    regressão vale **por construção**, porque a mesma regra roda para as 6 e
    para as novas; mudar o CSV não exige rebuild; menos código e menos schema.
  - *Contras:* ~196 ms por sequência (medido: 1,17 s para as 6 sobre 67.585
    músicas), contra 1–15 ms do handler atual; não dá para devolver `contagem`
    no catálogo sem varrer tudo; cada leitura paga o custo de novo.
- **Validação:**
  - Teste-oráculo de regressão: para cada uma das 6, conjunto de ids do
    endpoint == conjunto marcado pela tag, por sequência e por sequência+gênero;
    contagens de página 100/99/0 em `BmGDA`.
  - Testes unitários de `casa`: ordem importa, repetição importa, acorde fora
    da sequência exclui, `G` não casa dentro de `Gm`, `Em G` não casa com
    música que tenha `G7`, cifra vazia (8.141 músicas) nunca casa.
  - Medição de latência do endpoint antes/depois (p95 de 20 chamadas) para
    confirmar a ordem de grandeza dos 196 ms.
- **Questões em aberto:** o custo é aceitável para um catálogo que pode crescer
  sem limite? (A Proposta 2 é o caminho de saída.) Devolver `contagem` no
  catálogo é requisito de UI ou não?

### Proposta 2 — SQLite + índice materializado música↔sequência

- **Visão geral:** além da tabela de sequências, uma tabela
  `sequencia_musicas(sequencia_id, id_unico_musica)` guarda o resultado do
  matching. A leitura vira "carregue o conjunto de ids da sequência e filtre as
  músicas em memória"; a escrita paga o cálculo uma vez.
- **Mudanças principais:**
  - `catalogo.py` com duas tabelas e `rebuild_indice(sequencia_id)`.
  - `POST /sequencias` insere a sequência e calcula/grava as associações
    (~196 ms por cadastro).
  - Seed no boot: as 6 originais são inseridas e indexadas na primeira subida
    (≈1,2 s) e ficam persistidas nos boots seguintes.
  - `scripts/rebuild_indice.py` (novo) para quando o CSV mudar.
  - O resto (API, frontend, volume) é idêntico à Proposta 1.
- **Trade-offs:**
  - *Prós:* leitura ~10–20 ms (o scan de 67.585 objetos continua, mas sem o
    custo do matching); `contagem` por sequência sai de graça; cadastro fica
    "caro" no momento em que já há um POST explícito do usuário.
  - *Contras:* duas fontes de verdade — a tabela derivada pode divergir da
    regra se o CSV mudar ou se o rebuild falhar; exige teste-oráculo
    permanente e um script a mais; o boot da primeira execução fica ~1,2 s mais
    lento; mais schema, mais código, mais modos de falha (transação parcial,
    sequência sem associações).
- **Validação:** tudo da Proposta 1, mais um teste que compara, para **todas**
  as sequências do catálogo, o conjunto materializado com o cálculo em tempo
  real (oráculo); e um teste de rebuild que muda o CSV de teste e confere que o
  índice é reconstruído.
- **Questões em aberto:** vale otimizar para um catálogo que hoje tem 6 itens e
  provavelmente terá dezenas? Quem lembra de rodar o rebuild quando o CSV
  mudar?

### Comparação

| Critério | Proposta 1 | Proposta 2 |
|---|---|---|
| Latência de leitura | ~196 ms/sequência (medido) | ~10–20 ms (estimado) |
| Latência de escrita | ~1–5 ms (estimado, só `INSERT`) | ~196 ms (calcula e grava) |
| Schema | 1 tabela | 2 tabelas + script de rebuild |
| Fontes de verdade | 1 | 2 (regra + tabela derivada) |
| Regressão | por construção | exige teste-oráculo e rebuild |
| Mudança no CSV | nada a fazer | rebuild obrigatório |
| Complexidade | baixa | média |
| Alinhamento com as restrições | **alto** | médio |

## Abordagem escolhida

**Proposta 1.** O catálogo tem 6 sequências hoje e o requisito é crescer "sem
novo deploy", não "em escala". Pagar ~196 ms por busca é aceitável para um app
local com barra de progresso na tela (`sequencia.js:67`), e elimina a classe de
bug mais provável desta feature: índice derivado divergindo da regra. Se a
latência incomodar, a Proposta 2 entra depois sem mudar a API nem o schema de
`sequencias` — é uma otimização incremental, não uma reescrita. A decisão está
registrada em [`docs/adr/0002-persist-custom-sequences.md`](../../adr/0002-persist-custom-sequences.md).

### Algoritmo de matching

Uma música `m` casa com a sequência `S = [s1..sn]` (n ≥ 1) se, e somente se,
as duas condições valem sobre `cifra(m)` normalizada para minúsculas:

- **(a) contiguidade na ordem:** existe `i` tal que
  `cifra_norm(m)[i:i+n] == [s1..sn]` normalizada. Ordem e repetição importam.
- **(b) contenção de vocabulário:** `set(cifra_norm(m)) ⊆ set(S)` — a música
  não pode ter **nenhum** acorde fora da sequência.

```python
def casa(cifra_norm, acordes_norm, alvo_norm, alvo_set):
    n = len(alvo_norm)
    if n == 0 or len(cifra_norm) < n:
        return False
    if not any(cifra_norm[i:i + n] == alvo_norm
               for i in range(len(cifra_norm) - n + 1)):
        return False
    return acordes_norm <= alvo_set          # (b)
```

`alvo_norm`/`alvo_set` são derivados uma vez por sequência, não por música.

Três pontos de precisão:

1. **Comparação de janela de tokens, não de substring de texto.** É equivalente
   ao `s in acorde` de `generate_data_set.py:13` sempre que (b) vale, porque
   (b) proíbe tokens que não sejam exatamente os da sequência; evita o falso
   positivo de borda (`Em;G` casando com `Em;G7`) e foi medido igual à tag nas
   6 (199/296/4/5/7/3 nesta fase).
2. **Minúsculas nas duas pontas**, como `generate_data_set.py:12`. Isso
   reproduz a tag **por construção** — medido nesta fase: as duas pontas em
   minúsculas dão os mesmos conjuntos das 6 (199/296/4/5/7/3, 0 faltando, 0
   sobrando). Consequência herdada e aceita: `Gm` e `GM` colapsam (o vocabulário
   do CSV tem 151 grupos que só diferem em caixa; na prática `GM` aparece em 1
   música e `Gm` em 5.733). Corrigir a grafia do dataset é outro problema, fora
   do escopo.
3. **Pré-cálculo no boot:** `Musica.__init__` guarda `cifra_norm` e
   `acordes_norm`; o custo de normalizar 3,5 M tokens é pago uma vez, não a
   cada busca.

A tag `SEQ_FAMOSA` deixa de ser fonte de runtime e vira **oráculo de teste**
(continua carregada em `musica.seqs_famosas`, `main.py:63`).

### Banco de dados

**SQLite da stdlib** (`sqlite3`), arquivo único em disco. Motivos, todos da
pesquisa (§3):

- zero dependência nova — já existe no `python:3.9-slim` (3.46.1) e no `.venv`
  (3.54.0);
- `UNIQUE` no banco resolve duplicata de sequência sem lock em Python;
- transação e `WAL` cobrem POST concorrente, se o gunicorn ganhar workers
  (hoje o `CMD` do `Dockerfile` usa o default de 1);
- SQL dá inspeção e correção manual sem escrever parser.

Descartados `dbm`/`shelve` e JSON em disco: reescrevem o arquivo inteiro a cada
escrita e não têm unicidade nem concorrência embutida. TinyDB exigiria linha
nova em `requirements.txt`.

### Persistência no container

O arquivo precisa sobreviver a `docker restart` **e** a `docker rm` + novo
`docker run`. Decisão:

- `Dockerfile`: `RUN mkdir -p /data`, `ENV CIFRAME_DB=/data/catalogo.db`,
  `VOLUME ["/data"]`.
- Comando documentado (`AGENTS.md`/`README.md`) passa a ser
  `docker run -v ciframe-data:/data -p 8080:8080 ciframe`.
- Fora do Docker (`python main.py`), default `var/catalogo.db`, criado no boot;
  `var/` entra no `.gitignore` e no `.dockerignore` (para um banco local não ser
  copiado para a imagem).

Com `VOLUME` declarado, até o comando nu do `AGENTS.md` sobrevive a
`docker restart` (volume anônimo); o volume nomeado é o que garante reuso entre
containers recriados. Custo: quem rodar sem `-v` deixa volumes anônimos órfãos —
documentado no ADR 0002.

### Esquema de dados (alto nível)

```sql
CREATE TABLE IF NOT EXISTS sequencias (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nome      TEXT    NOT NULL,
    acordes   TEXT    NOT NULL,   -- JSON array, grafia como digitada (exibição)
    chave     TEXT    NOT NULL UNIQUE,  -- ';'.join(minúsculas) — dedupe + matching
    criado_em TEXT    NOT NULL    -- ISO-8601 UTC
);
```

- `chave` é derivada de `acordes`, mas existe como coluna para o `UNIQUE`:
  `['C','G','Am','F']` e `['c','g','am','f']` são a mesma sequência;
  `['C','G','F','Am']` (ordem) e `['C','C','G']` (repetição) são sequências
  diferentes.
- Seed idempotente das 6 originais com `INSERT OR IGNORE`, na ordem de
  `main.py:40-45`, nomes de `data/mapeamento_sequencias_famosas.txt`; ids 1–6.
- Conexão por request (`sqlite3.connect`, `PRAGMA journal_mode=WAL`,
  `busy_timeout=5000`), fechada no `finally` — conexão de módulo não é segura
  sob fork do gunicorn.

### API

Todas as respostas continuam `json.dumps(...)` (string, `text/html`), inclusive
as novas; só o status code muda.

| Rota | Entrada | Saída |
|---|---|---|
| `GET /sequencias` | — | 200, lista ordenada por `id`: `[{id, nome, acordes:[...], criado_em}]` |
| `POST /sequencias` | JSON `{"nome"?: str, "acordes": [str, ...]}` | 201 + objeto criado; 400 inválido; 409 duplicata |
| `GET /similares?sequencia_id=N` | inteiro | 200, mesma forma de hoje (`main.py:210-220`), paginado em 100; 400 se não for inteiro; 404 se não existir |
| `GET /similares?sequencia=...` | formato legado | inalterado, `[]` para chave desconhecida |

- **Validação do POST:** 1 a 12 acordes; cada token `strip()`ado, não vazio, ≤ 20
  caracteres, sem `;` nem `,`; `nome` opcional (default
  `"Sequência de " + " - ".join(acordes)`).
- **409** devolve `{"erro": "sequencia ja cadastrada", "id": <existente>}` para a
  UI selecionar a sequência que já existe em vez de dar erro seco.
- **Legado:** `?sequencia=Bm,G,D,A` continua valendo; a resolução remove as
  vírgulas (como `main.py:191`), passa para minúsculas e procura no catálogo
  comparando com `chave.replace(';','')` — o catálogo é pequeno, não precisa de
  coluna extra. Mudança intencional e documentada: `?sequencia=cgamf` passa a
  funcionar (hoje devolve `[]`); as 6 grafias canônicas não mudam.
- **Precedência** em `/similares` (`main.py:184-197`): `acordes` >
  `id_unico_musica` > (`sequencia_id` > `sequencia`). `sequencia_id` vence
  `sequencia` se os dois vierem.

### Frontend

- `sequencia.js:2-37`: as 4 sequências literais saem; `SequenciaController`
  carrega `GET /sequencias` no init e mapeia `acordes: ["Bm","G",...]` para
  `[{acorde, cor: '#2E1C74'}]`, preservando o contrato que o template já usa
  (`df-hex`, `temAcorde`, `sequencia.html:6-8`). Estados de carregando/erro
  visíveis no painel esquerdo.
- `sequencia.js:63-90`: a busca passa a montar
  `similares?sequencia_id=<id>` (+ `&generos=`); `createChordsString` e o
  caminho de string legado saem do controller (o backend mantém o legado).
- `sequencia.html`: formulário no painel esquerdo — campo de acordes (separados
  por vírgula ou espaço), campo de nome opcional, botão "Cadastrar". No 201,
  recarrega o catálogo, seleciona a nova sequência e dispara a busca; no 409,
  seleciona a existente e avisa; no 400, mostra a mensagem do backend.
- Fica como está: `GENEROS` literal (`sequencia.js:43`, 51 itens × 52 do
  backend), `ng-hide="music.diferenca.length"` (`sequencia.html:43`) e a
  ausência de paginação na UI — nenhum dos três é requisito desta feature.

### Fluxo ponta a ponta (depois)

```
cadastro: formulário → POST /sequencias → valida → INSERT → 201 → GET /sequencias
busca:    clique → GET /similares?sequencia_id=N[&generos=X]
            → catalogo.buscar(N) → apply_filtro (main.py:266)
            → casa(cifra_norm, acordes_norm, alvo) por música
            → get_pagina(..., 100) → json.dumps → cards
```

## Alternativas consideradas e descartadas

- **Índice em memória, reconstruído no boot e no POST (sem tabela derivada).**
  Leitura rápida e schema mínimo, mas o boot passa a custar ~196 ms × tamanho do
  catálogo (50 sequências ≈ 10 s) e o POST só é visível no worker que o
  atendeu. Com 1 worker funciona; vira bug silencioso no dia em que alguém
  aumentar `--workers`. Descartada por acoplar a feature ao número de workers.
- **JSON em disco / `dbm` / `shelve`.** Zero SQL, mas reescreve o arquivo
  inteiro a cada POST e não tem `UNIQUE` nem transação — a duplicata e a
  concorrência teriam de ser resolvidas em Python, com mais código do que o
  `sqlite3` que já vem no runtime.
- **Manter as 6 no código e só as novas no banco.** Menos mudança, mas duas
  fontes de verdade para o mesmo botão e a divergência 6 (backend) × 4
  (frontend) continuaria; uma sequência nova duplicada de uma antiga não seria
  detectada. Contraria a decisão 1 da pesquisa (uma semântica só).
- **Regra só de contiguidade (a) ou só de vocabulário (b).** Inflam de 3× a
  2.700× e quebram a regressão exigida; "conjunto invertido" (o que
  `/similares?acordes=` faz) dá 5.768 contra 199 em `BmGDA`. Todas medidas na
  pesquisa (§1).
- **Volume como bind mount (`-v "$PWD/data:/data"`).** Inspecionável e sem
  volume órfão, mas suja o repo com arquivo binário, depende do CWD de quem
  roda e no macOS tem custo de I/O. O volume nomeado é mais previsível; o bind
  fica como opção documentada para quem quiser abrir o `.db`.

## Plano de validação

**Regressão obrigatória (a mesma para as duas propostas):**

1. Para cada uma das 6 sequências: conjunto de `id_unico_musica` devolvido por
   `/similares?sequencia_id=` == conjunto de músicas cuja tag contém o índice
   correspondente; 0 faltando, 0 sobrando.
2. Mesma comparação com `&generos=<gênero>` para todos os gêneros que tenham
   pelo menos uma música marcada.
3. Contagens de página em `BmGDA`: página 1 → 100, página 2 → 99, página 3 → 0.
4. Ordem **não** entra no critério (varia com `PYTHONHASHSEED` desde antes da
   feature, §2 da pesquisa); o teste compara conjuntos.

**Testes automatizados (novo `tests/`, pytest 8.4.2 já no `.venv`; criar um
`requirements-dev.txt` com `pytest` para reprodutibilidade, fora da imagem):**

- `test_matching.py` (puro, sem CSV): tabela-verdade de `casa` — ordem,
  repetição, acorde extra, `G` × `Gm`, `Em G` × música com `G7`, cifra vazia,
  caixa alta/baixa.
- `test_api.py` (Flask test client, `CIFRAME_DB` apontando para tmp):
  `GET /sequencias` com os 6 seeds; `POST` válido → 201 e aparece no `GET`;
  `POST` duplicado → 409 com o id existente; `POST` inválido (vazio, 13
  acordes, token com `;`) → 400; busca por `sequencia_id` de sequência nova
  devolve exatamente as músicas que casam; `sequencia_id` inexistente → 404.
- `test_regressao.py`: os 4 itens acima, contra a tag do CSV.
- `test_persistencia.py`: cria sequência, abre uma segunda conexão no mesmo
  arquivo (simula outro processo) e confere que ela está lá; reabre com
  `init_db` e confere que o seed não duplica.
- `test_legado.py`: `?sequencia=BmGDA`, `?sequencia=Bm,G,D,A` e
  `?sequencia=cgamf` devolvem o mesmo conjunto; chave desconhecida → `[]`.

**Container (obrigatório, porque o requisito é persistência):**

```
docker build -t ciframe .
docker run -d --name ciframe -v ciframe-data:/data -p 8080:8080 ciframe
curl -X POST localhost:8080/sequencias -H 'Content-Type: application/json' \
     -d '{"acordes":["Am","F","C","G"]}'
docker restart ciframe && curl localhost:8080/sequencias     # nova sequência presente
docker rm -f ciframe
docker run -d --name ciframe -v ciframe-data:/data -p 8080:8080 ciframe
curl localhost:8080/sequencias                               # idem, após recriar
```

**Manual:** cadastrar pelo formulário, buscar pela sequência nova, filtrar por
gênero, recarregar a página e confirmar que o catálogo veio do backend (as 6
aparecem, incluindo `Em-G` e `C-A7-Dm-G7`, que hoje não aparecem).

## Questões em aberto

1. **Catálogo aberto e anônimo** não tem rate limit nem moderação. Para um app
   local-only o risco é baixo, mas um script pode encher a tabela. Fora do
   escopo; se virar requisito, entra junto com `DELETE`/moderação.
2. **Editar/apagar sequência** não está no enunciado. O seed é inserido uma vez;
   remover exige SQL manual. Decidir na fase de plano se vale um `DELETE`.
3. **`contagem` por sequência no catálogo** não existe na Proposta 1 (custaria
   uma varredura por item). Se a UI quiser mostrar "199 músicas", isso é
   argumento para a Proposta 2.
4. **Volume:** nomeado (escolhido) × bind mount (mais inspecionável). O ADR 0002
   registra a escolha; trocar depois é mudar uma linha do comando e do
   `Dockerfile`.
5. **Grafia de acorde:** a comparação em minúsculas colapsa `Gm`/`GM` e afins,
   herdado do gerador. Corrigir o vocabulário do CSV é uma tarefa de dados
   separada.
6. **`?sequencia=` legado** fica para sempre ou é depreciado quando ninguém mais
   tiver link antigo? Mantido nesta feature por compatibilidade.

## Escopo explícito

**Dentro do escopo:**

- Tabela `sequencias` em SQLite, com seed idempotente das 6 originais.
- `GET /sequencias`, `POST /sequencias`, `GET /similares?sequencia_id=`.
- Matching (a)+(b) em tempo real para qualquer sequência do catálogo.
- `#/porsequencia` lendo o catálogo do backend e formulário de cadastro.
- Volume no `Dockerfile` e comando de execução documentado.
- Testes de matching, API, regressão e persistência; ADR 0002.

**Fora do escopo (e por quê):**

- Migrar músicas/gêneros para o banco — proibido pelo enunciado.
- Editar/apagar sequências, login, moderação, rate limit — não são requisito e
  mudam o modelo de ameaça.
- Paginação na UI e correção de `GENEROS`/`ng-hide` — dívidas pré-existentes,
  ortogonais à feature.
- Normalização/correção do vocabulário de acordes do CSV — tarefa de dados.
- Índice materializado (Proposta 2) — otimização prematura para 6 itens.
