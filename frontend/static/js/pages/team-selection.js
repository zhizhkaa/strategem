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

            get canEnterGame() {
                return (
                    this.selectedTeam && this.selectedTeamData?.has_active_game
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
                            API.get("/teams/"),
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
            },

            onGroupChange() {
                this.selectedTeam = "";
            },

            onTeamChange() {
                this.error = null;
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

                    // Check if team has active game
                    const response = await API.get(
                        `/teams/${this.selectedTeam}/game/`,
                    );

                    if (response.game) {
                        localStorage.setItem(
                            "strategem_game",
                            response.game.id,
                        );
                        window.location.href = "/game/";
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
