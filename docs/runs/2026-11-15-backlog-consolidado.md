# Consolidação do backlog · 15/11/2026

Pedido do dono do produto: o backlog crescia sem parar, com duplicações, e ninguém sabia a ordem.

## Diagnóstico

- **Tamanho.** 583 linhas, 81 KB, 318 linhas de tabela em 52 seções "Ideias (Passo 7 ...)" e uma tabela de features da primeira semana.
- **Quem escreve.** Só a raia de especificação, no Passo 7. A regra mandava gerar de 5 a 8 ideias por rodada, registrar todas (inclusive as descartadas) e transformar uma em spec. Nenhuma regra tirava do backlog a ideia que virava spec. Saldo de cada rodada: de +4 a +7 linhas. Em 15/11 foram cinco rodadas.
- **Por que nunca diminuía.** A entrada era obrigatória e a saída não existia. Mesmo com o desenvolvimento entregando uma spec por dia, o arquivo só crescia.
- **Duplicação.** Seções inteiras copiadas com outro carimbo de data ("Passo 7 - Atual" aparece duas vezes, com as mesmas linhas). Alguns exemplos: "Agrupamento Dinâmico de Indicadores" 5 vezes, "Termômetro de Concentração de Ordens" 4 (e já entregue na 058), "Detector de Ação Órfã" 3 (entregue na 038 e podado na 067), "Análise de Assimetria Risco/Retorno" 4 (entregue na 065), "Ações em vários radares" 3 (entregue na 155).
- **Fósseis.** Boa parte das linhas já tinha virado produto: maiores altas, médias móveis, volume anormal, manchete dinâmica, abas, Só Sinais, Maré, Motores, Fator Peso Pesado, Clima Global, compradores de fundo, armadilha de abertura, exaustões de alta, de queda e de tendência, falso rompimento, congestionamento, esforço × resultado, instrumentação (056, 062, 152 a 154), heatmap da Maré (123), unificação de histórico (063), pool de conexões (129), entre outras.

## O que foi feito

| Destino | Critério | Resultado |
|---|---|---|
| Removidas | Já existe spec `done`, ou é cópia de outra linha | a maioria das 318 |
| Fila | Ainda vale (conferido no código de `main` em 15/11), com prioridade | 25 itens |
| Reserva | Vale pouco hoje, sobe quando abrir vaga | 9 linhas temáticas |
| Estacionadas | Dependem de fonte que o sistema não tem (book, leilão, curva intraday, notícias, derivativos) | 8 linhas temáticas |
| Descartadas | Já resolvidas por outro caminho ou sem objeto | 5 linhas |

Conferido no código antes de entrar na fila: `time.sleep` dentro de `async_fetch_with_retry` (`app/collectors/utils.py:175`), `get_*_desde` sem usar `desde` (`app/database.py:1459`), scripts de CDN sem `integrity`, `instrumentacao_coleta_tempo` só criada, classe `destaque` sem CSS, ausência de `executemany`.

## Critério da ordem

1. Número errado na tela ou risco de segurança (itens 1 a 3).
2. O que destrava a poda prevista na 153/154 (itens 4 e 5).
3. As duas primeiras perguntas do produto acima da dobra (6 e 7).
4. Saúde técnica com medida e baixo esforço, intercalada com experiência.
5. Capacidade nova que só este sistema pode ter: o próprio histórico de sinais (14, 18, 19).

As cadências continuam mandando: se a de experiência ou a de manutenção vencer, a raia pega o primeiro item da gaveta certa, não o primeiro da lista.

## Mudança de regra

Para o arquivo não voltar ao tamanho anterior, o Passo 7 (`devagent/CICLO.md`), o Especificador (`devagent/agents/raias.md`) e `devagent/skills/descobrir-ideias.md` passam a dizer: fila com teto de 25, procurar antes de registrar, a escolhida sai no mesmo PR `spec:`, descartada em uma linha.
