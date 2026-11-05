---
id: 2026-11-05-agendador-mascara-excecao
severidade: media
painel: app/agendador.py
status: aberto
visto_em: 2026-11-05T22:30:00-03:00
pr: 765
---

# Agendador engole detalhes de falhas sistêmicas e sobrepõe o último erro

## O que acontece
O PR 765 envolveu o processamento de todos os coletores em `_coletar` com um bloco genérico `try...except Exception:` para cada iteração do loop sobre os painéis. Se ocorre um erro sistêmico durante as checagens iniciais dentro do loop (como o Disjuntor do banco abrindo em chamadas a `app.banco.ler_snapshot`), a exceção é pega por esse catch abrangente e convertida em um log com a mensagem `{nome}: erro fatal` no array `estado_detalhes_manual` sem preservar a mensagem original. Pior, `estado["ultimo_erro"]` é sobreposto a cada vez que uma falha real ocorre na etapa `coletor.collect_and_save()` e a execução levanta exceção na etapa `except Exception as e:`, registrando `_mask_secrets(f"{nome}: {e}")` repetidamente, ou "nenhuma fonte respondeu", mantendo apenas o último erro no dicionário global de estado, o que mascara a origem sistêmica do problema.

## O que deveria acontecer
O robustecimento do agendador não deve comprometer a observabilidade ("erro engolido em silêncio", "Robustez"). Erros de infraestrutura (como indisponibilidade de banco de dados ou Disjuntor aberto) devem ser reportados com detalhes úteis em vez de ofuscados por um genérico "erro fatal", e o registro de erros em `ultimo_erro` deveria apensar ou preservar o erro inicial / original mais importante do ciclo (pois os próximos coletores falharão pelo mesmo motivo se for falha global).

## Evidência
No bloco iterando nomes, após as coletas:
```python
        except Exception:
            logger.exception("Falha ao inicializar ou coletar %s", nome)
            if estado_detalhes_manual is not None:
                estado_detalhes_manual.append(f"{nome}: erro fatal")
```

## Como reproduzir
1. Pare o servidor de banco de dados para abrir o Disjuntor.
2. Acione o script de coleta com `python -c "import app.agendador; app.agendador.coletar_tudo()"`.
3. Inspecione `app.agendador.estado["detalhes"]` para ver que informações da exceção de Disjuntor viraram apenas "erro fatal".
