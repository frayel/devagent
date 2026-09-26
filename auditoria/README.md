# Auditoria de produção

O auditor confere o site publicado contra o mundo, não contra o código. Nasceu do incidente de 26/09/2026: todos os testes passavam enquanto produção mostrava o Ibovespa a 130.000 pontos, valor de um fixture de teste.

Ele tem duas camadas:

| Camada | Onde | Quando roda | O que entrega |
|---|---|---|---|
| Determinística | `auditoria/auditar.py`, workflow `auditoria-producao.yml` | a cada 30 min no pregão, antes da abertura, após cada deploy | issue `producao-incorreta`, fechada sozinha quando volta a passar |
| Exploratória (LLM) | persona `docs/agents/auditor.md`, tarefa agendada no Jules | uma vez por dia | relatório e achados em `docs/auditoria/`, que viram issues pelo `auditoria-achados.yml` |

## Separação de poderes

Quem é auditado não altera o auditor. O `automerge.yml` recusa merge automático de PRs que mexam em:

- `auditoria/`
- `docs/agents/auditor.md`
- `.github/workflows/automerge.yml` e `.github/workflows/auditoria-*.yml`

Esses PRs recebem o label `revisao-humana` e esperam aprovação manual. Isso vale também para o auditor LLM quando ele propõe checagens novas.

## O que a camada determinística verifica

| Grupo | Checagens |
|---|---|
| Aplicação | `/healthz` 200, página 200, aviso legal presente, sem erros de JavaScript, gráficos Plotly desenhados com dados |
| Fonte independente | valor exibido a no máximo 1,5% do Yahoo Finance (ou Stooq, se o Yahoo falhar); fechamentos do gráfico a no máximo 0,5% |
| Frescor | gráfico chega ao pregão mais recente (calendário da B3 em `calendario.py`); coleta com menos de 45 min durante o pregão; coleta feita no último pregão fora dele |
| Coerência | variação % bate com a variação em pontos; variação diária abaixo de 12%; valor em faixa plausível; histórico ordenado, com pelo menos 15 pregões e sem datas de mais de 60 dias |
| Vazamento de teste | nenhum valor de `tests/fixtures/` aparece em produção |

Fonte independente fora do ar gera resultado `inconclusivo`, que não reprova.

## Rodar localmente

```
python -m auditoria.auditar                        # contra PRODUCTION_URL ou a URL padrão
python -m auditoria.auditar --url http://127.0.0.1:8000 --navegador --saida /tmp/aud
pytest -q auditoria
```

Código de saída: 0 sem falhas, 1 com falha, 3 produção inacessível.

## Contrato `/api/snapshot` (a implementar pelo desenvolvedor)

Hoje o auditor extrai os números do HTML, o que quebra se o template mudar. A aplicação deve expor o que a tela mostra, no formato abaixo. Quando o endpoint existir, o auditor passa a usá-lo e ainda confere se a página mostra o mesmo valor.

```json
{
  "gerado_em": "2026-09-28T14:37:00-03:00",
  "paineis": {
    "ibovespa": {
      "valor": 183476.86,
      "fechamento_anterior": 182050.10,
      "variacao_pct": 0.78,
      "coletado_em": "2026-09-28T14:30:00-03:00",
      "fonte": "brapi",
      "historico": {"datas": ["2026-08-17", "..."], "fechamentos": [176210.4, "..."]}
    }
  }
}
```

`fonte` é o nome do coletor que produziu o dado (`brapi` ou `yahoo`). O auditor usa esse campo para escolher uma referência diferente.

## Painel novo, checagem nova

Toda spec tem a seção **Invariantes de produção**. Ao publicar um painel, o desenvolvedor acrescenta o painel ao `/api/snapshot`. Um humano, ou o auditor LLM num PR com revisão humana, transforma as invariantes em funções `checar_*` em `auditar.py`, com teste em `auditoria/tests/`.
