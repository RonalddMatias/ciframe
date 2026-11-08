# Relatório de testes — Sequências de Acordes Customizadas

> Apague este bloco de instruções antes de entregar.

## Cobertura

[O que tem teste automatizado, e o que cada teste verifica.]

## Teste de regressão obrigatório

As 6 sequências originais (`main.py`, linhas 40-45) precisam continuar
retornando os mesmos resultados de antes da migração para o banco de dados.

[Descreva como você verificou isso, e o resultado.]

## Números medidos na implementação

> Dados coletados na fase de implementação para a fase de testes usar. A
> narrativa de cobertura e a conclusão deste relatório continuam pendentes.

- Tag vs regra/endpoint, por sequência (0 faltando / 0 sobrando): `Bm-G-D-A`
  199; `C-G-Am-F` 296; `Em-G` 4; `C-A7-Dm-G7` 5; `Gm-F` 7; `C-C7-F-Fm` 3.
- Contagens de página em `BmGDA`: 100 / 99 / 0.
- Latência de `/similares?sequencia_id=1` (20 chamadas, Flask test client):
  mín. 210 ms, mediana 219 ms, p95 235 ms, máx. 252 ms.
- Container (`python:3.9-slim`): `POST` 201 → `docker restart` → sequência
  presente → `docker rm` + `docker run` com o volume `ciframe-data` →
  sequência presente; duplicata devolve 409 com o id existente.
- Render de `#/porsequencia` em Chrome headless: 6 sequências (20 hexágonos),
  incluindo `Em-G` e `C-A7-Dm-G7`; formulário presente; `GET /sequencias` 200.
- `pytest -q`: 48 passed em 12,31 s.

## Como rodar

```
[comando exato para rodar a suíte de testes]
```

## O que ficou de fora

[O que você decidiu não testar e por quê. Ser honesto aqui conta mais do que
fingir cobertura total.]
