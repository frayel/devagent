---
id: 137
titulo: A fonte de referência da auditoria nunca é a que o produto usou
status: ready
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_137.py
---

## Problema
O usuário perguntou: "por que a verificação não pegou o +12,87%?" Uma das respostas está na própria auditoria. A regra do `PRODUTO.md` (linha 143) e do `devagent/agents/auditor.md` (seção 2) é que a prova vem de uma fonte que **não** seja a que o coletor usou. O código tenta cumprir isso em `auditoria/auditar.py:226-238`:

```python
def obter_referencia(evitar):
    for f in FONTES_REFERENCIA:               # ref_yahoo, ref_stooq
        if evitar and evitar.lower() in f.__name__:
            continue
```

`evitar` recebe o rótulo de fonte que o painel declara (`painel.fonte`, linha 811), e os rótulos reais são `mt5`, `yfinance`, `brapi` e `mt5+yfinance` (`app/collectors/mt5.py:161`). Os nomes das funções são `ref_yahoo` e `ref_stooq`. `"yfinance" in "ref_yahoo"` é falso, então, quando o produto declara `yfinance`, o Yahoo **não é pulado** e é usado como "fonte independente" contra um dado que veio do Yahoo. O mesmo vale para `mt5+yfinance`. Só o texto literal `yahoo` casaria, e nenhum rótulo real o usa.

Nesse caso a checagem `ibov.confere_com_fonte` compara o Yahoo com ele mesmo e passa, por construção. O achado de 26/10 (`docs/auditoria/achados/2026-10-26-ibov-variacao-implausivel.md`) cita exatamente uma "conferência com Yahoo Finance" como confirmação.

## Comportamento esperado
1. Uma tabela explícita liga cada referência às fontes do produto que ela representa:

   | Referência | Fontes do produto que a excluem |
   |---|---|
   | `ref_yahoo` | `yfinance`, `yahoo` |
   | `ref_stooq` | `stooq` |

   `mt5` e `brapi` não excluem nenhuma das duas, porque são outras origens.
2. `obter_referencia(evitar)` quebra o rótulo em partes por `+`, normaliza para minúsculas e pula toda referência cuja lista de exclusão cruze com essas partes. Rótulo desconhecido não pula nada, e o resultado carrega um aviso `fonte do produto desconhecida: <rótulo>`, visível no detalhe do resultado.
3. O detalhe de `ibov.confere_com_fonte`, `ibov.historico_confere` e das checagens novas da spec 138 passa a mostrar as duas pontas: `produto: <rótulo>; referência: <nome>`.
4. Se todas as referências forem excluídas, vale o comportamento que já existe: `ibov.fonte_independente` fica `inconclusivo` com os motivos. Uma referência não independente nunca vira `OK`.
5. `auditoria/README.md` ganha a tabela acima.

Esta spec não afrouxa nenhuma checagem: troca uma comparação que podia ser circular por outra honesta.

## Fontes de dados
As que já existem: Yahoo (`ref_yahoo`) e Stooq (`ref_stooq`). Plano B: `inconclusivo`, como hoje. Fonte nova fica para outra spec.

## Cálculos
Nenhum.

## Critérios de aceite
- [ ] `obter_referencia("yfinance")` pula `ref_yahoo` e devolve a referência do Stooq (as duas funções trocadas por falsas no teste).
- [ ] `obter_referencia("mt5+yfinance")` pula `ref_yahoo`.
- [ ] `obter_referencia("mt5")` e `obter_referencia("brapi")` usam `ref_yahoo` primeiro.
- [ ] `obter_referencia("yfinance")` com o Stooq fora do ar devolve `(None, erros)`, e `checar_referencia` produz `ibov.fonte_independente` como `inconclusivo`, sem nenhum `OK`.
- [ ] Rótulo desconhecido (`"xpto"`) não pula nada e aparece como aviso no detalhe.
- [ ] O detalhe de `ibov.confere_com_fonte` contém `produto: yfinance` e o nome da referência usada.
- [ ] Os testes de `auditoria/tests/test_auditar.py` seguem verdes, e nenhum limite numérico de `auditoria/auditar.py` muda.
- Arquivos tocados: `auditoria/auditar.py`, `auditoria/README.md`, o novo `tests/test_aceite_137.py`.

## Invariantes de produção
- O relatório da auditoria (`make audit`) mostra, em cada checagem contra fonte externa, a fonte do produto e a da referência, e elas nunca são a mesma.
- Com o produto declarando `yfinance` e o Stooq fora do ar, o resultado é `inconclusivo`, nunca `OK`.

## Fora do escopo
- Novas fontes de referência (Investing.com, B3).
- Alterar `devagent/agents/auditor.md` (a regra já está certa; o código é que não a cumpria).
- As checagens novas de variação do dia (spec 138).
