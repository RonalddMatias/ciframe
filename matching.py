# coding: utf-8
"""Regra pura de matching entre uma sequência de acordes e a cifra de uma música.

Reproduz a regra (a)+(b) de ``scripts/generate_data_set.py:7-24``, que gerou a
tag ``SEQ_FAMOSA``:

(a) contiguidade na ordem -- a sequência é uma janela contígua de tokens da
    cifra (ordem e repetição importam);
(b) contenção de vocabulário -- a música não tem nenhum acorde fora do conjunto
    de acordes da sequência.

O módulo não importa ``main.py``, ``musica.py`` nem Flask: é testável sozinho.
"""


def normaliza(token):
    """Forma canônica de um acorde: sem espaços nas bordas, minúsculas."""
    return token.strip().lower()


def chave_de(acordes):
    """Chave de deduplicação: ``';'.join`` dos acordes normalizados."""
    return ';'.join(normaliza(acorde) for acorde in acordes)


def prepara_alvo(acordes):
    """Deriva uma vez por sequência a lista ordenada e o conjunto normalizados."""
    alvo_norm = [normaliza(acorde) for acorde in acordes]
    return alvo_norm, set(alvo_norm)


def casa(cifra_norm, acordes_norm, alvo_norm, alvo_set):
    """True se a música casa com a sequência segundo (a) e (b).

    ``cifra_norm`` é a lista de tokens da cifra normalizados (ordem e
    repetições preservadas); ``acordes_norm`` é o conjunto desses tokens;
    ``alvo_norm``/``alvo_set`` vêm de :func:`prepara_alvo`.
    """
    n = len(alvo_norm)
    if n == 0 or len(cifra_norm) < n:
        return False

    # (a) janela contígua de tokens, na mesma ordem.
    if not any(cifra_norm[i:i + n] == alvo_norm
               for i in range(len(cifra_norm) - n + 1)):
        return False

    # (b) nenhum acorde da música fora do vocabulário da sequência.
    return acordes_norm <= alvo_set
