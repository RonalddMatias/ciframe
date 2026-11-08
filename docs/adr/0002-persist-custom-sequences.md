# Persistir o catálogo de sequências em SQLite e calcular o matching em tempo real

O catálogo de sequências "famosas" era um dicionário de seis chaves dentro de
`main.py`, e a busca não calculava nada: apenas lia a coluna `SEQ_FAMOSA`, uma
tag pré-computada no CSV por `scripts/generate_data_set.py`. A página
`#/porsequencia` tinha outras quatro sequências literais em JavaScript, então o
que o usuário via nem correspondia ao que o backend sabia responder. O requisito
novo é que qualquer visitante cadastre uma sequência e busque por ela, sem
login, e que o catálogo sobreviva a reinícios do servidor — ou seja, o catálogo
precisa sair do código e do CSV e virar estado persistido.

Decidimos introduzir **SQLite da biblioteca padrão** como a única persistência
do projeto, num arquivo único montado em `/data` por um volume nomeado, com uma
tabela `sequencias` (`id`, `nome`, `acordes` em JSON, `chave` normalizada com
`UNIQUE`, `criado_em`). As seis sequências originais são inseridas de forma
idempotente no boot (`INSERT OR IGNORE`), na mesma ordem do dicionário que
existia em `main.py:40-45`, e passam a ser linhas comuns do catálogo — não há
mais distinção entre "sequência do sistema" e "sequência de usuário".

O matching passa a ser calculado em tempo real, com a mesma regra que gerou a
tag: a sequência aparece como janela contígua de acordes na cifra **(a)** e a
música não tem nenhum acorde fora do conjunto da sequência **(b)**
(`scripts/generate_data_set.py:7-24`). A tag `SEQ_FAMOSA` deixa de ser fonte de
runtime e vira oráculo de teste. A escolha de manter exatamente essa regra, em
vez de uma definição mais intuitiva de "a sequência aparece na música", é o que
faz a regressão das seis valer por construção: só contiguidade inflaria os
resultados de 3× a 780×, e só vocabulário, de 30× a 2.700×.

SQLite foi escolhido porque já vem no `python:3.9-slim` e no runtime local (não
adiciona dependência nem muda o build além do volume), porque `UNIQUE` e
transação resolvem duplicata e POST concorrente sem código de lock em Python, e
porque um arquivo `.db` é inspecionável com qualquer cliente SQL. As
alternativas foram descartadas: `dbm`/`shelve` e JSON em disco reescrevem o
arquivo inteiro a cada escrita e não têm unicidade nem concorrência embutida;
TinyDB exigiria uma dependência nova; e manter as seis no código, com só as
novas no banco, criaria duas fontes de verdade para o mesmo botão — exatamente o
problema que a feature veio resolver.

A consequência mais visível é no deploy. Antes desta mudança, um arquivo escrito
em runtime sobrevivia a `docker restart` mas desaparecia no `docker run`
seguinte, porque o `Dockerfile` não declarava `VOLUME` e o comando nu não montava
nada — medido na fase de pesquisa. Agora o `Dockerfile` declara
`VOLUME ["/data"]` e `CIFRAME_DB=/data/catalogo.db`, e o comando documentado
ganha `-v ciframe-data:/data`. Quem rodar sem `-v` ainda sobrevive a restart
(volume anônimo), mas não reaproveita o banco num container recriado; isso fica
documentado no `AGENTS.md` e no `README.md`.

O custo aceito é a latência: aplicar a regra sobre 67.585 músicas leva ~196 ms
por sequência (1,17 s para as seis), contra 1–15 ms do handler que só lia a tag.
Para um app local, com barra de progresso na tela, é aceitável — e o caminho de
saída, se o catálogo crescer, é materializar as associações numa tabela
`sequencia_musicas` e responder por consulta, sem mudar a API nem o schema de
`sequencias`. Também são consequências aceitas: o catálogo é aberto e anônimo,
sem rate limit nem moderação; a comparação é feita em minúsculas, como no
gerador, então `Gm` e `GM` colapsam (herdado do dataset, não desta decisão); e o
frontend AngularJS volta a ser tocado, o que o ADR 0003 já permite.

Não há migração de dados: o banco nasce vazio e é semeado no boot. Reverter a
decisão é remover o volume e voltar o commit; nenhum dado de usuário existente
fica órfão.
