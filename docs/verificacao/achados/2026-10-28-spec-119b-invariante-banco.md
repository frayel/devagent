---
id: 2026-10-28-spec-119b-invariante-banco
severidade: media
painel: app/services/validador_gemini.py
status: aberto
visto_em: 2026-10-28T12:00-03:00
pr: 571
---

# Validação do Gemini não registra resultado no banco de dados

## O que acontece
O arquivo `app/services/validador_gemini.py` e o modelo atualizado `gemini_modelo` usam a estrutura de `registro_fontes` para registrar o sucesso ou falha da validação da chave do Gemini. Porém, `registro_fontes` é um módulo estritamente baseado em memória (dicionário interno `_fontes`).

## O que deveria acontecer
A seção "Invariantes de produção" da spec 119b estipula: "A tabela de banco de dados registra sucesso ou erro a cada 6 horas para as chaves presentes, mantendo visibilidade da validade". Como a spec especificava a gravação na *tabela de banco de dados*, essa invariante foi ignorada na implementação, e a visibilidade se perde a cada reinício do serviço.

## Evidência
Em `app/services/validador_gemini.py`:
`await asyncio.to_thread(gemini_modelo._listar_modelos, api_key)`

Em `app/services/gemini_modelo.py` (`_listar_modelos`):
```python
            if resp.status_code != 200:
                registro_fontes.falha(...)
```
Não há chamadas para o banco de dados (`app/database.py` ou módulo similar).

## Como reproduzir
1. Configurar `GEMINI_API_KEY`
2. Executar a aplicação e esperar a validação rodar.
3. Observar que não existem tabelas ou inserções feitas para a validação no banco de dados SQLite/Postgres.
