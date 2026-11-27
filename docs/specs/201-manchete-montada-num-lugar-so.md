---
id: 201
titulo: A manchete montada num lugar só
status: ready
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_201.py
origem: A manchete montada num lugar só
---

## Problema
A manchete que o usuário lê em `/` é a mesma que o `/api/snapshot` publica para o auditor?

Nem sempre. `gerar_manchete` (`app/services/manchete.py`) é chamada em dois lugares de `app/main.py`, e cada rota monta as entradas do seu jeito:

- **`snapshot`** (~linha 1580): relê a linha do Ibovespa e calcula `variacao_pct` à mão; passa os motores de `motores_json` com o pregão de `_pregao("motores_indice")`, **mesmo quando o carimbo falta** (o pregão vira `None` e os motores entram assim mesmo).
- **`index`** (~linha 2042): passa o dicionário de `get_ibovespa_view_data`, cuja chave é `variation_pct` (inglês), não a `variacao_pct` que `gerar_manchete` lê; e descarta os motores sem carimbo (spec 141).

Medido em 27/11/2026, chamando `gerar_manchete` com as duas formas de entrada que as rotas montam, sobre o mesmo banco (30 ações na amostra, 12 em alta, 15 em baixa, pregão 26/11):

| Caso | `/api/snapshot` | `/` |
|---|---|---|
| Ibovespa parado: `previous_close` = `current_price` = 125.000 pts (variação 0,00%) | "O mercado opera sem direção definida." (`sem_direcao`) | "O mercado opera em baixa, com indicadores internos apresentando sinais mistos (12 altas e 15 baixas de 30 ações; motores ausentes)." (`misto`) |
| Ibovespa +0,50%, motores Vale −1,2% e Petro −0,8% gravados **sem** carimbo de pregão | "O mercado opera em alta, mas os motores setoriais divergem (12 altas e 15 baixas de 30 ações)." | "O mercado opera em alta, mas os indicadores internos mostram sinais mistos (12 altas e 15 baixas de 30 ações; motores ausentes)." |

Na primeira linha a home está errada: sem `variacao_pct`, `gerar_manchete` toma `is_positive = False` e inventa `variacao_pct = -1.0`, e um índice parado vira "em baixa". Na segunda o snapshot está errado: a spec 141 manda motor sem carimbo não entrar na leitura. Nos dois casos o auditor confere uma frase e o usuário lê outra.

## Comportamento esperado
1. Uma função em `app/services/manchete.py`, por exemplo `entradas_da_manchete(ibovespa, highlights, apetite_estado, motores, carimbos)`, recebe as linhas que a rota já leu do banco (os objetos de `get_latest_ibovespa_data`, `get_latest_highlights_data`, o `estado` do apetite a risco, `get_latest_motores_indice_data`) e o dicionário de `_carimbos_criticos`, e devolve os quatro argumentos de `gerar_manchete` (ou já a `Manchete`). Ela é o único lugar que monta essas entradas.
2. As duas rotas (`snapshot` e `index`) chamam essa função, dentro do `lendo_pregao` que já abrem; os blocos atuais de montagem ("Manchete (Spec 140)" no snapshot e a chamada com `_com_pregao` na home) saem.
3. Regras da montagem (as que já valem em uma das rotas, agora nas duas):
   - `variacao_pct` = `(current_price − previous_close) / previous_close × 100`, em percentual; `is_positive` = `variacao_pct > 0`; `revisao_variacao` pelos limiares `LIMIAR_PCT_REVISAO`/`LIMIAR_PONTOS_REVISAO` de hoje; sem `previous_close` (nulo ou ≤ 0), `estado = "indisponivel"`.
   - pregão de cada entrada (`ibovespa`, `altas_baixas`, `motores_indice`) vem do carimbo de `_carimbos_criticos`;
   - motores sem carimbo não entram (`motores = None`), como a home já faz pela spec 141;
   - a dispersão entra pelas contagens `up_count`, `down_count` e `total_count` da linha de `highlights`.
4. O texto e o humor de `gerar_manchete` não mudam: as regras da spec 140 ficam como estão. Só a montagem das entradas se unifica.
5. O JSON do snapshot não muda de forma: `paineis.manchete` continua com `humor`, `texto`, `coletado_em` e `fonte: "composto"`.

## Fontes de dados
Nenhuma nova. As mesmas tabelas que as duas rotas já leem (Ibovespa, `highlights`, apetite a risco, motores do índice) e os carimbos de `_carimbos_criticos`.

