---
id: 2026-11-02-test-bloqueio-rede
severidade: baixa
painel: tests/test_aceite_095.py
status: aberto
visto_em: 2026-11-02T05:20:00-03:00
pr: 672
---

# Teste de bloqueio de rede falha com ConnectError por resolução de DNS

## O que acontece
Em `tests/test_aceite_095.py`, o teste `test_bloqueio_rede` espera um `RuntimeError` ao tentar acessar a rede, usando a infraestrutura do pytest-asyncio ou interceptações de rede (como sockets bloqueados). Porém, ele falha prematuramente com `httpx.ConnectError: [Errno -3] Temporary failure in name resolution` antes de lançar o `RuntimeError` esperado pela camada de interceptação/simulação.
Comando que mostra o comportamento: `pytest -m "not rede" tests/test_aceite_095.py`

## O que deveria acontecer
O teste `test_bloqueio_rede` deveria validar a restrição de rede de forma robusta a ambientes com e sem DNS, possivelmente mockando a camada DNS ou capturando subclasses mais amplas de erros de rede para validar o bloqueio, ou a interceptação deveria ocorrer antes da resolução de nomes. O teste não deve falhar a suíte do CI por problemas de resolução de nome do hospedeiro.

## Evidência
Saída do pytest:
`E httpx.ConnectError: [Errno -3] Temporary failure in name resolution` na tentativa de acessar `https://example.com`.

## Como reproduzir
1. Rode a suíte de testes em um ambiente ou container onde a resolução de nomes (DNS) externa esteja propositalmente indisponível ou seja mais lenta.
2. Execute o teste isolado: `python -m pytest tests/test_aceite_095.py::test_bloqueio_rede`.
