# Plano — Sequências de Acordes Customizadas

Baseline: branch `feat/sequencias-customizadas`, HEAD `81bb459`. Executa a
**Proposta 1** de [`02-proposal.md`](02-proposal.md): SQLite + matching (a)+(b)
em tempo real, volume nomeado e frontend lendo o catálogo do backend.

Decisões fechadas nesta fase, além da proposta:

- **Sem `DELETE`/edição de sequência** — não é requisito; remoção continua sendo
  SQL manual, documentada no README. A API expõe só `GET`/`POST`.
- **Sem `contagem` por sequência** no catálogo — `GET /sequencias` devolve
  `id, nome, acordes, criado_em`; se um dia a UI precisar do número, é o gatilho
  para a Proposta 2.
- **Ordem de implementação:** regra → dados → persistência → API → container →
  frontend → testes, para que cada passo seja verificável sozinho e a regressão
  possa ser medida antes de qualquer mudança de UI.

Esforço estimado: 6–8 h em uma sessão de implementação (~11 passos). Nenhum
passo depende de serviço externo ou de nova dependência de runtime.

## Passos

1. [x] **Criar `matching.py` e `tests/test_matching.py`** (~45 min).
   - `normaliza(token)` = `token.strip().lower()`;
     `chave_de(acordes)` = `';'.join(normaliza(a) ...)`;
     `prepara_alvo(acordes)` devolve `(lista_norm, set_norm)`;
     `casa(cifra_norm, acordes_norm, alvo_norm, alvo_set)` exatamente como em
     [`02-proposal.md`](02-proposal.md#algoritmo-de-matching) — janela de tokens
     contígua + `acordes_norm <= alvo_set`.
   - Módulo puro: não importa `main.py`, `musica.py` nem Flask.
   - Tabela-verdade em `test_matching.py`: ordem importa; repetição importa;
     acorde extra exclui; `G` não casa dentro de `Gm`; `Em G` não casa com
     música que tenha `G7`; cifra vazia nunca casa; caixa alta/baixa colapsam.
   - **Feito quando:** `pytest tests/test_matching.py -q` verde.

2. [x] **Pré-computar normalização em `musica.py`** (~20 min).
   - No `__init__`, adicionar `self.cifra_norm` (lista de tokens em minúsculas)
     e `self.acordes_norm` (set). Manter `cifra` e `acordes` como estão para não
     mudar `/similares?acordes=` nem `/musicas`.
   - **Feito quando:** `/musicas` e `/acordes` devolvem o mesmo payload de antes
     (comparar tamanho/amostra) e o boot não passa de ~1 s além do atual.

3. [x] **Criar `catalogo.py`** (~1 h 30 min).
   - `DB_PATH = os.environ.get("CIFRAME_DB", "var/catalogo.db")`;
     `conectar()` por request com `row_factory`, `PRAGMA journal_mode=WAL` e
     `busy_timeout=5000`; fechar no `finally` de cada operação.
   - `init_db()`: cria o diretório do arquivo se faltar, cria a tabela e roda o
     seed idempotente das 6 originais com `INSERT OR IGNORE` (ordem de
     `main.py:40-45`, nomes de `data/mapeamento_sequencias_famosas.txt`,
     `criado_em` fixo/UTC). Não reescrever linhas existentes.
   - `listar()`, `buscar(id)`, `criar(nome, acordes)` e
     `resolver_legado(chave_sem_separador)`; `criar` deriva `chave` e trata
     `UNIQUE` devolvendo o id existente (`SequenciaDuplicada`).
   - **Feito quando:** rodar `init_db()` duas vezes no mesmo arquivo deixa
     exatamente 6 linhas; criar/reabrir em processo separado encontra a nova.

4. [x] **Expor a API em `main.py`** (~1 h 30 min).
   - Chamar `init_db()` no import; remover o dict literal `sequencias`
     (`main.py:40-45`) e `get_similares_por_sequencia` (vira busca por id).
   - `GET /sequencias` → 200, lista ordenada por `id`, `json.dumps(...)`.
   - `POST /sequencias` → valida 1–12 acordes, `strip()`, não vazio, ≤ 20
     caracteres, sem `;`/`,`; `nome` opcional com default
     `"Sequência de " + " - ".join(acordes)`; 201 criado, 400 inválido, 409
     `{"erro": ..., "id": <existente>}`.
   - `GET /similares?sequencia_id=N`: 400 se não inteiro, 404 se não existir;
     filtra com `apply_filtro`, aplica `casa` música a música, monta o mesmo
     dict de hoje (`main.py:210-220`) e pagina com `get_pagina(..., 100)`.
   - Precedência em `/similares`: `acordes` > `id_unico_musica` >
     (`sequencia_id` > `sequencia`). O ramo legado resolve pelo catálogo
     (`chave` sem `;`, minúsculas); desconhecida → `[]`.
   - **Feito quando:** `curl` dos quatro casos do plano de validação responde
     com status e corpo esperados, inclusive `?sequencia=cgamf` (passa a
     funcionar, mudança intencional).

5. [x] **Persistência no container** (~45 min).
   - `Dockerfile`: `RUN mkdir -p /data`, `ENV CIFRAME_DB=/data/catalogo.db`,
     `VOLUME ["/data"]`.
   - `.gitignore` e `.dockerignore`: adicionar `var/`.
   - Atualizar o comando em `AGENTS.md`/`README.md` para
     `docker run -v ciframe-data:/data -p 8080:8080 ciframe` e registrar a
     opção de bind mount para inspeção do `.db`.
   - **Feito quando:** o roteiro de container da proposta passa (POST →
     `restart` → ainda lá; `rm` + `run` com o mesmo volume → ainda lá).

6. [x] **Catálogo no frontend** (~45 min).
   - `sequencia.js:2-37`: remover as 4 sequências literais; carregar
     `GET /sequencias` no init e mapear `acordes: ["Bm","G",...]` para
     `[{acorde, cor: '#2E1C74'}]`, guardando `id`/`nome` no objeto da sequência
     (contrato atual de `df-hex`, `temAcorde` e `sequencia.html:6-8`).
   - Estados de carregando/erro no painel esquerdo; erro do `GET` não pode
     deixar a tela em branco.
   - **Feito quando:** `#/porsequencia` mostra as 6 (incluindo `Em-G` e
     `C-A7-Dm-G7`, que hoje não aparecem) sem erro no console.

7. [x] **Formulário de cadastro** (~1 h).
   - `sequencia.html`: no painel esquerdo, input de acordes (vírgula ou espaço),
     input de nome opcional e botão "Cadastrar"; desabilitar durante o POST.
   - `sequencia.js`: `POST /sequencias`; 201 → recarrega o catálogo, seleciona a
     nova e dispara a busca; 409 → seleciona a existente e avisa; 400 → mostra
     a mensagem do backend.
   - **Feito quando:** cadastrar `Am F C G` pelo browser cria a sequência, ela
     aparece no catálogo e a busca funciona; cadastrar a mesma de novo cai no
     409 sem duplicar.

8. [x] **Busca por id no frontend** (~30 min).
   - `sequencia.js:63-90`: montar `similares?sequencia_id=<id>` (+ `&generos=`)
     e remover `createChordsString` do controller (o backend mantém o legado).
   - **Feito quando:** clicar numa das 6 e numa nova devolve os mesmos cards
     que o caminho legado, inclusive com filtro de gênero.

9. [x] **Fechar a suíte de testes** (~1 h 30 min).
   - `requirements-dev.txt` com `pytest` (fora da imagem).
   - `test_api.py`: seeds no `GET`; POST válido/duplicado/inválido; busca por
     `sequencia_id` de sequência nova; `sequencia_id` inexistente → 404;
     `CIFRAME_DB` em `tmp_path`.
   - `test_persistencia.py`: nova conexão no mesmo arquivo vê a sequência;
     `init_db()` repetido não duplica o seed.
   - `test_legado.py`: `BmGDA`, `Bm,G,D,A` e `cgamf` → mesmo conjunto;
     desconhecida → `[]`.
   - `test_regressao.py`: para cada uma das 6, conjunto de `id_unico_musica` por
     sequência e por sequência+gênero (só gêneros com música marcada) == tag
     `SEQ_FAMOSA`; contagens de página em `BmGDA` 100/99/0; ordem ignorada.
   - **Feito quando:** `pytest -q` verde e o teste de regressão acusa 0 faltando
     / 0 sobrando nas 6.

10. [x] **Validação manual e de container** (~45 min).
    - Rodar o roteiro de container da proposta e o manual (cadastrar, buscar,
      filtrar por gênero, recarregar; catálogo com as 6).
    - Registrar no `04-test-report.md` os números medidos (contagens por
      sequência, latência p95 de 20 buscas, resultado do restart/rm).
    - **Feito quando:** todos os itens do roteiro passam e os números estão
      anotados para a fase de testes.

11. [x] **Fechar a fase** (~15 min).
    - Atualizar este plano se algum passo tiver mudado de fato (não deixar plano
      desatualizado).
    - Exportar a sessão da implementação para `sessions/04-implementacao.json`
      ao final dela (a sessão desta fase já vai para `sessions/03-plano.json`).

## Ajustes durante a implementação

Decisões que mudaram em relação ao texto original dos passos, registradas aqui
antes de seguir (nenhuma muda a API, o schema ou o comportamento visível):

- **`catalogo.caminho_db()` em vez de `DB_PATH` constante.** O caminho lê
  `CIFRAME_DB` a cada operação (default `var/catalogo.db`). O motivo é teste:
  `main.py` chama `init_db()` no import, então uma constante congelada no import
  impediria cada teste de apontar para o próprio `tmp_path`. O default e o
  comportamento em produção não mudam.
- **`Musica.to_dict()` novo, e `/musicas`/`/musica/<id>` passam a usá-lo.**
  Guardar `cifra_norm`/`acordes_norm` no `__dict__` os faria vazar no payload
  desses dois endpoints (que serializavam `__dict__`). `to_dict()` devolve
  exatamente as 12 chaves originais, na mesma ordem; o payload não muda.
- **`sys.intern` nos tokens normalizados.** Evita duplicar 3,5 M strings de
  acorde; as 6.653 formas distintas ficam compartilhadas.
- **Regressão por gênero no teste agrupa o resultado da regra em tempo real** em
  vez de fazer uma chamada HTTP por sequência × gênero (seriam ~60 s só nisso).
  O conjunto global continua sendo comparado via endpoint, e há um
  spot-check de endpoint com filtro de gênero para cada uma das 6. A suíte
  inteira roda em ~13 s.
- **`static/assets/css/app.css`** ganhou `.sequencia-nome` para o nome da
  sequência abaixo dos hexágonos.

## Arquivos afetados

| Arquivo | Mudança |
|---|---|
| `matching.py` (novo) | `normaliza`, `chave_de`, `prepara_alvo`, `casa` — regra pura (a)+(b). |
| `catalogo.py` (novo) | Conexão SQLite, `init_db` + seed das 6, `listar`/`buscar`/`criar`/`resolver_legado`, `SequenciaDuplicada`. |
| `musica.py` | `cifra_norm`/`acordes_norm` no `__init__`; `to_dict()` para preservar o payload de `/musicas` e `/musica/<id>`. |
| `main.py` | `init_db()` no import; `GET`/`POST /sequencias`; ramo `sequencia_id` e legado reescrito em `/similares`; sai o dict literal e `get_similares_por_sequencia`. |
| `Dockerfile` | `mkdir /data`, `ENV CIFRAME_DB`, `VOLUME ["/data"]`. |
| `.gitignore`, `.dockerignore` | Ignorar `var/` (banco local). |
| `AGENTS.md`, `README.md` | Comando de execução com `-v ciframe-data:/data`; nota sobre bind mount e remoção manual. |
| `static/assets/js/controllers/sequencia.js` | Catálogo via `GET`, formulário/`POST`, busca por `sequencia_id`; saem literais e `createChordsString`. |
| `static/templates/sequencia.html` | Formulário de cadastro, estados de carregando/erro e mensagens de 400/409. |
| `static/assets/css/app.css` | `.sequencia-nome` para o rótulo abaixo dos hexágonos. |
| `tests/` (novo: `test_matching.py`, `test_api.py`, `test_persistencia.py`, `test_legado.py`, `test_regressao.py`) | Cobertura da regra, API, persistência, legado e regressão. |
| `requirements-dev.txt` (novo) | `pytest` para reprodutibilidade, fora da imagem. |
| `docs/features/sequencias-customizadas/04-test-report.md` | Números medidos na validação (fase seguinte). |
| `docs/adr/0002-persist-custom-sequences.md` | Já existe; só ajustar se a implementação divergir da decisão. |

## Riscos e mitigação

| Risco | Como perceber | O que fazer |
|---|---|---|
| Regra nova diverge da tag nas 6 (caixa, borda `G`×`Gm`, tokem) | `test_regressao.py` com faltando/sobrando > 0 | Corrigir `casa`/normalização antes de seguir; comparar com `research_compare.py`. |
| Ordem dos resultados muda e quebra comparação | Teste falha por lista ordenada | Comparar **conjuntos** de `id_unico_musica`; ordem já varia com `PYTHONHASHSEED` (pesquisa §2). |
| Seed duplica ou sobrescreve em boot repetido | `GET /sequencias` com > 6 itens | `UNIQUE(chave)` + `INSERT OR IGNORE`; teste de persistência roda `init_db` 2×. |
| POST concorrente / múltiplos workers do gunicorn | `database is locked` no log | Conexão por request, `WAL`, `busy_timeout=5000`; hoje o `CMD` usa 1 worker. |
| Volume declarado mas `docker run` sem `-v` | Nova sequência some ao recriar o container | Volumes anônimos sobrevivem a `restart`, não a `rm`; documentar o comando nomeado e testar o fluxo completo. |
| Busca fica lenta (~196 ms/sequência) e a UI parece travada | p95 alto e tela sem retorno | Barra de progresso já existe (`sequencia.js:67`); medir e registrar; se incomodar, Proposta 2 depois, sem mudar API/schema. |
| `/similares` legado muda de comportamento | Teste de legado ou link antigo retorna diferente | `cgamf` passar a funcionar é intencional e documentado; as 6 grafias canônicas têm de dar o mesmo conjunto. |
| Erro no `GET /sequencias` deixa o painel vazio | Console/aba de rede no browser | Estado de erro explícito com botão de retry; nunca renderizar catálogo hardcoded de fallback (duas fontes de verdade). |
| `cifra` vazia (8.141 músicas) casa por acidente | Teste unitário de cifra vazia falha | `casa` retorna `False` quando `n == 0` ou `len(cifra_norm) < n`; teste cobre. |
| Banco local (`var/`) vaza para a imagem ou para o git | `git status`/`docker build` mostram o arquivo | `var/` nos dois ignore files; `init_db` cria o diretório em runtime. |
| Edição futura do CSV invalida resultados | Busca por sequência muda sem deploy | Comportamento esperado na Proposta 1 (não há índice); registrar no README que o matching é sempre em tempo real. |

## Definição de pronto

- [x] Qualquer visitante cadastra uma sequência pela página `#/porsequencia`,
      sem login, e recebe 201; duplicata retorna 409 com o id existente e a UI
      seleciona a sequência já cadastrada.
- [x] A sequência cadastrada aparece no catálogo após reload da página e pode
      ser usada para buscar músicas, com e sem filtro de gênero.
- [x] O catálogo da tela vem de `GET /sequencias` (nenhuma sequência hardcoded
      em JS) e mostra as 6 originais, incluindo `Em-G` e `C-A7-Dm-G7`.
- [x] As 6 originais produzem **o mesmo conjunto de `id_unico_musica`** de
      antes (por sequência e por sequência+gênero), com 0 faltando e 0
      sobrando; contagens de página em `BmGDA`: 100 / 99 / 0.
- [x] Persistência comprovada no container: sequência cadastrada sobrevive a
      `docker restart` e a `docker rm` + `docker run` com o volume
      `ciframe-data`.
- [x] Respostas continuam sendo `json.dumps(...)` (string, `text/html`),
      inclusive `GET`/`POST /sequencias`; `musicas`/`generos` continuam vindo
      do CSV em memória.
- [x] `?sequencia=` legado devolve o mesmo conjunto das 6 grafias canônicas;
      chave desconhecida devolve `[]`.
- [x] `pytest -q` verde cobrindo matching, API, persistência, legado e
      regressão; `requirements-dev.txt` versionado e `pytest` fora da imagem.
- [x] `Dockerfile` com `VOLUME`, `AGENTS.md`/`README.md` com o comando novo e
      ADR 0002 consistente com o que foi implementado.
- [ ] `04-test-report.md` preenchido com os números medidos e o resultado do
      teste de regressão; sessões das fases exportadas em `sessions/`.
      *Nesta fase os números já estão registrados no relatório e a sessão da
      implementação foi exportada; a narrativa de cobertura fica para a fase de
      testes.*