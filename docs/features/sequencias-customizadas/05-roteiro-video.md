# Roteiro do vídeo — Sequências de Acordes Customizadas

Meta: ~2min30, 1080p/30fps, com narração. O vídeo precisa mostrar a feature
funcionando no browser: catálogo vindo do backend, cadastro de sequência nova,
busca por ela, duplicata e persistência após reiniciar o container.

## Antes de gravar (fora do vídeo)

Precisa de internet: o `static/index.html` carrega Bootstrap, jQuery e
AngularJS de CDN. Sem rede o layout quebra.

```bash
# 1. Estado limpo: só as 6 sequências originais
docker rm -f ciframe-demo 2>/dev/null || true
docker volume rm ciframe-demo-data 2>/dev/null || true

# 2. Imagem (já existe nesta máquina; rebuild só se mudou código)
docker build -t ciframe .

# 3. Sobe com volume nomeado, que é o que prova a persistência
docker run -d --name ciframe-demo \
  -v ciframe-demo-data:/data \
  -p 8080:8080 ciframe

# 4. Espera o boot e confere que há 6
until curl -fsS http://localhost:8080/sequencias >/dev/null; do sleep 1; done
curl -s http://localhost:8080/sequencias \
  | python3 -c "import json,sys; print(len(json.load(sys.stdin)), 'sequencias')"
```

Checklist de gravação:

- [ ] `lsof -nP -iTCP:8080 -sTCP:LISTEN` vazio (porta livre).
- [ ] Abrir `http://localhost:8080/` e fazer um F5 para conferir o layout.
- [ ] Esconder a barra de favoritos (Cmd+Shift+B) e silenciar notificações.
- [ ] Aumentar a fonte do terminal (Cmd+) antes de gravar a parte do Docker.
- [ ] Testar o microfone e gravar em 1080p/30fps.
- [ ] Se errar, recomece do início: o catálogo precisa ter 6 itens no take final.

## Roteiro (take único)

### 0:00–0:15 — Abertura

**Tela:** home do deciframe (`http://localhost:8080/`).

**Ação:** clique no card “Conheces alguma dessas sequências de acordes?”.

**Fala:**
“O deciframe agora permite cadastrar sequências de acordes e buscar músicas
por elas. Vou mostrar a página Por Sequência.”

### 0:15–0:40 — Catálogo vindo do backend

**Tela:** `#/porsequencia`, coluna da esquerda.

**Ação:** passe o mouse pela lista e destaque as seis sequências. Pare em
“Sequência Em” (Em-G) e em “Sequência de C (Samba)” (C-A7-Dm-G7).

**Fala:**
“Antes o frontend tinha quatro sequências fixas em JavaScript. Agora ele
carrega o catálogo real do backend. As seis originais aparecem, inclusive
Em-G e C-A7-Dm-G7, que não existiam na tela antiga.”

**Resultado esperado:** seis blocos de hexágonos, cada um com seu nome.

### 0:40–1:05 — Buscar por uma sequência original

**Ação:** clique em “Sequência de Bm” (Bm-G-D-A) e espere os cards.

**Fala:**
“Ao clicar, a busca roda em tempo real na cifra das músicas. A sequência
precisa aparecer na ordem, numa janela contígua, e a música não pode ter
acordes fora dela. É a mesma regra que gerou a tag original: dá os mesmos 199
resultados do teste de regressão — aqui aparecem os 100 primeiros.”

**Resultado esperado:** grade de cards de música; botão “Encontrei essas
músicas” no topo da coluna esquerda.

### 1:05–1:40 — Cadastrar uma sequência nova

**Ação:** no formulário “Cadastrar nova sequência”:
1. em “Acordes”, digite `G, D, Em, C`;
2. em “Nome (opcional)”, digite `Progressão pop (G-D-Em-C)`;
3. clique em “Cadastrar”.

**Fala:**
“Qualquer visitante cadastra uma sequência, sem login. Eu digito os acordes na
ordem, separados por vírgula, e um nome opcional.”

**Resultado esperado:** mensagem “Sequência cadastrada!”, sétimo item no
catálogo já selecionado e a busca disparando nele (252 músicas no total; os 100
primeiros cards na tela).

