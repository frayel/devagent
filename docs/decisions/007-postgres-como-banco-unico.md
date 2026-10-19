# ADR 007 · Postgres como banco único e snapshots por painel

**Data:** 2026-10-18 · **Status:** aceito · **Origem:** pedido do dono do produto · **Substitui:** itens 2 e 4 do ADR 006

## Contexto

Toda vez que o Render acorda da hibernação, o SQLite renasce vazio e os painéis aparecem um a um, à medida que a coleta avança (ADR 004). Com o Neon configurado para o consultor (ADR 006), o produto já tem um banco durável. O dono do produto pediu que o SQLite deixe de ser usado em produção, que os dados sejam congelados depois do fechamento (ADR 008) e que os últimos 5 pregões possam ser consultados.

Hoje cada painel tem tabela própria, função de gravação e função de leitura em `app/database.py` (45 tabelas, cerca de 2.500 linhas). Migrar tabela por tabela para o Postgres repetiria o problema apontado na seção *Manutenção* do `PRODUTO.md`: muita estrutura repetida para guardar, em quase todos os casos, um único resultado por coleta.

## Decisão

1. **Em produção, o único banco é o Postgres de `DATABASE_URL`.** O SQLite fica só para testes e desenvolvimento local, pela mesma interface. Os testes nunca acessam Postgres real.
2. **Uma camada só:** `app/banco.py` expõe conexão, transação e as operações abaixo para os dois bancos, com SQL portável (sem recursos exclusivos de um dialeto) e tradução de parâmetros. O `app/consultor/armazenamento.py` (ADR 006) passa a usar essa camada.
3. **Uma tabela genérica para os painéis:**

   ```
   snapshots_paineis(
     painel           texto,       -- chave do painel no /api/snapshot
     data_referencia  data,        -- pregão a que o dado pertence (ADR 008)
     estado           texto,       -- 'ao_vivo' | 'final' | 'incompleto'
     coletado_em      timestamp com fuso,
     fonte            texto,
     payload          JSON (jsonb no Postgres, texto no SQLite),
     PRIMARY KEY (painel, data_referencia)
   )
   ```

   Cada coleta faz *upsert* na linha do painel para o pregão corrente. Para pregões passados fica só a versão final. As tabelas `*_cache` por painel deixam de existir.
4. **Séries compartilhadas.** `historico_diario_cache` (séries diárias por ativo) vira `series_diarias(ticker, data, abertura, maxima, minima, fechamento, volume, fonte)`, com chave `(ticker, data)`. Uma série já gravada não é baixada de novo; a coleta só pede os pregões que faltam.
5. **Instrumentação** (`instrumentacao_coleta_*`) vai para o Postgres, para o histórico de saúde por painel da rotina de manutenção sobreviver a reinícios.
6. **Retenção:** 30 pregões em `snapshots_paineis`; `series_diarias` sem limite (é pequena). A limpeza roda uma vez por dia.
7. **Sem `DATABASE_URL` em produção** (variável `RENDER` presente), a aplicação sobe com SQLite, mostra no topo de todas as páginas "Banco persistente não configurado: dados se perdem ao reiniciar" e registra o problema em `GET /api/coleta`. Ela não deixa de subir.
8. **Conexões:** um pool pequeno (até 3 conexões), timeout de conexão de 10 s e uma nova tentativa, porque o Neon leva alguns segundos para acordar a computação.

## Consequências

- Ao acordar, a página lê o último snapshot do banco e mostra os painéis de imediato, com o horário da coleta. A coleta em segundo plano só atualiza o que estiver vencido.
- Painel novo não cria tabela: grava e lê pela camada genérica. O `docs/skills/criar-coletor.md` e o `PRODUTO.md` passam a dizer isso.
- A migração é feita em fatias (specs 073 a 076), e durante ela convivem as duas formas. A spec 076 remove as tabelas antigas.
- Consumo estimado no Neon: dezenas de linhas por pregão, poucos MB por mês, e computação ativa só durante as rodadas de coleta e as visitas; cabe com folga no plano gratuito.
- A latência entre Render e Neon pesa em cada leitura. O ideal é que os dois fiquem na mesma região da nuvem.
- O `PRODUTO.md` (seção 2) e `docs/context/arquitetura.md` passam a descrever o Postgres como banco de produção.
