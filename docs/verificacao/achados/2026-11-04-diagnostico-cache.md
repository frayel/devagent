---
id: 2026-11-04-diagnostico-cache
severidade: media
painel: app/banco.py diagnostico
status: resolvido
visto_em: 2026-11-04T18:45-03:00
pr: 744
---

# Diagnóstico de banco de dados omite queda recente por causa de cache

## O que acontece
A função `diagnostico()` em `app/banco.py` usa um cache de 5 minutos (`agora - _diagnostico_cache_time < 300`). Quando o banco de dados cai e o disjuntor abre, a tela de sistema continua exibindo a versão e o tamanho cacheados (como se estivesse normal) durante até 5 minutos, e não exibe o alerta de disjuntor imediatamente. Isso ocorre porque o cache intercepta a chamada de diagnóstico antes de verificar o status do disjuntor.

## O que deveria acontecer
A regra da spec diz que deve mostrar "Postgres configurado e inacessível desde HH:MM" enquanto o disjuntor estiver aberto. A presença de falha (disjuntor aberto) deveria invalidar ou furar o cache do diagnóstico, garantindo que o alerta de indisponibilidade seja refletido imediatamente.

## Evidência
Se `_diagnostico_cache_time` é recente e `_disjuntor_aberto_desde` tem valor, o começo da função `diagnostico` retorna imediatamente o cache antigo:
```python
    if (
        _diagnostico_cache
        and _diagnostico_cache_time
        and (agora - _diagnostico_cache_time < 300)
    ):
        return _diagnostico_cache
```

## Como reproduzir
1. Inicie a aplicação com o banco normal.
2. Aguarde que a página de sistema seja acessada, o que popula `_diagnostico_cache`.
3. Derrube o banco de dados.
4. Faça uma requisição para que o disjuntor seja aberto.
5. Acesse a rota de diagnóstico. Ela exibirá o banco como funcional até o cache expirar.
