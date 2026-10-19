# ADR 005 · Consultor: página própria, regras determinísticas e LLM só para extração

**Data:** 2026-10-18 · **Status:** aceito · **Origem:** pedido do dono do produto

## Contexto

O painel mostra dezenas de indicadores, mas não responde à pergunta que o investidor leva para a corretora: o que fazer com cada ação do Ibovespa hoje. O dono do produto pediu uma aba de recomendações que diga o que comprar, o que vender e o que aguardar acontecer antes de agir, e que reúna a opinião de casas de análise publicada em sites de notícia. A decisão de operar continua sendo dele.

Restrições levantadas em 18/10/2026:

- Não existe fonte gratuita e estruturada de consenso de analistas para a B3. A documentação da brapi não oferece recomendações nem preço-alvo. O módulo `quoteSummary` do Yahoo (que tem consenso) e a busca RSS do Google News são proibidos pelo `robots.txt`, e a seção 5 do `PRODUTO.md` proíbe ignorá-lo. Relatórios de corretoras ficam atrás de login.
- Feeds RSS de portais funcionam (Money Times e InfoMoney verificados) e publicam matérias com recomendações e carteiras de casas de análise, em texto livre e com redação variada.
- Uma página com recomendações pode precisar ficar privada se o site for divulgado.

## Decisão

1. **Página própria.** O consultor vive em `GET /consultor` e `GET /api/consultor`, separado da página inicial e do `/api/snapshot`. Se a variável `CONSULTOR_SENHA` estiver definida, as duas rotas exigem HTTP Basic (usuário `consultor`, comparação com `secrets.compare_digest`); sem ela, ficam públicas. O `/api/snapshot` público só recebe metadados do consultor (horário da última avaliação, quantidade de ativos avaliados, estado das fontes), nunca ativos com recomendação.
2. **Universo.** Apenas as ações da carteira teórica vigente do Ibovespa, versionada em `app/consultor/universo.py` com a data de vigência e a fonte. Composição vencida gera aviso, não erro.
3. **A decisão é de regras determinísticas.** Comprar, vender, aguardar ou neutro saem de regras com limiares nomeados num único módulo, aplicadas a dados de mercado. Mesma entrada, mesma saída. É isso que permite medir o histórico de cada regra e manter o placar.
4. **O LLM só extrai.** Um modelo de linguagem lê matérias já filtradas e devolve registros estruturados (ativo, casa, recomendação, preço-alvo, resumo, trecho de apoio). O código valida cada registro contra o texto da matéria e descarta o que não confere. O modelo nunca decide, pontua nem escreve a recomendação final.
5. **Provedor: Gemini, camada gratuita, por REST.** Chamada `generateContent` com `httpx` (já é dependência), resposta em JSON com esquema. Sem SDK novo. Modelo configurável por `GEMINI_MODELO`. O volume esperado (dezenas de chamadas por dia, com lotes de até 10 matérias) cabe na camada gratuita.
6. **O LLM é opcional.** Sem `GEMINI_API_KEY`, com cota esgotada, timeout, erro do serviço ou JSON inválido, o consultor funciona só com os sinais técnicos e exibe um aviso com o motivo e o horário. Nenhuma falha do LLM ou dos feeds pode gerar exceção não tratada, resposta 500 ou página vazia.

## Consequências

- O consultor responde mesmo sem nenhuma opinião externa; as casas enriquecem a decisão, não a sustentam.
- Opiniões dependem do ritmo de publicação dos portais (algumas matérias relevantes por dia), não de tempo real.
- Na camada gratuita, o Google pode usar o conteúdo enviado para melhorar seus produtos. Só matérias públicas são enviadas; nenhum dado do usuário (carteira, posições, senha) pode ir para o LLM.
- A camada gratuita muda sem aviso. O coletor respeita um teto diário de chamadas (`GEMINI_MAX_CHAMADAS_DIA`) e guarda na fila o que não conseguiu processar.
- O auditor precisa da senha (secret `CONSULTOR_SENHA` no GitHub) para checar o consultor quando a página estiver privada.
- Trocar de provedor de LLM exige só um novo adaptador com a mesma interface de extração, não um novo ADR, desde que as regras 4 e 6 continuem valendo.
