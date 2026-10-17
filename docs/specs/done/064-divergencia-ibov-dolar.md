# Spec 064 - Radar de Divergência Ibovespa vs Dólar

**Gaveta:** capacidade nova
**Status:** ready

## Problema
O mercado brasileiro freqüentemente possui forte correlação inversa com o dólar (BRL=X). Porém, em alguns momentos críticos intradiários, o Ibovespa e o dólar podem se mover na mesma direção (ex: fuga generalizada de capital ou fluxo massivo institucional anômalo). O Painel não mostra atualmente se o movimento de alta ou baixa do Ibov está sendo "legitimado" pelo comportamento do câmbio no curto prazo.

## Solução proposta
Criar um painel (Radar de Divergência Ibovespa vs Dólar) na seção "Alertas Intraday" ou "Sentimento & Risco" (via `/api/snapshot` inicialmente, focando na coleta e cache) que colete a variação intradiária na última hora do `^BVSP` e do `BRL=X` via yfinance e calcule a correlação intradiária no período de 1 hora.

Se a correlação na última hora for positiva (ambos subindo ou ambos caindo significativamente juntos), disparar um alerta visual indicando "Divergência de Fluxo Detectada".

## Critérios de aceite
1. Tabela `divergencia_ibov_dolar_cache` criada no `app/database.py`.
2. Coletor `app/collectors/divergencia_ibov_dolar.py` implementado.
3. Chave `divergencia_ibov_dolar` exportada em `/api/snapshot`.
4. Os testes verificam a coleta bem-sucedida, cálculo correto de direcionalidade e tratamento de falhas na fonte.
