# coding: utf-8
"""Script de pesquisa da feature "Sequências de Acordes Customizadas".

Compara o matching atual (tag SEQ_FAMOSA do CSV) com regras calculadas em tempo
real sobre `musica.cifra`, e mede o custo de cada uma.

Roda com: .venv/bin/python docs/features/sequencias-customizadas/research_compare.py

O parser abaixo é uma cópia fiel de `main.py:49-63` (mesmo `readline`, mesmo
`replace('"','').replace('NA','')`, mesmo `limpa_cifra`), para que os números
sejam os do processo que a aplicação realmente carrega.
"""
import sys
import time

CSV = 'data/top/dataset_final.csv'

# main.py:40-45 — chave sem separador -> (id da tag, acordes na ordem do
# data/mapeamento_sequencias_famosas.txt)
SEQUENCIAS = {
    'BmGDA': (0, ['Bm', 'G', 'D', 'A']),
    'CGAmF': (1, ['C', 'G', 'Am', 'F']),
    'EmG': (2, ['Em', 'G']),
    'CA7DmG7': (3, ['C', 'A7', 'Dm', 'G7']),
    'GmF': (4, ['Gm', 'F']),
    'CC7FFm': (5, ['C', 'C7', 'F', 'Fm']),
}


def limpa_cifra(raw_cifra):
    cifra = []
    for m in raw_cifra:
        if m.strip() != '':
            if '|' in m:
                acorde = m.split('|')[0].split()[0]
                cifra.append(acorde)
            else:
                cifra += m.split()
    return cifra


def load():
    songs = []
    with open(CSV) as f:
        f.readline()
        for line in f:
            line = line.replace('"', '').replace('NA', '')[:-1]
            musica = line.split(',')
            cifra = limpa_cifra(musica[8].split(';')) if musica[8] != '' else []
            songs.append({
                'id': '%s_%s' % (musica[0], musica[1]),
                'popularidade': int(musica[5].replace('.', '')),
                'cifra': cifra,
                'acordes': list(set(cifra)),
                'seqs_famosas': musica[7].split(';'),
            })
    return songs


# --- regras candidatas -------------------------------------------------------

def match_tag(song, id_seq):
    """O que o código atual faz: pertinência à tag do CSV."""
    return str(id_seq) in song['seqs_famosas']


def match_contiguo(song, chords):
    """(a) a sequência aparece contígua e na ordem dentro da cifra."""
    n = len(chords)
    cifra = song['cifra']
    return any(cifra[i:i + n] == chords for i in range(len(cifra) - n + 1))


def match_vocabulario(song, chords):
    """(b) todo acorde usado na música pertence à sequência."""
    return set(song['acordes']) <= set(chords)


def match_legado(song, chords):
    """(a) e (b), que é o que scripts/generate_data_set.py:7-24 computou."""
    return match_contiguo(song, chords) and match_vocabulario(song, chords)


def match_conjunto(song, chords):
    """Alternativa frouxa: só exige que os acordes da sequência existam."""
    return set(chords) <= set(song['acordes'])


def match_subsequencia(song, chords):
    """Alternativa: ordem importa, mas aceita acordes no meio."""
    it = iter(song['cifra'])
    return all(c in it for c in chords)


def main():
    t0 = time.time()
    songs = load()
    t_load = time.time() - t0
    tokens = sum(len(s['cifra']) for s in songs)
    print('## Carga')
    print('musicas: %d | carga: %.2fs | tokens de cifra: %d | media: %.2f'
          % (len(songs), t_load, tokens, tokens / float(len(songs))))
    print('max tokens numa cifra: %d' % max(len(s['cifra']) for s in songs))
    tagged = sum(1 for s in songs if s['seqs_famosas'] != [''])
    print('linhas com tag preenchida: %d (%.2f%% do total)'
          % (tagged, 100.0 * tagged / len(songs)))

    print('\n## Comparação das regras (nº de músicas)')
    print('| seq | acordes | tag | (a) contíguo | (b) vocabulário | (a)+(b) | conjunto | subseq |')
    print('|---|---|---|---|---|---|---|---|')
    for key, (id_seq, chords) in SEQUENCIAS.items():
        counts = [
            sum(1 for s in songs if match_tag(s, id_seq)),
            sum(1 for s in songs if match_contiguo(s, chords)),
            sum(1 for s in songs if match_vocabulario(s, chords)),
            sum(1 for s in songs if match_legado(s, chords)),
            sum(1 for s in songs if match_conjunto(s, chords)),
            sum(1 for s in songs if match_subsequencia(s, chords)),
        ]
        print('| %s | %s | %s |' % (key, ' '.join(chords), ' | '.join(map(str, counts))))

    print('\n## Igualdade com a tag (conjunto de id_unico_musica)')
    for key, (id_seq, chords) in SEQUENCIAS.items():
        tag = set(s['id'] for s in songs if match_tag(s, id_seq))
        legado = set(s['id'] for s in songs if match_legado(s, chords))
        print('%s: tag=%d legado=%d iguais=%s  faltam=%d  extras=%d'
              % (key, len(tag), len(legado), tag == legado,
                 len(tag - legado), len(legado - tag)))

    print('\n## Custo do matching em tempo real')
    t0 = time.time()
    for key, (id_seq, chords) in SEQUENCIAS.items():
        sum(1 for s in songs if match_legado(s, chords))
    t_all = time.time() - t0
    print('6 sequências sobre %d músicas: %.3fs (%.1f ms por sequência)'
          % (len(songs), t_all, 1000 * t_all / 6))

    print('\n## Duplicata e normalização')
    print("'C;C7;F;Fm' vs 'c;c7;f;fm' -> mesma chave após casefold")
    print("'C;G;Am;F' vs 'C;F;Am;G' -> chaves diferentes (ordem importa)")
    print("'C;C' vs 'C' -> chaves diferentes (repetição importa)")


if __name__ == '__main__':
    sys.exit(main())
