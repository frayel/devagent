"""Lê a página de saúde do produto em produção (ADR 016).

O produto publica um JSON com o estado geral e a lista do que pede ação. O
núcleo não sabe o que cada item significa: só lê o nível. Contrato mínimo:

    {
      "parcial": false,              # opcional: true enquanto o produto ainda
                                     # não terminou a primeira leitura
      "geral": {
        "nivel": "ok" | "atencao" | "problema",
        "pendentes": [
          {"nivel": "problema" | "atencao", "grupo": "...", "nome": "...",
           "resumo": "...", "detalhe": "...", "link": "...",
           "cura": "entrega",        # opcional: o item some quando a raia
                                     # de desenvolvimento entrega na main
           "desde": "2026-01-01T00:00:00+00:00",  # opcional: aberto desde
           "envelhece": false}       # opcional (padrão true): false impede
                                     # que a atenção vire problema em 24 h
        ]
      }
    }

Configuração em devagent.toml:

    [saude]
    caminho = "/api/saude"     # vazio desliga a verificação
    usuario = "admin"          # se o endpoint usa HTTP Basic

A senha vem de SAUDE_SENHA; a URL base, de PRODUCTION_URL ou `producao_url`.

Uso:
    python -m devagent.saude                    # resumo legível
    python -m devagent.saude --json             # o JSON lido
    python -m devagent.saude --issue corpo.md   # escreve o corpo da issue e
                                                # imprime a chave dos problemas

Código de saída: 0 sem problema · 1 com problema · 3 sem configuração,
fora do ar ou sem permissão. Só usa a biblioteca padrão.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

from devagent.config import CONFIG, PROJETO

LABEL = "sistema-com-problema"
MARCA = "<!-- saude: {chave} -->"


class Indisponivel(Exception):
    """A página de saúde não pôde ser lida (configuração, rede ou senha)."""


def url() -> str:
    caminho = str((CONFIG.get("saude") or {}).get("caminho", "")).strip()
    base = os.environ.get("PRODUCTION_URL", "").strip() or PROJETO.get(
        "producao_url", ""
    )
    if not caminho:
        raise Indisponivel("[saude] caminho não está no devagent.toml")
    if not base:
        raise Indisponivel("sem PRODUCTION_URL nem producao_url no devagent.toml")
    return base.rstrip("/") + "/" + caminho.lstrip("/")


def _pedido(endereco: str) -> urllib.request.Request:
    cabecalhos = {"Accept": "application/json", "User-Agent": "devagent-saude"}
    senha = os.environ.get("SAUDE_SENHA", "")
    if senha:
        usuario = str((CONFIG.get("saude") or {}).get("usuario", ""))
        par = base64.b64encode(f"{usuario}:{senha}".encode()).decode()
        cabecalhos["Authorization"] = f"Basic {par}"
    return urllib.request.Request(endereco, headers=cabecalhos)


def _baixar(endereco: str) -> dict[str, Any]:
    with urllib.request.urlopen(_pedido(endereco), timeout=60) as resp:
        return json.load(resp)


def ler(
    espera: float = 120,
    baixar: Callable[[str], dict[str, Any]] = _baixar,
    dormir: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Lê a página, esperando o serviço acordar e a primeira leitura terminar.

    No plano gratuito o serviço hiberna e leva até um minuto para subir; logo
    depois de subir, a página vem `parcial`. Espera até `espera` segundos por
    uma resposta completa e, se não vier, devolve a parcial que tiver.
    """
    endereco = url()
    limite = time.monotonic() + espera
    ultimo: dict[str, Any] | None = None
    erro = ""
    while True:
        try:
            ultimo = baixar(endereco)
            if not ultimo.get("parcial"):
                return ultimo
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise Indisponivel(
                    f"HTTP {e.code} em {endereco}: defina SAUDE_SENHA"
                ) from e
            erro = f"HTTP {e.code}"
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            erro = str(getattr(e, "reason", e))
        if time.monotonic() >= limite:
            break
        dormir(10)
    if ultimo is not None:
        return ultimo
    raise Indisponivel(f"{endereco} não respondeu: {erro}")


