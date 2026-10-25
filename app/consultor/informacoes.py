from datetime import datetime, timezone, timedelta
from app.calendario import ultimo_pregao_fechado, e_pregao

BRT = timezone(timedelta(hours=-3))


def parse_iso(dt_str):
    if not dt_str:
        return None
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(BRT)
    except Exception:
        return None


def construir_informacoes_de(dados):
    agora = datetime.now(timezone.utc).astimezone(BRT)
    sinais_pregao_ts = dados.get("sinais_pregao") if isinstance(dados, dict) else None

    sinais_pregao_str = ""
    sinais_pregao_dt = None
    if sinais_pregao_ts and sinais_pregao_ts != 1:
        dt = datetime.fromtimestamp(sinais_pregao_ts, timezone.utc).astimezone(BRT)
        sinais_pregao_str = dt.strftime("%d/%m/%Y")
        sinais_pregao_dt = dt.date()

    sinais_coletado_em_str = ""
    sinais_coletado_dt = parse_iso(
        dados.get("sinais_coletado_em") if isinstance(dados, dict) else None
    )
    if sinais_coletado_dt:
        sinais_coletado_em_str = sinais_coletado_dt.strftime("%d/%m/%Y %H:%M")

    opinioes_status = (
        dados.get("opinioes_status", {}) if isinstance(dados, dict) else {}
    )
    opinioes_extraidas_em_str = ""
    opinioes_extraidas_dt = parse_iso(opinioes_status.get("ultima_extracao_em"))
    if opinioes_extraidas_dt:
        opinioes_extraidas_em_str = opinioes_extraidas_dt.strftime("%d/%m/%Y %H:%M")

    opinioes_recentes = (
        dados.get("opinioes_recentes", []) if isinstance(dados, dict) else []
    )
    opinioes_materia_recente_str = ""
    if opinioes_recentes:
        max_dt = None
        for op in opinioes_recentes:
            dt_pub = parse_iso(op.get("publicada_em"))
            if dt_pub:
                if max_dt is None or dt_pub > max_dt:
                    max_dt = dt_pub
        if max_dt:
            opinioes_materia_recente_str = max_dt.strftime("%d/%m/%Y %H:%M")

    from app.consultor.universo import CARTEIRA_CONFERIDA_EM

    composicao_conferida_em_str = CARTEIRA_CONFERIDA_EM.strftime("%d/%m/%Y")

    # Avaliacao estado sinais
    estado_sinais = "Atualizado"
    frase_sinais = ""
    ultimo_fechado = ultimo_pregao_fechado(agora)

    if sinais_pregao_dt and sinais_pregao_dt < ultimo_fechado:
        estado_sinais = "Defasado"
        frase_sinais = f"Os sinais técnicos referem-se a {sinais_pregao_str}, mas o último pregão fechado foi {ultimo_fechado.strftime('%d/%m/%Y')}."
    elif (
        sinais_coletado_dt
        and (agora - sinais_coletado_dt).total_seconds() > 4 * 24 * 3600
    ):
        estado_sinais = "Defasado"
        frase_sinais = (
            f"Os dados foram coletados há mais de 4 dias ({sinais_coletado_em_str})."
        )

    # Avaliacao estado opinioes
    estado_opinioes = "Atualizado"
    frase_opinioes = ""
    if opinioes_extraidas_dt:
        age_hours = (agora - opinioes_extraidas_dt).total_seconds() / 3600
        if e_pregao(agora.date()):
            if age_hours > 24:
                estado_opinioes = "Defasado"
                frase_opinioes = f"As opiniões de especialistas foram extraídas há mais de 24h em dia útil ({opinioes_extraidas_em_str})."
        else:
            if age_hours > 72:
                estado_opinioes = "Defasado"
                frase_opinioes = f"As opiniões de especialistas foram extraídas há mais de 72h ({opinioes_extraidas_em_str})."

    if not sinais_pregao_str:
        sinais_pregao_str = "-"
    if not sinais_coletado_em_str:
        sinais_coletado_em_str = "-"
    if not opinioes_extraidas_em_str:
        opinioes_extraidas_em_str = "-"
    if not opinioes_materia_recente_str:
        opinioes_materia_recente_str = "-"

    return {
        "sinais_pregao": sinais_pregao_str,
        "sinais_coletado_em": sinais_coletado_em_str,
        "opinioes_extraidas_em": opinioes_extraidas_em_str,
        "opinioes_materia_mais_recente": opinioes_materia_recente_str,
        "composicao_conferida_em": composicao_conferida_em_str,
        "estado_sinais": estado_sinais,
        "estado_opinioes": estado_opinioes,
        "frase_sinais": frase_sinais,
        "frase_opinioes": frase_opinioes,
    }
