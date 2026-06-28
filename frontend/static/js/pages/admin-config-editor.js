function configEditor(filename) {
    return {
        filename,
        title: "",
        content: "",
        builtinContent: "",
        isModified: false,
        loading: true,
        saving: false,
        validating: false,
        resetting: false,
        validation: null,
        showHelp: false,
        showResetModal: false,
        resetCountdown: 0,
        resetTimer: null,

        get lineCount() {
            return Math.max(1, this.content.split("\n").length);
        },

        get lineNumbers() {
            return Array.from({ length: this.lineCount }, (_, index) => index + 1);
        },

        get errorLines() {
            const lines = new Set();
            for (const item of this.visibleValidationItems) {
                if (item.line) lines.add(item.line);
            }
            return lines;
        },

        get visibleValidationItems() {
            if (!this.validation) return [];
            const all = [
                ...(this.validation.errors || []),
                ...(this.validation.warnings || []),
            ];
            return all.filter((item) => item.filename === this.filename || !item.filename);
        },

        async initialize() {
            await this.checkAdmin();
            await this.loadConfig();
        },

        async checkAdmin() {
            const response = await API.get("/admin/check/");
            if (!response.is_admin) {
                window.location.href = "/admin-login/";
            }
        },

        async loadConfig() {
            this.loading = true;
            try {
                const data = await API.get(`/admin/config-files/${encodeURIComponent(this.filename)}/`);
                this.title = data.title;
                this.content = data.content || "";
                this.builtinContent = data.builtin_content || "";
                this.isModified = Boolean(data.is_modified);
                this.validation = null;
                this.$nextTick(() => this.syncScroll());
            } catch (e) {
                showToast("Ошибка загрузки файла: " + e.message, "error");
            } finally {
                this.loading = false;
                this.$nextTick(() => this.syncScroll());
            }
        },

        async validateConfig() {
            this.validating = true;
            try {
                this.validation = await API.post(
                    `/admin/config-files/${encodeURIComponent(this.filename)}/validate/`,
                    { content: this.content },
                );
                if (this.validation.valid) {
                    showToast("Конфигурация корректна", "success");
                } else {
                    showToast("Найдены ошибки в конфигурации", "error");
                }
            } catch (e) {
                showToast("Ошибка проверки: " + e.message, "error");
            } finally {
                this.validating = false;
            }
        },

        async saveConfig() {
            this.saving = true;
            try {
                const data = await API.patch(
                    `/admin/config-files/${encodeURIComponent(this.filename)}/`,
                    { content: this.content },
                );
                this.isModified = Boolean(data.is_modified);
                this.validation = data.validation || null;
                showToast("Конфигурационный файл сохранён", "success");
                window.location.href = "/admin-panel/#admin-settings";
            } catch (e) {
                const payload = e.apiErrorPayload;
                if (payload && (payload.errors || payload.warnings)) {
                    this.validation = payload;
                }
                showToast("Файл не сохранён: " + e.message, "error");
            } finally {
                this.saving = false;
            }
        },

        openResetModal() {
            this.showResetModal = true;
            this.resetCountdown = 3;
            window.clearInterval(this.resetTimer);
            this.resetTimer = window.setInterval(() => {
                this.resetCountdown -= 1;
                if (this.resetCountdown <= 0) {
                    window.clearInterval(this.resetTimer);
                    this.resetTimer = null;
                }
            }, 1000);
        },

        closeResetModal() {
            this.showResetModal = false;
            window.clearInterval(this.resetTimer);
            this.resetTimer = null;
            this.resetCountdown = 0;
        },

        async resetConfig() {
            if (this.resetCountdown > 0) return;
            this.resetting = true;
            try {
                const data = await API.post(
                    `/admin/config-files/${encodeURIComponent(this.filename)}/reset/`,
                    {},
                );
                this.content = data.content || "";
                this.builtinContent = data.builtin_content || "";
                this.isModified = Boolean(data.is_modified);
                this.validation = null;
                this.$nextTick(() => this.syncScroll());
                this.closeResetModal();
                showToast("Файл сброшен до исходной версии", "success");
            } catch (e) {
                showToast("Ошибка сброса: " + e.message, "error");
            } finally {
                this.resetting = false;
            }
        },

        syncScroll() {
            const editor = this.$refs.editor;
            const lineGutter = this.$refs.lineGutter;
            if (!editor || !lineGutter) return;
            lineGutter.scrollTop = editor.scrollTop;
        },

        goToLine(line) {
            if (!line) return;
            const textarea = this.$refs.editor;
            if (!textarea) return;
            const lines = this.content.split("\n");
            const position = lines.slice(0, Math.max(0, line - 1)).join("\n").length + (line > 1 ? 1 : 0);
            textarea.focus();
            textarea.setSelectionRange(position, position);
            textarea.scrollTop = Math.max(0, (line - 4) * 24);
            this.syncScroll();
        },
    };
}
