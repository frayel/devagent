document.addEventListener('DOMContentLoaded', () => {
    // Barras proporcionais nas tabelas
    document.querySelectorAll('tbody[data-rank]').forEach(tb => {
        const is = [...tb.querySelectorAll('i[data-v]')];
        if (!is.length) return;
        const max = Math.max(...is.map(i => parseFloat(i.dataset.v)));
        if (max === 0) return;
        is.forEach(i => i.style.width = (18 + 70 * (parseFloat(i.dataset.v) / max)) + '%');
    });

    document.querySelectorAll('.heatmap-ativo').forEach(el => {
        const peso = parseFloat(el.dataset.peso);
        el.style.setProperty('--ativo-peso', peso);
        el.style.setProperty('--ativo-cor', el.dataset.cor);
        el.style.setProperty('--ativo-opacidade', el.dataset.opacidade);
    });

    // Seletor de pregão (issue 883): a CSP bloqueia `onchange` inline, então a troca
    // de data envia o formulário daqui. Vale em toda página que usa o base.html.
    document.querySelectorAll('select.seletor-data').forEach(sel => {
        sel.addEventListener('change', () => { if (sel.form) sel.form.submit(); });
    });

    // A aba aberta fica na URL (?aba=) e segue junto na troca de data e no
    // "Voltar para hoje", para a recarga não voltar à Visão Geral (issue 883).
    const lembrarAba = (categoria) => {
        const url = new URL(window.location.href);
        url.searchParams.set('aba', categoria);
        try { history.replaceState(history.state, '', url); } catch (e) { /* URL fica como está */ }
        document.querySelectorAll('form input[type="hidden"][name="aba"]').forEach(campo => {
            campo.value = categoria;
            campo.disabled = false;
        });
        document.querySelectorAll('a.voltar-hoje').forEach(link => {
            const destino = new URL(link.getAttribute('href'), window.location.href);
            destino.searchParams.set('aba', categoria);
            link.setAttribute('href', destino.pathname + destino.search);
        });
    };

    // Abas de Navegação Contextual
    const abas = document.querySelectorAll('.aba-btn');
    const todosPaineis = document.querySelectorAll('.painel');

    abas.forEach(aba => {
        aba.addEventListener('click', () => {
            const categoria = aba.getAttribute('data-aba');

            abas.forEach(a => a.classList.remove('ativo'));
            aba.classList.add('ativo');
            if (categoria) lembrarAba(categoria);

            document.body.classList.remove('modo-so-sinais');

            if (categoria === 'sinais') {
                document.body.classList.add('modo-so-sinais');
                todosPaineis.forEach(p => p.style.display = '');
            } else {
                todosPaineis.forEach(p => {
                    if (p.classList.contains(categoria)) {
                        p.style.display = '';
                    } else {
                        if(p.classList.contains('visao-geral') || p.classList.contains('sentimento-risco') || p.classList.contains('rankings') || p.classList.contains('alertas')) {
                            p.style.display = 'none';
                        }
                    }
                });
            }
        });
    });

    todosPaineis.forEach(p => {
        if (!p.classList.contains('visao-geral') && (p.classList.contains('sentimento-risco') || p.classList.contains('rankings') || p.classList.contains('alertas'))) {
            p.style.display = 'none';
        }
    });

    // Spec 156: /?aba=<data-aba> abre essa aba, como um clique no botão. Valor
    // ausente ou que não corresponde a nenhuma aba mantém a Visão Geral.
    const abaPedida = new URLSearchParams(window.location.search).get('aba');
    if (abaPedida) {
        const botao = [...abas].find(a => a.getAttribute('data-aba') === abaPedida);
        if (botao) botao.click();
    }

    // Densidade Dinamica
    const btnDensidade = document.getElementById('btn-densidade');
    if (btnDensidade) {
        const grade = document.querySelector('.grade');

        // Spec 146: com o armazenamento bloqueado (cookies desligados, modo
        // restrito), ler localStorage lança e derrubava o resto deste handler.
        const lerDensidade = () => { try { return localStorage.getItem('densidade'); } catch (e) { return null; } };
        const gravarDensidade = (v) => { try { localStorage.setItem('densidade', v); } catch (e) { /* sem memória da escolha */ } };
        const densidadeState = lerDensidade();
        if (densidadeState === 'compacto') {
            grade.classList.add('compacto');
            btnDensidade.textContent = 'Confortável';
            btnDensidade.classList.add('ativo');
        }

        btnDensidade.addEventListener('click', () => {
            if (grade.classList.contains('compacto')) {
                grade.classList.remove('compacto');
                btnDensidade.textContent = 'Compacto';
                btnDensidade.classList.remove('ativo');
                gravarDensidade('confortavel');
            } else {
                grade.classList.add('compacto');
                btnDensidade.textContent = 'Confortável';
                btnDensidade.classList.add('ativo');
                gravarDensidade('compacto');
            }
        });
    }

});

document.addEventListener("DOMContentLoaded", () => {
    // Grafico Ibovespa
    const graficoIbovespa = document.getElementById('grafico-ibovespa');
    if (graficoIbovespa) {
        var dates = JSON.parse(graficoIbovespa.getAttribute('data-dates'));
        var closes = JSON.parse(graficoIbovespa.getAttribute('data-closes'));
        var tooltips = JSON.parse(graficoIbovespa.getAttribute('data-tooltips') || '[]');
        // Spec 145: a cor segue o sinal do período (último contra primeiro ponto),
        // não o do dia, que continua no card (DESIGN.md, seção 5).
        var periodo_positivo = graficoIbovespa.getAttribute('data-periodo-positivo') === 'true';

        // O Plotly não entende var(--x): resolve os tokens do tema para cores reais.
        var css = function(n) { return getComputedStyle(document.documentElement).getPropertyValue(n).trim(); };
        var cor = css(periodo_positivo ? '--alta' : '--baixa');
        var validos = closes.filter(function(c) { return c !== null && isFinite(c); });
        var minimo = Math.min.apply(null, validos);
        var maximo = Math.max.apply(null, validos);

        // Base invisível no mínimo do período: o preenchimento vai até ela, não até zero.
        var base = {
            x: dates,
            y: dates.map(function() { return minimo; }),
            type: 'scatter',
            mode: 'lines',
            line: { width: 0 },
            hoverinfo: 'skip',
            showlegend: false
        };
        var trace = {
            x: dates,
            y: closes,
            type: 'scatter',
            mode: 'lines',
            line: { color: cor, width: 1.5 },
            fill: 'tonexty',
            fillcolor: css(periodo_positivo ? '--alta-area' : '--baixa-area'),
            text: tooltips,
            // O texto de cada ponto vem pronto do servidor; o último traz o
            // fechamento anterior e a variação do dia (spec 145).
            hovertemplate: '%{text}<extra></extra>'
        };

        if (typeof Painel !== 'undefined' && Painel.grafico) {
            Painel.grafico('grafico-ibovespa', [base, trace], {
                margin: { t: 16, r: 64, b: 24, l: 8 },
                // Eixo Y nunca começa em zero: 2% abaixo do mínimo do período.
                yaxis: {
                    showgrid: true,
                    gridcolor: css('--borda'),
                    zeroline: false,
                    side: 'right',
                    range: [minimo * 0.98, maximo + (maximo - minimo) * 0.05]
                }
            });
        }
    }
});
