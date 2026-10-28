---
id: 131
titulo: Histórico do Consultor sem consultas repetidas por recomendação
status: ready
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_131.py
---

## Problema
Em `/api/consultor?data=<pregão passado>` (`app/main.py`, ramo `is_historical`), para **cada** recomendação do dia o código:
1. chama `init_db()`;
2. abre uma conexão nova;
3. lê a tabela `consultor_fechamentos` inteira (`SELECT data_pregao ... ORDER BY`) para achar o pregão 5 dias depois;
4. faz mais três `SELECT` (preço futuro do ativo, Ibovespa no dia e Ibovespa no futuro).

Com cerca de 85 ativos, isso dá cerca de 340 consultas e 85 conexões por requisição, e a tabela inteira é relida 85 vezes. O Ibovespa do dia e do futuro é o mesmo para todas as linhas.

## Comportamento esperado
- Antes do laço, uma consulta lista as datas de `consultor_fechamentos` e outra traz, num dicionário `(data, ticker) -> preço`, os fechamentos das datas necessárias (o dia da recomendação e os até 5 pregões seguintes), incluindo `^BVSP`.
- O laço só consulta os dicionários. Uma conexão por requisição.
- A mensagem de confiança (`+x,x% contra o IBOV em N pregões` ou `ainda sem resultado`) continua exatamente igual.

## Fontes de dados
Nenhuma.

## Cálculos
Os mesmos de hoje (`_calcular_excesso`).

## Critérios de aceite
- [ ] Com 85 recomendações fixture e 10 pregões de fechamentos, `GET /api/consultor?data=D` executa no máximo 4 consultas (espião) e abre uma conexão.
- [ ] As mensagens de confiança são iguais, texto a texto, às produzidas pelo código anterior para o mesmo fixture (fixture com resultado esperado gravado).
- [ ] Os testes das specs 113a e 113b continuam verdes.
- Arquivos tocados: `app/main.py` (ou uma função nova em `app/consultor/placar.py`) e o novo `tests/test_aceite_131.py`.

## Invariantes de produção
- `/api/consultor?data=<pregão anterior>` responde em menos de 2 s.

## Fora do escopo
- A página `/consultor` (mesma lógica duplicada): vale aplicar a mesma função se for trivial, senão fica para a unificação das duas rotas (backlog).
- O formato do campo `consenso` (spec 132).
