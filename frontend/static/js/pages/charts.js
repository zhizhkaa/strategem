function chartsApp() {
        return {
            // State
            gameId: null,
            teamName: "",
            loading: true,
            error: null,
            currentPeriod: 1,
            totalPeriods: 10,
            initialized: false,
            chartsData: null,
            allPeriods: [],

            // Search & Custom Chart
            searchQuery: "",
            filteredParams: [],
            customChartParams: [],
            allParameters: [],

            // Chart instances
            charts: {},

            // Methods
            async init() {
                if (this.initialized) return;
                this.initialized = true;

                this.gameId = localStorage.getItem("strategem_game");
                this.teamName =
                    localStorage.getItem("strategem_team_name") || "Команда";

                if (!this.gameId) {
                    this.error = "Игра не выбрана. Вернитесь к выбору команды.";
                    this.loading = false;
                    return;
                }

                await this.loadCharts();
                this.loading = false;
            },

            async loadCharts() {
                try {
                    // Load game state for period info
                    const gameState = await API.get(
                        `/games/${this.gameId}/state/`,
                    );
                    this.currentPeriod =
                        gameState.game_info?.current_period || 1;
                    this.totalPeriods =
                        gameState.game_info?.total_periods || 10;

                    // Load charts data
                    this.chartsData = await API.get(
                        `/games/${this.gameId}/charts/`,
                    );

                    // Load all periods for search functionality
                    const periodsResponse = await API.get(
                        `/games/${this.gameId}/periods/`,
                    );
                    this.allPeriods = periodsResponse.results || periodsResponse;

                    // Build parameters list for search
                    this.buildParametersList();

                    this.$nextTick(() => {
                        this.renderAllCharts();
                    });
                } catch (e) {
                    this.error = "Ошибка загрузки данных: " + e.message;
                }
            },

            buildParametersList() {
                // Collect all unique parameters from all periods
                const paramsMap = new Map();
                
                this.allPeriods.forEach(period => {
                    Object.entries(period).forEach(([code, value]) => {
                        if (!paramsMap.has(code)) {
                            if (!/^(P|E|F|G|TF)\d+$/.test(code)) return;
                            if (!Number.isFinite(Number(value))) return;
                            paramsMap.set(code, {
                                code: code,
                                name: this.getParameterName(code),
                                category: this.getParameterCategory(code)
                            });
                        }
                    });
                });

                this.allParameters = Array.from(paramsMap.values()).sort((a, b) => 
                    a.code.localeCompare(b.code)
                );
            },

            getParameterName(code) {
                // Try to find in existing chart data
                for (const category of Object.values(this.chartsData || {})) {
                    const param = category.find(p => p.parameter === code);
                    if (param) return param.verbose_name || code;
                }
                return code;
            },

            getParameterCategory(code) {
                if (code.startsWith('P')) return 'population';
                if (code.startsWith('E')) return 'energy';
                if (code.startsWith('G')) return 'industry';
                if (code.startsWith('F')) return 'agriculture';
                if (code.startsWith('TF')) return 'trade';
                return 'other';
            },

            filterParameters() {
                if (!this.searchQuery || this.searchQuery.length < 1) {
                    this.filteredParams = [];
                    return;
                }

                const query = this.searchQuery.toLowerCase();
                this.filteredParams = this.allParameters.filter(param =>
                    param.code.toLowerCase().includes(query) ||
                    param.name.toLowerCase().includes(query)
                ).slice(0, 30); // Limit results
            },

            clearSearch() {
                this.searchQuery = "";
                this.filteredParams = [];
            },

            addParameterToChart(paramCode) {
                if (!this.customChartParams.includes(paramCode)) {
                    this.customChartParams.push(paramCode);
                    this.$nextTick(() => {
                        this.renderCustomChart();
                    });
                }
            },

            removeParameterFromChart(paramCode) {
                const index = this.customChartParams.indexOf(paramCode);
                if (index > -1) {
                    this.customChartParams.splice(index, 1);
                    if (this.customChartParams.length > 0) {
                        this.$nextTick(() => {
                            this.renderCustomChart();
                        });
                    } else if (this.charts.custom) {
                        this.charts.custom.destroy();
                        delete this.charts.custom;
                    }
                }
            },

            clearCustomChart() {
                this.customChartParams = [];
                if (this.charts.custom) {
                    this.charts.custom.destroy();
                    delete this.charts.custom;
                }
            },

            renderCustomChart() {
                const ctx = document.getElementById("customChart");
                if (!ctx) return;

                this.destroyChart("custom", ctx);

                const datasets = this.customChartParams.map((paramCode, index) => {
                    const data = this.allPeriods.map(period => ({
                        x: period.period_number,
                        y: Number(period[paramCode] || 0),
                    }));

                    const colors = [
                        '#3b82f6', '#22c55e', '#eab308', '#a855f7', '#14b8a6',
                        '#f97316', '#ec4899', '#6366f1', '#84cc16', '#06b6d4'
                    ];

                    return {
                        label: this.getParameterName(paramCode) + ' (' + paramCode + ')',
                        data: data,
                        borderColor: colors[index % colors.length],
                        backgroundColor: colors[index % colors.length] + '20',
                        tension: 0.3,
                        fill: false,
                        pointRadius: 4,
                        pointHoverRadius: 6,
                    };
                });

                this.charts.custom = new Chart(ctx, {
                    type: "line",
                    data: { datasets },
                    options: this.getChartOptions("Период", "Значение"),
                });
            },

            renderAllCharts() {
                this.renderPopulationChart();
                this.renderEconomyChart();
                this.renderCapitalChart();
                this.renderFinanceChart();
                this.renderEnvironmentChart();
            },

            destroyChart(key, ctx) {
                if (this.charts[key]) {
                    this.charts[key].destroy();
                    delete this.charts[key];
                }
                const existingChart = Chart.getChart?.(ctx);
                if (existingChart) {
                    existingChart.destroy();
                }
            },

            renderChart(key, canvasId, data, colors, xLabel, yLabel) {
                const ctx = document.getElementById(canvasId);
                if (!ctx || !data?.length) return;
                this.destroyChart(key, ctx);

                this.charts[key] = new Chart(ctx, {
                    type: "line",
                    data: { datasets: this.createDatasets(data, colors) },
                    options: this.getChartOptions(xLabel, yLabel),
                });
            },

            renderPopulationChart() {
                this.renderChart(
                    "population",
                    "populationChart",
                    this.chartsData?.population,
                    ["#3b82f6", "#60a5fa", "#93c5fd", "#1d4ed8", "#2563eb", "#1e40af"],
                    "Период",
                    "Значение",
                );
            },

            renderEconomyChart() {
                this.renderChart(
                    "economy",
                    "economyChart",
                    this.chartsData?.economy,
                    ["#22c55e", "#4ade80", "#86efac", "#15803d"],
                    "Период",
                    "Производство",
                );
            },

            renderCapitalChart() {
                this.renderChart(
                    "capital",
                    "capitalChart",
                    this.chartsData?.capital,
                    ["#eab308", "#facc15", "#fde047", "#ca8a04"],
                    "Период",
                    "Капитал",
                );
            },

            renderFinanceChart() {
                this.renderChart(
                    "finance",
                    "financeChart",
                    this.chartsData?.finance,
                    [
                        "#a855f7",
                        "#c084fc",
                        "#d8b4fe",
                        "#7c3aed",
                        "#16a34a",
                        "#22c55e",
                        "#86efac",
                        "#c026d3",
                        "#e879f9",
                        "#f5d0fe",
                        "#8b5cf6",
                    ],
                    "Период",
                    "Финансы",
                );
            },

            renderEnvironmentChart() {
                this.renderChart(
                    "environment",
                    "environmentChart",
                    this.chartsData?.environment,
                    ["#14b8a6", "#2dd4bf", "#5eead4", "#0d9488"],
                    "Период",
                    "Экология",
                );
            },

            createDatasets(data, colors) {
                if (!data || !Array.isArray(data)) return [];

                return data.map((item, index) => ({
                    label:
                        item.verbose_name ||
                        item.name ||
                        `Параметр ${index + 1}`,
                    data: (item.data || []).map((d) => ({
                        x: d.period,
                        y: d.value,
                    })),
                    borderColor: colors[index % colors.length],
                    backgroundColor: colors[index % colors.length] + "20",
                    tension: 0.3,
                    fill: false,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                }));
            },

            formatChartValue(value) {
                return new Intl.NumberFormat("ru-RU", {
                    notation: "compact",
                    maximumFractionDigits: 1,
                }).format(value);
            },

            getChartOptions(xLabel, yLabel) {
                const formatter = this.formatChartValue;
                return {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        intersect: false,
                        mode: "index",
                    },
                    plugins: {
                        legend: {
                            position: "bottom",
                            labels: {
                                usePointStyle: true,
                                padding: 15,
                            },
                        },
                        tooltip: {
                            backgroundColor: "rgba(0, 0, 0, 0.8)",
                            padding: 12,
                            titleFont: { size: 14 },
                            bodyFont: { size: 13 },
                            callbacks: {
                                label: function (context) {
                                    return `${context.dataset.label}: ${formatter(context.parsed.y)}`;
                                },
                            },
                        },
                    },
                    scales: {
                        x: {
                            type: "linear",
                            title: {
                                display: true,
                                text: xLabel,
                                font: { weight: "bold" },
                            },
                            ticks: {
                                stepSize: 1,
                            },
                        },
                        y: {
                            title: {
                                display: true,
                                text: yLabel,
                                font: { weight: "bold" },
                            },
                            ticks: {
                                callback: function (value) {
                                    return formatter(value);
                                },
                            },
                        },
                    },
                };
            },
        };
    }
