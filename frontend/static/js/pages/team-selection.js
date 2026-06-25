function teamSelection() {
        return {
            // Data
            faculties: [],
            groups: [],
            teams: [],

            // Selected values
            selectedFaculty: "",
            selectedGroup: "",
            selectedTeam: "",
            teamPassword: "",
            showTeamPassword: false,

            // State
            loading: false,
            error: null,

            // Computed
            get filteredGroups() {
                if (!this.selectedFaculty) return [];
                return this.groups.filter(
                    (g) => g.faculty == this.selectedFaculty,
                );
            },

            get filteredTeams() {
                if (!this.selectedGroup) return [];
                return this.teams.filter((t) => t.group == this.selectedGroup);
            },

            get selectedTeamData() {
                if (!this.selectedTeam) return null;
                return this.teams.find((t) => t.id == this.selectedTeam);
            },

            get selectedTeamHasGame() {
                return Boolean(
                    this.selectedTeamData?.has_active_game
                    || this.selectedTeamData?.has_finished_game
                );
            },

            get canEnterGame() {
                return (
                    this.selectedTeam
                    && this.selectedTeamHasGame
                    && (
                        !this.selectedTeamData?.has_access_password
                        || this.teamPassword.trim().length > 0
                    )
                );
            },

            // Methods
            async init() {
                this.loading = true;
                try {
                    // Load all data in parallel
                    const [facultiesRes, groupsRes, teamsRes] =
                        await Promise.all([
                            API.get("/faculties/"),
                            API.get("/groups/"),
                            API.get("/teams/?public=1"),
                        ]);

                    this.faculties = facultiesRes;
                    this.groups = groupsRes;
                    this.teams = teamsRes;

                    // Restore previous selection from localStorage
                    const savedTeam = localStorage.getItem("strategem_team");
                    if (savedTeam) {
                        const team = this.teams.find((t) => t.id == savedTeam);
                        if (team) {
                            const group = this.groups.find(
                                (g) => g.id == team.group,
                            );
                            if (group) {
                                this.selectedFaculty = group.faculty;
                                this.selectedGroup = group.id;
                                this.selectedTeam = team.id;
                            }
                        }
                    }
                } catch (e) {
                    this.error = "Ошибка загрузки данных: " + e.message;
                    showToast(this.error, "error");
                } finally {
                    this.loading = false;
                }
            },

            onFacultyChange() {
                this.selectedGroup = "";
                this.selectedTeam = "";
                this.teamPassword = "";
                this.showTeamPassword = false;
            },

            onGroupChange() {
                this.selectedTeam = "";
                this.teamPassword = "";
                this.showTeamPassword = false;
            },

            onTeamChange() {
                this.error = null;
                this.teamPassword = "";
                this.showTeamPassword = false;
            },

            teamOptionLabel(team) {
                if (team.has_finished_game) return `${team.name} (игра завершена)`;
                return team.has_active_game ? `${team.name} (есть игра)` : team.name;
            },

            teamStatusMessage() {
                if (!this.selectedTeamData) return "";
                if (this.selectedTeamData.has_finished_game) {
                    return "Команда завершила игру";
                }
                if (this.selectedTeamData.has_active_game) {
                    return "У команды есть активная игра";
                }
                return "У команды нет активной игры. Обратитесь к администратору.";
            },

            teamStatusClass() {
                if (!this.selectedTeamData) return "";
                if (this.selectedTeamData.has_finished_game) {
                    return "text-blue-700 bg-blue-50 border-blue-200";
                }
                if (this.selectedTeamData.has_active_game) {
                    return "text-green-700 bg-green-50 border-green-200";
                }
                return "text-yellow-700 bg-yellow-50 border-yellow-200";
            },

            async enterGame() {
                if (!this.canEnterGame) return;

                this.loading = true;
                this.error = null;

                try {
                    // Save selection
                    localStorage.setItem("strategem_team", this.selectedTeam);
                    localStorage.setItem(
                        "strategem_team_name",
                        this.selectedTeamData?.name || "",
                    );
                    // Clear view-only mode (player is entering their own game)
                    localStorage.removeItem("strategem_view_only");

                    // Check password and active game
                    const response = await API.post(
                        `/teams/${this.selectedTeam}/game/`,
                        {
                            password: this.selectedTeamData?.has_access_password
                                ? this.teamPassword.trim()
                                : "",
                        },
                    );

                    if (response.game) {
                        localStorage.setItem(
                            "strategem_game",
                            response.game.id,
                        );
                        window.location.href = response.game.status === "finished"
                            ? "/game-results/"
                            : "/game/";
                    } else {
                        this.error =
                            "У команды нет активной игры. Обратитесь к администратору.";
                    }
                } catch (e) {
                    this.error = "Ошибка: " + e.message;
                    showToast("Ошибка входа в игру: " + e.message, "error");
                } finally {
                    this.loading = false;
                }
            },
        };
    }
