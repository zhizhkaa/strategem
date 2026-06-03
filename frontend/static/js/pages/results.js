function gameResults() {
        return {
            // State
            gameId: null,
            teamName: "",
            loading: true,
            error: null,
            totalPeriods: 10,

            // Data
            finalState: {},
            initialState: {},
            periodsData: [],
            chartsData: null,

            // Computed
            get energyBalance() {
                return (this.finalState.E17 || 0) - (this.finalState.E15 || 0);
            },

            get changes() {
                return {
                    population: this.calculateChange("P1"),
                    environment: this.calculateChange("F7"),
                    debt: this.calculateChange("TF1"),
                };
            },

            get overallStatus() {
                const p4 = this.finalState.P4 || 0;
                const p6 = this.finalState.P6 || 0;
                const f7 = this.finalState.F7 || 0;
                const energy = this.energyBalance;

                let score = 0;
                if (p4 >= 2) score++;
                if (p6 >= 2) score++;
                if (f7 >= 0.6) score++;
                if (energy >= 0) score++;
                if (this.finalState.TF1 <= 1000) score++;
                if (this.finalState.P1 >= this.initialState.P1) score++;

                if (score >= 5)
                    return {
                        label: "🏆 Процветание",
                        class: "bg-green-100 text-green-800",
                    };
                if (score >= 3)
                    return {
                        label: "📊 Стабильность",
                        class: "bg-yellow-100 text-yellow-800",
                    };
                if (score >= 1)
                    return {
                        label: "⚠️ Кризис",
                        class: "bg-orange-100 text-orange-800",
                    };
                return {
                    label: "💀 Катастрофа",
                    class: "bg-red-100 text-red-800",
                };
            },

            get assessments() {
                const p1Change = this.changes.population;
                const p4 = this.finalState.P4 || 0;
                const p6 = this.finalState.P6 || 0;
                const energy = this.energyBalance;
                const f7 = this.finalState.F7 || 0;
                const debt = this.finalState.TF1 || 0;

                return {
                    population:
                        p1Change >= 0
                            ? {
                                  class: "bg-green-50 border-green-200",
                                  text: `Население выросло на ${p1Change.toFixed(0)}%`,
                              }
                            : {
                                  class: "bg-red-50 border-red-200",
                                  text: `Население сократилось на ${Math.abs(p1Change).toFixed(0)}%`,
                              },
                    food:
                        p4 >= 2.5
                            ? {
                                  class: "bg-green-50 border-green-200",
                                  text: "Изобилие продовольствия",
                              }
                            : p4 >= 2.0
                              ? {
                                    class: "bg-green-50 border-green-200",
                                    text: "Достаточное обеспечение продовольствием",
                                }
                              : p4 >= 1.5
                                ? {
                                      class: "bg-yellow-50 border-yellow-200",
                                      text: "Продовольственный дефицит",
                                  }
                                : {
                                      class: "bg-red-50 border-red-200",
                                      text: "Голод в стране",
                                  },
                    goods:
                        p6 >= 2.0
                            ? {
                                  class: "bg-green-50 border-green-200",
                                  text: "Достаточное обеспечение товарами",
                              }
                            : p6 >= 1.0
                              ? {
                                    class: "bg-yellow-50 border-yellow-200",
                                    text: "Дефицит товаров",
                                }
                              : {
                                    class: "bg-red-50 border-red-200",
                                    text: "Острая нехватка товаров",
                                },
                    energy:
                        energy >= 500
                            ? {
                                  class: "bg-green-50 border-green-200",
                                  text: "Энергетическая безопасность обеспечена",
                              }
                            : energy >= 0
                              ? {
                                    class: "bg-green-50 border-green-200",
                                    text: "Энергобаланс положительный",
                                }
                              : {
                                    class: "bg-red-50 border-red-200",
                                    text: "Дефицит энергии",
                                },
                    environment:
                        f7 >= 0.8
                            ? {
                                  class: "bg-green-50 border-green-200",
                                  text: "Отличное состояние экологии",
                              }
                            : f7 >= 0.6
                              ? {
                                    class: "bg-green-50 border-green-200",
                                    text: "Экология в норме",
                                }
                              : f7 >= 0.4
                                ? {
                                      class: "bg-yellow-50 border-yellow-200",
                                      text: "Экология ухудшается",
                                  }
                                : {
                                      class: "bg-red-50 border-red-200",
                                      text: "Экологическая катастрофа",
                                  },
                    finance:
                        debt <= 500
                            ? {
                                  class: "bg-green-50 border-green-200",
                                  text: "Минимальный внешний долг",
                              }
                            : debt <= 1500
                              ? {
                                    class: "bg-green-50 border-green-200",
                                    text: "Долг под контролем",
                                }
                              : debt <= 3000
                                ? {
                                      class: "bg-yellow-50 border-yellow-200",
                                      text: "Значительный внешний долг",
                                  }
                                : {
                                      class: "bg-red-50 border-red-200",
                                      text: "Критический уровень долга",
                                  },
                };
            },

            // Charts
            charts: {},

            // Methods
            async init() {
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

            formatNumber(value) {
                if (value === undefined || value === null) return "-";
                return new Intl.NumberFormat("ru-RU").format(Math.round(value));
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
                this.renderPopulationChart();
                this.renderEconomyChart();
                this.renderEnergyChart();
                this.renderFinanceChart();
                this.renderEnvironmentChart();
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

            getChartOptions(title) {
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
                                    let value = context.parsed.y;
                                    if (value !== null) {
                                        value = new Intl.NumberFormat(
                                            "ru-RU",
                                        ).format(value);
                                    }
                                    return `${context.dataset.label}: ${value}`;
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
                            title: { display: true, text: "Значение" },
                            ticks: {
                                callback: function (value) {
                                    return new Intl.NumberFormat("ru-RU", {
                                        notation: "compact",
                                        maximumFractionDigits: 1,
                                    }).format(value);
                                },
                            },
                        },
                    },
                };
            },

            renderPopulationChart() {
                const ctx = document.getElementById("populationChart");
                if (!ctx || !this.chartsData?.population) return;

                const datasets = this.createDatasets(
                    this.chartsData.population,
                    ["#3b82f6", "#60a5fa", "#93c5fd"],
                );

                this.charts.population = new Chart(ctx, {
                    type: "line",
                    data: { datasets },
                    options: this.getChartOptions(),
                });
            },

            renderEconomyChart() {
                const ctx = document.getElementById("economyChart");
                if (!ctx || !this.chartsData?.economy) return;

                const datasets = this.createDatasets(this.chartsData.economy, [
                    "#22c55e",
                    "#4ade80",
                    "#86efac",
                ]);

                this.charts.economy = new Chart(ctx, {
                    type: "line",
                    data: { datasets },
                    options: this.getChartOptions(),
                });
            },

            renderEnergyChart() {
                const ctx = document.getElementById("energyChart");
                if (!ctx || !this.chartsData?.energy) return;

                const datasets = this.createDatasets(this.chartsData.energy, [
                    "#eab308",
                    "#facc15",
                    "#fde047",
                ]);

                this.charts.energy = new Chart(ctx, {
                    type: "line",
                    data: { datasets },
                    options: this.getChartOptions(),
                });
            },

            renderFinanceChart() {
                const ctx = document.getElementById("financeChart");
                if (!ctx || !this.chartsData?.finance) return;

                const datasets = this.createDatasets(this.chartsData.finance, [
                    "#a855f7",
                    "#c084fc",
                    "#d8b4fe",
                    "#7c3aed",
                    "#8b5cf6",
                ]);

                this.charts.finance = new Chart(ctx, {
                    type: "line",
                    data: { datasets },
                    options: this.getChartOptions(),
                });
            },

            renderEnvironmentChart() {
                const ctx = document.getElementById("environmentChart");
                if (!ctx || !this.chartsData?.environment) return;

                const datasets = this.createDatasets(
                    this.chartsData.environment,
                    ["#14b8a6", "#2dd4bf"],
                );

                this.charts.environment = new Chart(ctx, {
                    type: "line",
                    data: { datasets },
                    options: this.getChartOptions(),
                });
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
