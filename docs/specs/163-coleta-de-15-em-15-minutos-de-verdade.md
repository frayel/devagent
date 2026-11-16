---
id: 163
titulo: A coleta do pregão começa de 15 em 15 minutos, não 15 minutos depois de terminar
status: done
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_163.py
origem: nova
revisada: 2026-11-16
---

## Problema
De quanto em quanto tempo os painéis se atualizam durante o pregão?

O agendador promete 15 minutos (docstring de `app/agendador.py`: "a cada 15 minutos durante o pregão, a cada 2 horas fora dele"), e `/sistema` repete no item "Agendador da coleta": "Intervalo agora: 15 min." (`app/services/sistema.py`, `verificar_agendador`). Mas o laço espera o intervalo inteiro **depois** que a rodada termina (`laco_de_coleta`, `app/agendador.py:455`):

```python
while True:
    await asyncio.to_thread(coletar_tudo)
    espera = intervalo(datetime.now(timezone.utc))
    await asyncio.sleep(espera.total_seconds())
```

A distância entre o começo de duas rodadas é `intervalo + duração da rodada`. A spec 162 passou a medir a duração no relógio: em 16/11/2026 a saúde de produção mostra "rodada das 04h47 em 10,3 min". Com uma rodada de 10,3 min, a de "15 em 15 minutos" começa de 25,3 em 25,3 minutos, e quanto mais a rodada cresce (mais painéis, fonte lenta), mais raros ficam os dados, sem nenhum aviso.

Esta spec faz o laço descontar a duração da rodada da espera, com uma pausa mínima.

## Comportamento esperado
- `app/agendador.py` ganha:
  - `PAUSA_MINIMA = timedelta(seconds=60)`;
  - `proxima_espera(intervalo_atual: timedelta, duracao: timedelta) -> timedelta`, que devolve `max(intervalo_atual − duracao, PAUSA_MINIMA)`;
  - `_relogio() -> float`, que devolve `time.monotonic()` do módulo padrão `time` (no módulo, `time` é o `datetime.time`; importe como `import time as std_time` no topo, ao lado dos outros imports; o `import time as std_time` local que `_coletar` já faz continua e não conflita). Existe para o teste trocar o relógio.
- `laco_de_coleta` mede a rodada e desconta:
  ```python
  while True:
      t0 = _relogio()
      await asyncio.to_thread(coletar_tudo)
      duracao = timedelta(seconds=_relogio() - t0)
      espera = proxima_espera(intervalo(datetime.now(timezone.utc)), duracao)
      logger.info("Rodada levou %s; próxima coleta em %s", duracao, espera)
      await asyncio.sleep(espera.total_seconds())
  ```
  O `intervalo` continua sendo calculado no **fim** da rodada, como hoje: uma rodada que começa no pregão e termina depois das 18h15 já usa o intervalo de 30 min.
- `intervalo()`, `NO_PREGAO`, `FORA_DO_PREGAO`, `coletar_tudo` e `_coletar` não mudam. O item "Agendador da coleta" de `/sistema` não muda: "Intervalo agora: 15 min." passa a ser verdade.
- As rodadas continuam sequenciais: nunca duas ao mesmo tempo. Rodada mais longa que o intervalo é seguida pela próxima depois de `PAUSA_MINIMA`, não na hora.

## Fontes de dados
Nenhuma nova. Mais rodadas por pregão quer dizer mais pedidos às fontes que já são lidas a cada rodada (MT5, Yahoo, brapi), na mesma proporção das rodadas: com rodadas de 10,3 min, de ~20 para ~33 por pregão (cálculo abaixo). Os limites por domínio de `app/collectors/utils.py` continuam valendo dentro de cada rodada. Plano B se uma fonte reclamar (HTTP 429 que não havia antes): a pausa por fonte que já existe (Yahoo · consenso, MT5) segura a fonte; o intervalo em si pode voltar a crescer só aumentando `NO_PREGAO`, sem desfazer esta spec.

## Cálculos
`espera = max(intervalo − duração, 60 s)`, em segundos, com `duração` no relógio monotônico (o mesmo princípio do `perf_counter` da 162; o relógio de parede pode pular).

