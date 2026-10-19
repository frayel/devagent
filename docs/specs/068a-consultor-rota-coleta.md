---
id: 068a
titulo: Consultor · Rota, Privacidade, Universo e Coleta
status: ready
esforco: M
---

## Problema
Primeira fatia do consultor de investimentos conforme spec 068. Cria a fundação: a rota privada, o universo de ativos (carteira do Ibovespa), a coleta do histórico necessário para o cálculo das regras, e uma página provisória de testes, garantindo a segurança sem afetar a página atual de cotações.

## Comportamento esperado
- Nova página `GET /consultor`, com o template base, o aviso legal do rodapé e um link "Consultor" no topo da página inicial, fora da barra de abas atual. Ela não é uma aba de `index.html`: precisa poder ficar privada sozinha. Por ora, exibe um painel de placeholder indicando "Construindo o motor de regras...".
- `GET /api/consultor` devolve um JSON provisório com os metadados.
- **Privacidade:** com `CONSULTOR_SENHA` definida no ambiente, as duas rotas exigem HTTP Basic (usuário `consultor`), usando `secrets.compare_digest`, e respondem 401 com `WWW-Authenticate: Basic` sem credencial válida. Sem a variável, ficam públicas.
- **Universo:** `app/consultor/universo.py` contendo a lista constante da carteira teórica vigente do Ibovespa (fonte: página da carteira teórica no site da B3), a data de início e fim da vigência (`composicao_vigente_ate`) e o link da fonte. Se a data de hoje passar do fim da vigência, a página exibe um alerta provisório "Composição do Ibovespa possivelmente desatualizada". O módulo também deve ter um mapa de `nome da empresa -> tickers`.
- `/api/snapshot` ganha a chave `consultor` só com metadados: `atualizado_em`, `ativos_avaliados`, `composicao_vigente_ate`. Nenhum ticker aparece no snapshot.

## Fontes de dados
- Histórico diário de cada ativo do universo e do `^BVSP`: utiliza o pipeline já existente no projeto para buscar histórico (no mínimo 220 pregões diários, com MT5 preferencial e yfinance como fallback). A coleta roda via `app/agendador.py` e persiste no SQLite, não bloqueando a thread principal.
- Último preço: via `yfinance` endpoint `spark`.

## Cálculos
- Os cálculos completos dos indicadores estão previstos para a 068b. O objetivo aqui é apenas viabilizar que o `agendador` preencha o banco de dados.

## Critérios de aceite
- [ ] Com `CONSULTOR_SENHA` definida, acessar `GET /consultor` sem senha retorna 401; com a credencial correta, 200. Sem a variável, 200.
- [ ] O `app/consultor/universo.py` mapeia corretamente o Ibovespa e exporta a lista e as datas.
- [ ] `/api/snapshot` reflete a estrutura de metadados exigida sem vazar dados de tickers.
- [ ] Se a data de vigência expirar em um teste, a renderização de `GET /consultor` deve conter o aviso correspondente no HTML e retornar 200.
- [ ] Os coletores básicos não quebram a página principal.

## Invariantes de produção
- Acesso à rota `/consultor` e `/api/consultor` exibe comportamento de HTTP Basic se a senha estiver setada.
- O `/api/snapshot` segue o contrato estrito sem exportar lista de ativos avaliados.

## Fora do escopo
- Cálculo real do MM21, MM200, IFR14.
- Regras de decisão e categorizações "Aguardar, Comprar, Vender".
