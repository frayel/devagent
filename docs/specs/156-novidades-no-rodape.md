---
id: 156
titulo: O rodapé mostra o que mudou no painel e onde conferir
status: ready
esforco: M
gaveta: capacidade nova
aceite: tests/test_aceite_156.py
revisada: 2026-11-15
---

## Problema
O usuário perguntou: "o que mudou no painel desde a última vez que eu olhei, e onde eu vejo isso?"

Pedido do dono do produto em 15/11/2026. Em 14 e 15/11 o painel recebeu oito mudanças visíveis (specs 144 a 147 e 149 a 151, mais a correção da frase do Fator Peso Pesado no #836). Nenhuma aparece no site. O único registro é o `CHANGELOG.md`, que mistura o que o usuário vê com mudanças internas do agente (entradas `Agente:`, `Refactor:`, `Poda:`) e usa nomes de arquivo e de função. O rodapé de `app/templates/base.html` só traz o aviso de que o conteúdo não é recomendação.

## Comportamento esperado
1. **Rodapé.** Todas as páginas que estendem `base.html` ganham, acima do aviso que já existe, a linha `Novidades · atualizado em DD/MM/AAAA`. A data é a da entrada mais recente, e a linha é um link para `/novidades`. Sem nenhuma entrada, a linha não aparece. O aviso continua igual.
2. **Página `/novidades`.** Lista as entradas dos últimos 60 dias, da mais nova para a mais antiga, agrupadas por data (`DD/MM/AAAA`). Cada entrada tem:
   - um selo com o tipo: **Novidade** (algo que não existia), **Melhoria** (algo que existia e ficou melhor) ou **Correção** (algo que mostrava errado e foi consertado);
   - o texto da entrada, em linguagem de usuário: sem nome de arquivo, função ou número de spec;
   - quando a mudança é visível, uma linha `Onde ver: <aba_nome> › <painel>` com link `/?aba=<aba>` que abre a aba indicada na página inicial. Para uma entrada com `onde.pagina`, a linha é `Onde ver: <pagina_nome> › <painel>` (ou só `Onde ver: <pagina_nome>`, sem `painel`) com link para `onde.pagina`. Entrada sem `onde` (uma correção de cálculo sem mudança de tela, por exemplo) não tem essa linha.
   Sem entradas no período, a página diz `Nenhuma novidade nos últimos 60 dias.` A página estende `base.html` e usa o tema existente: sem CSS ou JS novo além do necessário para os selos.
3. **Página inicial com `?aba=`.** `app/static/ui.js` lê o parâmetro `aba` no carregamento e ativa o botão `.aba-btn[data-aba="<valor>"]`, como se o usuário tivesse clicado nele. Valor ausente ou que não corresponde a nenhuma aba mantém a Visão Geral, sem erro no console.
4. **`/api/snapshot`** ganha a chave de topo `novidades` (ao lado de `consultor`, fora de `paineis`, por isso sem `fonte` e `coletado_em`) com as entradas dos últimos 60 dias, no mesmo formato do arquivo, para o auditor conferir as invariantes. A lista não depende do `?data=`.

## Fontes de dados
O arquivo versionado `app/novidades.json`, escrito à mão pela raia de desenvolvimento no mesmo PR da mudança. Ninguém coleta nada de fora. Formato: uma lista de objetos, do mais novo para o mais antigo.

```json
[
  {
    "data": "2026-11-15",
    "tipo": "melhoria",
    "texto": "O sinal de inflexão aparece num só lugar, com a queda acumulada e a alta de hoje lado a lado.",
    "onde": {"aba": "alertas", "aba_nome": "Alertas Intraday", "painel": "Radar de Inflexão"},
    "spec": "151"
  }
]
```

- `data`: `AAAA-MM-DD`, o dia do merge.
- `tipo`: `novidade`, `melhoria` ou `correcao`.
- `texto`: até 200 caracteres.
- `onde`: opcional. `aba` é um `data-aba` que existe em `app/templates/index.html` (`visao-geral`, `sentimento-risco`, `rankings`, `alertas`, `sinais`), `aba_nome` é o rótulo do botão e `painel` é o título do painel como aparece na tela. Para uma página que não é a inicial, `{"pagina": "/sistema", "pagina_nome": "Sistema", "painel": "..."}`, com `painel` opcional.
- `spec` ou `pr`: a origem (`"151"` ou `"#836"`). Não aparece na página.

Plano B: um arquivo ausente ou inválido não derruba nenhuma página. O rodapé some, `/novidades` diz `Novidades indisponíveis.`, `/api/snapshot` traz `novidades: []`, e o erro vai para o log uma vez por processo.

Para o teste conseguir trocar o arquivo e o dia, a leitura fica num módulo próprio (`app/services/novidades.py`, por exemplo) com o caminho do arquivo numa constante de módulo e o dia de hoje numa função (`hoje()`, no fuso do projeto), as duas substituíveis por `monkeypatch`. O arquivo é lido a cada requisição (tem poucas dezenas de linhas), sem cache entre requisições, para o teste que troca o arquivo não herdar o anterior.

## Cálculos
- **Janela:** a entrada aparece se `hoje − data ≤ 60 dias`, com `hoje` no fuso de `[projeto].fuso` do `devagent.toml` (`America/Sao_Paulo`).
- **Data do rodapé:** a maior `data` entre todas as entradas, mesmo fora da janela.

### Exemplo de ponta a ponta
Arquivo com três entradas: `2026-11-15` (melhoria, `onde` na aba `alertas`), `2026-11-14` (correção, sem `onde`) e `2026-09-01` (novidade). Hoje é 15/11/2026.

- O rodapé mostra `Novidades · atualizado em 15/11/2026`.
- Entre 01/09 e 15/11 são 75 dias, mais de 60, então a entrada de setembro fica fora da página e do snapshot. 14/11 está a 1 dia e entra.
- A página mostra dois grupos, `15/11/2026` e `14/11/2026`. O primeiro tem o selo `Melhoria`, o texto e `Onde ver: Alertas Intraday › Radar de Inflexão`, com link `/?aba=alertas`. O segundo tem o selo `Correção` e o texto, sem linha de onde ver.
- `/api/snapshot` traz `novidades` com 2 itens.
- Abrir `/?aba=alertas` mostra a página inicial com o botão "Alertas Intraday" ativo. `/?aba=xyz` mostra a Visão Geral.

## Carga inicial
O PR desta spec cria o arquivo com as mudanças visíveis de 13/11 a 15/11/2026: specs 141, 142, 143, 144, 145, 146, 147, 149, 150 e 151 e o #836. Cada uma vira uma entrada com tipo, texto em linguagem de usuário e `onde` conferido no template atual. A 148 voltou a `draft` e não entra. A 155 (card "Em vários radares", entregue em 15/11) também entra, como `novidade`, com `onde` na aba `alertas`. A própria 156 entra como `novidade`, com `onde` `{"pagina": "/novidades", "pagina_nome": "Novidades"}`. Entradas `Agente:`, `Refactor:`, `Poda:` e `Saúde técnica` não entram, a menos que mudem algo na tela.

## Critérios de aceite
- [ ] Com um `app/novidades.json` de teste igual ao do exemplo e `hoje` fixado em 2026-11-15, `/` e `/sistema` contêm `Novidades · atualizado em 15/11/2026` com link para `/novidades`.
- [ ] `/novidades` contém `15/11/2026`, `14/11/2026`, os selos `Melhoria` e `Correção`, `Onde ver: Alertas Intraday › Radar de Inflexão` com `href="/?aba=alertas"`, e não contém o texto da entrada de 01/09.
- [ ] `/api/snapshot` tem `novidades` com exatamente 2 itens.
- [ ] Com o arquivo ausente, `/` responde 200 sem a linha `Novidades`, e `/novidades` responde 200 com `Novidades indisponíveis.`. Com JSON inválido, o resultado é o mesmo.
- [ ] O `app/novidades.json` real é uma lista válida, e em cada entrada:
  - `tipo` é um dos três valores;
  - `data` é uma data válida;
  - `texto` tem até 200 caracteres e não contém `.py`, `app/` nem a palavra `spec`/`specs` isolada (regex `\bspecs?\b`, sem diferenciar maiúsculas; "especial" e "inspeção" passam);
  - `onde.aba`, quando existe, é um `data-aba` presente em `app/templates/index.html`, e `onde.aba_nome` é o rótulo desse botão;
  - `onde.pagina`, quando existe, responde 200 no `TestClient`.
- [ ] Toda spec com número a partir de 156, `status: done` e gaveta `capacidade nova` ou `experiência` tem uma entrada no `app/novidades.json` com `"spec"` igual ao seu número. Assim as próximas entregas visíveis não esquecem a novidade.
- [ ] No Chromium, `/?aba=alertas` deixa o botão `[data-aba="alertas"]` com a classe `ativo`, e `/?aba=xyz` não registra erro no console. Use o mesmo navegador de `tests/test_aceite_146.py`, com `CHROMIUM_PATH` quando existir.
- [ ] `tests/test_aceite_156.py` usa `exigir_spec_done("156")` e não abre rede.

## Invariantes de produção
- O rodapé de `/` mostra uma data de novidade que não é posterior a hoje.
- Toda entrada de `novidades` no `/api/snapshot` tem `tipo` em {`novidade`, `melhoria`, `correcao`}, e toda `onde.aba` abre uma aba que existe na página inicial.
- Nenhuma entrada publicada cita nome de arquivo ou de função.

## Fora do escopo
- Gerar as entradas a partir do `CHANGELOG.md` ou dos PRs. O texto para o usuário é escrito à mão, de propósito.
- Rolar a página até o painel ou destacá-lo. A primeira fatia só abre a aba e diz o nome do painel.
- Marcar o que o usuário já viu, contar não lidas ou notificar.
- Mudanças internas do agente (`Agente:`) na página.

## Plano de validação
`pytest -q tests/test_aceite_156.py` sem internet. O PR de implementação traz as capturas de `make telas` do rodapé e de `/novidades`, em 1440 e 390 px.
