1. Add new table `sensibilidade_juros_cache` and its index in `app/database.py`.
2. Add `SensibilidadeJurosData`, `save_sensibilidade_juros_data`, `get_latest_sensibilidade_juros_data` in `app/database.py`.
3. Create `app/collectors/sensibilidade_juros.py` based on `dolar_correlation.py`. It should fetch DI Futuro (`DI1F27.SA`) and a specific basket of tickers sensitive to interest rates (e.g. LREN3, MGLU3, PETZ3, BHIA3, EZTC3, CYRE3, MRVE3, TEND3, DIRR3, CVCB3, RENT3, NTCO3, ALOS3, SOMA3, ARZZ3, SMFT3, LWSA3, CASH3, BMOB3, TOTS3) or simply use TICKERS but focused on them (if TICKERS includes them). Let's define the basket explicitly or use TICKERS if simpler. We should define a list of tickers. It should save top 3 with the most negative correlation.
4. Add `sensibilidade_juros` collector to `app/agendador.py` to `_coletar()` method.
5. Create `app/services/sensibilidade_juros.py` to format the data for view.
6. Update `app/main.py` to include `sensibilidade_juros` in `/api/snapshot` and `/` routes.
7. Update `app/templates/index.html` to display the new panel in the "Sentimento & Risco" section.
8. Update `scripts/telas.py` to include seed data for `sensibilidade_juros_cache`.
9. Complete pre-commit steps to ensure proper testing, verification, review, and reflection are done.
10. Submit PR.
