# deciframe

Descubra as músicas que você já sabe tocar (e ainda não faz ideia). Busque por
título/artista, gênero, pelos acordes que você já manja, ou por sequências de
acordes famosas — o deciframe cruza isso com uma base de cifras e sugere
músicas parecidas.

Stack: backend Flask (Python) servindo uma API JSON + um frontend AngularJS
estático, numa base de músicas carregada de um CSV em memória. O catálogo de
sequências de acordes é persistido em SQLite.

## Rodando localmente

### Com Docker

```
docker build -t ciframe .
docker run -v ciframe-data:/data -p 8080:8080 ciframe
```

Acesse [http://localhost:8080](http://localhost:8080). O volume
`ciframe-data` guarda o catálogo de sequências (`/data/catalogo.db`), que
sobrevive a reinícios e à recriação do container. Para inspecionar o banco,
use um bind mount (`-v "$PWD/var:/data"`). O matching das sequências é sempre
calculado em tempo real sobre o CSV em memória — mudar o CSV não exige rebuild
do banco.

### Com virtualenv

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Acesse [http://localhost:5000](http://localhost:5000).

---

Para convenções de contribuição, veja [CONTRIB.md](CONTRIB.md). Licença: [LICENSE](LICENSE).
