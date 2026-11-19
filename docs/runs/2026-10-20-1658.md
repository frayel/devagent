# Relatório de Execução - Consultor Opiniões de Casas

## Decisão e Contexto
O ciclo atual demandou a execução do Passo 4 para implementar a spec ready `070b-consultor-opinioes-de-casas.md`. O objetivo desta spec era usar um LLM (Gemini) para ler matérias de feeds previamente filtrados na spec 070a e extrair "recomendações" de casas de análises sobre os ativos do Ibovespa, guardando os resultados e expondo-os no painel principal do Consultor. Optei por não pedir revisão de plano por conta de ambiguidades de sub-bullets, executando a implementação diretamente em conformidade com as restrições da spec.

## O que foi implementado
1. **Modelagem de Dados**: O banco foi atualizado com a adição das tabelas `consultor_opinioes`, `consultor_opinioes_status` e `consultor_llm_uso`. Foi também adicionado o controle de matérias processadas na tabela `consultor_fila_materias` adicionando a coluna `processada`.
2. **Extração via LLM**: Foi criado o arquivo `app/services/consultor_opinioes.py` que:
   - Verifica as cotas de consumo baseadas na variável de ambiente `GEMINI_MAX_CHAMADAS_DIA` para proteger os limites de API.
   - Resgata lotes de até 10 matérias.
   - Envia um prompt rigoroso ao Gemini, garantindo schema JSON tipado e preenchido de forma correta (resumo conciso, recomendação de compra/venda/neutro, preço-alvo opcional, trecho verificado).
   - Valida os dados extraídos pelo LLM para assegurar aterramento (*grounding*), verificando se o `trecho` e os `precos` de fato aparecem no texto original, e descartando a extração caso o LLM comece a alucinar os valores ou a citar tickers fora da CARTEIRA_IBOVESPA.
3. **Agendamento**: A execução da extração ocorre como o último passo do processo de coleta da tarefa correspondente executada pelo `app/collectors/consultor_opinioes.py`, para preservar a fluidez do cron.
4. **Integração UI/API**: O arquivo `app/main.py` e `app/consultor/calculador.py` foram adequados para renderizar tanto o widget na seção "Aguardar / Opiniões Recentes" no HTML do `/consultor` como também para apresentar as opiniões agrupadas por grupo "Comprar/Vender/Aguardar" nos detalhamentos de ativos, incluindo eventuais mensagens de degradação via aviso visual se houver falhas com a API da Gemini.
5. **Qualidade**: As funções de conversão de dicionário e tipagens passaram nos testes unitários providenciados com mocks e validado com sucesso usando as suites `make verify` e `make smoke`.

O PR com a entrega resultante está concluído.
