# ADR 028 · Ritmo do desenvolvedor pela cota que resta

- **Data:** 2026-10-29 · **Status:** aceita
- **Revê:** ADR 012 (ritmo da cota)

## Contexto

O intervalo mínimo entre sessões do desenvolvedor era 24 h / (`JULES_LIMITE_DIARIO` − reserva), como se a cota fosse só dele. As raias paralelas (teto de 8 + 24 + 16 sessões em 24 h), os especialistas e o auditor gastam da mesma cota. Com o plano Pro (100 sessões), o ritmo prometia ~15 min entre sessões do desenvolvedor, mas a soma de todos podia chegar ao limite antes da janela de 24 h andar, e então `cota_esgotada` segurava o desenvolvedor até as sessões mais antigas saírem da janela.

## Decisão

Com `JULES_LIMITE_DIARIO` e a lista de sessões, `intervalo_do_desenvolvedor` passa a ser:

    (momento em que a sessão mais antiga da janela sai dela − agora) / vagas que restam

em que as vagas que restam são o limite, menos a reserva, menos **todas** as sessões abertas nas últimas 24 h. A conta se refaz a cada rodada: quanto mais perto a próxima vaga, mais curta a espera.

- Sem sessões na janela, não há espera.
- Sem vaga, espera até a mais antiga sair (o `cota_esgotada` continua valendo).
- Sem a lista de sessões, vale a conta antiga. `JULES_INTERVALO_MINUTOS` continua tendo precedência.

## Consequências

- A cota que as raias gastam desacelera o desenvolvedor na hora, em vez de esgotar a cota mais tarde e parar a esteira.
- No início de uma janela vazia, a primeira sessão sai na hora e as seguintes se espalham sozinhas, porque a sessão recém-aberta passa a ser a mais antiga da janela.
