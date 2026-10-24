1. **Collector and Database Definition**
   - Execute `cat << 'EOF' >> app/database.py` to append `CorrelacaoDiData` dataclass with `timestamp` (datetime), `correlacao_intradia` (float|None), `correlacao_5d` (float|None), `status` (str|None), and `fonte` (str) along with snapshot helper functions `save_correlacao_di_data` and `get_latest_correlacao_di_data`.
     ```python
     @dataclass
     class CorrelacaoDiData:
         timestamp: datetime
         correlacao_intradia: float | None
         correlacao_5d: float | None
         status: str | None
         fonte: str = "yfinance"

     def save_correlacao_di_data(data: CorrelacaoDiData) -> None:
         from app.banco import gravar_snapshot
         payload = data.__dict__.copy()
         payload["timestamp"] = payload["timestamp"].isoformat()
         gravar_snapshot("correlacao_di", data.timestamp.astimezone(timezone.utc).date(), "ao_vivo", getattr(data, "fonte", "yfinance"), payload)

     def get_latest_correlacao_di_data() -> CorrelacaoDiData | None:
         from app.banco import ler_snapshot
         payload = ler_snapshot("correlacao_di")
         if not payload:
             return None
         payload_copy = payload.copy()
         if "timestamp" in payload_copy:
             payload_copy["timestamp"] = datetime.fromisoformat(payload_copy["timestamp"])
         return CorrelacaoDiData(**payload_copy)
     ```
   - Verify changes with `tail -n 25 app/database.py`.

2. **Collector Implementation (`app/collectors/correlacao_di.py`)**
   - Execute `cat << 'EOF' > app/collectors/correlacao_di.py` to implement `collect_and_save()`. The script will use `math` to calculate pearson, and `fetch_with_retry` for `DI1F27.SA` and `^BVSP` using `interval=15m`, `range=5d`. Determine status `Correlacionado` (<-0.7) or `Descolado`.
     ```python
     import logging
     import math
     from datetime import datetime, timezone
     from app.database import CorrelacaoDiData, save_correlacao_di_data
     from app.collectors.utils import fetch_with_retry
     from app.collectors import mt5

     logger = logging.getLogger(__name__)

     def calculate_returns(prices):
         return [(prices[i] - prices[i-1])/prices[i-1] for i in range(1, len(prices)) if prices[i-1] != 0]

     def calculate_pearson(x, y):
         n = len(x)
         if n == 0 or n != len(y): return 0.0
         sum_x, sum_y = sum(x), sum(y)
         sum_xy = sum(i * j for i, j in zip(x, y))
         sum_x_sq, sum_y_sq = sum(i**2 for i in x), sum(i**2 for i in y)
         num = (n * sum_xy) - (sum_x * sum_y)
         den = math.sqrt(max(0, ((n * sum_x_sq) - sum_x**2) * ((n * sum_y_sq) - sum_y**2)))
         return num / den if den != 0 else 0.0

     def collect_and_save() -> bool:
         logger.info("Starting correlacao_di collection...")
         url = "https://query1.finance.yahoo.com/v7/finance/spark?symbols=DI1F27.SA,^BVSP&range=5d&interval=15m"
         try:
             response = fetch_with_retry(url, timeout=15.0)
             data = response.json()
             results = data.get("spark", {}).get("result", [])
             if len(results) < 2: raise ValueError("Not enough symbols returned")
         except Exception as e:
             logger.error(f"Error fetching correlacao_di: {e}")
             save_correlacao_di_data(CorrelacaoDiData(timestamp=datetime.now(timezone.utc), correlacao_intradia=None, correlacao_5d=None, status=None, fonte=mt5.fonte_efetiva("yfinance")))
             return False

         di_res = next((r for r in results if r["symbol"] == "DI1F27.SA"), None)
         ibov_res = next((r for r in results if r["symbol"] == "^BVSP"), None)
         if not di_res or not ibov_res:
             save_correlacao_di_data(CorrelacaoDiData(timestamp=datetime.now(timezone.utc), correlacao_intradia=None, correlacao_5d=None, status=None, fonte=mt5.fonte_efetiva("yfinance")))
             return False

         di_closes = di_res.get("response", [{}])[0].get("indicators", {}).get("quote", [{}])[0].get("close", [])
         di_dates = di_res.get("response", [{}])[0].get("timestamp", [])
         ibov_closes = ibov_res.get("response", [{}])[0].get("indicators", {}).get("quote", [{}])[0].get("close", [])
         ibov_dates = ibov_res.get("response", [{}])[0].get("timestamp", [])

         di_dict = {d: c for d, c in zip(di_dates, di_closes) if c is not None}
         ibov_dict = {d: c for d, c in zip(ibov_dates, ibov_closes) if c is not None}
         common_dates = sorted(list(set(di_dict.keys()).intersection(set(ibov_dict.keys()))))

         if len(common_dates) < 5:
             save_correlacao_di_data(CorrelacaoDiData(timestamp=datetime.now(timezone.utc), correlacao_intradia=None, correlacao_5d=None, status=None, fonte=mt5.fonte_efetiva("yfinance")))
             return False

         di_common = [di_dict[d] for d in common_dates]
         ibov_common = [ibov_dict[d] for d in common_dates]

         di_returns = calculate_returns(di_common)
         ibov_returns = calculate_returns(ibov_common)
         corr_5d = calculate_pearson(di_returns, ibov_returns)

         # Extract last day (approx last 25-35 15m intervals)
         last_day_ts = common_dates[-1]
         last_day_start = last_day_ts - (last_day_ts % 86400) # Simple start of day estimate
         di_today = [c for d, c in zip(common_dates, di_common) if d >= last_day_start]
         ibov_today = [c for d, c in zip(common_dates, ibov_common) if d >= last_day_start]
         corr_intra = calculate_pearson(calculate_returns(di_today), calculate_returns(ibov_today)) if len(di_today) > 3 else None

         status = "Correlacionado" if corr_5d <= -0.7 else "Descolado"

         save_correlacao_di_data(CorrelacaoDiData(
             timestamp=datetime.now(timezone.utc),
             correlacao_intradia=corr_intra,
             correlacao_5d=corr_5d,
             status=status,
             fonte=mt5.fonte_efetiva("yfinance")
         ))
         logger.info("Saved correlacao_di data")
         return True
     ```
   - Verify with `cat app/collectors/correlacao_di.py`.

