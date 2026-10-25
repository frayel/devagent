1. **Atualizar `Fonte` em `app/collectors/registro_fontes.py`:**
   - Adicionar uma classe `Falha` para armazenar detalhes da falha: `endpoint`, `simbolo`, `status` e `trecho_corpo`.
   - Modificar `_fonte(nome)` e `Fonte` para manter um histórico das últimas 10 falhas ou um dicionário por endpoint (como diz a spec, manter, por fonte, um contador por endpoint (ok, falhas, ultimo_status) com os 10 endpoints mais recentes).
   - Alterar `falha(...)` em `registro_fontes.py` para aceitar `endpoint`, `simbolos` (lista de strings), `status_code` e `corpo`. E mascara segredos no corpo antes de salvar.
   - Alterar `sucesso(...)` para aceitar também informações do endpoint.
2. **Atualizar `fetch_with_retry` e `async_fetch_with_retry` em `app/collectors/utils.py`:**
   - Ao chamar `registro_fontes.falha(...)`, extrair o endpoint e os símbolos a partir da URL.
   - Extrair um trecho de até 200 caracteres de `response.text`.
   - Extrair endpoint: a url sem dominio e sem querystring, mas substituindo variaveis conhecidas (ex. o simbolo) por `{simbolo}`.
3. **Atualizar `app/services/sistema.py` e/ou `app/collectors/sistema.py` para as novas regras de nível de fonte:**
   - Ajustar `verificar_integracoes` / `_item_da_fonte` para analisar os endpoints que falharam (baseando-se nos 10 mais recentes).
   - "Atenção: falhas 404 isoladas em símbolos específicos, listados."
   - "Problema: o mesmo endpoint devolveu 404 para 3 ou mais pedidos seguidos de símbolos diferentes, incluindo um símbolo que respondeu antes (`^BVSP`). Texto: 'o endpoint X parece ter mudado ou saído do ar'."
4. **Criar testes em `tests/test_aceite_090a.py` e unitários:**
   - Garantir que as regras de aceite de 090a funcionem.
5. **Pré-commit:**
   - Complete pre-commit steps to ensure proper testing, verification, review, and reflection are done.
