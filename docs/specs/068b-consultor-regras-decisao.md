---
id: 068b
titulo: Consultor · Regras de Decisão e Interface de Recomendações
status: ready
esforco: G
---

## Problema
Segunda fatia do consultor, finalizando a especificação 068 original. Tendo a infraestrutura da 068a, agora implementaremos o motor lógico que determina se o usuário deve Comprar, Vender ou Aguardar uma ação específica do Ibovespa baseada puramente em indicadores técnicos, exibindo isso numa interface limpa.

## Comportamento esperado
- O `GET /consultor` deixa de exibir um placeholder e passa a mostrar o resultado real.
- Agrupamento na página, nesta ordem: Comprar, Vender, Aguardar e Sem sinal (este recolhido por padrão).
- Cada linha mostra ticker, preço, regra disparada, motivo com os números que a acionaram, gatilho (para Aguardar) ou condição de invalidação (para Comprar e Vender), fonte do dado e horário da coleta.
- Uma seção recolhível "Como o consultor decide" lista as regras e os limiares. Os limiares devem ser lidos das próprias constantes do backend (`app/consultor/regras.py`), e não duplicados via texto estático.
- O grau de confiança no cabeçalho diz "Baixa: regra ainda sem histórico medido".

## Fontes de dados
- Os dados recolhidos pelo `app/agendador.py` e populados no cache local conforme implementado na spec 068a.
- Caso o ativo tenha menos de 220 pregões, ele deve ser alocado em "Sem sinal".
- Caso a API de coleta quebre totalmente, a página `/consultor` deve renderizar um graceful fallback "Dados do consultor indisponíveis", sem afetar a página inicial do site.

## Cálculos
Para o último dia com pregão fechado (o preço intraday é exibido apenas por referência):
- `MM21`, `MM200`: médias simples dos fechamentos.
- `IFR14`: índice de força relativa de Wilder.
- `FR20`: retorno do ativo em 20 pregões menos o retorno do Ibovespa no mesmo período, em pontos percentuais.
- `VOL_REL`: volume do último pregão dividido pela média de volume dos 20 anteriores.
- `QUEDAS_SEGUIDAS`: fechamentos consecutivos abaixo do fechamento anterior.

Regras (primeira que der match, nesta ordem; os limiares moram em `app/consultor/regras.py`):
- **R1 Faca caindo**: `QUEDAS_SEGUIDAS >= 5` -> *Aguardar* (gatilho: primeiro fechamento em alta com `VOL_REL >= 1.5`)
- **R2 Tendência de baixa**: fechamento < `MM200`, `MM21 < MM200` e `FR20 < 0` -> *Vender* (invalida: fechamento acima da `MM200`)
- **R3 Esticada**: fechamento > `MM200`, `MM21 > MM200` e `IFR14 > 70` -> *Aguardar* (recuo até a `MM21` ou `IFR14 < 60`)
- **R4 Rompimento pendente**: fechamento até 3% abaixo da `MM200` e `MM21` de hoje maior que de 5 pregões atrás -> *Aguardar* (fechamento acima da `MM200` com `VOL_REL >= 1`)
- **R5 Tendência de alta saudável**: fechamento > `MM200`, `MM21 > MM200`, `40 <= IFR14 <= 65` e `FR20 > 0` -> *Comprar* (invalida: fechamento abaixo da `MM200`)
- **R0 Sem sinal**: fallback se nada bater, ou se houver dados insuficientes.

## Critérios de aceite
- [ ] Dado um fixture de histórico em que o ativo atende R5, `/api/consultor` o lista em "comprar" com regra `R5` e invalidação contendo o valor da `MM200` formatado em R$.
- [ ] Um fixture para cada regra R1 a R4 produz a decisão e o gatilho da tabela; um ativo que atende R1 e R2 sai como R1 (ordem de avaliação).
- [ ] `IFR14` e `MM200` batem, com tolerância de 0,01, com valores calculados à mão num fixture pequeno documentado no teste.
- [ ] Com o coletor do consultor falhando, a página inicial responde 200 com seus painéis e `/consultor` mostra "Dados do consultor indisponíveis".
- [ ] A seção "Como o consultor decide" mostra os limiares lidos das constantes (o teste altera uma constante e confere a página).
- [ ] A página funciona em 390 px sem rolagem horizontal (checklist visual do `docs/DESIGN.md`).

## Invariantes de produção
- O preço exibido de cada ativo no `/api/consultor` fica a no máximo 1,5% de uma fonte independente no mesmo horário.
- Todo ativo em "comprar" tem fechamento acima da própria `MM200` exibida; todo ativo em "vender", abaixo.
- A soma dos ativos nos quatro grupos é igual a `ativos_avaliados` e ao tamanho do universo vigente.

## Fora do escopo
- Opiniões de casas de análise.
