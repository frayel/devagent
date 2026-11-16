---
id: 164
titulo: A leitura das opiniões corre num laço próprio e não segura a rodada de mercado
status: ready
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_164.py
origem: A leitura do Telegram não segura a rodada
revisada: 2026-11-16
---

## Problema
Por que a rodada que atualiza os painéis de mercado leva 10 minutos, se 40% dela não é mercado?

A saúde de produção de 16/11/2026 mostra "Duração da coleta: rodada das 07h48 em 10,4 min (Mais lentos: consultor_opinioes 246 s, consultor_historico 127 s, consultor_fechamento 70 s)". Às 04h47 foram 249 s de 10,3 min. O `consultor_opinioes` roda em toda rodada (janela `continua` em `_coletar`, `app/agendador.py`) e, dentro dele (`collect_and_save`, `app/collectors/consultor_opinioes.py`):

- os 2 feeds RSS, com 2 s de pausa depois de cada um;
- o Clube Acionista pela prévia `t.me/s/`, até 5 páginas com 2 s entre elas;
- o Repositório de Ações e o Universo Antifrágil lidos por ID, até 30 IDs por canal, cada ID com 2 pedidos (widget e post) e 2 s de pausa antes de cada um: 30 × 4 s ≈ 120 s por canal quando o canal tem mensagem nova (o Repositório repassa documentos da CVM, spec 157);
- a extração pelo Gemini das matérias novas.

Nada disso é dado de mercado nem depende do pregão. Enquanto o Telegram é lido, os radares esperam: com a spec 163 a rodada começa de 15 em 15 minutos, e uma rodada de 10,4 min deixa só 4,6 min de folga antes de a seguinte começar atrasada.

Esta spec tira o `consultor_opinioes` da rodada de mercado e o põe num laço próprio, no mesmo ritmo, rodando ao lado dela.

## Comportamento esperado
- `app/agendador.py`:
  - `"consultor_opinioes"` sai da tupla de coletores de `_coletar` e do dicionário `janelas`. A janela `"continua"` fica sem usuário: o ramo `if janela == "continua":` sai junto.
  - Nova função `rodar_opinioes() -> None` (síncrona), uma volta do laço novo:
    ```python
    def rodar_opinioes() -> None:
        from app.collectors import consultor_opinioes
        try:
            if not consultor_opinioes.collect_and_save():
                logger.warning("consultor_opinioes: nenhuma fonte respondeu")
        except Exception as e:  # noqa: BLE001 - o laço não pode morrer
            _avisar_falha("Coleta falhou:", "consultor_opinioes", e)
    ```
    Ela **não** chama `_registrar_erro`, não mexe no dicionário `estado` nem em `tempos`/`vazias`/`gravar_instrumentacao_rodada`: esses são da rodada de mercado, e escrevê-los de outro fio no meio de uma rodada misturaria as duas. As falhas de cada fonte continuam aparecendo em `/sistema` pelo `registro_fontes` (Money Times, InfoMoney, Telegram), como hoje.
  - Nova corrotina `laco_das_opinioes()`, com o mesmo ritmo do laço de mercado (spec 163):
    ```python
    async def laco_das_opinioes() -> None:
        while True:
            t0 = _relogio()
            await asyncio.to_thread(rodar_opinioes)
            duracao = timedelta(seconds=_relogio() - t0)
            espera = proxima_espera(intervalo(datetime.now(timezone.utc)), duracao)
            logger.info("Opiniões levaram %s; próxima leitura em %s", duracao, espera)
            await asyncio.sleep(espera.total_seconds())
    ```
    Reusa `_relogio`, `proxima_espera` e `intervalo`, sem mudá-los. Voltas do laço novo nunca se sobrepõem entre si; elas podem correr ao mesmo tempo que uma rodada de mercado.
- `app/main.py`, `lifespan`: dentro do mesmo `if agendador.coleta_ligada():`, logo depois da tarefa do `laco_de_coleta`, cria a tarefa do `laco_das_opinioes()`. Com `COLETA_AUTOMATICA=0` (ou em teste) nenhum dos dois laços sobe, como hoje. O cancelamento no desligamento já percorre `tarefas`.
- `app/collectors/consultor_opinioes.py` não muda: mesmas fontes, pausas, tetos de 5 páginas e 30 IDs, cursores e extração.
- O `_Memoria` de `coletar_tudo` (avisos do logger `app.collectors` guardados em `estado["detalhes"]`) não muda. Ele escuta o logger de qualquer fio, então um aviso das opiniões emitido durante uma rodada de mercado ainda pode aparecer em `detalhes`, como hoje, em que as opiniões rodam dentro da rodada. Separar os avisos por fio fica fora desta spec.
- `/consultor`, `/api/consultor` e o item "Agendador da coleta" de `/sistema` não mudam. Em "Duração da coleta" de `/sistema`, o `consultor_opinioes` deixa de aparecer em "Mais lentos", porque sai de `tempos`.

