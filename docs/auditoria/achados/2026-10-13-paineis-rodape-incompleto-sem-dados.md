---
id: 2026-10-13-paineis-rodape-incompleto-sem-dados
severidade: media
painel: multiplos
status: resolvido
visto_em: 2026-10-13T02:46+00:00
---

# Painéis vazios continuam exibindo rodapés incompletos sem fonte ou data

## O que o investidor vê
Ao acessar o site em produção, múltiplos painéis (como Visão Macro, Sentimento de Risco, rankings e alertas) exibem o rodapé como `Fonte  · ` sem indicar a fonte ou a data, e em vários casos não exibem conteúdo, apenas o rodapé malformado.

## O que deveria ver
Mesmo quando um painel não possui dados, seu rodapé deve informar qual foi a fonte tentada e a data e hora da tentativa (incluindo o fuso horário BRT), ou então ocultar completamente o rodapé se o painel estiver oculto ou indisponível por erro severo. A transparência deve ser mantida.

## Evidência
O HTML capturado de produção revela a presença do rodapé `<div class="rodape">Fonte  · </div>` repetido mais de 20 vezes na página inicial.
Por exemplo:
```html
<section class="painel span-4 visao-macro alertas">
  <div class="cab">
    <h2>Alerta de Falso Rompimento</h2>
    <details>
      <summary aria-label="Método">i</summary>
      <div class="metodo">Ações que romperam resistência mas devolveram...</div>
    </details>
  </div>
  <div class="vazio">Dado indisponível agora.<br>A fonte não respondeu na última coleta.</div>
  <div class="rodape">Fonte  · </div>
</section>
```

## Como reproduzir
1. Acessar https://devagent-vb52.onrender.com/
2. Procurar pelos painéis com dados vazios ou não disponíveis e analisar o conteúdo do `.rodape`.

## Invariante proposta
Verificar no auditor determinístico (`auditar.py`) se não existe nenhum elemento `.rodape` contendo apenas `Fonte  · `.

## Resolução
Corrigido via PR, condicionando a exibição do rodapé à presença de fonte no HTML (`app/templates/componentes.html`), e com o teste garantido em `auditoria/auditar.py`.