// ============================================================
// Alpine.js компонент
// ============================================================
function ministerApp(ministerKey) {
    return {
        ministerKey,
        gameId: null,
        teamName: '',
        gameState: null,
        pastPeriods: [],
        loading: true,
        error: null,
        isViewOnly: false,
        isGamePaused: false,

        // Заполняется из API /games/decision-structure/
        MINISTER_TABS: [],
        PARAM_VERBOSE: {},
        START_VALUES: {},
        TARGET_VALUES: {},
        ministerConfig: { name: ministerKey, info_first: [], situation: [], info: [], decisions: [] },

        inputValues: {},
        touchedParams: {},    // param → true (параметр был изменён пользователем)
        paramErrors: {},      // param → true (красный: ошибка в расчётах)
        paramIncomplete: {},  // param → true (жёлтый: не заполнено)
        submitting: false,
        submitResult: null,

        // Серверное состояние валидации — синхронизируется между экранами
        validationState: { errors: [], incomplete: [], by_minister: {}, last_validated: null },

        interpolationTables: null,

        chartModal: { open: false, param: '', title: '', loading: false },
        _chartInstance: null,

        // ---- Computed ----
        get currentPeriod() {
            return this.gameState?.game_info?.current_period || 1;
        },
        get totalPeriods() {
            return this.gameState?.game_info?.total_periods || 10;
        },
        get futurePeriodNums() {
            const result = [];
            for (let p = this.currentPeriod + 1; p <= this.totalPeriods; p++) result.push(p);
            return result;
        },
        get allPeriodCols() {
            const cols = [];
            for (const p of this.pastPeriods) {
                cols.push({ period: p.period_number, label: this.getPeriodRange(p.period_number), isCurrent: false, isPast: true });
            }
            cols.push({ period: this.currentPeriod, label: this.getPeriodRange(this.currentPeriod), isCurrent: true, isPast: false });
            for (const fp of this.futurePeriodNums) {
                cols.push({ period: fp, label: this.getPeriodRange(fp), isCurrent: false, isPast: false });
            }
            return cols;
        },
        // Total columns: Название + Старт + Периоды
        get colCount() {
            return 2 + this.allPeriodCols.length;
        },
        get ministerStages() {
            if (!this.gameState) return [];
            return (this.gameState.available_stages || []).filter(s => s.minister === this.ministerKey);
        },
        get allInputParams() {
            return this.ministerConfig.decisions.flatMap(d => d.inputs);
        },
        get inputCount() {
            return this.allInputParams.length;
        },
        get filledCount() {
            return this.allInputParams.filter(p => this.getParamStatus(p) === 'filled').length;
        },
        get allFilled() {
            return this.inputCount > 0 && this.filledCount === this.inputCount;
        },
        get myErrorCount() {
            return Object.keys(this.paramErrors).length;
        },
        get myIncompleteCount() {
            return Object.keys(this.paramIncomplete).length;
        },

        // ---- Init ----
        async init() {
            this.gameId = localStorage.getItem('strategem_game');
            this.teamName = localStorage.getItem('strategem_team_name') || 'Команда';
            this.isViewOnly = localStorage.getItem('strategem_view_only') === 'true';

            if (!this.gameId) {
                this.error = 'Игра не выбрана. Вернитесь к выбору команды.';
                this.loading = false;
                return;
            }

            try {
                await this.loadStructure();
                await this.loadGameState();
                await Promise.all([this.loadPeriods(), this.loadInterpolation()]);
            } catch (e) {
                this.error = 'Ошибка загрузки: ' + e.message;
            } finally {
                this.loading = false;
            }
        },

        async loadStructure() {
            const data = await API.get('/games/decision-structure/');
            this.PARAM_VERBOSE = Object.fromEntries(
                Object.entries(data.parameters).map(([k, v]) => [k, v.verbose_name])
            );
            this.START_VALUES = Object.fromEntries(
                Object.entries(data.parameters).map(([k, v]) => [k, v.default])
            );
            this.TARGET_VALUES = Object.fromEntries(
                Object.entries(data.parameters)
                    .filter(([, v]) => v.target_value != null)
                    .map(([k, v]) => [k, v.target_value])
            );
            const ministers = data.ministers;
            this.ministerConfig = ministers[this.ministerKey] || this.ministerConfig;
            this.MINISTER_TABS = Object.entries(ministers).map(([key, m]) => ({
                key, short: m.short_name
            }));
        },

        async loadGameState() {
            this.gameState = await API.get(`/games/${this.gameId}/state/`);
            this.isGamePaused = this.gameState?.game_info?.status === 'paused';
            this.applyValidationState(this.gameState?.validation_state);
            this.initInputValues();
        },

        async loadPeriods() {
            try {
                const data = await API.get(`/games/${this.gameId}/periods/`);
                const periods = data.results || data;
                this.pastPeriods = periods.filter(p => p.period_number < this.currentPeriod);
            } catch (_) {
                this.pastPeriods = [];
            }
        },

        async loadInterpolation() {
            try {
                const allTables = await API.get(`/games/interpolation-tables/`);
                const keys = this.ministerConfig.interpolation_keys || [];
                const filtered = {};
                for (const k of keys) {
                    if (allTables[k]) filtered[k] = allTables[k];
                }
                this.interpolationTables = filtered;
            } catch (_) {}
        },

        initInputValues() {
            if (!this.gameState?.parameters) return;
            const inputParams = new Set(this.ministerConfig.decisions.flatMap(d => d.inputs));
            const newValues = {};
            const newTouched = {};
            for (const [name, param] of Object.entries(this.gameState.parameters)) {
                const bounds = param.bounds;
                const isFixed = bounds != null && bounds.min != null && bounds.max != null && bounds.min === bounds.max;
                if (isFixed) {
                    // Fixed params always show their computed value
                    newValues[name] = bounds.min;
                } else if (!inputParams.has(name)) {
                    // Non-input (calculated) params: show current value for read-only display
                    newValues[name] = param.value ?? null;
                } else if (param.status === 'filled') {
                    // Input param that user already explicitly set: pre-fill
                    newValues[name] = param.value ?? '';
                } else {
                    // Input param not yet filled: leave blank
                    newValues[name] = '';
                }
            }
            this.inputValues = newValues;
            this.touchedParams = newTouched;
        },

        // ---- Validation state ----
        applyValidationState(vs) {
            if (!vs) return;
            this.validationState = vs;
            const myVs = vs.by_minister?.[this.ministerKey] || { errors: [], incomplete: [] };
            const newErrors = {};
            const newIncomplete = {};
            for (const p of (myVs.errors || [])) newErrors[p] = true;
            for (const p of (myVs.incomplete || [])) newIncomplete[p] = true;
            this.paramErrors = newErrors;
            this.paramIncomplete = newIncomplete;
        },

        // ---- Cell change: только локальное обновление (без обращения к серверу) ----
        onCellChange(param) {
            // Помечаем параметр как изменённый пользователем
            this.touchedParams[param] = true;
            // Только локальное обновление — сервер не трогаем
            this.recalcAutoParams();
            // Убираем ошибку этого параметра если она была
            delete this.paramErrors[param];
        },

        // ---- Локальный пересчёт авторасчётных параметров ----
        recalcAutoParams() {
            if (!this.ministerConfig?.decisions) return;
            for (const decision of this.ministerConfig.decisions) {
                if (!decision.total) continue;
                for (const autoParam of (decision.auto || [])) {
                    const config = this.gameState?.parameters?.[autoParam];
                    if (!config) continue;
                    const bounds = config.bounds;
                    if (bounds && bounds.min !== null && bounds.max !== null
                        && bounds.min === bounds.max) {
                        this.inputValues[autoParam] = bounds.min;
                    }
                }
            }
        },

        // ---- Submit: batch-отправка всех решений одним запросом ----
        async submitAll() {
            if (this.submitting) return;
            this.submitting = true;
            this.submitResult = null;
            this.paramErrors = {};

            try {
                const parameters = {};
                for (const decision of (this.ministerConfig?.decisions || [])) {
                    for (const param of decision.inputs) {
                        const value = this.inputValues[param];
                        if (this.touchedParams[param] && value !== null && value !== undefined && value !== '') {
                            parameters[param] = Number(value);
                        }
                    }
                }

                if (Object.keys(parameters).length === 0) {
                    showToast('Заполните хотя бы одно решение', 'warning');
                    return;
                }

                const response = await API.post(
                    `/games/${this.gameId}/parameters/batch/`,
                    { parameters, minister: this.ministerKey }
                );

                if (!response.success) {
                    this.paramErrors = {};
                    for (const [param, msg] of Object.entries(response.errors)) {
                        this.paramErrors[param] = msg;
                    }
                    showToast(`Ошибки в ${Object.keys(response.errors).length} параметрах`, 'error');
                    console.debug('Batch validation errors:', response.errors);
                    const firstError = Object.keys(response.errors)[0];
                    const el = document.querySelector(`[data-param="${firstError}"]`);
                    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    return;
                }

                // Перезагружаем полное состояние с сервера чтобы обновить все auto-calculated
                await this.loadGameState();
                await this.loadPeriods();

                showToast('Значения министра сохранены', 'success');
                this.submitResult = { success: true };
            } catch (e) {
                showToast(e.message || 'Ошибка при отправке', 'error');
            } finally {
                this.submitting = false;
            }
        },


        // ---- Parameter chart ----
        async openParamChart(param) {
            this.chartModal.param = param;
            this.chartModal.title = this.getParamVerbose(param);
            this.chartModal.loading = true;
            this.chartModal.open = true;

            try {
                const data = await API.get(`/games/${this.gameId}/parameter-history/${param}/`);
                await this.$nextTick();
                this._renderParamChart(data);
            } catch (_) {}
            this.chartModal.loading = false;
        },

        _renderParamChart(data) {
            const canvas = this.$refs.chartCanvas;
            if (!canvas) return;
            if (this._chartInstance) {
                this._chartInstance.destroy();
                this._chartInstance = null;
            }
            const labels = data.data.map(d => 'П' + d.period);
            const values = data.data.map(d => d.value);
            this._chartInstance = new Chart(canvas, {
                type: 'line',
                data: {
                    labels,
                    datasets: [{
                        label: data.verbose_name,
                        data: values,
                        borderColor: '#0284c7',
                        backgroundColor: 'rgba(2,132,199,0.08)',
                        borderWidth: 2,
                        pointRadius: 4,
                        tension: 0.3,
                        fill: true,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { beginAtZero: false },
                    },
                },
            });
        },

        // ---- Helpers ----
        hasChecks(decision) {
            if (decision.total) return true;
            return (decision.inputs_detail || []).some(inp => inp.note);
        },
        getParamVerbose(param) {
            return this.PARAM_VERBOSE[param] || this.gameState?.parameters?.[param]?.verbose_name || param;
        },
        getParamName(param) {
            return this.gameState?.parameters?.[param]?.verbose_name || param;
        },
        getParamStatus(param) {
            return this.gameState?.parameters?.[param]?.status || 'locked';
        },
        getParamValue(param) {
            return this.gameState?.parameters?.[param]?.value ?? null;
        },
        getStartValue(param) {
            return this.START_VALUES[param] ?? null;
        },
        getTargetValue(param) {
            return this.TARGET_VALUES[param] ?? null;
        },
        getPastValue(param, periodNum) {
            const p = this.pastPeriods.find(p => p.period_number === periodNum);
            return p?.[param] ?? null;
        },
        isFixed(param) {
            const bounds = this.gameState?.parameters?.[param]?.bounds;
            return bounds != null && bounds.min != null && bounds.max != null && bounds.min === bounds.max;
        },
        isStageAvailable(stageKey) {
            const stage = this.ministerStages.find(s => s.key === stageKey);
            return stage ? stage.available : false;
        },
        isStageCompleted(stageKey) {
            const stage = this.ministerStages.find(s => s.key === stageKey);
            return stage ? stage.completed : false;
        },
        isInputEnabled(param) {
            if (this.isViewOnly || this.isGamePaused) return false;
            if (this.isFixed(param)) return false;
            if (this.getParamStatus(param) === 'filled') return true;
            const decision = this.ministerConfig.decisions.find(d => d.inputs.includes(param));
            if (!decision) return false;
            return this.isStageAvailable(decision.key);
        },
        getPeriodRange(n) {
            const start = (n - 1) * 5;
            return `${start}-${start + 4}`;
        },
        formatNumber(num) {
            if (num === null || num === undefined) return '—';
            return new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 2 }).format(num);
        },

        renderOneChart(canvas, data) {
            new Chart(canvas, {
                type: 'line',
                data: {
                    datasets: [{
                        data: data.x.map((x, i) => ({ x, y: data.y[i] })),
                        borderColor: '#0ea5e9',
                        backgroundColor: '#0ea5e920',
                        tension: 0.3,
                        fill: true,
                        pointRadius: 3,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { type: 'linear', title: { display: true, text: 'x' } },
                        y: { title: { display: true, text: 'y' } },
                    },
                },
            });
        },
    };
}
