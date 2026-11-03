---
id: 138
titulo: A auditoria confere a variação do dia do Ibovespa, não só o preço
status: ready
esforco: M
gaveta: saúde técnica
aceite: tests/test_aceite_138.py
revisada: 2026-11-03
---

## Problema
O usuário perguntou: "o número de variação do painel está certo?" A auditoria hoje não consegue responder. Em `checar_coerencia` (`auditoria/auditar.py:393-470`):

- `ibov.variacao_coerente` compara o percentual com os pontos da variação, e os dois saem do mesmo `previous_close`. Se o fechamento anterior estiver errado, os dois erram juntos e a checagem passa. Ela prova a aritmética, não o dado.
- `ibov.variacao_plausivel` compara o módulo com `VARIACAO_DIARIA_MAXIMA` (20%): mede magnitude, não verdade.
- `ibov.historico_vs_valor` compara o último ponto do gráfico com o valor exibido: confere o preço, não a variação.
- `checar_referencia` (linhas 554-612) confere o **valor** e os **fechamentos antigos** com a fonte externa. Nenhuma checagem confere a variação do dia com a fonte externa.

Resultado: um painel com preço certo, gráfico certo e variação de +12,87% calculada contra o fechamento de um ano atrás (spec 134) passa em todas as checagens de coerência e de referência.

## Comportamento esperado
Duas checagens novas, ambas sem tocar nos limites das existentes:

1. **`ibov.fechamento_anterior_coerente`** (interna, funciona só com a página ou o snapshot). Se o valor exibido é igual ao último ponto do gráfico (tolerância de 0,05%), então o `fechamento_anterior` precisa ser igual ao penúltimo ponto (mesma tolerância). Falha com a mensagem `fechamento anterior <x>; penúltimo ponto do gráfico <y>`. Se o valor difere do último ponto (por exemplo, antes da abertura), o resultado é `inconclusivo`. Dados: `Painel.fechamento_anterior`, `.valor`, `.fechamentos` (já extraídos por `extrair_do_html` e `extrair_do_snapshot`).
2. **`ibov.variacao_confere_com_fonte`** (externa, dentro de `checar_referencia`). Com `d` a data do último ponto do gráfico exibido e `a` a maior data de `ref.fechamentos` menor que `d`, a variação de referência é `(ref.fechamentos.get(d, ref.valor) / ref.fechamentos[a] − 1) × 100`. Compara com `p.variacao_pct` e falha se a diferença passar de 0,5 ponto percentual (`TOLERANCIA_VARIACAO`, constante nova junto das demais). `inconclusivo` se não houver referência, se `a` não existir ou se a referência for a mesma fonte do produto (spec 137).
3. Um comentário em `ibov.variacao_coerente` registra o que ela **não** prova, para quem a lê no futuro não tomá-la por conferência do dado.
4. `auditoria/README.md` ganha as duas linhas na tabela "O que a camada determinística verifica".

Regras de convivência: nenhum limite existente (`VARIACAO_DIARIA_MAXIMA`, `TOLERANCIA_PRECO`, `TOLERANCIA_FECHAMENTO`) é alterado nesta spec, e as checagens novas só acrescentam.

## Fontes de dados
A referência que `obter_referencia` já devolve (Yahoo ou Stooq, conforme a spec 137). Plano B: `inconclusivo`, que não reprova.

## Cálculos
Variação de referência como descrita. Tolerância: 0,5 ponto percentual, a mesma usada na confirmação da spec 136.

## Critérios de aceite
- [ ] Snapshot com `valor = 131300`, `fechamentos[-1] = 131300`, `fechamentos[-2] = 130000` e `fechamento_anterior = 105000`: `ibov.fechamento_anterior_coerente` falha, com os dois números na mensagem.
- [ ] O mesmo snapshot com `fechamento_anterior = 130000`: passa.
- [ ] Snapshot com `valor = 131900` e `fechamentos[-1] = 131300` (antes da abertura): `inconclusivo`.
- [ ] Referência com `fechamentos = {"2026-11-02": 130000, "2026-11-03": 131300}` e página com `variacao_pct = +12,87` e último ponto em `2026-11-03`: `ibov.variacao_confere_com_fonte` falha (referência +1,00%).
- [ ] Mesma referência e página com `+1,20%`: passa; com `+1,60%`: falha (diferença de 0,60 p.p.).
- [ ] Sem referência, ou com a referência excluída pela spec 137: `inconclusivo`, o código de saída da auditoria continua 0 por causa dessas duas checagens.
- [ ] `pytest -q auditoria tests/test_aceite_138.py` verde, sem alterar os testes das checagens que já existem.
- Arquivos tocados: `auditoria/auditar.py`, `auditoria/README.md`, o novo `tests/test_aceite_138.py`.
- Pode entrar antes ou depois da 134. Se entrar antes de a correção chegar à produção, a falha da checagem no site publicado é o comportamento correto, não um problema desta spec.

## Invariantes de produção
- Em `/api/snapshot`, `paineis.ibovespa.fechamento_anterior` coincide, com tolerância de 0,05%, com `paineis.ibovespa.historico.fechamentos[-2]` quando o valor coincide com `fechamentos[-1]`.
- A variação do dia exibida difere em até 0,5 ponto percentual da calculada por uma fonte que não seja a do produto.

## Fora do escopo
- Conferir a variação das demais ações (a invariante da spec 135 cobre `altas_baixas`).
- Alterar `VARIACAO_DIARIA_MAXIMA` ou qualquer outro limite, em qualquer direção.
- Editar `docs/auditoria/` (pertence ao auditor).
