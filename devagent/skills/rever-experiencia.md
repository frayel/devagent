# Skill · Rever a experiência

Use no Passo 7, sempre que a cadência do `CICLO.md` mandar, e ao gerar ideias: pelo menos uma das ideias de toda rodada nasce desta revisão. O objetivo é tratar a tela inteira como produto, não só os painéis novos. Um produto que só cresce por adição fica cada vez mais longo, e a parte mais importante vai parar no fim da página.

## 1. Olhar antes de opinar

1. Rode o alvo de capturas indicado no `PRODUTO.md` e **abra as imagens** de desktop e celular. Sem abrir as imagens, a revisão não aconteceu.
2. Abra também a referência visual do projeto, se existir, e compare.
3. Percorra a página como o usuário descrito no `PRODUTO.md`, chegando pela primeira vez com uma dúvida concreta. Anote quanto ele precisou rolar e ler até achar a resposta.

## 2. Perguntas da revisão

- **Hierarquia.** O que está acima da dobra é o que responde às perguntas mais urgentes do produto? Algum painel novo empurrou para baixo algo mais importante?
- **Redundância.** Dois painéis dizem quase a mesma coisa? Dá para fundi-los num só, com uma visão mais rica?
- **Peso.** Algum painel ocupa mais espaço do que a informação que entrega? Algum está espremido demais para ser lido?
- **Agrupamento.** Os painéis estão em ordem de chegada ou em ordem de sentido? Painéis que respondem à mesma pergunta estão juntos?
- **Navegação.** A página ficou longa demais para uma única rolagem? Chegou a hora de seções, abas, âncoras ou uma segunda página?
- **Coerência.** O painel mais recente segue o guia visual tão bem quanto os primeiros? Algum padrão do guia nunca foi usado e deveria ser?
- **Estados.** Como a página fica quando uma fonte falha, de madrugada, num fim de semana? Ela ainda parece viva e honesta?

## 3. Transformar em ideia

Cada problema encontrado vira uma ideia no backlog com: a evidência (o que a captura mostra), a mudança proposta, o esforço e o risco. A pergunta do usuário que ela responde é "consigo achar o que preciso, rápido?". A escolhida vira spec pelo modelo de `escrever-spec.md`, com os critérios de aceite verificáveis por teste ou pelas capturas.

Uma revisão de experiência pode reorganizar a página inteira, fundir ou dividir painéis, criar navegação ou remover o que não se paga, desde que nenhuma informação exigida pelo `PRODUTO.md` (fonte, horário, aviso legal, transparência) desapareça.

## 4. Limites

- O guia visual manda. A revisão aplica o guia melhor; ela não cria estilo paralelo. Se a revisão mostrar que o próprio guia está errado ou incompleto, proponha a mudança num PR `agent:` só para o guia, com as capturas como evidência, e siga sem ela.
- Sem a captura, não há evidência, e sem evidência não há spec de experiência.
- Ao concluir uma revisão (mesmo que ela conclua que nada precisa mudar), registre a data e o resultado no `docs/STATE.md` e zere o contador de painéis da cadência.
