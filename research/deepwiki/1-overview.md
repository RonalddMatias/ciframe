Title: Overview

URL Source: https://deepwiki.com/joaoarthurbm/ciframe/1-overview

Published Time: 2026-10-23T13:29:52.677186

Markdown Content:
Relevant source files
*   [.dockerignore](https://github.com/joaoarthurbm/ciframe/blob/fb970019/.dockerignore)
*   [AGENTS.md](https://github.com/joaoarthurbm/ciframe/blob/fb970019/AGENTS.md?plain=1)
*   [Dockerfile](https://github.com/joaoarthurbm/ciframe/blob/fb970019/Dockerfile)
*   [README.md](https://github.com/joaoarthurbm/ciframe/blob/fb970019/README.md?plain=1)
*   [docs/adr/0001-local-only-docker-deploy.md](https://github.com/joaoarthurbm/ciframe/blob/fb970019/docs/adr/0001-local-only-docker-deploy.md?plain=1)
*   [docs/adr/0003-lift-frontend-freeze.md](https://github.com/joaoarthurbm/ciframe/blob/fb970019/docs/adr/0003-lift-frontend-freeze.md?plain=1)
*   [main.py](https://github.com/joaoarthurbm/ciframe/blob/fb970019/main.py)
*   [musica.py](https://github.com/joaoarthurbm/ciframe/blob/fb970019/musica.py)
*   [requirements.txt](https://github.com/joaoarthurbm/ciframe/blob/fb970019/requirements.txt)

`deciframe` (also known as `ciframe`) is a chord-based song discovery application designed for musicians [AGENTS.md 3-5](https://github.com/joaoarthurbm/ciframe/blob/fb970019/AGENTS.md?plain=1#L3-L5)[README.md 1-6](https://github.com/joaoarthurbm/ciframe/blob/fb970019/README.md?plain=1#L1-L6). The application allows users to find songs based on artist names, song titles, musical genres, known chords, or famous chord progressions by cross-referencing user inputs against a curated dataset of song chords (cifras) [README.md 3-6](https://github.com/joaoarthurbm/ciframe/blob/fb970019/README.md?plain=1#L3-L6).

The system relies on a lightweight architecture consisting of a single-file Flask backend (`main.py`) that loads an in-memory CSV dataset at startup, paired with a static AngularJS 1.4.9 client (`static/`) served directly by the backend [AGENTS.md 9-13](https://github.com/joaoarthurbm/ciframe/blob/fb970019/AGENTS.md?plain=1#L9-L13)[README.md 8-9](https://github.com/joaoarthurbm/ciframe/blob/fb970019/README.md?plain=1#L8-L9).

Sources: [AGENTS.md 3-13](https://github.com/joaoarthurbm/ciframe/blob/fb970019/AGENTS.md?plain=1#L3-L13)[README.md 1-10](https://github.com/joaoarthurbm/ciframe/blob/fb970019/README.md?plain=1#L1-L10)[main.py 1-76](https://github.com/joaoarthurbm/ciframe/blob/fb970019/main.py#L1-L76)[musica.py 1-25](https://github.com/joaoarthurbm/ciframe/blob/fb970019/musica.py#L1-L25)

* * *

## High-Level Architecture

The system architecture is divided into three core tiers: a client-side Single Page Application (SPA), a Python/Flask REST API backend, and an in-memory data store initialized from a static CSV file at process startup.

Sources: [AGENTS.md 9-13](https://github.com/joaoarthurbm/ciframe/blob/fb970019/AGENTS.md?plain=1#L9-L13)[main.py 11-98](https://github.com/joaoarthurbm/ciframe/blob/fb970019/main.py#L11-L98)[musica.py 1-25](https://github.com/joaoarthurbm/ciframe/blob/fb970019/musica.py#L1-L25)

* * *

## 1.1. Getting Started and Deployment

The application supports local execution via a standard Python virtual environment (`python main.py` on port `5000`) as well as production-grade containerized deployment via Docker and Gunicorn (`gunicorn` on port `8080`) [AGENTS.md 18-33](https://github.com/joaoarthurbm/ciframe/blob/fb970019/AGENTS.md?plain=1#L18-L33)[README.md 11-31](https://github.com/joaoarthurbm/ciframe/blob/fb970019/README.md?plain=1#L11-L31)[Dockerfile 1-12](https://github.com/joaoarthurbm/ciframe/blob/fb970019/Dockerfile#L1-L12). Dependencies are declared in `requirements.txt`[requirements.txt 1-5](https://github.com/joaoarthurbm/ciframe/blob/fb970019/requirements.txt#L1-L5), and container exclusions are managed through `.dockerignore`[.dockerignore 1-4](https://github.com/joaoarthurbm/ciframe/blob/fb970019/.dockerignore#L1-L4). System health and operational readiness can be verified by querying the `/generos` endpoint [AGENTS.md 35-41](https://github.com/joaoarthurbm/ciframe/blob/fb970019/AGENTS.md?plain=1#L35-L41).

For detailed setup instructions, local virtualenv configuration, Docker image building, and deployment verification, see [Getting Started and Deployment](https://deepwiki.com/joaoarthurbm/ciframe/1.1-getting-started-and-deployment).

Sources: [AGENTS.md 18-41](https://github.com/joaoarthurbm/ciframe/blob/fb970019/AGENTS.md?plain=1#L18-L41)[README.md 11-31](https://github.com/joaoarthurbm/ciframe/blob/fb970019/README.md?plain=1#L11-L31)[requirements.txt 1-5](https://github.com/joaoarthurbm/ciframe/blob/fb970019/requirements.txt#L1-L5)[Dockerfile 1-12](https://github.com/joaoarthurbm/ciframe/blob/fb970019/Dockerfile#L1-L12)[.dockerignore 1-4](https://github.com/joaoarthurbm/ciframe/blob/fb970019/.dockerignore#L1-L4)

* * *

## 1.2. Repository Map and Conventions

The repository structure is organized into top-level application logic (`main.py`, `musica.py`), dataset artifacts (`data/`), data processing utilities (`scripts/`), client-side assets (`static/`), and architectural documentation (`docs/`) [AGENTS.md 9-16](https://github.com/joaoarthurbm/ciframe/blob/fb970019/AGENTS.md?plain=1#L9-L16)[README.md 8-9](https://github.com/joaoarthurbm/ciframe/blob/fb970019/README.md?plain=1#L8-L9). Project conventions include legacy raw JSON string serialization via `json.dumps` rather than standard Flask responses, an in-memory storage strategy without a traditional database, and the requirement of a server restart to reflect modifications made to underlying CSV datasets [AGENTS.md 43-47](https://github.com/joaoarthurbm/ciframe/blob/fb970019/AGENTS.md?plain=1#L43-L47). Additional development guidelines are maintained in `CONTRIB.md` and `.playground`[README.md 35](https://github.com/joaoarthurbm/ciframe/blob/fb970019/README.md?plain=1#L35-L35).

For a complete breakdown of project directories, file locations, coding conventions, and contribution workflows, see [Repository Map and Conventions](https://deepwiki.com/joaoarthurbm/ciframe/1.2-repository-map-and-conventions).

Sources: [AGENTS.md 43-47](https://github.com/joaoarthurbm/ciframe/blob/fb970019/AGENTS.md?plain=1#L43-L47)[README.md 35](https://github.com/joaoarthurbm/ciframe/blob/fb970019/README.md?plain=1#L35-L35)[main.py 1-168](https://github.com/joaoarthurbm/ciframe/blob/fb970019/main.py#L1-L168)[musica.py 1-25](https://github.com/joaoarthurbm/ciframe/blob/fb970019/musica.py#L1-L25)