## Fontes de dados
Nenhuma nova, e o volume de pedidos não muda: o laço novo usa o mesmo `intervalo()` da rodada de mercado (em dia de pregão, 15 min das 9h55 às 18h15 e 30 min das 18h15 às 20h; 2 h no resto, como `intervalo()` em `app/agendador.py`), então a leitura das opiniões acontece no mesmo ritmo de hoje. As pausas de 2 s por pedido ao `t.me` e aos feeds continuam dentro de `collect_and_save`. O teto diário de chamadas ao Gemini (`GEMINI_MAX_CHAMADAS = 200`, `app/services/consultor_opinioes.py`) continua valendo e é contado no banco, como hoje.

Plano B: se uma fonte das opiniões cai, só o laço das opiniões sente; a rodada de mercado não espera mais por ela. Se o laço novo levantar exceção dentro de `rodar_opinioes`, ela é registrada no log e a próxima volta acontece no ritmo normal.

## Cálculos
A rodada de mercado perde o tempo do `consultor_opinioes`, medido pela instrumentação da spec 162 (`tempos`, em segundos, relógio `perf_counter`), sem outra mudança:

- Rodada das 07h48 de 16/11/2026: 10,4 min = 624 s, dos quais `consultor_opinioes` = 246 s. Sem ele: 624 − 246 = **378 s ≈ 6,3 min**. Folga até a próxima rodada de 15 min (900 s): hoje 900 − 624 = 276 s (4,6 min); com a spec, 900 − 378 = **522 s (8,7 min)**.
- Rodada das 04h47: 618 s, `consultor_opinioes` = 249 s → 369 s (6,2 min).
- Espera do laço novo, pelo mesmo `proxima_espera` da 163, no pregão (`intervalo` = 900 s): volta de 246 s → `max(900 − 246, 60)` = **654 s**; a próxima leitura começa 900 s depois do começo da anterior, igual à rodada de mercado. Volta de 1.000 s → espera de 60 s.

Os 246 s são uma medida só, de uma rodada fora do pregão (07h48, antes da abertura das 10h). Durante o pregão o número pode ser outro; a conta muda na mesma medida.

## Critérios de aceite
- [ ] `tests/test_aceite_164.py`, com `exigir_spec_done("164")`, sem rede e sem banco:
  - `"consultor_opinioes"` não está entre os nomes que `_coletar` percorre: com todos os outros `collect_and_save` trocados por funções que retornam `True` e o de `app.collectors.consultor_opinioes.collect_and_save` trocado por uma função que anota a chamada, uma chamada a `_coletar()` não chama o das opiniões, e `tempos` (lido pela troca de `gravar_instrumentacao_rodada` por uma função que guarda o argumento) não tem a chave `consultor_opinioes`. Use o mesmo jeito de trocar os coletores que `tests/test_agendador.py` já usa.
  - `rodar_opinioes` com `collect_and_save` trocado para retornar `True` chama-o uma vez e não levanta exceção; trocado para levantar `RuntimeError("caiu")`, também não levanta exceção e deixa `agendador.estado["ultimo_erro"]` como estava antes da chamada.
  - `laco_das_opinioes` com `rodar_opinioes` trocado por uma função que anota a chamada, `_relogio` trocado para devolver 0,0 e depois 246,0, `intervalo` trocado para devolver 15 min e `asyncio.sleep` trocado por uma corrotina que guarda o argumento e levanta uma exceção própria do teste para sair do laço: o valor guardado é 654,0 e `rodar_opinioes` foi chamada uma vez antes do `sleep`. Mesmo molde do teste de `laco_de_coleta` em `tests/test_aceite_163.py`.
  - Com o relógio devolvendo 0,0 e depois 1.000,0, o valor guardado é 60,0.
- [ ] `tests/test_agendador.py` e `tests/test_aceite_163.py` continuam verdes sem mudar expectativa (as trocas de `consultor_opinioes.collect_and_save` que eles fazem ficam inofensivas).

## Invariantes de produção
- Em `/sistema`, o detalhe de "Duração da coleta" ("Mais lentos: ...") nunca cita `consultor_opinioes` depois do deploy.
- Em `/api/consultor`, a `ultima_coleta` de cada fonte de `fontes_opiniao.feeds` (feeds e canais do Telegram), durante o pregão, nunca tem mais de 20 min de idade (15 min do intervalo + a duração de uma volta das opiniões, ~4 min). Fora do pregão vale o intervalo de 2 h + 5 min.
- Durante o pregão, a "Duração da coleta" de `/sistema` cai na mesma medida do tempo que o `consultor_opinioes` levava: com as medidas de 16/11, de ~10,4 min para ~6,3 min.

## Fora do escopo
- Mudar o coletor do Telegram: teto de tempo por canal, pausa, teto de 30 IDs, ou medir o atraso do cursor em relação ao fim do canal (ideia "Atraso dos canais do Telegram" do relatório `docs/runs/2026-11-16-1132.md`).
- Gravar a duração das voltas do laço novo na instrumentação ou mostrá-la em `/sistema` (fica no log).
- Tirar outros coletores do Consultor da rodada (`consultor_historico`, `consultor_fechamento`, `consultor_yahoo`), que já rodam em janelas próprias (semanal e fechamento).
- Rodar coletores de mercado em paralelo dentro da rodada.
- Remover canais do Telegram: é o item "Repositório de Ações sai dos canais" do backlog.