## Cálculos
Exemplo de ponta a ponta (o primeiro caso da tabela):

- Linha do Ibovespa como o coletor grava: `current_price = 125000.0`, `previous_close = 125000.0` (pontos).
- `variacao_pct = (125000 − 125000) / 125000 × 100 = 0,0` (percentual); `is_positive = False`; `revisao_variacao = False`.
- `highlights`: `up_count = 12`, `down_count = 15`, `total_count = 30` (ações); fração em alta 12/30 = 0,40 (fração, não percentual), dentro de 0,20–0,80, então a regra 4 não dispara.
- Regra 8 de `gerar_manchete`: `abs(0,0) < 1e-9` e não positivo → "O mercado opera sem direção definida.", humor `sem_direcao`. É o que as duas rotas passam a mostrar.

Segundo exemplo (motores sem carimbo): Ibovespa `current_price = 125625.0`, `previous_close = 125000.0` → `variacao_pct = 625 / 125000 × 100 = 0,50`; motores gravados com Vale −1,2 e Petro −0,8, mas `carimbos["motores_indice"] is None` → motores ficam fora, `motores_faltantes` → as duas rotas mostram "O mercado opera em alta, mas os indicadores internos mostram sinais mistos (12 altas e 15 baixas de 30 ações; motores ausentes).".

## Critérios de aceite
- [ ] `tests/test_aceite_201.py`, com `exigir_spec_done("201")`, sem internet, banco de teste do `conftest.py` e relógio fixo num pregão:
  - **mesma frase nas duas rotas:** com o banco do primeiro exemplo (Ibovespa parado, 12/15/30, carimbos presentes), `GET /api/snapshot` traz `paineis.manchete.texto == "O mercado opera sem direção definida."` e `humor == "sem_direcao"`, e o HTML de `GET /` contém a mesma frase no `.manchete-texto`;
  - **motor sem carimbo fica fora nas duas:** com o banco do segundo exemplo, as duas rotas trazem a frase "… sinais mistos (12 altas e 15 baixas de 30 ações; motores ausentes)." e nenhuma traz "motores setoriais divergem";
  - **paridade em lote:** para pelo menos quatro bancos (os dois exemplos, um com o índice em alta ampla e "Tomando risco", um com o Ibovespa sem `previous_close`), o texto de `paineis.manchete` do snapshot é igual ao texto da manchete da home;
  - **um lugar só:** `app/main.py` não chama `gerar_manchete` diretamente (`"gerar_manchete(" not in` o código-fonte de `app/main.py`), e a função nova de `app/services/manchete.py` é chamada pelas duas rotas.
- [ ] Os testes atuais da manchete (`tests/test_manchete.py`, `tests/test_aceite_140.py`, `tests/test_aceite_134.py`) continuam passando sem afrouxar asserção: `gerar_manchete` não muda.
- [ ] Tamanho medido em 27/11 com `grep -rl gerar_manchete app tests`: 2 arquivos de código (`app/main.py`, `app/services/manchete.py`) e 3 de teste (que não precisam mudar), mais o teste de aceite novo.
- [ ] `make verify` verde; `CHANGELOG.md`, `docs/STATE.md` e `app/novidades.json` na entrega, como em todo PR.

## Invariantes de produção
- Em qualquer instante, o `texto` de `paineis.manchete` de `/api/snapshot` é igual ao texto do `.manchete-texto` de `/` buscados no mesmo minuto (fora de virada de coleta entre as duas leituras). Vale também com `?data=` de um pregão passado.
- Com o Ibovespa de variação 0,00% no snapshot (`paineis.ibovespa`), a manchete não diz "em alta" nem "em baixa".
- Se a manchete diz "motores setoriais divergem", o carimbo dos motores (`pregao` do painel de motores no snapshot) não é nulo.

## Fora do escopo
- Mudar as regras de `gerar_manchete` (spec 140) ou o texto das frases.
- As linhas de radar raro que a home mostra abaixo da manchete (`manchete_raros`, spec 199): já vêm de `radares_servico` nas duas rotas.
- Unificar outras montagens duplicadas entre `snapshot` e `index` (os 20 radares são o item "Radares do snapshot num laço" da *Fila*).
- Trocar a chave `variation_pct` de `get_ibovespa_view_data` para português: o template a usa; a função nova não depende do dicionário de exibição.
