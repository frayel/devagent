const Painel = {
    grafico: function(id, traces, layout_opcoes) {
        const el = document.getElementById(id);
        if (!el) return;
        // Sem a biblioteca (CDN fora do ar, bloqueada ou recusada pelo
        // integrity), o contêiner diz que falhou em vez de ficar em branco.
        const indisponivel = () => {
            el.innerHTML = '<div class="vazio grafico-indisponivel">Gráfico indisponível agora.<br>O navegador não carregou a biblioteca de gráficos.</div>';
        };
        if (typeof window.Plotly === 'undefined' || typeof window.Plotly.newPlot !== 'function') {
            indisponivel();
            return;
        }
        const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
        const cor_texto_3 = css('--texto-3');
        const cor_borda = css('--borda');

        const layout_padrao = {
            paper_bgcolor: 'transparent',
            plot_bgcolor: 'transparent',
            font: { family: '-apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif', size: 12, color: cor_texto_3 },
            margin: { t: 16, r: 64, b: 24, l: 8 },
            xaxis: {
                showgrid: false,
                zeroline: false,
                nticks: 6,
                tickformat: '%d/%m'
            },
            yaxis: {
                showgrid: true,
                gridcolor: cor_borda,
                zeroline: false,
                side: 'right'
            },
            showlegend: false,
            hovermode: 'x unified',
            separators: ',.',
            dragmode: false
        };

        const config = { displayModeBar: false, responsive: true };
        Promise.resolve(window.Plotly.newPlot(id, traces, Object.assign(layout_padrao, layout_opcoes), config)).then(() => {
            if (document.getElementById(id)) {
                document.getElementById(id).classList.add('js-plotly-plot');
            }
        }).catch(indisponivel);

    }
};
