from datetime import datetime
import statistics
from collections import defaultdict
from app.consultor.armazenamento import get_connection, init_db


def _calcular_excesso(
    preco_inicial: float,
    preco_final: float,
    ibov_inicial: float,
    ibov_final: float,
) -> float:
    retorno_ativo = (preco_final / preco_inicial) - 1.0
    retorno_ibov = (ibov_final / ibov_inicial) - 1.0
    return retorno_ativo - retorno_ibov


def _acertou(decisao: str, excesso: float) -> bool:
    if decisao in ("Comprar", "No radar"):
        return excesso > 0
    elif decisao == "Vender":
        return excesso < 0
    return False


def _acertou_casa(recomendacao: str, excesso: float) -> bool:
    rec = recomendacao.lower()
    if rec == "compra":
        return excesso > 0
    elif rec == "venda":
        return excesso < 0
    else:  # neutro
        return abs(excesso) <= 0.02


def calcular_placar():
    init_db()
    conn, backend = get_connection()
    try:
        cursor = conn.cursor()

        # fetch fechamentos
        cursor.execute(
            "SELECT data_pregao, ticker, preco_fechamento FROM consultor_fechamentos"
        )
        fechamentos_db = cursor.fetchall()

        fechamentos = {}
        datas_por_ativo = defaultdict(list)
        datas_pregao_set = set()

        for f in fechamentos_db:
            dp, ticker, preco = f[0], f[1], f[2]
            fechamentos[(dp, ticker)] = preco
            datas_por_ativo[ticker].append(dp)
            datas_pregao_set.add(dp)

        datas_pregao_list = sorted(list(datas_pregao_set))

        # fetch recomendacoes
        cursor.execute(
            "SELECT timestamp, ticker, decisao_final, regra_tecnica, consenso, preco, gatilho FROM consultor_recomendacoes"
        )
        recomendacoes = cursor.fetchall()

        # fetch opinioes
        cursor.execute(
            "SELECT ticker, casa, recomendacao, data_materia FROM consultor_opinioes"
        )
        opinioes = cursor.fetchall()

        stats_consultor = defaultdict(
            lambda: {
                "n": 0,
                "n5": 0,
                "n20": 0,
                "acertos5": 0,
                "acertos20": 0,
                "excessos5": [],
                "excessos20": [],
                "n_gatilhos": 0,
                "acertos_gatilhos": 0,
                "excessos_gatilho20": [],
            }
        )
        stats_regras = defaultdict(
            lambda: {
                "n": 0,
                "n5": 0,
                "n20": 0,
                "acertos5": 0,
                "acertos20": 0,
                "excessos5": [],
                "excessos20": [],
                "n_gatilhos": 0,
                "acertos_gatilhos": 0,
                "excessos_gatilho20": [],
            }
        )
        stats_casas = defaultdict(
            lambda: {"n": 0, "n20": 0, "acertos20": 0, "excessos20": []}
        )

        for rec in recomendacoes:
            ts_raw = rec[0]
            if " " in ts_raw:
                try:
                    dp = datetime.strptime(ts_raw.split(" ")[0], "%d/%m/%Y").strftime(
                        "%Y-%m-%d"
                    )
                except Exception:
                    dp = ts_raw.split(" ")[0]
            else:
                dp = ts_raw

            ticker = rec[1]
            decisao = rec[2]
            regra = rec[3]
            preco_rec = rec[5]
            gatilho_raw = rec[6]

            try:
                idx_hoje = datas_pregao_list.index(dp)
            except ValueError:
                continue

            ibov_preco_hoje = fechamentos.get((dp, "^BVSP"))
            if not ibov_preco_hoje:
                continue

            stats_consultor[decisao]["n"] += 1
            if regra.startswith("R"):
                regra_base = regra.split(" ")[0]
                stats_regras[regra_base]["n"] += 1

            # avaliacao em 5 e 20 pregoes
            for offset in (5, 20):
                if idx_hoje + offset < len(datas_pregao_list):
                    dp_futuro = datas_pregao_list[idx_hoje + offset]
                    preco_futuro = fechamentos.get((dp_futuro, ticker))
                    ibov_preco_futuro = fechamentos.get((dp_futuro, "^BVSP"))

                    if preco_futuro and ibov_preco_futuro:
                        excesso = _calcular_excesso(
                            preco_rec, preco_futuro, ibov_preco_hoje, ibov_preco_futuro
                        )

                        if decisao != "Aguardar":
                            if offset == 5:
                                stats_consultor[decisao]["n5"] += 1
                                stats_consultor[decisao]["excessos5"].append(excesso)
                                if _acertou(decisao, excesso):
                                    stats_consultor[decisao]["acertos5"] += 1

                                if regra.startswith("R"):
                                    regra_base = regra.split(" ")[0]
                                    stats_regras[regra_base]["n5"] += 1
                                    stats_regras[regra_base]["excessos5"].append(
                                        excesso
                                    )
                                    if _acertou(decisao, excesso):
                                        stats_regras[regra_base]["acertos5"] += 1
                            else:
                                stats_consultor[decisao]["n20"] += 1
                                stats_consultor[decisao]["excessos20"].append(excesso)
                                if _acertou(decisao, excesso):
                                    stats_consultor[decisao]["acertos20"] += 1

                                if regra.startswith("R"):
                                    regra_base = regra.split(" ")[0]
                                    stats_regras[regra_base]["n20"] += 1
                                    stats_regras[regra_base]["excessos20"].append(
                                        excesso
                                    )
                                    if _acertou(decisao, excesso):
                                        stats_regras[regra_base]["acertos20"] += 1

            # Gatilhos para Aguardar
            if decisao == "Aguardar" and gatilho_raw != "-":
                try:
                    gatilho_val = float(gatilho_raw)
                except ValueError:
                    continue

                # Check next 20 pregoes for gatilho hit
                gatilho_hit_dp = None
                gatilho_hit_idx = -1
                for offset in range(1, 21):
                    if idx_hoje + offset < len(datas_pregao_list):
                        dp_futuro = datas_pregao_list[idx_hoje + offset]
                        preco_futuro = fechamentos.get((dp_futuro, ticker))
                        if preco_futuro is not None:
                            # Simplification: we check if closing price crossed gatilho
                            if (
                                preco_rec < gatilho_val and preco_futuro >= gatilho_val
                            ) or (
                                preco_rec > gatilho_val and preco_futuro <= gatilho_val
                            ):
                                gatilho_hit_dp = dp_futuro
                                gatilho_hit_idx = idx_hoje + offset
                                break

                if gatilho_hit_dp:
                    stats_consultor[decisao]["acertos_gatilhos"] += 1
                    # calculate excesso 20 pregoes after gatilho hit
                    if gatilho_hit_idx + 20 < len(datas_pregao_list):
                        dp_20 = datas_pregao_list[gatilho_hit_idx + 20]
                        preco_20 = fechamentos.get((dp_20, ticker))

                        ibov_gatilho = fechamentos.get((gatilho_hit_dp, "^BVSP"))
                        ibov_20 = fechamentos.get((dp_20, "^BVSP"))

                        if preco_20 and ibov_gatilho and ibov_20:
                            excesso = _calcular_excesso(
                                gatilho_val, preco_20, ibov_gatilho, ibov_20
                            )
                            stats_consultor[decisao]["excessos_gatilho20"].append(
                                excesso
                            )

        for op in opinioes:
            ticker = op[0]
            casa = op[1]
            recomendacao = op[2]
            ts_raw = op[3]

            try:
                dp = datetime.strptime(ts_raw, "%d/%m/%Y").strftime("%Y-%m-%d")
            except Exception:
                try:
                    dp = ts_raw[:10]
                except Exception:
                    continue

            try:
                idx_hoje = datas_pregao_list.index(dp)
            except ValueError:
                continue

            preco_hoje = fechamentos.get((dp, ticker))
            ibov_preco_hoje = fechamentos.get((dp, "^BVSP"))
            if not preco_hoje or not ibov_preco_hoje:
                continue

            stats_casas[casa]["n"] += 1
            if idx_hoje + 20 < len(datas_pregao_list):
                dp_futuro = datas_pregao_list[idx_hoje + 20]
                preco_futuro = fechamentos.get((dp_futuro, ticker))
                ibov_preco_futuro = fechamentos.get((dp_futuro, "^BVSP"))

                if preco_futuro and ibov_preco_futuro:
                    excesso = _calcular_excesso(
                        preco_hoje, preco_futuro, ibov_preco_hoje, ibov_preco_futuro
                    )
                    stats_casas[casa]["n20"] += 1
                    stats_casas[casa]["excessos20"].append(excesso)
                    if _acertou_casa(recomendacao, excesso):
                        stats_casas[casa]["acertos20"] += 1

        def format_stats(stats):
            res = {}
            for k, v in stats.items():
                if k == "Aguardar":
                    pct_gatilho = (
                        (v["acertos_gatilhos"] / v["n"] * 100) if v["n"] > 0 else 0
                    )
                    med_gatilho20 = (
                        statistics.median(v["excessos_gatilho20"])
                        if v["excessos_gatilho20"]
                        else 0
                    )
                    res[k] = {
                        "n": v["n"],
                        "pct_gatilho": pct_gatilho,
                        "med_gatilho20": med_gatilho20,
                    }
                else:
                    tx5 = (v["acertos5"] / v["n5"] * 100) if v["n5"] > 0 else 0
                    med5 = statistics.median(v["excessos5"]) if v["excessos5"] else 0
                    tx20 = (v["acertos20"] / v["n20"] * 100) if v["n20"] > 0 else 0
                    med20 = statistics.median(v["excessos20"]) if v["excessos20"] else 0
                    res[k] = {
                        "n": v["n"],
                        "n5": v["n5"],
                        "n20": v["n20"],
                        "tx5": tx5,
                        "med5": med5,
                        "tx20": tx20,
                        "med20": med20,
                    }
            return res

        placar = {
            "armazenamento": backend,
            "consultor": format_stats(stats_consultor),
            "regras": format_stats(stats_regras),
            "casas": {
                c: {
                    "n20": v["n20"],
                    "tx20": (v["acertos20"] / v["n20"] * 100) if v["n20"] > 0 else 0,
                    "med20": statistics.median(v["excessos20"])
                    if v["excessos20"]
                    else 0,
                }
                for c, v in stats_casas.items()
                if v["n20"] >= 5
            },
        }

        # Ensure default values are populated for empty rules / decisions to display correctly
        for dec in ("Comprar", "Vender", "No radar"):
            if dec not in placar["consultor"]:
                placar["consultor"][dec] = {
                    "n": 0,
                    "n5": 0,
                    "n20": 0,
                    "tx5": 0,
                    "med5": 0,
                    "tx20": 0,
                    "med20": 0,
                }
        if "Aguardar" not in placar["consultor"]:
            placar["consultor"]["Aguardar"] = {
                "n": 0,
                "pct_gatilho": 0,
                "med_gatilho20": 0,
            }

        for reg in ("R1", "R2", "R3", "R4", "R5"):
            if reg not in placar["regras"]:
                placar["regras"][reg] = {
                    "n": 0,
                    "n5": 0,
                    "n20": 0,
                    "tx5": 0,
                    "med5": 0,
                    "tx20": 0,
                    "med20": 0,
                }

        return placar

    finally:
        conn.close()
