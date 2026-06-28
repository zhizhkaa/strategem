function docsApp() {
    return {
        loading: true,
        error: null,
        documents: [],
        activeDoc: null,
        pdfLoading: false,
        pdfError: null,
        pdfPageCount: 0,
        pdfZoom: 1,
        ministerKey: null,
        ministerConfig: null,
        ministers: {},
        interpolationTables: {},
        gameId: null,
        _pdfRenderToken: 0,

        get visibleDocs() {
            if (!this.ministerKey) return this.documents;
            return [...this.generalDocs, ...this.ministerDocs];
        },

        get generalDocs() {
            return this.documents.filter((doc) => doc.scope === 'general');
        },

        get ministerDocs() {
            if (!this.ministerKey) return this.documents.filter((doc) => doc.scope === 'minister');
            return this.documents.filter((doc) => doc.scope === 'minister' && doc.minister === this.ministerKey);
        },

        get ministerLabel() {
            return this.ministerConfig?.name || this.ministerConfig?.short_name || this.ministerKey || '';
        },

        get chartEntries() {
            const entries = Object.entries(this.interpolationTables || {});
            if (!this.ministerKey) return entries;

            const keys = this.ministerConfig?.interpolation_keys || [];
            return keys
                .map((key) => [key, this.interpolationTables?.[key]])
                .filter(([, tableData]) => tableData);
        },

        async init() {
            const params = new URLSearchParams(window.location.search);
            this.ministerKey = params.get('minister') || null;
            this.gameId = localStorage.getItem('strategem_game');
            const gameQuery = this.gameId ? `?game_id=${encodeURIComponent(this.gameId)}` : '';

            try {
                const [docsData, interpolationData, structureData] = await Promise.all([
                    API.get('/documents/?include_builtin=1'),
                    API.get(`/games/interpolation-tables/${gameQuery}`),
                    API.get(`/games/decision-structure/${gameQuery}`),
                ]);
                this.documents = docsData.documents || [];
                this.interpolationTables = interpolationData || {};
                this.ministers = structureData.ministers || {};
                this.ministerConfig = this.ministerKey ? this.ministers[this.ministerKey] : null;
                this.activeDoc = this.defaultActiveDoc();
            } catch (e) {
                this.error = 'Ошибка загрузки справки: ' + e.message;
            }
            this.loading = false;
            this.$nextTick(() => this.renderActivePdf());
        },

        defaultActiveDoc() {
            if (!this.ministerKey) return null;
            return this.ministerDocs[0] || null;
        },

        selectDoc(doc) {
            this.activeDoc = doc;
            this.$nextTick(() => this.renderActivePdf());
        },

        async getPdfJs() {
            if (window.StrategemPdfJs) return window.StrategemPdfJs;

            const pdfjs = await import('/static/vendor/pdfjs/pdf.min.mjs');
            pdfjs.GlobalWorkerOptions.workerSrc = '/static/vendor/pdfjs/pdf.worker.min.mjs';
            window.StrategemPdfJs = pdfjs;
            return pdfjs;
        },

        async renderActivePdf() {
            const container = this.$refs.pdfViewer;
            const doc = this.activeDoc;
            const token = ++this._pdfRenderToken;

            this.pdfError = null;
            this.pdfPageCount = 0;
            if (container) container.innerHTML = '';
            if (!container || !doc?.url) {
                this.pdfLoading = false;
                return;
            }

            this.pdfLoading = true;

            try {
                const pdfjs = await this.getPdfJs();
                const loadingTask = pdfjs.getDocument({
                    url: doc.url,
                    cMapUrl: '/static/vendor/pdfjs/cmaps/',
                    cMapPacked: true,
                    standardFontDataUrl: '/static/vendor/pdfjs/standard_fonts/',
                });
                const pdf = await loadingTask.promise;
                if (token !== this._pdfRenderToken) {
                    pdf.destroy();
                    return;
                }

                this.pdfPageCount = pdf.numPages;
                for (let pageNumber = 1; pageNumber <= pdf.numPages; pageNumber += 1) {
                    await this.renderPdfPage(pdf, pageNumber, container, token);
                    if (token !== this._pdfRenderToken) {
                        pdf.destroy();
                        return;
                    }
                }
                pdf.destroy();
            } catch (e) {
                if (token === this._pdfRenderToken) {
                    this.pdfError = 'Не удалось открыть PDF: ' + e.message;
                }
            } finally {
                if (token === this._pdfRenderToken) {
                    this.pdfLoading = false;
                }
            }
        },

        async renderPdfPage(pdf, pageNumber, container, token) {
            const page = await pdf.getPage(pageNumber);
            if (token !== this._pdfRenderToken) return;

            const baseViewport = page.getViewport({ scale: 1 });
            const containerWidth = Math.max(container.clientWidth - 48, 320);
            const cssScale = Math.max(0.5, Math.min(3, (containerWidth / baseViewport.width) * this.pdfZoom));
            const viewport = page.getViewport({ scale: cssScale });
            const outputScale = Math.min(window.devicePixelRatio || 1, 2);
            const pageWidth = Math.floor(viewport.width);
            const pageHeight = Math.floor(viewport.height);

            const wrapper = document.createElement('div');
            wrapper.className = 'pdf-page mx-auto bg-white shadow-sm border border-gray-200';
            wrapper.style.width = `${pageWidth}px`;
            wrapper.style.maxWidth = '100%';

            const pageLabel = document.createElement('div');
            pageLabel.className = 'px-3 py-1 text-xs text-gray-500 border-b border-gray-100 bg-white';
            pageLabel.textContent = `Страница ${pageNumber}`;

            const canvas = document.createElement('canvas');
            canvas.className = 'block w-full h-auto';
            canvas.width = Math.floor(pageWidth * outputScale);
            canvas.height = Math.floor(pageHeight * outputScale);
            canvas.style.width = `${pageWidth}px`;
            canvas.style.height = `${pageHeight}px`;

            wrapper.append(pageLabel, canvas);
            container.appendChild(wrapper);

            const context = canvas.getContext('2d');
            await page.render({
                canvasContext: context,
                viewport,
                transform: outputScale === 1 ? null : [outputScale, 0, 0, outputScale, 0, 0],
            }).promise;
        },

        changePdfZoom(delta) {
            this.pdfZoom = Math.max(0.75, Math.min(1.6, Number((this.pdfZoom + delta).toFixed(2))));
            this.$nextTick(() => this.renderActivePdf());
        },

        resetPdfZoom() {
            this.pdfZoom = 1;
            this.$nextTick(() => this.renderActivePdf());
        },

        isActiveDoc(doc) {
            return Boolean(this.activeDoc) && (
                (doc.slot && this.activeDoc.slot === doc.slot)
                || (!doc.slot && this.activeDoc.id === doc.id)
            );
        },

        renderInterpolationChart(canvas, tableData) {
            new Chart(canvas, {
                type: 'line',
                data: {
                    datasets: [{
                        data: tableData.x.map((x, i) => ({ x, y: tableData.y[i] })),
                        borderColor: '#0f766e',
                        backgroundColor: 'rgba(15,118,110,0.08)',
                        borderWidth: 2,
                        tension: 0.25,
                        pointRadius: 3,
                        fill: true,
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
