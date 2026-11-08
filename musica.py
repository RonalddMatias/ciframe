# coding: utf-8
import sys

from matching import normaliza


class Musica:

    def __init__(self, id_artista, nome_artista, id_musica, nome_musica,
    
            genero, popularidade, seqs_famosas, tom, cifra):

            self.id_artista = id_artista
            self.nome_artista = nome_artista
            
            self.id_musica = id_musica
            self.nome_musica = nome_musica

            self.genero = genero
            self.popularidade = popularidade
            self.tom = tom
            self.cifra = cifra
            self.acordes = list(set(cifra))
            self.seqs_famosas = seqs_famosas

            # Normalização pré-computada uma vez por música, usada pelo matching
            # em tempo real. sys.intern compartilha as strings do vocabulário
            # (6.653 tokens) em vez de duplicar cada ocorrência.
            self.cifra_norm = [sys.intern(normaliza(token)) for token in cifra]
            self.acordes_norm = set(self.cifra_norm)

            self.id_unico_musica = '%s_%s' % (id_artista, id_musica)

            self.url = 'http://www.cifraclub.com.br/%s/%s' % (id_artista, id_musica)

    def to_dict(self):
        """Payload público da música, sem os campos derivados do matching.

        Mantém exatamente as chaves (e a ordem) que ``__dict__`` expunha antes
        de ``cifra_norm``/``acordes_norm`` existirem, para não mudar
        ``/musicas`` nem ``/musica/<id>``.
        """
        return {
            'id_artista': self.id_artista,
            'nome_artista': self.nome_artista,
            'id_musica': self.id_musica,
            'nome_musica': self.nome_musica,
            'genero': self.genero,
            'popularidade': self.popularidade,
            'tom': self.tom,
            'cifra': self.cifra,
            'acordes': self.acordes,
            'seqs_famosas': self.seqs_famosas,
            'id_unico_musica': self.id_unico_musica,
            'url': self.url,
        }

    def __str__(self):
        return '%s,%s,%s' % (self.id_unico_musica, self.genero, self.popularidade)
