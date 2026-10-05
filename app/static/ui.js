document.addEventListener('DOMContentLoaded', () => {
    // Barras proporcionais nas tabelas
    document.querySelectorAll('tbody[data-rank]').forEach(tb => {
        const is = [...tb.querySelectorAll('i[data-v]')];
        if (!is.length) return;
        const max = Math.max(...is.map(i => parseFloat(i.dataset.v)));
        if (max === 0) return;
        is.forEach(i => i.style.width = (18 + 70 * (parseFloat(i.dataset.v) / max)) + '%');
    });

    // Filtros
    const botoes = document.querySelectorAll('.filtro-btn');
    const paineisMacro = document.querySelectorAll('.visao-macro');
    const paineisMicro = document.querySelectorAll('.visao-micro');

    botoes.forEach(btn => {
        btn.addEventListener('click', () => {
            const filtro = btn.getAttribute('data-filtro');

            botoes.forEach(b => {
                b.classList.remove('ativo');
            });
            btn.classList.add('ativo');

            document.body.classList.remove('modo-so-sinais');

            if (filtro === 'todos') {
                paineisMacro.forEach(p => p.style.display = '');
                paineisMicro.forEach(p => p.style.display = '');
            } else if (filtro === 'macro') {
                paineisMacro.forEach(p => p.style.display = '');
                paineisMicro.forEach(p => p.style.display = 'none');
            } else if (filtro === 'micro') {
                paineisMacro.forEach(p => p.style.display = 'none');
                paineisMicro.forEach(p => p.style.display = '');
            } else if (filtro === 'sinais') {
                document.body.classList.add('modo-so-sinais');
                paineisMacro.forEach(p => p.style.display = '');
                paineisMicro.forEach(p => p.style.display = '');
            }
        });
    });
});

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
            fill: 'tozeroy',
            fillcolor: css(is_positive ? '--alta-fundo' : '--baixa-fundo'),
            hovertemplate: '%{x|%d/%m/%Y}<br><b>%{y:,.0f}</b><extra></extra>'
        };

        if (typeof Painel !== 'undefined' && Painel.grafico) {
            Painel.grafico('grafico-ibovespa', [trace], {
                margin: { t: 16, r: 64, b: 24, l: 8 }
            });
        }
    }
