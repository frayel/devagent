---
id: 2026-10-26-spec-092-variaveis-render
severidade: media
painel: render.yaml
status: aberto
visto_em: 2026-10-26T14:00-03:00
pr: 524
---

# `render.yaml` declara GEMINI_MODELO e GEMINI_MAX_CHAMADAS_DIA não previstas na spec

## O que acontece
Em `render.yaml`, além de declarar `GEMINI_API_KEY`, `BRAPI_TOKEN` e `DATABASE_URL` conforme estipulado nos critérios de aceite das specs 092 e 092a, também foram declaradas as variáveis `GEMINI_MODELO` e `GEMINI_MAX_CHAMADAS_DIA`. A spec original menciona que essas variáveis existiam no painel do Render, mas no critério de aceite (tanto na 092 original quanto na divisao 092a) exige-se especificamente: "render.yaml declara as três variáveis com sync: false, sem valor, e os testes do adaptador do Render passam." (as três sendo GEMINI_API_KEY, BRAPI_TOKEN e DATABASE_URL).

## O que deveria acontecer
Seguir os critérios de aceite. Na seção "Comportamento esperado -> Variáveis declaradas" da spec 092a (e 092 original): "render.yaml passa a declarar, com sync: false e sem valores, GEMINI_API_KEY, BRAPI_TOKEN e DATABASE_URL, no mesmo padrão das variáveis do MT5".

## Evidência
```yaml
    envVars:
      - key: MT5_API_URL
        sync: false
      - key: MT5_API_KEY
        sync: false
      - key: GEMINI_API_KEY
        sync: false
      - key: GEMINI_MODELO
        sync: false
      - key: GEMINI_MAX_CHAMADAS_DIA
        sync: false
      - key: BRAPI_TOKEN
        sync: false
      - key: DATABASE_URL
        sync: false
```

## Como reproduzir
Ler o arquivo `render.yaml`.