def pendentes(dados: dict[str, Any], nivel: str) -> list[dict[str, Any]]:
    """Itens do nível pedido, com a atenção aberta há mais de 24 h promovida.

    O item que declara `"envelhece": false` fica no nível que a página diz:
    o produto sabe quais atenções são medida de manutenção (lentidão, lacuna
    histórica, issue com fluxo próprio) e não defeito que piora com o tempo.
    """
    from datetime import datetime, timezone, timedelta

    agora = datetime.now(timezone.utc)

    lista = []
    for p in (dados.get("geral") or {}).get("pendentes", []):
        n = p.get("nivel")
        desde = p.get("desde")

        efetivo = n
        if n in ("atencao", "inativo") and desde and p.get("envelhece", True):
            try:
                dt = datetime.fromisoformat(desde)
                if agora - dt > timedelta(hours=24):
                    efetivo = "problema"
            except ValueError:
                pass

        if nivel == "problema" and efetivo == "problema":
            lista.append(p)
        elif nivel == "atencao" and efetivo == "atencao":
            lista.append(p)

    return lista


CURA_POR_ENTREGA = "entrega"


def pedem_correcao(dados: dict[str, Any]) -> list[dict[str, Any]]:
    """Problemas que a sessão precisa corrigir antes de seguir o ciclo.

    Fica de fora o problema que declara `cura: "entrega"` (por exemplo, a main
    parada): a correção dele é justamente entregar. Mandar a sessão tratar só
    a issue e proibir o resto travou a main de 09/11 a 13/11 (issue #807).
    """
    return [
        p for p in pendentes(dados, "problema") if p.get("cura") != CURA_POR_ENTREGA
    ]


def _linha(p: dict[str, Any]) -> str:
    grupo = f"{p['grupo']} · " if p.get("grupo") else ""
    texto = f"{grupo}{p.get('nome', '?')}: {p.get('resumo', '')}"
    if p.get("detalhe"):
        texto += f" ({p['detalhe']})"
    return texto


def resumo(dados: dict[str, Any]) -> str:
    problemas = pendentes(dados, "problema")
    atencoes = pendentes(dados, "atencao")
    linhas = [
        f"Saúde de produção: {len(problemas)} problema(s), {len(atencoes)} atenção(ões)"
        + (
            " (leitura parcial: o serviço acabou de subir)"
            if dados.get("parcial")
            else ""
        )
    ]
    linhas += [f"  PROBLEMA  {_linha(p)}" for p in problemas]
    linhas += [f"  atenção   {_linha(p)}" for p in atencoes]
    return "\n".join(linhas)


def chave(dados: dict[str, Any]) -> str:
    """Identifica o conjunto de problemas (não o texto, que muda a cada leitura)."""
    nomes = sorted(
        f"{p.get('grupo', '')}/{p.get('nome', '')}"
        for p in pendentes(dados, "problema")
    )
    return hashlib.sha1("\n".join(nomes).encode()).hexdigest()[:12] if nomes else ""


def corpo_da_issue(dados: dict[str, Any], endereco: str) -> str:
    problemas = pendentes(dados, "problema")
    atencoes = pendentes(dados, "atencao")
    partes = [
        f"A página de saúde de produção ({endereco}) acusa {len(problemas)} problema(s).",
        "",
        "## Problemas",
        *[
            f"- **{p.get('grupo', '')} · {p.get('nome', '')}**: {p.get('resumo', '')}"
            + (f"\n  (desde {p['desde']})" if p.get("desde") else "")
            + (f"\n  {p['detalhe']}" if p.get("detalhe") else "")
            + (f"\n  {p['link']}" if p.get("link") else "")
            for p in problemas
        ],
    ]
    if atencoes:
        partes += [
            "",
            "## Atenções (não bloqueiam; servem de medida para a manutenção)",
            *[f"- {_linha(p)}" for p in atencoes],
        ]
    partes += [
        "",
        "O agente trata esta issue no Passo 1 de devagent/CICLO.md: corrige no "
        "repositório o que tem causa no código ou nos workflows; o que depende de "
        "configuração fora do repositório vai descrito aqui, com o label `bloqueado`. "
        "O workflow atualiza esta issue a cada verificação e a fecha quando os "
        "problemas somem.",
        "",
        MARCA.format(chave=chave(dados)),
    ]
    return "\n".join(partes)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--issue", metavar="ARQUIVO")
    parser.add_argument("--espera", type=float, default=120)
    args = parser.parse_args(argv)
    try:
        dados = ler(espera=args.espera)
    except Indisponivel as e:
        print(f"Saúde de produção indisponível: {e}", file=sys.stderr)
        return 3
    if args.json:
        print(json.dumps(dados, ensure_ascii=False, indent=2))
    elif args.issue:
        with open(args.issue, "w", encoding="utf-8") as f:
            f.write(corpo_da_issue(dados, url()))
        print(chave(dados))
    else:
        print(resumo(dados))
    return 1 if pendentes(dados, "problema") else 0


if __name__ == "__main__":
    sys.exit(main())
