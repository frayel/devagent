document.addEventListener('DOMContentLoaded', () => {
    // Barras proporcionais nas tabelas
    document.querySelectorAll('tbody[data-rank]').forEach(tb => {
        const is = [...tb.querySelectorAll('i[data-v]')];
        if (!is.length) return;
        const max = Math.max(...is.map(i => parseFloat(i.dataset.v)));
        if (max === 0) return;
        is.forEach(i => i.style.width = (18 + 70 * (parseFloat(i.dataset.v) / max)) + '%');
    });

    // Abas de Navegação Contextual
    const abas = document.querySelectorAll('.aba-btn');
    const todosPaineis = document.querySelectorAll('.painel');

    abas.forEach(aba => {
        aba.addEventListener('click', () => {
            const categoria = aba.getAttribute('data-aba');

            abas.forEach(a => a.classList.remove('ativo'));
            aba.classList.add('ativo');

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
});

document.addEventListener("DOMContentLoaded", () => {
    // Grafico Ibovespa
    const graficoIbovespa = document.getElementById('grafico-ibovespa');
    if (graficoIbovespa) {
        var dates = JSON.parse(graficoIbovespa.getAttribute('data-dates'));
        var closes = JSON.parse(graficoIbovespa.getAttribute('data-closes'));
        var is_positive = graficoIbovespa.getAttribute('data-is-positive') === 'true';

        // O Plotly não entende var(--x): resolve os tokens do tema para cores reais.
        var css = function(n) { return getComputedStyle(document.documentElement).getPropertyValue(n).trim(); };
        var cor = css(is_positive ? '--alta' : '--baixa');

        var trace = {
            x: dates,
            y: closes,
            type: 'scatter',
            mode: 'lines',
            line: { color: cor, width: 1.5 },
            // Preenche até a base do eixo, que fica 2% abaixo do mínimo (DESIGN.md, seção 5).
            fill: 'tozeroy',
            fillcolor: css(is_positive ? '--alta-fundo' : '--baixa-fundo'),
            hovertemplate: '%{x|%d/%m/%Y}<br><b>%{y:,.0f}</b><extra></extra>'
        };

        if (typeof Painel !== 'undefined' && Painel.grafico) {
            var validos = closes.filter(function(c) { return c !== null && isFinite(c); });
            var minimo = Math.min.apply(null, validos);
            var maximo = Math.max.apply(null, validos);
            Painel.grafico('grafico-ibovespa', [trace], {
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
