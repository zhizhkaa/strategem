function gameApp() {
    return {
        gameId: null,
        teamName: '',
        gameState: null,
        pastPeriods: [],
        loading: true,
        error: null,
        isViewOnly: false,
        isGamePaused: false,
        inputValues: {},
        touchedParams: {},
        processingAction: false,
        validationErrors: [],
        validationErrorSet: {},
        decisionStates: null,
        incompleteByMinister: {},
        incompleteParamSet: {},
        DECISION_REQUIRED: { capital: 4, energy: 1, finance: 3, import: 3 },
        DECISION_LABELS: { capital: 'Капиталовложения', energy: 'Энергетика', finance: 'Торговля и финансы', import: 'Импорт' },

        // Заполняется из API /games/decision-structure/
        SUMMARY_GROUPS: [],
        PARAM_VERBOSE: {},
        START_VALUES: {},
        MINISTER_SHORTS: {},
        allInputParams: new Set(),

        get currentPeriod() { return this.gameState?.game_info?.current_period || 1; },
        get totalPeriods()  { return this.gameState?.game_info?.total_periods || 10; },

        get allPeriodCols() {
            const cols = [];
            for (const p of this.pastPeriods)
                cols.push({ period:p.period_number, label:'П'+p.period_number, isCurrent:false, isPast:true });
            cols.push({ period:this.currentPeriod, label:'П'+this.currentPeriod, isCurrent:true, isPast:false });
            for (let fp = this.currentPeriod+1; fp <= this.totalPeriods; fp++)
                cols.push({ period:fp, label:'П'+fp, isCurrent:false, isPast:false });
            return cols;
        },

        async init() {
            this.gameId   = localStorage.getItem('strategem_game');
            this.teamName = localStorage.getItem('strategem_team_name') || 'Команда';
            this.isViewOnly = localStorage.getItem('strategem_view_only') === 'true';

            if (!this.gameId) {
                this.error = 'Игра не выбрана. Вернитесь к выбору команды.';
                this.loading = false;
                return;
            }
            try {
                await this.loadStructure();
                await this.loadState();
                await this.loadPeriods();
            } catch(e) {
                this.error = 'Ошибка загрузки: ' + e.message;
            } finally {
                this.loading = false;
            }
        },

        async loadStructure() {
            const data = await API.get('/games/decision-structure/');
            this.SUMMARY_GROUPS = data.summary_groups;
            this.PARAM_VERBOSE = Object.fromEntries(
                Object.entries(data.parameters).map(([k, v]) => [k, v.verbose_name])
            );
            this.START_VALUES = Object.fromEntries(
                Object.entries(data.parameters).map(([k, v]) => [k, v.default])
            );
            this.MINISTER_SHORTS = Object.fromEntries(
                Object.entries(data.ministers).map(([k, v]) => [k, v.short_name])
            );
            this.allInputParams = new Set(this.SUMMARY_GROUPS.flatMap(g => g.inputs));
        },

        async loadState() {
            this.gameState = await API.get(`/games/${this.gameId}/state/`);
            this.isGamePaused = this.gameState?.game_info?.status === 'paused';
            if (this.gameState?.game_info?.status === 'finished')
                window.location.href = '/game-results/';
            this.applyValidationState(this.gameState?.validation_state);
            this.initInputs();
        },

        async loadPeriods() {
            try {
                const data = await API.get(`/games/${this.gameId}/periods/`);
                const periods = data.results || data;
                this.pastPeriods = periods.filter(p => p.period_number < this.currentPeriod);
            } catch(_) { this.pastPeriods = []; }
        },

        initInputs() {
            if (!this.gameState?.parameters) return;
            const vals = {};
            this.touchedParams = {};
            for (const param of this.allInputParams) {
                const p = this.gameState.parameters[param];
                if (!p) continue;
                const b = p.bounds;
                if (b?.min != null && b?.max != null && b.min === b.max) { vals[param] = b.min; this.touchedParams[param] = true; }
                else if (p.status === 'filled') { vals[param] = p.value ?? ''; this.touchedParams[param] = true; }
                else { vals[param] = p.value ?? ''; }
            }
            this.inputValues = vals;
        },

        setErrors(errors) {
            this.validationErrors = errors;
            const s = {};
            for (const p of errors) s[p] = true;
            this.validationErrorSet = s;
        },

        applyValidationState(vs) {
            if (!vs) return;
            this.setErrors(vs.errors || []);
            const byMinister = vs.by_minister || {};
            const incomplete = {};
            for (const [m, data] of Object.entries(byMinister)) {
                if (data.incomplete?.length) incomplete[m] = data.incomplete;
            }
            this.incompleteByMinister = incomplete;
            const flat = {};
            for (const params of Object.values(incomplete)) {
                for (const p of params) flat[p] = true;
            }
            this.incompleteParamSet = flat;
        },

        getVal(param)              { return this.gameState?.parameters?.[param]?.value; },
        getPastVal(param, period)  { const p = this.pastPeriods.find(x => x.period_number === period); return p?.[param] ?? null; },
        isSummaryInputEnabled(param) { return this.allInputParams.has(param); },
        isError(param)             { return this.validationErrors.indexOf(param) !== -1; },
        isIncomplete(param)        { return !!this.incompleteParamSet[param]; },
        getMinisterShort(key)      { return this.MINISTER_SHORTS[key] || key; },

        onCellChange(param) {
            this.touchedParams[param] = true;
            this.recalcAutoParams();
            const idx = this.validationErrors.indexOf(param);
            if (idx > -1) this.validationErrors.splice(idx, 1);
        },

        recalcAutoParams() {
            if (!this.SUMMARY_GROUPS) return;
            for (const group of this.SUMMARY_GROUPS) {
                for (const param of (group.auto || [])) {
                    const config = this.gameState?.parameters?.[param];
                    if (!config) continue;
                    const bounds = config.bounds;
                    if (bounds && bounds.min !== null && bounds.max !== null
                        && bounds.min === bounds.max) {
                        this.inputValues[param] = bounds.min;
                    }
                }
            }
        },

        async submitPeriod() {
            if (this.isViewOnly || this.isGamePaused || this.processingAction) return;
            this.processingAction = true;
            this.validationErrors = [];

            try {
                const parameters = {};
                for (const param of this.allInputParams) {
                    const value = this.inputValues[param];
                    if (this.touchedParams[param] && value !== null && value !== undefined && value !== '') {
                        parameters[param] = Number(value);
                    }
                }

                // Шаг 1: Batch-submit всех параметров одним запросом
                const batchResponse = await API.post(
                    `/games/${this.gameId}/parameters/batch/`,
                    { parameters }
                );

                if (!batchResponse.success) {
                    this.validationErrors = Object.keys(batchResponse.errors || {});
                    this.validationErrorSet = batchResponse.errors || {};
                    const formatted = formatErrorPayload(
                        { errors: batchResponse.errors || {} },
                        `Ошибки в ${this.validationErrors.length} параметрах`,
                    );
                    showToast({
                        message: formatted.message,
                        type: 'error',
                        details: formatted.details,
                        detailsTitle: 'Ошибки в решениях',
                    });
                    console.debug('Batch validation errors:', batchResponse.errors);
                    this.processingAction = false;
                    return;
                }

                // Перезагружаем состояние после успешного batch-submit
                await this.loadState();

                // Шаг 2: Валидируем период
                const validation = await API.post(`/games/${this.gameId}/validate-period/`);

                if (validation.validation_state) {
                    this.applyValidationState(validation.validation_state);
                }

                if (!validation.valid) {
                    showToast(`Ошибки в ${this.validationErrors.length} параметрах`, 'error');
                    this.processingAction = false;
                    return;
                }

                if (!validation.can_advance) {
                    showToast('Заполните все обязательные решения перед завершением периода', 'warning');
                    this.processingAction = false;
                    return;
                }

                // Шаг 3: Переход к следующему периоду
                const result = await API.post(`/games/${this.gameId}/next-period/`);

                if (result.success) {
                    this.setErrors([]);
                    this.incompleteByMinister = {};
                    this.incompleteParamSet = {};
                    if (result.game_finished) {
                        showToast('Игра завершена!', 'success');
                        window.location.href = '/game-results/';
                    } else {
                        showToast(`Период ${result.current_period} начался`, 'success');
                        await this.loadState();
                        await this.loadPeriods();
                    }
                } else {
                    showToast(result.error || 'Ошибка', 'error');
                }
            } catch (e) {
                showToast(e || 'Ошибка', 'error');
            } finally {
                this.processingAction = false;
            }
        },

        formatNum(num) {
            if (num === null || num === undefined || num === '') return '—';
            return new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 2 }).format(num);
        },
    };
}
