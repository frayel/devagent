# Skill · Escrever uma boa especificação

Use no Passo 7, ao transformar uma issue em spec (Passo 6) e ao dividir uma spec grande. Spec nascida de issue traz o link da issue no *Problema*.

- **Uma pergunta do investidor por spec.** Se o título precisa de "e", provavelmente são duas.
- **Cabe em um PR de ~400 linhas** (sem testes e fixtures). Se não couber, divida antes de marcar `ready`.
- **Critérios de aceite testáveis sem internet.** "Mostra a variação em %" vira "dado o fixture X, a página contém `+1,23%`".
- **Fontes com plano B.** Toda fonte tem reserva ou degradação explícita ("se falhar, o painel mostra 'dado indisponível' e o resto da página funciona").
- **Números com contexto.** Toda probabilidade ou recomendação especifica tamanho de amostra, janela e método.
- **Fora do escopo explícito.** Diga o que não será feito, para a implementação não crescer.
- **Leia `docs/context/dominio-b3.md`** para evitar armadilhas de mercado (feriados, atraso de dados, ajustes por proventos).
- Numere com o próximo `NNN` livre em `docs/specs/`.
