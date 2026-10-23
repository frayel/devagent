import subprocess


def test_tabelas_legadas_ausentes():
    cmd = 'grep -rn "radar_anomalia_fechamento_cache" app/'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    assert result.stdout.strip() == "", (
        "Tabela radar_anomalia_fechamento_cache encontrada no app/"
    )

    cmd = 'grep -rn "consultor_confianca_regras" app/'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    assert (
        "CREATE TABLE IF NOT EXISTS radar_anomalia_fechamento_cache"
        not in result.stdout
    )
    assert "CREATE TABLE IF NOT EXISTS consultor_confianca_regras" not in result.stdout