3. **Register Collector**
   - Execute `cat << 'EOF' > patch_agendador.py` to inject `"correlacao_di",` in `app/agendador.py`. (I verified earlier using `grep` that `assimetria_risco_retorno` and `consultor_historico` are adjacent in `app/agendador.py`).
     ```python
     with open("app/agendador.py", "r") as f: content = f.read()
     content = content.replace('"assimetria_risco_retorno",\n        "consultor_historico",', '"assimetria_risco_retorno",\n        "correlacao_di",\n        "consultor_historico",')
     with open("app/agendador.py", "w") as f: f.write(content)
     ```
   - Run `python patch_agendador.py && rm patch_agendador.py`.
   - Verify with `grep -C 2 "correlacao_di" app/agendador.py`.

4. **Service Layer (`app/services/correlacao_di.py`)**
   - Execute `cat << 'EOF' > app/services/correlacao_di.py`
     ```python
     from typing import Any
     from datetime import timezone, timedelta
     from app.database import get_latest_correlacao_di_data

     def get_correlacao_di_view_data() -> dict[str, Any] | None:
         data = get_latest_correlacao_di_data()
         if not data or data.status is None:
             return None

         return {
             "correlacao_intradia": data.correlacao_intradia,
             "correlacao_intradia_formatada": f"{data.correlacao_intradia:.2f}".replace(".", ",") if data.correlacao_intradia is not None else "-",
             "correlacao_5d": data.correlacao_5d,
             "correlacao_5d_formatada": f"{data.correlacao_5d:.2f}".replace(".", ",") if data.correlacao_5d is not None else "-",
             "status": data.status,
             "time": data.timestamp.astimezone(timezone(timedelta(hours=-3))).strftime("%d/%m/%Y %H:%M:%S BRT"),
             "fonte": getattr(data, "fonte", "yfinance"),
         }
     ```
   - Verify with `cat app/services/correlacao_di.py`.

5. **Integration in Main Application (`app/main.py`)**
   - Execute `cat << 'EOF' > patch_main.py`
     ```python
     with open("app/main.py", "r") as f: content = f.read()
     content = content.replace('from app.services.atrasadas_rally import get_atrasadas_rally_view_data', 'from app.services.atrasadas_rally import get_atrasadas_rally_view_data\nfrom app.services.correlacao_di import get_correlacao_di_view_data')
     content = content.replace('atrasadas_rally = get_atrasadas_rally_view_data()', 'atrasadas_rally = get_atrasadas_rally_view_data()\n    correlacao_di = get_correlacao_di_view_data()')
     content = content.replace('"atrasadas_rally": atrasadas_rally,', '"atrasadas_rally": atrasadas_rally,\n            "correlacao_di": correlacao_di,')
     content = content.replace('resp["paineis"]["assimetria_risco_retorno"] = {', 'correlacao_di_data = get_latest_correlacao_di_data()\n    if correlacao_di_data:\n        resp["paineis"]["correlacao_di"] = {\n            "coletado_em": correlacao_di_data.timestamp.isoformat(),\n            "fonte": getattr(correlacao_di_data, "fonte", "yfinance"),\n            "correlacao_intradia": correlacao_di_data.correlacao_intradia,\n            "correlacao_5d": correlacao_di_data.correlacao_5d,\n            "status": correlacao_di_data.status\n        }\n    else:\n        resp["paineis"]["correlacao_di"] = {}\n\n    resp["paineis"]["assimetria_risco_retorno"] = {')
     with open("app/main.py", "w") as f: f.write(content)
     ```
   - Run `python patch_main.py && rm patch_main.py`.
   - Verify with `grep -C 3 "correlacao_di" app/main.py`.

