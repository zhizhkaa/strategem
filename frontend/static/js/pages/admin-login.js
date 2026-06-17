function adminLogin() {
        return {
            password: '',
            showPassword: false,
            loading: false,
            error: null,

            async login() {
                if (!this.password) return;

                this.loading = true;
                this.error = null;

                try {
                    const response = await API.post('/admin/login/', {
                        password: this.password
                    });

                    if (response.success) {
                        showToast('Вход выполнен успешно', 'success');
                        window.location.href = '/admin-panel/';
                    }
                } catch (e) {
                    this.error = e.message || 'Неверный пароль';
                    this.password = '';
                } finally {
                    this.loading = false;
                }
            }
        };
    }
