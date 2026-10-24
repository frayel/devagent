---
id: 090
titulo: Yahoo Finance com 404: diagnosticar causa
status: draft
esforco: M
gaveta: saúde técnica
---

## Revisão
Esta spec era grande demais (alterava `registro_fontes`, banco de dados, montador de lote HTTP e a interface `/sistema` tudo junto) e foi dividida em:
- **090a**: Detalhar falhas do Yahoo no registro
- **090b**: Suspender símbolos deslistados por 24h e isolar do lote
