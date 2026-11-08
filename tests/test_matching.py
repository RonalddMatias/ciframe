# coding: utf-8
import pytest

from matching import casa, chave_de, normaliza, prepara_alvo


def alvo(acordes):
    return prepara_alvo(acordes)


def musica(cifra):
    norm = [normaliza(token) for token in cifra]
    return norm, set(norm)


def test_normaliza_remove_espacos_e_caixa():
    assert normaliza('  Bm ') == 'bm'
    assert normaliza('G7') == normaliza('g7')


def test_chave_de_normaliza_e_preserva_ordem():
    assert chave_de(['C', 'G', 'Am', 'F']) == 'c;g;am;f'
    assert chave_de(['C', 'G', 'F', 'Am']) == 'c;g;f;am'
    assert chave_de(['C', 'C', 'G']) == 'c;c;g'


def test_ordem_importa():
    alvo_norm, alvo_set = alvo(['Bm', 'G', 'D', 'A'])
    cifra_norm, acordes_norm = musica(['Bm', 'G', 'A', 'D'])
    assert casa(cifra_norm, acordes_norm, alvo_norm, alvo_set) is False


def test_repeticao_na_sequencia_importa():
    alvo_norm, alvo_set = alvo(['C', 'C', 'G'])
    cifra_norm, acordes_norm = musica(['C', 'G'])
    assert casa(cifra_norm, acordes_norm, alvo_norm, alvo_set) is False


def test_repeticao_na_cifra_nao_atrapalha():
    alvo_norm, alvo_set = alvo(['C', 'G'])
    cifra_norm, acordes_norm = musica(['C', 'C', 'G'])
    assert casa(cifra_norm, acordes_norm, alvo_norm, alvo_set) is True


def test_acorde_extra_exclui():
    alvo_norm, alvo_set = alvo(['Em', 'G'])
    cifra_norm, acordes_norm = musica(['Em', 'G', 'D'])
    assert casa(cifra_norm, acordes_norm, alvo_norm, alvo_set) is False


def test_g_nao_casa_dentro_de_gm():
    alvo_norm, alvo_set = alvo(['G'])
    cifra_norm, acordes_norm = musica(['Gm'])
    assert casa(cifra_norm, acordes_norm, alvo_norm, alvo_set) is False


def test_em_g_nao_casa_com_musica_com_g7():
    alvo_norm, alvo_set = alvo(['Em', 'G'])
    cifra_norm, acordes_norm = musica(['Em', 'G7'])
    assert casa(cifra_norm, acordes_norm, alvo_norm, alvo_set) is False


def test_janela_precisa_ser_contigua():
    alvo_norm, alvo_set = alvo(['Bm', 'D'])
    cifra_norm, acordes_norm = musica(['Bm', 'G', 'D'])
    assert casa(cifra_norm, acordes_norm, alvo_norm, alvo_set) is False


def test_cifra_vazia_nunca_casa():
    alvo_norm, alvo_set = alvo(['Bm', 'G'])
    assert casa([], set(), alvo_norm, alvo_set) is False


def test_alvo_vazio_nunca_casa():
    alvo_norm, alvo_set = alvo([])
    cifra_norm, acordes_norm = musica(['Bm'])
    assert casa(cifra_norm, acordes_norm, alvo_norm, alvo_set) is False


def test_cifra_menor_que_sequencia_nao_casa():
    alvo_norm, alvo_set = alvo(['Bm', 'G', 'D', 'A'])
    cifra_norm, acordes_norm = musica(['Bm', 'G'])
    assert casa(cifra_norm, acordes_norm, alvo_norm, alvo_set) is False


def test_caixa_alta_e_baixa_colapsam():
    alvo_norm, alvo_set = alvo(['Bm', 'G'])
    cifra_norm, acordes_norm = musica(['bm', 'g'])
    assert casa(cifra_norm, acordes_norm, alvo_norm, alvo_set) is True


@pytest.mark.parametrize('cifra', [
    ['Bm', 'G', 'D', 'A'],
    ['A', 'Bm', 'G', 'D', 'A'],
    ['Bm', 'G', 'D', 'A', 'A'],
])
def test_casa_quando_janela_e_vocabulario_valem(cifra):
    alvo_norm, alvo_set = alvo(['Bm', 'G', 'D', 'A'])
    cifra_norm, acordes_norm = musica(cifra)
    assert casa(cifra_norm, acordes_norm, alvo_norm, alvo_set) is True
