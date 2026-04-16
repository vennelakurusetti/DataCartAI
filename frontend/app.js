const API_URL = "http://localhost:8000/api/v1";

window.app = {
    currentQuery: "",
    currentSelection: null,
    currentProducts: [],
    savedProducts: JSON.parse(localStorage.getItem("datacart-saved") || "[]"),
    reminders: JSON.parse(localStorage.getItem("datacart-reminders") || "[]"),
    sentimentChartInstance: null,
    compareChartInstance: null,

    init() {
        this.renderWatchlist();
        this.updateCompareCount();
    },

    showView(viewId) {
        document.querySelectorAll(".view").forEach((view) => view.classList.remove("active"));
        document.getElementById(viewId).classList.add("active");
    },

    enterSearch() {
        this.showView("view-app");
        document.getElementById("searchInput").focus();
    },

    goHome() {
        this.showView("view-landing");
    },

    usePrompt(prompt) {
        document.getElementById("searchInput").value = prompt;
        this.enterSearch();
        this.handleSearch();
    },

    setPipeline(lines) {
        const pipelineBox = document.getElementById("pipelineBox");
        pipelineBox.innerHTML = lines.map((line) => `<p>${line}</p>`).join("");
    },

    async handleSearch(isRefine = false) {
        const input = isRefine ? document.getElementById("refineInput") : document.getElementById("searchInput");
        const newText = input.value.trim();
        if (!newText) {
            return;
        }

        this.currentQuery = isRefine ? `${this.currentQuery} ${newText}`.trim() : newText;
        this.setPipeline([
            "Parsing your request into category, budget, and intent...",
            "Ranking products from the catalog...",
            "Preparing compare-ready specs and analytics..."
        ]);

        try {
            const nlpRes = await fetch(`${API_URL}/nlp/extract`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text: this.currentQuery })
            });
            const nlpData = await nlpRes.json();

            const scoreRes = await fetch(`${API_URL}/predict/scoring`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text: this.currentQuery })
            });
            const scoreData = await scoreRes.json();

            const analyticsRes = await fetch(`${API_URL}/analytics/stats?query=${encodeURIComponent(this.currentQuery)}`);
            const analyticsData = await analyticsRes.json();

            this.currentProducts = scoreData.data.scored_items;
            this.renderDashboard(nlpData.data, this.currentProducts, analyticsData);
            if (isRefine) {
                input.value = "";
            }
        } catch (error) {
            console.error(error);
            this.setPipeline(["Backend not reachable. Start FastAPI on port 8000 and try again."]);
        }
    },

    refineSearch() {
        this.handleSearch(true);
    },

    renderDashboard(nlp, products, analytics) {
        document.getElementById("resultsTitle").innerText = `${nlp.category} results under Rs. ${nlp.price_cap}`;

        const tagsContainer = document.getElementById("nlpTags");
        const tags = [`${nlp.match_count} matches`, `Budget: Rs. ${nlp.price_cap}`, `Category: ${nlp.category}`];
        (nlp.detected_features || []).forEach((feature) => tags.push(`Need: ${feature}`));
        if (nlp.result_mode === "live_web") {
            tags.push("Live web results");
        }
        tagsContainer.innerHTML = tags.map((tag) => `<span class="tag">${tag}</span>`).join("");

        this.setPipeline([
            `Category detected: ${nlp.category}`,
            `Budget cap locked at Rs. ${nlp.price_cap}`,
            `${nlp.match_count} products ready for exploration`
        ]);

        const grid = document.getElementById("productGrid");
        if (!products.length) {
            grid.className = "product-grid empty-state";
            grid.innerText = "No exact matches found. Try broadening the budget or removing a feature.";
            return;
        }

        grid.className = "product-grid";
        grid.innerHTML = products.map((product) => {
            const specs = product.specs;
            const specBadges = [];
            if (specs.ram_gb) specBadges.push(`${specs.ram_gb}GB RAM`);
            if (specs.storage_gb) specBadges.push(`${specs.storage_gb}GB storage`);
            if (specs.battery_mah) specBadges.push(`${specs.battery_mah}mAh`);
            if (specs.network && specs.network !== "Unknown") specBadges.push(specs.network);
            if (!specBadges.length && product.is_live_result) {
                specBadges.push("Live web listing");
            }
            return `
                <article class="product-card ${product.is_best_buy ? "hero" : ""}" data-id="${product.id}">
                    <div class="product-top">
                        <div>
                            <h4>${product.name}</h4>
                            <p>${product.summary}</p>
                        </div>
                        <span class="score-pill">${Math.round(product.ml_score * 100)}% fit</span>
                    </div>
                    <div class="spec-strip">
                        ${specBadges.map((badge) => `<span class="spec-badge">${badge}</span>`).join("")}
                    </div>
                    <div class="product-top">
                        <span class="price-pill">Rs. ${product.price}</span>
                        <span class="muted">${product.source}</span>
                    </div>
                </article>
            `;
        }).join("");

        grid.querySelectorAll(".product-card").forEach((card) => {
            card.addEventListener("click", () => {
                const product = products.find((item) => item.id === Number(card.dataset.id));
                this.openProductModal(product);
            });
        });

        this.renderAnalytics(analytics);
    },

    renderAnalytics(analytics) {
        const ctx = document.getElementById("sentimentChart").getContext("2d");
        if (this.sentimentChartInstance) {
            this.sentimentChartInstance.destroy();
        }

        this.sentimentChartInstance = new Chart(ctx, {
            type: "doughnut",
            data: {
                labels: analytics.sentiment.map((item) => item.name),
                datasets: [{
                    data: analytics.sentiment.map((item) => item.value),
                    backgroundColor: ["#54f3c3", "#65c8ff", "#ff7d7d"],
                    borderWidth: 0
                }]
            },
            options: {
                plugins: { legend: { labels: { color: "#eef6ff" } } }
            }
        });

        document.getElementById("visibleCount").innerText = analytics.totals.visible_products;
        document.getElementById("avgPrice").innerText = `Rs. ${analytics.totals.avg_price}`;
    },

    openProductModal(product) {
        this.currentSelection = product;
        document.getElementById("modalProductName").innerText = product.name;
        document.getElementById("modalSummary").innerText = product.summary;
        document.getElementById("modalPrice").innerText = `Rs. ${product.price}`;
        document.getElementById("modalSource").innerText = product.source;
        document.getElementById("fitReasons").innerHTML = product.why.map((reason) => `<li>${reason}</li>`).join("");
        document.getElementById("liveScrapeWrap").classList.add("hidden");
        document.getElementById("coachPanel").classList.add("hidden");
        const openListingBtn = document.getElementById("openListingBtn");
        if (product.product_url) {
            openListingBtn.classList.remove("hidden");
        } else {
            openListingBtn.classList.add("hidden");
        }
        document.getElementById("productModal").classList.add("active");
    },

    closeModal(modalId) {
        document.getElementById(modalId).classList.remove("active");
    },

    async startLiveScraping() {
        if (!this.currentSelection) {
            return;
        }

        const wrap = document.getElementById("liveScrapeWrap");
        wrap.classList.remove("hidden");
        wrap.innerHTML = "<p>Searching marketplaces for this product...</p>";

        if (this.currentSelection.product_url) {
            wrap.innerHTML = `
                <div class="watch-item">
                    <strong>Direct result found</strong>
                    <p>This product came from live web search.</p>
                    <a class="offer-link" href="${this.currentSelection.product_url}" target="_blank" rel="noreferrer">Open current listing</a>
                </div>
            `;
            return;
        }

        try {
            const response = await fetch(`${API_URL}/price/live`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text: this.currentQuery, product_id: this.currentSelection.id })
            });
            const data = await response.json();

            wrap.innerHTML = data.offers.map((offer) => `
                <div class="watch-item">
                    <strong>${offer.seller}: Rs. ${offer.price}</strong>
                    <p>${offer.label}</p>
                    <a class="offer-link" href="${offer.link}" target="_blank" rel="noreferrer">Open live search</a>
                </div>
            `).join("");
        } catch (error) {
            console.error(error);
            wrap.innerHTML = "<p>Could not fetch marketplace options right now.</p>";
        }
    },

    openCurrentListing() {
        if (this.currentSelection?.product_url) {
            window.open(this.currentSelection.product_url, "_blank", "noopener,noreferrer");
        }
    },

    async askFitCoach() {
        if (!this.currentSelection) {
            return;
        }

        const panel = document.getElementById("coachPanel");
        panel.classList.remove("hidden");
        panel.innerHTML = "Thinking through who this product fits best...";

        try {
            const response = await fetch(`${API_URL}/coach/explain`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text: this.currentQuery, product_id: this.currentSelection.id })
            });
            const data = await response.json();
            panel.innerHTML = `
                <strong>${data.verdict}</strong>
                <p>Best for: ${data.best_for}</p>
                <p>${data.reasons.join(", ")}.</p>
            `;
        } catch (error) {
            console.error(error);
            panel.innerHTML = "Could not load fit guidance right now.";
        }
    },

    saveCurrentProduct() {
        if (!this.currentSelection) {
            return;
        }

        const exists = this.savedProducts.some((item) => item.id === this.currentSelection.id);
        if (!exists) {
            this.savedProducts.push(this.currentSelection);
            localStorage.setItem("datacart-saved", JSON.stringify(this.savedProducts));
        }
        this.renderWatchlist();
        this.updateCompareCount();
        this.closeModal("productModal");
    },

    renderWatchlist() {
        const wrap = document.getElementById("watchlist");
        if (!wrap) {
            return;
        }

        if (!this.savedProducts.length) {
            wrap.className = "watchlist empty-state";
            wrap.innerText = "You have not liked any products yet.";
            return;
        }

        wrap.className = "watchlist";
        wrap.innerHTML = this.savedProducts.map((product) => `
            <div class="watch-item">
                <strong>${product.name}</strong>
                <p>Rs. ${product.price} • ${product.source}</p>
            </div>
        `).join("");
    },

    updateCompareCount() {
        const compareCount = document.getElementById("compareCount");
        if (compareCount) {
            compareCount.innerText = this.savedProducts.length;
        }
    },

    openCompare() {
        if (this.savedProducts.length < 2) {
            alert("Save at least two products to compare.");
            return;
        }

        const ctx = document.getElementById("compareChart").getContext("2d");
        if (this.compareChartInstance) {
            this.compareChartInstance.destroy();
        }

        const colors = [
            ["rgba(84, 243, 195, 0.25)", "#54f3c3"],
            ["rgba(101, 200, 255, 0.2)", "#65c8ff"],
            ["rgba(255, 184, 77, 0.22)", "#ffb84d"]
        ];

        const datasets = this.savedProducts.slice(0, 3).map((product, index) => ({
            label: product.name,
            data: [
                Math.min(product.specs.battery_mah / 60, 100),
                Math.min(product.specs.camera_mp * 1.6, 100),
                product.specs.display_type.toLowerCase() === "amoled" ? 95 : Math.min(product.specs.refresh_rate_hz * 0.8, 100),
                product.specs.chipset_score
            ],
            backgroundColor: colors[index][0],
            borderColor: colors[index][1],
            borderWidth: 2
        }));

        this.compareChartInstance = new Chart(ctx, {
            type: "radar",
            data: {
                labels: ["Battery", "Camera", "Display", "Performance"],
                datasets
            },
            options: {
                plugins: { legend: { labels: { color: "#eef6ff" } } },
                scales: {
                    r: {
                        angleLines: { color: "rgba(255,255,255,0.08)" },
                        grid: { color: "rgba(255,255,255,0.08)" },
                        pointLabels: { color: "#eef6ff" },
                        ticks: { display: false, backdropColor: "transparent" },
                        suggestedMin: 0,
                        suggestedMax: 100
                    }
                }
            }
        });

        document.getElementById("compareModal").classList.add("active");
    },

    async downloadDataset() {
        try {
            const response = await fetch(`${API_URL}/dataset/export?query=${encodeURIComponent(this.currentQuery)}`);
            const data = await response.json();
            const blob = new Blob([data.content], { type: "text/csv;charset=utf-8;" });
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = data.filename;
            link.click();
            URL.revokeObjectURL(url);
        } catch (error) {
            console.error(error);
            alert("Could not export the dataset right now.");
        }
    },

    async setReminder() {
        if (!this.currentSelection) {
            return;
        }

        const target = prompt(`Notify when ${this.currentSelection.name} drops below this price`, String(this.currentSelection.price - 1000));
        if (!target) {
            return;
        }

        const reminder = {
            product_id: this.currentSelection.id,
            target_price: Number(target),
            name: this.currentSelection.name
        };

        this.reminders.push(reminder);
        localStorage.setItem("datacart-reminders", JSON.stringify(this.reminders));

        try {
            await fetch(`${API_URL}/reminders`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ product_id: reminder.product_id, target_price: reminder.target_price })
            });
        } catch (error) {
            console.error(error);
        }

        alert(`Price drop reminder added for ${this.currentSelection.name}.`);
    }
};

window.addEventListener("DOMContentLoaded", () => window.app.init());