6. **Frontend Integration (`app/templates/index.html`)**
   - Execute `cat << 'EOF' > patch_index.py` (I verified earlier that `{% call painel("Sensibilidade ao dólar"` exists in `app/templates/index.html`).
     ```python
     with open("app/templates/index.html", "r") as f: content = f.read()
     painel_html = """
     {% call painel("Correlação Ibov vs DI", 1, "Correlação de Pearson entre Ibovespa e DI1F27.SA (intervalos de 15m nos últimos 5 dias). Uma correlação menor que -0.7 indica que o mercado se move inversamente aos juros, o que é o comportamento correlacionado esperado.", correlacao_di.fonte if correlacao_di else None, correlacao_di.time if correlacao_di else None, "" if correlacao_di else "escondido") %}
         {% if not correlacao_di %}
             {{ estado('indisponivel') }}
         {% else %}
             {{ kpi(correlacao_di.status, "Situação em 5 pregões", gauge(correlacao_di.correlacao_5d, "Força", -1.0, 1.0, "{:+.2f}", divergente=False, resumo="Correlação de 5 dias", escala=["Inversa", "Direta"]), True) }}
             {{ kpi(correlacao_di.correlacao_intradia_formatada, "Intradia", "Correlação hoje") }}
         {% endif %}
     {% endcall %}
     """
     old_panel = '{% call painel("Sensibilidade ao dólar", 6, "Correlação de Pearson entre retornos diários da ação e do dólar (DOL$ no MT5, BRL=X no Yahoo) nos últimos 30 pregões.", dolar_correlation.fonte if dolar_correlation else "", dolar_correlation.time if dolar_correlation else "", "visao-macro alertas") %}'
     content = content.replace(old_panel, old_panel + "\n" + painel_html)
     with open("app/templates/index.html", "w") as f: f.write(content)
     ```
   - Run `python patch_index.py && rm patch_index.py`.
   - Verify with `grep -C 5 "Correlação Ibov vs DI" app/templates/index.html`.

7. **Documentation Updates**
   - Execute `cat << 'EOF' > patch_docs.py`
     ```python
     with open("docs/specs/081-rastreador-correlacao-di.md", "r") as f: content = f.read()
     content = content.replace("status: ready", "status: done")
     with open("docs/specs/081-rastreador-correlacao-di.md", "w") as f: f.write(content)

     with open("CHANGELOG.md", "r") as f: content = f.read()
     content = content.replace("## [Unreleased]", "## [Unreleased]\n- Entrega Spec 081: Rastreador de Correlação com Juros Futuros (DI)")
     with open("CHANGELOG.md", "w") as f: f.write(content)

     import re
     with open("docs/STATE.md", "r") as f: content = f.read()
     match = re.search(r"Specs entregues desde a última rodada.*?:\s*(\d+)", content)
     if match:
         count = int(match.group(1)) + 1
         content = content.replace(match.group(0), f"Specs entregues desde a última rodada (exceto as de manutenção): {count}")
     content = content.replace("## Implementado\n\n- Spec 082", "## Implementado\n\n- Spec 081 (Rastreador de Correlação DI):\n  - Banco de dados (snapshots `correlacao_di`).\n  - Coletor buscando `DI1F27.SA` e `^BVSP` no Yahoo Finance em intervalos de 15m.\n  - Exibição do status de correlação em 5 dias e intradia na página inicial.\n  - Adicionado ao contrato `/api/snapshot`.\n- Spec 082")
     with open("docs/STATE.md", "w") as f: f.write(content)
     ```
   - Run `python patch_docs.py && rm patch_docs.py`.
   - Verify with `cat docs/specs/081-rastreador-correlacao-di.md`, `git diff CHANGELOG.md`, and `git diff docs/STATE.md`.

8. **Linting and Formatting**
   - Execute `ruff format . && ruff check --fix .` in the bash session.

9. **Testing and Verification**
   - Execute `make verify` and `make smoke` in the bash session to ensure everything passes.
   - Execute `make telas` to generate UI screenshots.
   - Visually confirm the outcome via screenshots using the `read_media_file` tool if necessary.

10. **Pre-commit Steps**
    - Complete pre-commit steps to ensure proper testing, verification, review, and reflection are done.

11. **Status Update and Submit**
    - Use the `submit` tool to open the PR with title `feat: painel de correlação Ibovespa e DI`, description `Implementa o painel Rastreador de Correlação com Juros Futuros (DI) conforme spec 081.`, branch name `feat/correlacao-di` and commit message `feat: painel correlacao ibov e di`.
