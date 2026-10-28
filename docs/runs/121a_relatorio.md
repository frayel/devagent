# Relatório de Execução - Spec 121a

## Análise
O Passo 4 do ciclo exige implementar a spec 121a `Guia de resolução para alertas da página de sistema`. A spec requer que os itens do sistema apresentem `causa` e `acao` quando houver um aviso ou problema. A classificação deve ser feita a partir dos textos de erros existentes e não exige novas requisições externas.

## Modificações
1. **app/services/sistema.py**:
   - A classe `Item` foi alterada. Os novos atributos `causa` e `acao` foram adicionados.
   - O método mágico `__post_init__` foi implementado em `Item` para realizar a inferência de `causa` e `acao` baseado no `resumo`, `detalhe` e `nivel` do item. As lógicas descritas na spec usando regex em caso de HTTP foram aplicadas.
2. **app/templates/sistema.html**:
   - O template foi ajustado para mostrar `causa` e `acao` quando o item tiver os níveis 'problema' ou 'atencao' e possuir os atributos preenchidos.
   - O css para `.checagem-causa-acao` foi adicionado à tag `<style>`.
3. **tests/test_sistema.py**:
   - Foi criado o teste de unidade `test_item_classifica_causa_e_acao` que garante que o `__post_init__` está criando os campos corretamente.
4. **tests/test_aceite_121a.py**:
   - Teste de aceite criado, seguindo os critérios de aceite e comprovando os comportamentos esperados pela spec.
5. Atualizei o status da spec para `done`, assim como documentado no `CHANGELOG.md` e em `docs/STATE.md`.

## Verificação
O código passou no linter (`ruff`), type checker (`mypy`) e nos testes (`pytest`). A verificação `make verify` foi bem-sucedida e `devagent.conferir_pr` não acusou erros, indicando que o estado atende as regras do ciclo do agente.