Exemplo de ponta a ponta, pregão de quarta 18/11/2026:
- Rodada começa às 14h00m00s BRT e leva 618 s (os 10,3 min medidos em 16/11). Termina às 14h10m18s. `intervalo(14h10m18s)` = 15 min = 900 s. `espera = max(900 − 618, 60) = 282` s. A próxima começa às 14h10m18s + 282 s = **14h15m00s**. Hoje: 14h10m18s + 900 s = 14h25m18s.
- Rodada de 840 s (14 min): `espera = max(900 − 840, 60) = 60` s; a próxima começa 15 min depois da anterior.
- Rodada de 1.000 s (16,7 min): `900 − 1000 = −100` → `espera = 60` s; a próxima começa 1.060 s (17,7 min) depois da anterior, nunca colada.
- Virada para depois do pregão: rodada começa às 18h10m00s, leva 618 s, termina às 18h20m18s; `intervalo(18h20m18s)` = 30 min = 1.800 s; `espera = 1.800 − 618 = 1.182` s; a próxima começa às **18h40m00s**.
- Fora do pregão: rodada de 618 s, `intervalo` = 2 h = 7.200 s; `espera = 6.582` s.

Rodadas por pregão (9h55 a 18h15 = 500 min), com rodadas de 10,3 min: hoje uma a cada 15 + 10,3 = 25,3 min → 500 / 25,3 ≈ 19,8; com a spec, uma a cada 15 min → 500 / 15 ≈ 33,3. A rodada de 10,3 min é a única medida disponível (04h47, fora do pregão, com `consultor_opinioes` 249 s, `consultor_historico` 124 s e `consultor_fechamento` 67 s); durante o pregão ela pode ser outra, e a diferença cresce ou diminui na mesma medida.

## Critérios de aceite
- [ ] `tests/test_aceite_163.py`, com `exigir_spec_done("163")`, sem rede e sem banco:
  - `proxima_espera` com os números do exemplo: (900 s, 618 s) → 282 s; (900 s, 840 s) → 60 s; (900 s, 1.000 s) → 60 s; (1.800 s, 618 s) → 1.182 s; (7.200 s, 618 s) → 6.582 s; (900 s, 0 s) → 900 s;
  - `laco_de_coleta` com `coletar_tudo` falso (não faz nada), `_relogio` trocado para devolver 0,0 e depois 618,0, `intervalo` trocado para devolver 15 min e `asyncio.sleep` trocado por uma corrotina que guarda o argumento e levanta uma exceção própria do teste para sair do laço: o valor guardado é 282,0;
  - o mesmo com o relógio devolvendo 0,0 e 1.000,0: o valor guardado é 60,0;
  - `coletar_tudo` é chamado uma única vez antes do primeiro `sleep` (as rodadas não se sobrepõem).
- [ ] `tests/test_agendador.py` continua verde sem mudar expectativa (`intervalo` não muda).

## Invariantes de produção
- Durante o pregão, com a "Duração da coleta" de `/sistema` abaixo de 14 min, duas leituras de "rodada das HHhMM" feitas com 15 min de diferença mostram horários de início que diferem de 15 min (tolerância de 1 min). Hoje diferem de 15 min mais a duração da rodada.
- Durante o pregão, com rodadas de duração parecida (uma não passa a anterior em mais de 2 min), a `ultima_coleta` de `/api/coleta` (gravada no **fim** da rodada, `app/agendador.py:181`) nunca tem mais de 17 min de idade: espera + duração da atual = (15 − duração da anterior) + duração da atual ≤ 15 + 2. Hoje chega a 15 min + a duração da rodada (≈ 25 min com rodadas de 10 min).
- Nenhuma rodada começa menos de 60 s depois do fim da anterior.

## Fora do escopo
- Alinhar as rodadas ao relógio (14h00, 14h15, ...) ou mudar `NO_PREGAO` e `FORA_DO_PREGAO`.
- Encurtar a rodada: a leitura do Telegram que pesa 249 s em `consultor_opinioes` é o item "A leitura do Telegram não segura a rodada" do backlog; o cache de séries é o item "Medir quanto de série a rodada baixa repetido".
- Mostrar em `/sistema` o horário previsto da próxima rodada.
- Rodar coletores em paralelo dentro da rodada.
