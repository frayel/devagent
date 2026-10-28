from app.services.sistema import Item, PROBLEMA, ATENCAO, OK


def test_pedido_errado():
    i = Item("Coletor X", PROBLEMA, "HTTP 404 em ativo")
    assert i.causa == "pedido inválido ou ativo desconhecido (HTTP 404)"
    assert (
        i.acao == "corrigir o pedido no coletor Coletor X; o servidor está respondendo"
    )

    i = Item("Coletor X", PROBLEMA, "Erro HTTP 400 bad request")
    assert i.causa == "pedido inválido ou ativo desconhecido (HTTP 400)"


def test_fonte_fora_do_ar():
    i = Item("Fonte Y", PROBLEMA, "HTTP 503 Service Unavailable")
    assert i.causa == "fonte indisponível ou recusando a chave (HTTP 503)"
    assert i.acao == "aguardar, ou conferir a chave no Render"

    i = Item("Fonte Y", PROBLEMA, "HTTP 429 Too Many Requests")
    assert i.causa == "fonte indisponível ou recusando a chave (HTTP 429)"


def test_banco_incompleto():
    i = Item("Banco", PROBLEMA, "relation 'tabela' does not exist")
    assert i.causa == "esquema do banco incompleto"
    assert i.acao == "falta migração; ver spec do Consultor"


def test_integracao_sem_chamadas():
    i = Item("Integração Z", ATENCAO, "configurada, mas sem chamadas desde o início")
    assert i.causa == "configurada, mas nunca chamada"
    assert i.acao == "verificar o pipeline que a usa"


def test_erro_desconhecido():
    i = Item("Algo", PROBLEMA, "um erro estranho aconteceu")
    assert i.causa == "causa não classificada"
    assert i.acao == "ver o detalhe e abrir issue"


def test_ok_nao_tem_causa():
    i = Item("Tudo Certo", OK, "funciona")
    assert i.causa == ""
    assert i.acao == ""
