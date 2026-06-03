function docsApp() {
    return {
        loading: true,
        error: null,
        documents: [],
        activeScope: 'general',
        ministerKey: null,
        ministerLabel: '',

        get filteredDocs() {
            if (this.activeScope === 'general') {
                return this.documents.filter(d => d.scope === 'general');
            }
            return this.documents.filter(d => d.scope === 'minister' && d.minister === this.activeScope);
        },

        async init() {
            // Определяем министра из URL (если открыта со страницы министра)
            const params = new URLSearchParams(window.location.search);
            this.ministerKey = params.get('minister') || null;
            if (this.ministerKey) {
                this.activeScope = this.ministerKey;
                const labels = {
                    population: 'Населения',
                    energy: 'Энергетики',
                    industry: 'Промышленности',
                    agriculture: 'С/х',
                    trade_finance: 'Торговли и финансов',
                };
                this.ministerLabel = labels[this.ministerKey] || this.ministerKey;
            }

            try {
                const data = await API.get('/documents/');
                this.documents = data.documents || [];
            } catch (e) {
                this.error = 'Ошибка загрузки документов: ' + e.message;
            }
            this.loading = false;
        },
    };
}
