function adminPanel() {
        return {
            // State
            loading: true,
            isAdmin: false,
            games: [],
            teams: [],
            faculties: [],
            groups: [],
            documents: [],
            savingTeamPasswords: {},
            showArchivedGames: false,

            // Modal state
            showCreateModal: false,
            showDeleteModal: false,
            showCreateFacultyModal: false,
            showCreateGroupModal: false,
            showCreateTeamModal: false,
            showCreateTeamPassword: false,
            showTeamPasswordModal: false,
            showOperatorModal: false,
            showUploadDocModal: false,

            // Operator parameter state
            operatorGame: null,
            operatorValue: 0,
            operatorLoading: false,
            operatorSaving: false,
            operatorError: null,

            // Form state
            newGame: {
                team: "",
                difficulty: "standard",
                total_periods: 10,
            },
            creatingGame: false,
            createError: null,

            // Faculty form state
            newFaculty: { name: "" },
            creatingFaculty: false,
            createFacultyError: null,

            // Group form state
            newGroup: { name: "", faculty: "", year: new Date().getFullYear() },
            creatingGroup: false,
            createGroupError: null,

            // Team form state
            newTeam: { name: "", group: "", access_password: "", password_enabled: true },
            creatingTeam: false,
            createTeamError: null,
            teamPasswordModalTeam: null,
            teamPasswordModalValue: "",
            teamPasswordModalEnabled: true,
            savingTeamPasswordModal: false,
            teamPasswordModalError: null,

            // Document form state
            newDoc: { title: "", scope: "general", minister: "", slot: "" },
            docFile: null,
            uploadingDoc: false,
            uploadDocError: null,

            // Delete state (игры)
            gameToDelete: null,
            deletingGame: false,

            // Delete state (факультеты / группы / команды)
            entityToDelete: null,
            showEntityDeleteModal: false,
            deletingEntity: false,

            // Поиск и фильтрация дерева
            treeSearch: '',
            treeFacultyFilter: '',
            expandedFaculties: {},
            expandedGroups: {},

            facultiesFiltered() {
                return this.faculties.filter(f => {
                    if (this.treeFacultyFilter && f.id !== parseInt(this.treeFacultyFilter)) return false;
                    if (!this.treeSearch.trim()) return true;
                    const q = this.treeSearch.trim().toLowerCase();
                    if (f.name.toLowerCase().includes(q)) return true;
                    return this.groupsFiltered(f.id).length > 0;
                });
            },
            groupsFiltered(facultyId) {
                const q = this.treeSearch.trim().toLowerCase();
                return this.groups.filter(g => {
                    if (g.faculty !== facultyId) return false;
                    if (!q) return true;
                    if (g.name.toLowerCase().includes(q)) return true;
                    return this.teamsFiltered(g.id).length > 0;
                });
            },
            teamsFiltered(groupId) {
                const q = this.treeSearch.trim().toLowerCase();
                return this.teams.filter(t => {
                    if (t.group !== groupId) return false;
                    if (!q) return true;
                    return t.name.toLowerCase().includes(q);
                });
            },

            isFacultyCollapsed(facultyId) {
                return !this.expandedFaculties[facultyId];
            },
            toggleFaculty(facultyId) {
                this.expandedFaculties = {
                    ...this.expandedFaculties,
                    [facultyId]: !this.expandedFaculties[facultyId],
                };
            },
            isGroupCollapsed(groupId) {
                return !this.expandedGroups[groupId];
            },
            toggleGroup(groupId) {
                this.expandedGroups = {
                    ...this.expandedGroups,
                    [groupId]: !this.expandedGroups[groupId],
                };
            },

            // Computed
            get availableTeams() {
                return this.teams.filter((team) => !team.game_status);
            },

            // Lifecycle
            async initialize() {
                await this.checkAdmin();
                if (this.isAdmin) {
                    await Promise.all([
                        this.loadGames(),
                        this.loadTeams(),
                        this.loadFaculties(),
                        this.loadGroups(),
                        this.loadDocuments(),
                    ]);
                }
                this.loading = false;
            },

            // Methods
            async checkAdmin() {
                try {
                    const response = await API.get("/admin/check/");
                    this.isAdmin = response.is_admin;
                } catch (e) {
                    this.isAdmin = false;
                }
            },

            async loadGames() {
                try {
                    const suffix = this.showArchivedGames ? "?archived=1" : "";
                    this.games = await API.get(`/games/${suffix}`);
                } catch (e) {
                    showToast("Ошибка загрузки игр: " + e.message, "error");
                }
            },

            async setGamesArchiveView(showArchived) {
                this.showArchivedGames = showArchived;
                await this.loadGames();
            },

            async loadTeams() {
                try {
                    const teams = await API.get("/teams/");
                    this.teams = teams.map((team) => ({
                        ...team,
                    }));
                } catch (e) {
                    showToast("Ошибка загрузки команд: " + e.message, "error");
                }
            },

            async loadFaculties() {
                try {
                    this.faculties = await API.get("/faculties/");
                } catch (e) {
                    showToast(
                        "Ошибка загрузки факультетов: " + e.message,
                        "error",
                    );
                }
            },

            async loadGroups() {
                try {
                    this.groups = await API.get("/groups/");
                } catch (e) {
                    showToast("Ошибка загрузки групп: " + e.message, "error");
                }
            },

            async loadDocuments() {
                try {
                    const response = await API.get("/documents/?include_builtin=1");
                    this.documents = response.documents || [];
                } catch (e) {
                    showToast("Ошибка загрузки документов: " + e.message, "error");
                }
            },

            openCreateModal() {
                this.newGame = {
                    team: "",
                    difficulty: "standard",
                    total_periods: 10,
                };
                this.createError = null;
                this.showCreateModal = true;
            },

            async createGame() {
                if (!this.newGame.team) return;

                this.creatingGame = true;
                this.createError = null;

                try {
                    await API.post("/games/", {
                        team: parseInt(this.newGame.team),
                        difficulty: this.newGame.difficulty,
                        total_periods: parseInt(this.newGame.total_periods),
                    });

                    showToast("Игра успешно создана", "success");
                    this.showCreateModal = false;
                    await Promise.all([this.loadGames(), this.loadTeams()]);
                } catch (e) {
                    this.createError = e.message;
                } finally {
                    this.creatingGame = false;
                }
            },

            getDifficultyDisplay(difficulty) {
                const labels = {
                    simple: "Simple",
                    standard: "Standard",
                    tough: "Tough",
                    veryhard: "Very hard",
                    higheq: "High EQ",
                };
                return labels[difficulty] || difficulty || "—";
            },

            // Pause/Resume methods
            async pauseGame(game) {
                try {
                    await API.post(`/games/${game.id}/pause/`);
                    showToast("Игра приостановлена", "success");
                    await this.loadGames();
                } catch (e) {
                    showToast("Ошибка: " + e.message, "error");
                }
            },

            async resumeGame(game) {
                try {
                    await API.post(`/games/${game.id}/resume/`);
                    showToast("Игра возобновлена", "success");
                    await this.loadGames();
                } catch (e) {
                    showToast("Ошибка: " + e.message, "error");
                }
            },

            async archiveGame(game) {
                try {
                    await API.post(`/games/${game.id}/archive/`);
                    showToast("Игра перемещена в архив", "success");
                    await this.loadGames();
                } catch (e) {
                    showToast("Ошибка архивирования: " + e.message, "error");
                }
            },

            async unarchiveGame(game) {
                try {
                    await API.post(`/games/${game.id}/unarchive/`);
                    showToast("Игра возвращена из архива", "success");
                    await this.loadGames();
                } catch (e) {
                    showToast("Ошибка восстановления: " + e.message, "error");
                }
            },

            exportPdf(game) {
                window.location.href = `/api/games/${game.id}/export/pdf/`;
            },

            exportExcel(game) {
                window.location.href = `/api/games/${game.id}/export/excel/`;
            },

            async openOperatorModal(game) {
                this.operatorGame = game;
                this.operatorValue = 0;
                this.operatorError = null;
                this.operatorLoading = true;
                this.showOperatorModal = true;

                try {
                    const response = await API.get(`/games/${game.id}/parameters/TF9/`);
                    this.operatorValue = Number(response.value || 0);
                } catch (e) {
                    this.operatorError = e.message;
                } finally {
                    this.operatorLoading = false;
                }
            },

            async saveOperatorParam() {
                if (!this.operatorGame) return;
                if (this.operatorValue < 0) {
                    this.operatorError = "Значение не может быть отрицательным";
                    return;
                }

                this.operatorSaving = true;
                this.operatorError = null;

                try {
                    await API.post(`/games/${this.operatorGame.id}/parameters/TF9/`, {
                        value: Number(this.operatorValue || 0),
                        force: true,
                    });
                    showToast("Иностранная помощь сохранена", "success");
                    this.showOperatorModal = false;
                } catch (e) {
                    this.operatorError = e.message;
                } finally {
                    this.operatorSaving = false;
                }
            },

            viewGame(game) {
                // Set view-only mode flag
                localStorage.setItem("strategem_view_only", "true");
                localStorage.setItem("strategem_game", game.id);
                localStorage.setItem("strategem_team_name", game.team_name);
                window.location.href = "/game/";
            },

            viewResults(game) {
                // View results for finished game
                localStorage.setItem("strategem_game", game.id);
                localStorage.setItem("strategem_team_name", game.team_name);
                localStorage.removeItem("strategem_view_only");
                window.location.href = "/game-results/";
            },

            confirmDelete(game) {
                this.gameToDelete = game;
                this.showDeleteModal = true;
            },

            async deleteGame() {
                if (!this.gameToDelete) return;

                this.deletingGame = true;

                try {
                    await API.delete(`/games/${this.gameToDelete.id}/`);
                    showToast("Игра удалена", "success");
                    this.showDeleteModal = false;
                    this.gameToDelete = null;
                    await Promise.all([this.loadGames(), this.loadTeams()]);
                } catch (e) {
                    showToast("Ошибка удаления: " + e.message, "error");
                } finally {
                    this.deletingGame = false;
                }
            },

            confirmDeleteEntity(type, id, name) {
                this.entityToDelete = { type, id, name };
                this.showEntityDeleteModal = true;
            },

            async deleteEntity() {
                if (!this.entityToDelete) return;
                this.deletingEntity = true;
                const { type, id } = this.entityToDelete;
                const urls = { faculty: `/faculties/${id}/`, group: `/groups/${id}/`, team: `/teams/${id}/` };
                const labels = { faculty: 'Факультет', group: 'Группа', team: 'Команда' };
                try {
                    await API.delete(urls[type]);
                    showToast(labels[type] + ' удалён', 'success');
                    this.showEntityDeleteModal = false;
                    this.entityToDelete = null;
                    await Promise.all([
                        this.loadFaculties(),
                        this.loadGroups(),
                        this.loadTeams(),
                        this.loadGames(),
                    ]);
                } catch (e) {
                    showToast('Ошибка удаления: ' + e.message, 'error');
                } finally {
                    this.deletingEntity = false;
                }
            },

            openUploadDocModal(doc = null) {
                this.newDoc = {
                    title: doc?.title || "",
                    scope: doc?.scope || "general",
                    minister: doc?.minister || "",
                    slot: doc?.slot || "",
                };
                this.docFile = null;
                this.uploadDocError = null;
                this.showUploadDocModal = true;
                this.$nextTick(() => {
                    if (this.$refs.docFileInput) {
                        this.$refs.docFileInput.value = "";
                    }
                });
            },

            onDocFileChange(event) {
                const file = event.target.files?.[0] || null;
                this.docFile = file;
                if (file && !this.newDoc.title.trim()) {
                    this.newDoc.title = file.name.replace(/\.[^.]+$/, "");
                }
            },

            async uploadDocument() {
                if (!this.docFile) {
                    this.uploadDocError = "Выберите файл";
                    return;
                }
                if (this.newDoc.scope === "minister" && !this.newDoc.minister) {
                    this.uploadDocError = "Выберите министра";
                    return;
                }

                const form = new FormData();
                form.append("file", this.docFile);
                form.append("title", this.newDoc.title.trim() || this.docFile.name);
                form.append("scope", this.newDoc.scope);
                if (this.newDoc.slot) {
                    form.append("slot", this.newDoc.slot);
                }
                if (this.newDoc.scope === "minister") {
                    form.append("minister", this.newDoc.minister);
                }

                this.uploadingDoc = true;
                this.uploadDocError = null;

                try {
                    const response = await fetch(API.baseUrl + "/documents/", {
                        method: "POST",
                        body: form,
                        credentials: "include",
                        headers: {
                            "X-CSRFToken": API.getCSRFToken(),
                        },
                    });
                    if (!response.ok) {
                        throw await parseApiError(response);
                    }

                    showToast("Файл загружен", "success");
                    this.showUploadDocModal = false;
                    await this.loadDocuments();
                } catch (e) {
                    this.uploadDocError = e.message;
                } finally {
                    this.uploadingDoc = false;
                }
            },

            async deleteDocument(doc) {
                if (!doc.id) {
                    showToast("Стартовый файл можно только заменить", "warning");
                    return;
                }
                if (!window.confirm(`Удалить файл «${doc.title}»?`)) return;

                try {
                    await API.delete(`/documents/${doc.id}/`);
                    await this.loadDocuments();
                    showToast("Файл удалён", "success");
                } catch (e) {
                    showToast("Ошибка удаления файла: " + e.message, "error");
                }
            },

            async logout() {
                try {
                    await API.post("/admin/logout/");
                    showToast("Выход выполнен", "success");
                    window.location.href = "/";
                } catch (e) {
                    showToast("Ошибка выхода: " + e.message, "error");
                }
            },

            // Faculty methods
            openCreateFacultyModal() {
                this.newFaculty = { name: "" };
                this.createFacultyError = null;
                this.showCreateFacultyModal = true;
            },

            async createFaculty() {
                if (!this.newFaculty.name) return;
                this.creatingFaculty = true;
                this.createFacultyError = null;

                try {
                    await API.post("/faculties/", {
                        name: this.newFaculty.name,
                    });
                    showToast("Факультет создан", "success");
                    this.showCreateFacultyModal = false;
                    await this.loadFaculties();
                } catch (e) {
                    this.createFacultyError = e.message;
                } finally {
                    this.creatingFaculty = false;
                }
            },

            // Group methods
            openCreateGroupModal() {
                this.newGroup = {
                    name: "",
                    faculty: "",
                    year: new Date().getFullYear(),
                };
                this.createGroupError = null;
                this.showCreateGroupModal = true;
            },

            async createGroup() {
                if (!this.newGroup.faculty || !this.newGroup.name) return;
                this.creatingGroup = true;
                this.createGroupError = null;

                try {
                    await API.post("/groups/", {
                        name: this.newGroup.name,
                        faculty: parseInt(this.newGroup.faculty),
                        year: parseInt(this.newGroup.year),
                    });
                    showToast("Группа создана", "success");
                    this.showCreateGroupModal = false;
                    await Promise.all([this.loadGroups(), this.loadTeams()]);
                } catch (e) {
                    this.createGroupError = e.message;
                } finally {
                    this.creatingGroup = false;
                }
            },

            // Team methods
            openCreateTeamModal() {
                this.newTeam = {
                    name: "",
                    group: "",
                    access_password: "",
                    password_enabled: true,
                };
                this.showCreateTeamPassword = false;
                this.createTeamError = null;
                this.showCreateTeamModal = true;
            },

            async createTeam() {
                if (!this.newTeam.group || !this.newTeam.name) return;
                if (this.newTeam.password_enabled && this.newTeam.access_password.trim().length < 6) {
                    this.createTeamError = "Пароль команды должен быть не короче 6 символов";
                    return;
                }
                this.creatingTeam = true;
                this.createTeamError = null;

                try {
                    await API.post("/teams/", {
                        name: this.newTeam.name,
                        group: parseInt(this.newTeam.group),
                        access_password: this.newTeam.password_enabled
                            ? this.newTeam.access_password.trim()
                            : "",
                    });
                    showToast("Команда создана", "success");
                    this.showCreateTeamModal = false;
                    this.showCreateTeamPassword = false;
                    await this.loadTeams();
                } catch (e) {
                    this.createTeamError = e.message;
                } finally {
                    this.creatingTeam = false;
                }
            },

            generateTeamPassword() {
                const words = ["luna", "vega", "terra", "atlas", "nova", "orbit", "river", "delta"];
                const word = words[Math.floor(Math.random() * words.length)];
                const num = Math.floor(Math.random() * 90) + 10;
                return `${word}-${num}`;
            },

            createTeamPassword() {
                this.newTeam.password_enabled = true;
                this.newTeam.access_password = this.generateTeamPassword();
                this.showCreateTeamPassword = true;
            },

            openTeamPasswordModal(team) {
                this.teamPasswordModalTeam = team;
                this.teamPasswordModalValue = "";
                this.teamPasswordModalEnabled = Boolean(team.has_access_password);
                this.teamPasswordModalError = null;
                this.showTeamPasswordModal = true;
            },

            closeTeamPasswordModal() {
                this.showTeamPasswordModal = false;
                this.teamPasswordModalTeam = null;
                this.teamPasswordModalValue = "";
                this.teamPasswordModalEnabled = true;
                this.teamPasswordModalError = null;
                this.savingTeamPasswordModal = false;
            },

            generateTeamPasswordForModal() {
                this.teamPasswordModalEnabled = true;
                this.teamPasswordModalValue = this.generateTeamPassword();
            },

            canSaveTeamPassword() {
                return (!this.teamPasswordModalEnabled || Boolean(this.teamPasswordModalValue && this.teamPasswordModalValue.trim().length >= 6))
                    && !this.savingTeamPasswordModal;
            },

            async saveTeamPassword() {
                if (!this.teamPasswordModalTeam) return;
                if (this.teamPasswordModalEnabled && this.teamPasswordModalValue.trim().length < 6) {
                    this.teamPasswordModalError = "Пароль команды должен быть не короче 6 символов";
                    return;
                }
                this.savingTeamPasswordModal = true;
                this.teamPasswordModalError = null;
                try {
                    await API.patch(`/teams/${this.teamPasswordModalTeam.id}/`, {
                        access_password: this.teamPasswordModalEnabled
                            ? this.teamPasswordModalValue.trim()
                            : "",
                    });
                    showToast(
                        this.teamPasswordModalEnabled
                            ? "Пароль команды сохранён"
                            : "Вход без пароля включён",
                        "success",
                    );
                    this.closeTeamPasswordModal();
                    await this.loadTeams();
                } catch (e) {
                    this.teamPasswordModalError = e.message;
                } finally {
                    this.savingTeamPasswordModal = false;
                }
            },

            // Helpers
            getStatusDisplay(status) {
                const statuses = {
                    created: "Создана",
                    active: "Активна",
                    paused: "Пауза",
                    finished: "Завершена",
                };
                return statuses[status] || status;
            },

            getMinisterLabel(minister) {
                const labels = {
                    population: "Население",
                    energy: "Энергетика",
                    industry: "Промышленность",
                    agriculture: "Сельское хозяйство",
                    trade_finance: "Торговля и финансы",
                };
                return labels[minister] || minister || "—";
            },

            formatDate(dateStr) {
                if (!dateStr) return "—";
                const date = new Date(dateStr);
                return date.toLocaleDateString("ru-RU", {
                    day: "2-digit",
                    month: "2-digit",
                    year: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                });
            },
        };
    }
