# Skill · Manutenção e poda

Use no Passo 7, sempre que a cadência de manutenção do `CICLO.md` vencer, e ao gerar ideias: pelo menos uma ideia de toda rodada sai desta skill. O objetivo é tratar o sistema como algo que envelhece. Um produto que só ganha partes fica mais lento, mais caro e mais difícil de mudar, e cada parte nova herda esse custo.

Duas gavetas saem daqui:

- **Saúde técnica:** o código e a operação aguentam o próximo ano de crescimento?
- **Poda:** cada parte que existe ainda se paga?

## 1. Medir antes de opinar

Manutenção sem medida vira gosto, e gosto não é evidência. Antes de propor, colete números do próprio repositório e da produção. Os caminhos concretos deste projeto estão na seção de manutenção do `PRODUTO.md`.

Comece pela página de saúde (`python -m devagent.saude`, ADR 016): cada item em **Atenção** é uma medida já pronta de algo degradado (integração instável, coleta lenta, painel vazio, agendamento perdido) e o primeiro candidato a virar spec de saúde técnica ou de poda.

**Saúde técnica**

- **Repetição.** Quantos módulos seguem o mesmo molde copiado (mesma estrutura de coletor, de cache, de rota, de teste)? Conte as linhas que só mudam de nome. Três cópias pedem uma abstração; dez pedem com urgência.
- **Custo de operação.** Quantas chamadas externas cada rodada de coleta faz, quanto tempo leva e quanto disso se repete entre módulos que pedem o mesmo dado à mesma fonte.
- **Fragilidade.** Quais testes falharam ou foram corrigidos mais de uma vez nos relatórios recentes? Quais dependem de horário, rede ou ordem de execução?
- **Tempo de verificação.** Quanto `make verify` demora, e quanto cresceu desde a última rodada.
- **Dependências.** Bibliotecas sem uso, versões muito atrás, duas bibliotecas para a mesma tarefa.
- **Documentação de arquitetura.** O documento de arquitetura do projeto ainda descreve o que está na `main`?

**Poda**

- **Vazio.** Quanto tempo cada parte visível passa sem dados, escondida ou mostrando estado de indisponível.
- **Redundância.** Duas partes respondem à mesma pergunta com dados quase iguais?
- **Custo sem retorno.** Uma parte custa muito para coletar ou manter e entrega pouco (um número que quase nunca muda, uma lista quase sempre vazia).
- **Critério do produto.** O `PRODUTO.md` pode definir um limite objetivo de poda. Quando definir, ele manda.

**Sem instrumento, a primeira entrega é o instrumento.** Se o sistema não guarda o que você precisa medir (por exemplo, quantas vezes cada parte ficou vazia), a spec escolhida desta rodada é criar essa medida, de forma barata e durável. A poda vem na rodada seguinte, com os números.

## 2. Transformar em ideia

Cada achado vira uma ideia no backlog com: a gaveta, a medida que a sustenta (com o número e de onde ele veio), a mudança proposta, o ganho esperado em número (linhas a menos, chamadas a menos, segundos a menos, partes a menos), o esforço e o risco.

Ideias de manutenção também podem ser originais: um cache compartilhado que deixa dez módulos mais simples, uma parte que se funde com outra e vira uma visão que não existia, um teste que passa a verificar uma classe inteira de erro.

## 3. Escrever a spec

Use o modelo de `escrever-spec.md` e acrescente no cabeçalho `gaveta: saúde técnica` ou `gaveta: poda`. Os critérios de aceite são verificáveis:

- **Saúde técnica:** o comportamento visível não muda (a saída de `/api/snapshot` ou equivalente continua a mesma, testes existentes passam sem alteração de expectativa) e a medida melhora no número prometido.
- **Poda:** diz o que sai, para onde vai o que ainda tem valor (fundido em outra parte, guardado como ideia no backlog) e qual medida justificou a remoção.

Refatoração grande vai em fatias, como qualquer spec: a primeira fatia converte um ou dois módulos para o molde novo e prova o ganho; o backlog guarda a conversão dos demais.

## 4. Limites

- **Comportamento visível não muda na saúde técnica.** Se a refatoração muda o que o usuário vê, ela é outra coisa e precisa de outra spec.
- **Poda não apaga história.** Specs `done`, relatórios e o registro no `CHANGELOG.md` ficam. A spec de poda cita as specs que criaram o que sai.
- **Testes saem junto com o código que testam, e só assim.** Remover o teste de uma parte que foi podada faz parte da poda. Remover ou afrouxar um teste para o CI passar continua proibido (seção 6 do `CICLO.md`).
- **Checagens de produção são do auditor.** Se a parte podada tem checagem na auditoria, a remoção dessa checagem vai num PR próprio, depois da poda chegar à `main`, citando a spec de poda. Nunca no mesmo PR.
- **Nada protegido some.** Informações exigidas pelo `PRODUTO.md` (fonte, horário, aviso legal, transparência) continuam presentes.
- Ao concluir uma rodada de manutenção (mesmo que a medida mostre que nada precisa mudar), registre a data, as medidas principais e o resultado na própria spec, com `gaveta: saúde técnica` ou `gaveta: poda`. As medidas registradas viram a linha de base da próxima rodada. O contador não é editado à mão: ele zera quando essa spec fica `done` (`python -m devagent.cadencias`, ADR 024).
