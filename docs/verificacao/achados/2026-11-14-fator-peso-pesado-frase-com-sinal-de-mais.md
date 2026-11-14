---
id: 2026-11-14-fator-peso-pesado-frase-com-sinal-de-mais
severidade: media
painel: Fator Peso Pesado (app/services/fator_peso_pesado.py)
status: aberto
visto_em: 2026-11-14T11:05-03:00
pr: 813
---

# A frase do Fator Peso Pesado escreve "+50,8%" quando as cinco andaram contra o índice

## O que acontece
`app/services/fator_peso_pesado.py:34` monta o módulo da razão com `formatar_razao(abs(proporcao))`. `formatar_razao` põe `+` em todo valor positivo, e o valor de `abs()` é sempre positivo. A frase sai com o sinal de mais, mesmo no sentido oposto:

```
>>> frase(-50.8, False)
'As 5 maiores ações andaram no sentido oposto ao do Ibovespa, somando +50,8% do tamanho do movimento.'
>>> frase(150, False)
'... somando +150,0% do tamanho do movimento. O restante do índice compensou a diferença.'
```

No caso da spec 143 (índice +1.000 pontos, cinco nomes somando −508), o card mostra `−50,8%` no número grande e, logo abaixo, "sentido oposto ... somando +50,8%". Os dois sinais se contradizem na mesma tela, na conta que a spec existe para deixar clara.

## O que deveria acontecer
A spec 143 pede "com 50,8% do tamanho do movimento": o módulo, sem sinal. O sentido já está dito pelas palavras "mesmo sentido" e "sentido oposto".

## Evidência
`tests/test_aceite_143.py` confere `−50,8%` e "sentido oposto" no HTML, mas nenhum teste olha o texto da frase em volta do módulo, então o `+` passa. O `+150,0%` do segundo critério de aceite também é satisfeito pela frase, o que esconde o defeito.

## Como reproduzir
```
python -c "from app.services.fator_peso_pesado import frase; print(frase(-50.8, False))"
```
