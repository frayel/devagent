const Painel = {
    grafico: function(id, traces, layout_opcoes) {
        const el = document.getElementById(id);
        if (!el) return;
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
        Plotly.newPlot(id, traces, Object.assign(layout_padrao, layout_opcoes), config).then(() => {
            if (document.getElementById(id)) {
                document.getElementById(id).classList.add('js-plotly-plot');
            }
        });

    }
};
