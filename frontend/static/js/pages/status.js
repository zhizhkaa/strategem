function statusApp(templateGameId) {
    return {
        gameId: null,
        teamName: '',
        gameState: null,
        allPeriods: [],
        loading: true,
        error: null,
        totalPeriods: 10,
        _charts: {},

        // ---- Computed helpers ----
        get scoreIndicator() {
            return this.indicators.find(i => i.key === 'score') || null;
        },
        get otherIndicators() {
            return this.indicators.filter(i => i.key !== 'score');
        },

        // ---- Computed indicators list ----
        get indicators() {
            if (!this.allPeriods.length) return [];

            const periods = this.allPeriods;
            const params  = this.gameState?.parameters || {};

            // Вспомогательные функции получения значения
            const pv  = (name) => params[name]?.value ?? null;
            const pdiv = (a, b) => (b && b !== 0) ? (a / b) : null;

            // Вычисляем ряды и текущие значения для каждого показателя
            const def = [
                {
                    key:     'score',
                    label:   'Сводный счёт',
                    formula: 'P6 + 4·P4',
                    note:    'Среднее за все завершённые периоды',
                    color:   '#6366f1',
                    series:  periods.map(p => ({ period: p.period_number, value: p.P6 + 4 * p.P4 })),
                    current: (() => {
                        const vals = periods.map(p => p.P6 + 4 * p.P4);
                        return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null;
                    })(),
                    round:   2,
                },
                {
                    key:     'P1',
                    label:   'Численность населения',
                    formula: 'P1',
                    note:    'Округляется до десятков',
                    color:   '#3b82f6',
                    series:  periods.map(p => ({ period: p.period_number, value: Math.round((p.P1 || 0) / 10) * 10 })),
                    current: pv('P1') != null ? Math.round(pv('P1') / 10) * 10 : null,
                    round:   0,
                },
                {
                    key:     'P4',
                    label:   'Продовольствие на душу населения в год',
                    formula: 'P4',
                    color:   '#22c55e',
                    series:  periods.map(p => ({ period: p.period_number, value: p.P4 })),
                    current: pv('P4'),
                    round:   2,
                },
                {
                    key:     'P6',
                    label:   'Товары на душу населения в год',
                    formula: 'P6',
                    color:   '#14b8a6',
                    series:  periods.map(p => ({ period: p.period_number, value: p.P6 })),
                    current: pv('P6'),
                    round:   2,
                },
                {
                    key:     'growth',
                    label:   'Темпы роста численности населения',
                    formula: '(P8 − P5) / 1000',
                    note:    'Годовой прирост населения в процентах',
                    color:   '#f97316',
                    series:  periods.map(p => ({ period: p.period_number, value: ((p.P8 || 0) - (p.P5 || 0)) / 1000 })),
                    current: (pv('P8') != null && pv('P5') != null) ? (pv('P8') - pv('P5')) / 1000 : null,
                    round:   4,
                },
                {
                    key:     'TF1',
                    label:   'Внешний долг',
                    formula: 'TF1',
                    color:   '#ef4444',
                    series:  periods.map(p => ({ period: p.period_number, value: p.TF1 })),
                    current: pv('TF1'),
                    round:   0,
                },
                {
                    key:     'F7',
                    label:   'Состояние окружающей среды',
                    formula: 'F7',
                    color:   '#10b981',
                    series:  periods.map(p => ({ period: p.period_number, value: p.F7 })),
                    current: pv('F7'),
                    round:   3,
                },
                {
                    key:     'E10',
                    label:   'Коэффициент потребления энергоресурсов',
                    formula: 'E10',
                    color:   '#eab308',
                    series:  periods.map(p => ({ period: p.period_number, value: p.E10 })),
                    current: pv('E10'),
                    round:   3,
                },
                {
                    key:     'agriEff',
                    label:   'Эффективность сельского хозяйства',
                    formula: 'F9 / F3',
                    note:    'Продовольствие на единицу капитала в с/х',
                    color:   '#84cc16',
                    series:  periods.map(p => ({
                        period: p.period_number,
                        value:  (p.F3 && p.F3 !== 0) ? Math.round(p.F9 / p.F3) : null,
                    })),
                    current: (pv('F3') && pv('F9') != null) ? Math.round(pv('F9') / pv('F3')) : null,
                    round:   0,
                },
                {
                    key:     'indEff',
                    label:   'Эффективность промышленности',
                    formula: 'G15 / (G3 + G6)',
                    note:    'Товаров на единицу капитала в промышленности и услугах',
                    color:   '#8b5cf6',
                    series:  periods.map(p => ({
                        period: p.period_number,
                        value:  ((p.G3 || 0) + (p.G6 || 0) !== 0) ? Math.round(p.G15 / ((p.G3 || 0) + (p.G6 || 0))) : null,
                    })),
                    current: (() => {
                        const g3 = pv('G3'), g6 = pv('G6'), g15 = pv('G15');
                        return (g3 != null && g6 != null && g15 != null && (g3 + g6) !== 0)
                            ? Math.round(g15 / (g3 + g6)) : null;
                    })(),
                    round:   0,
                },
                {
                    key:     'E16',
                    label:   'Эффективность энергетики',
                    formula: 'E16',
                    note:    'Генерация энергии на единицу капитала',
                    color:   '#f59e0b',
                    series:  periods.map(p => ({ period: p.period_number, value: p.E16 != null ? Math.round(p.E16) : null })),
                    current: pv('E16') != null ? Math.round(pv('E16')) : null,
                    round:   0,
                },
                {
                    key:     'P2',
                    label:   'Всего продовольствия',
                    formula: 'P2',
                    color:   '#06b6d4',
                    series:  periods.map(p => ({ period: p.period_number, value: p.P2 })),
                    current: pv('P2'),
                    round:   0,
                },
                {
                    key:     'P3',
                    label:   'Всего товаров',
                    formula: 'P3',
                    color:   '#0ea5e9',
                    series:  periods.map(p => ({ period: p.period_number, value: p.P3 })),
                    current: pv('P3'),
                    round:   0,
                },
                {
                    key:     'E7',
                    label:   'Всего энергоресурсов',
                    formula: 'E7',
                    color:   '#facc15',
                    series:  periods.map(p => ({ period: p.period_number, value: p.E7 })),
                    current: pv('E7'),
                    round:   0,
                },
            ];

            // Добавляем форматированное текущее значение
            return def.map(ind => ({
                ...ind,
                currentFormatted: this.fmt(ind.current, ind.round),
            }));
        },

        // ---- Init ----
        async init() {
            this.gameId = templateGameId != null ? String(templateGameId) : localStorage.getItem('strategem_game');
            this.teamName = localStorage.getItem('strategem_team_name') || 'Команда';

            if (!this.gameId) {
                this.error = 'Игра не выбрана.';
                this.loading = false;
                return;
            }

            try {
                const [stateData, periodsData] = await Promise.all([
                    API.get(`/games/${this.gameId}/state/`),
                    API.get(`/games/${this.gameId}/periods/`),
                ]);
                this.gameState   = stateData;
                this.totalPeriods = stateData.game_info?.total_periods || 10;
                this.allPeriods  = (periodsData.results || periodsData).sort((a, b) => a.period_number - b.period_number);
            } catch (e) {
                this.error = 'Ошибка загрузки: ' + e.message;
            } finally {
                this.loading = false;
                if (!this.error) {
                    this.$nextTick(() => this.renderAllCharts());
                }
            }
        },

        // ---- Charts ----
        renderAllCharts() {
            for (const ind of this.indicators) {
                this.renderSparkline(ind);
            }
        },

        renderSparkline(ind) {
            const ctx = document.getElementById('chart-' + ind.key);
            if (!ctx) return;
            if (this._charts[ind.key]) { this._charts[ind.key].destroy(); }

            const validData = ind.series.filter(d => d.value !== null && d.value !== undefined && isFinite(d.value));
            if (!validData.length) return;

            this._charts[ind.key] = new Chart(ctx, {
                type: 'line',
                data: {
                    datasets: [{
                        data: validData.map(d => ({ x: d.period, y: d.value })),
                        borderColor: ind.color,
                        backgroundColor: ind.color + '15',
                        borderWidth: 2,
                        tension: 0.3,
                        fill: true,
                        pointRadius: validData.length <= 12 ? 3 : 2,
                        pointHoverRadius: 5,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: false,
                    interaction: { intersect: false, mode: 'index' },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: (ctx) => this.fmt(ctx.parsed.y, ind.round),
                            },
                        },
                    },
                    scales: {
                        x: {
                            type: 'linear',
                            min: 1,
                            max: this.totalPeriods,
                            ticks: { stepSize: 1, font: { size: 10 } },
                            title: { display: false },
                            grid: { color: '#f3f4f6' },
                        },
                        y: {
                            ticks: {
                                maxTicksLimit: 4,
                                font: { size: 10 },
                                callback: v => new Intl.NumberFormat('ru-RU', {
                                    notation: 'compact', maximumFractionDigits: 1,
                                }).format(v),
                            },
                            grid: { color: '#f3f4f6' },
                        },
                    },
                },
            });
        },

        destroyCharts() {
            for (const c of Object.values(this._charts)) c.destroy();
            this._charts = {};
        },

        // ---- Formatters ----
        fmt(value, decimals = 2) {
            if (value === null || value === undefined) return '—';
            return new Intl.NumberFormat('ru-RU', {
                minimumFractionDigits: 0,
                maximumFractionDigits: decimals,
            }).format(value);
        },
    };
}