### 1:40–1:55 — A sequência nova já busca

**Ação:** role a grade de resultados devagar e volte ao topo.

**Fala:**
“A sequência nova entra no catálogo e já pode ser usada para buscar, do mesmo
jeito que as originais.”

### 1:55–2:15 — Duplicata não duplica

**Ação:** no formulário, digite `g d em c` (minúsculas, sem nome) e clique em
“Cadastrar”.

**Fala:**
“O cadastro normaliza maiúsculas, minúsculas e espaços. Se a sequência já
existe, nada é duplicado: o app avisa e seleciona a que já está no catálogo.”

**Resultado esperado:** “Essa sequência já existe; selecionando a cadastrada.”,
a mesma grade de resultados e o catálogo continuando com sete itens.

### 2:15–2:40 — Persistência no banco

**Ação:** troque para o terminal e rode:

```bash
docker restart ciframe-demo
```

Espere o container subir (~5 s), volte ao browser e aperte F5.

**Fala:**
“O catálogo fica num SQLite dentro do volume Docker. Reiniciando o container, a
sequência continua lá — não voltou para as seis originais.”

**Resultado esperado:** catálogo com sete sequências depois do reload,
incluindo “Progressão pop (G-D-Em-C)”.

### 2:40–2:50 — Fechamento

**Tela:** catálogo com as sete sequências.

**Fala:**
“Tudo isso sem mexer no CSV de músicas e sem precisar de um novo deploy para
cada sequência cadastrada.”

Fim da gravação.

## Se sobrar tempo (opcional, +15 s cada)

- Abrir o DevTools na aba Network e mostrar `GET /sequencias` e
  `GET /similares?sequencia_id=7` respondendo 200 depois do cadastro.
- Testar o link antigo `http://localhost:8080/#/porsequencia` com
  `/similares?sequencia=BmGDA` via curl, mostrando que a compatibilidade
  continua.
- Navegar pelo catálogo só com Tab + Enter, mostrando o acesso por teclado.

## Erros comuns a evitar

- **Não comece com o banco sujo.** Se o catálogo já tiver 7+ itens, refaça o
  “Estado limpo” antes do take.
- **Não digite 13 acordes nem acorde com `;`/`,` dentro:** o formulário aceita,
  mas o backend devolve 400 — fora do escopo da demonstração feliz.
- **Espere o “Carregando sequências...” sumir** antes de clicar em uma
  sequência; clicar durante o load não dispara busca.
- **Não use `docker run --rm`** na demo de persistência: o volume nomeado
  sobrevive, mas o `--rm` atrapalha o `restart` se o container já tiver saído.
- **F5 depois do restart**, senão a página continua com o estado em memória do
  Angular e não prova nada.
- Se o CSS não carregar, é falta de internet (CDN), não bug da feature.

## Depois de gravar

Salve em `docs/features/sequencias-customizadas/demo-sequencias-customizadas.mp4`
(ou `.mov`; se for GIF, mantenha abaixo de ~20 MB) e confira o arquivo antes de
commitar:

```bash
ls -lh docs/features/sequencias-customizadas/demo-sequencias-customizadas.*
git add docs/features/sequencias-customizadas/demo-sequencias-customizadas.*
git commit -m "Adiciona vídeo de demonstração das sequências customizadas"
```

Opcional, para gerar um GIF a partir do vídeo:

```bash
ffmpeg -i demo.mov -vf "fps=12,scale=960:-1" demo.gif
```

Limpeza do ambiente da demo:

```bash
docker rm -f ciframe-demo
docker volume rm ciframe-demo-data
```

## Plano B: gravar sem Docker (localhost:5000)

Se o Docker atrapalhar a gravação, rode pelo virtualenv — a persistência
continua sendo SQLite:

```bash
rm -f var/catalogo.db var/catalogo.db-shm var/catalogo.db-wal
source .venv/bin/activate
python main.py          # http://localhost:5000/#/porsequencia
```

Para o bloco de persistência, `Ctrl+C` e `python main.py` de novo; o arquivo
`var/catalogo.db` sobrevive e o catálogo continua com sete.
