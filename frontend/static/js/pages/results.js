function gameResults() {
        return {
            // State
            gameId: null,
            teamName: "",
            loading: true,
            error: null,
            totalPeriods: 10,
            initialized: false,

            // Data
            finalState: {},
            initialState: {},
            periodsData: [],
            chartsData: null,

            // Computed
            get changes() {
                return {
                    population: this.calculateChange("P1"),
                    environment: this.calculateChange("F7"),
                    debt: this.calculateChange("TF1"),
                };
            },

            get scoreIndicator() {
                const series = this.periodsData
                    .map((period) => ({
                        period: period.period,
                        value: this.scoreValue(period),
                    }))
                    .filter((point) => Number.isFinite(point.value));

                if (!series.length) return null;

                const current =
                    series.reduce((sum, point) => sum + point.value, 0) /
                    series.length;

                return {
                    label: "Сводный счёт",
                    formula: "P6 + 4·P4",
                    note: "Среднее за все завершённые периоды",
                    color: "#6366f1",
                    series,
                    current,
                    currentFormatted: this.formatScoreValue(current),
                };
            },

            // Charts
            charts: {},

            // Methods
            async init() {
                if (this.initialized) return;
                this.initialized = true;

                this.gameId = localStorage.getItem("strategem_game");
                this.teamName =
                    localStorage.getItem("strategem_team_name") || "Команда";

                if (!this.gameId) {
                    this.error = "Игра не выбрана.";
                    this.loading = false;
                    return;
                }

                await this.loadData();
                this.loading = false;
            },

            async loadData() {
                try {
                    // Load game state
                    const gameState = await API.get(
                        `/games/${this.gameId}/state/`,
                    );
                    this.totalPeriods =
                        gameState.game_info?.total_periods || 10;

                    // Extract final state
                    const params = gameState.parameters || {};
                    this.finalState = {};
                    for (const [key, val] of Object.entries(params)) {
                        this.finalState[key] = val.value;
                    }

                    // Load periods history
                    const periods = await API.get(
                        `/games/${this.gameId}/periods/`,
                    );
                    this.periodsData = periods.map((p) => ({
                        period: p.period_number,
                        P1: p.P1,
                        P4: p.P4,
                        P5: p.P5,
                        P6: p.P6,
                        P8: p.P8,
                        E7: p.E7,
                        E15: p.E15,
                        E17: p.E17,
                        F7: p.F7,
                        TF1: p.TF1,
                    }));

                    // Get initial state
                    if (this.periodsData.length > 0) {
                        this.initialState = this.periodsData[0];
                    }

                    // Load charts data
                    this.chartsData = await API.get(
                        `/games/${this.gameId}/charts/`,
                    );

                    this.$nextTick(() => {
                        this.renderAllCharts();
                    });
                } catch (e) {
                    this.error = "Ошибка загрузки данных: " + e.message;
                }
            },

            calculateChange(param) {
                if (!this.initialState[param] || !this.finalState[param])
                    return 0;
                const initial = this.initialState[param];
                const final = this.finalState[param];
                return ((final - initial) / initial) * 100;
            },

            scoreValue(period) {
                const food = Number(period?.P4);
                const goods = Number(period?.P6);
                if (!Number.isFinite(food) || !Number.isFinite(goods)) {
                    return null;
                }
                return goods + 4 * food;
            },

            formatNumber(value) {
                if (value === undefined || value === null) return "-";
                return new Intl.NumberFormat("ru-RU").format(Math.round(value));
            },

            formatScoreValue(value) {
                if (value === undefined || value === null) return "—";
                return new Intl.NumberFormat("ru-RU", {
                    minimumFractionDigits: 0,
                    maximumFractionDigits: 2,
                }).format(value);
            },

            formatChange(value) {
                if (!value) return "";
                const sign = value >= 0 ? "+" : "";
                return `${sign}${value.toFixed(1)}%`;
            },

            getChangeClass(value) {
                if (value > 0) return "text-green-600";
                if (value < 0) return "text-red-600";
                return "text-gray-500";
            },

            renderAllCharts() {
                this.renderScoreChart();
                this.renderPopulationCountChart();
                this.renderPerCapitaChart();
                this.renderDemographicsChart();
                this.renderEnergyTotalChart();
                this.renderEnergyProductionChart();
                this.renderEconomyChart();
                this.renderEnvironmentChart();
                this.renderDebtChart();
                this.renderImportChart();
                this.renderExportChart();
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

            formatChartValue(value) {
                return new Intl.NumberFormat("ru-RU", {
                    notation: "compact",
                    maximumFractionDigits: 1,
                }).format(value);
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

            pickDatasets(group, parameters) {
                const wanted = new Set(parameters);
                return (group || []).filter((item) => wanted.has(item.parameter));
            },

            getChartOptions({ yLabel = "Значение" } = {}) {
                const formatter = this.formatChartValue;
                return {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { intersect: false, mode: "index" },
                    plugins: {
                        legend: {
                            position: "bottom",
                            labels: { usePointStyle: true, padding: 10 },
                        },
                        tooltip: {
                            backgroundColor: "rgba(0, 0, 0, 0.8)",
                            padding: 10,
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
                            title: { display: true, text: "Период" },
                            ticks: { stepSize: 1 },
                        },
                        y: {
                            title: { display: true, text: yLabel },
                            ticks: {
                                callback: function (value) {
                                    return formatter(value);
                                },
                            },
                        },
                    },
                };
            },

            renderChart(key, canvasId, data, colors, options = {}) {
                const ctx = document.getElementById(canvasId);
                if (!ctx || !data?.length) return;
                this.destroyChart(key, ctx);

                this.charts[key] = new Chart(ctx, {
                    type: "line",
                    data: { datasets: this.createDatasets(data, colors) },
                    options: this.getChartOptions(options),
                });
            },

            renderScoreChart() {
                const indicator = this.scoreIndicator;
                const ctx = document.getElementById("chart-score");
                if (!ctx || !indicator?.series.length) return;
                this.destroyChart("score", ctx);

                this.charts.score = new Chart(ctx, {
                    type: "line",
                    data: {
                        datasets: [
                            {
                                data: indicator.series.map((point) => ({
                                    x: point.period,
                                    y: point.value,
                                })),
                                borderColor: indicator.color,
                                backgroundColor: indicator.color + "15",
                                borderWidth: 2,
                                tension: 0.3,
                                fill: true,
                                pointRadius:
                                    indicator.series.length <= 12 ? 3 : 2,
                                pointHoverRadius: 5,
                            },
                        ],
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        animation: false,
                        interaction: { intersect: false, mode: "index" },
                        plugins: {
                            legend: { display: false },
                            tooltip: {
                                callbacks: {
                                    label: (context) =>
                                        this.formatScoreValue(context.parsed.y),
                                },
                            },
                        },
                        scales: {
                            x: {
                                type: "linear",
                                min: 1,
                                max: this.totalPeriods,
                                ticks: { stepSize: 1, font: { size: 10 } },
                                grid: { color: "#f3f4f6" },
                            },
                            y: {
                                ticks: {
                                    maxTicksLimit: 4,
                                    font: { size: 10 },
                                    callback: (value) =>
                                        this.formatChartValue(value),
                                },
                                grid: { color: "#f3f4f6" },
                            },
                        },
                    },
                });
            },

            renderPopulationCountChart() {
                const ctx = document.getElementById("populationCountChart");
                if (!ctx || !this.chartsData?.population) return;
                this.renderChart(
                    "populationCount",
                    "populationCountChart",
                    this.pickDatasets(this.chartsData.population, ["P1"]),
                    ["#3b82f6", "#60a5fa", "#93c5fd"],
                    { yLabel: "Численность" },
                );
            },

            renderPerCapitaChart() {
                this.renderChart(
                    "perCapita",
                    "perCapitaChart",
                    this.pickDatasets(this.chartsData?.population, ["P4", "P6"]),
                    ["#0ea5e9", "#38bdf8"],
                    { yLabel: "На душу населения" },
                );
            },

            renderDemographicsChart() {
                this.renderChart(
                    "demographics",
                    "demographicsChart",
                    this.pickDatasets(this.chartsData?.population, ["P5", "P8"]),
                    ["#6366f1", "#818cf8"],
                    { yLabel: "Показатель" },
                );
            },

            renderEconomyChart() {
                this.renderChart(
                    "economy",
                    "economyChart",
                    this.chartsData?.economy,
                    ["#22c55e", "#4ade80", "#86efac"],
                    { yLabel: "Производство" },
                );
            },

            renderEnergyTotalChart() {
                this.renderChart(
                    "energyTotal",
                    "energyTotalChart",
                    this.pickDatasets(this.chartsData?.energy, ["E7"]),
                    ["#eab308"],
                    { yLabel: "Энергоресурсы" },
                );
            },

            renderEnergyProductionChart() {
                this.renderChart(
                    "energyProduction",
                    "energyProductionChart",
                    this.pickDatasets(this.chartsData?.energy, ["E17", "E15"]),
                    ["#f97316", "#fb923c"],
                    { yLabel: "Энергоресурсы" },
                );
            },

            renderDebtChart() {
                this.renderChart(
                    "debt",
                    "debtChart",
                    this.pickDatasets(this.chartsData?.finance, ["TF1"]),
                    ["#a855f7"],
                    { yLabel: "Внешний долг" },
                );
            },

            renderExportChart() {
                this.renderChart(
                    "export",
                    "exportChart",
                    this.pickDatasets(this.chartsData?.finance, [
                        "TF10",
                        "TF11",
                        "TF12",
                    ]),
                    ["#16a34a", "#22c55e", "#86efac"],
                    { yLabel: "Экспорт" },
                );
            },

            renderImportChart() {
                this.renderChart(
                    "import",
                    "importChart",
                    this.pickDatasets(this.chartsData?.finance, [
                        "TF16",
                        "TF17",
                        "TF18",
                    ]),
                    ["#c026d3", "#e879f9", "#f5d0fe"],
                    { yLabel: "Импорт" },
                );
            },

            renderEnvironmentChart() {
                this.renderChart(
                    "environment",
                    "environmentChart",
                    this.pickDatasets(this.chartsData?.environment, ["F7"]),
                    ["#14b8a6"],
                    { yLabel: "Состояние" },
                );
            },

            exportResults() {
                // Create CSV content
                let csv =
                    "Период,Население,Прод./чел,Товары/чел,Энергия,Экология,Долг,Смертность,Рождаемость\n";

                for (const p of this.periodsData) {
                    csv += `${p.period},${p.P1},${p.P4?.toFixed(2)},${p.P6?.toFixed(2)},${p.E17},${(p.F7 * 100).toFixed(0)}%,${p.TF1},${p.P5?.toFixed(1)},${p.P8?.toFixed(1)}\n`;
                }

                // Download
                const blob = new Blob([csv], {
                    type: "text/csv;charset=utf-8;",
                });
                const link = document.createElement("a");
                link.href = URL.createObjectURL(blob);
                link.download = `strategem_results_${this.teamName.replace(/\s+/g, "_")}.csv`;
                link.click();

                showToast("Результаты экспортированы", "success");
            },
        };
    }
