"use strict";

const dateRange = document.getElementById("date-range");
const refreshButton = document.getElementById("refresh-btn");
const dashboardStatus = document.getElementById("dashboard-status");

const numberFormat = new Intl.NumberFormat("en-US");

const labels = {
    inference_reliability_gateway: "Inference Reliability Gateway",
    agentic_rag_research_assistant: "Agentic RAG Research Assistant",
    post_quantum_pharmacovigilance: "Post-Quantum Pharmacovigilance",
    multimodal_emotion_to_art: "Multimodal Emotion-to-Art",
    reddit_moderation: "Reddit Moderation & Emotion Analysis",
    facial_expression_recognition: "Facial Expression Recognition",
    pqc_technical_paper: "PQC Technical Paper",
    pqc_arxiv: "Post-Quantum Pharmacovigilance · arXiv",
    quantum_cryptography_springer: "Quantum Cryptography · Springer",
    direct_or_unknown: "Direct / Unknown",
};

function formatLabel(value) {
    return labels[value] || String(value).replaceAll("_", " ");
}

function formatDuration(seconds) {
    const total = Math.round(seconds || 0);
    const minutes = Math.floor(total / 60);
    const remaining = total % 60;

    return minutes ? `${minutes}m ${remaining}s` : `${remaining}s`;
}

async function fetchAnalytics(endpoint, days) {
    const response = await fetch(
        `/analytics/${endpoint}?days=${days}`,
        { cache: "no-store" }
    );

    if (response.status === 401) {
        window.location.replace("/login");
        throw new Error("Session expired");
    }

    if (!response.ok) {
        throw new Error(`Failed to load ${endpoint}`);
    }

    return response.json();
}

function setMetric(id, value) {
    document.getElementById(id).textContent = value;
}

function renderSummary(data) {
    setMetric("page-views", numberFormat.format(data.page_views));
    setMetric("sessions", numberFormat.format(data.sessions));
    setMetric("resume-clicks", numberFormat.format(data.resume_clicks));
    setMetric("engagement-rate", `${data.engagement_rate.toFixed(1)}%`);
    setMetric("avg-duration", formatDuration(data.avg_active_seconds_per_session));
    setMetric("project-clicks", numberFormat.format(data.project_clicks));
}

function renderBars(containerId, items, maximum = null) {
    const container = document.getElementById(containerId);
    container.replaceChildren();

    if (!items.length) {
        const empty = document.createElement("p");
        empty.className = "empty-state";
        empty.textContent = "No activity recorded for this period.";
        container.appendChild(empty);
        return;
    }

    const max = maximum ?? Math.max(1, ...items.map(item => item.value));

    items.forEach(item => {
        const wrapper = document.createElement("div");
        const row = document.createElement("div");
        row.className = "data-row";

        const label = document.createElement("span");
        label.textContent = item.label;

        const value = document.createElement("strong");
        value.textContent = `${numberFormat.format(item.value)}${item.suffix || ""}`;

        row.append(label, value);

        const track = document.createElement("div");
        track.className = "bar-track";

        const fill = document.createElement("div");
        fill.className = "bar-fill";
        fill.style.width = `${Math.min(100, item.value / max * 100)}%`;

        track.appendChild(fill);
        wrapper.append(row, track);
        container.appendChild(wrapper);
    });
}

function renderCampaigns(campaigns) {
    const table = document.getElementById("campaign-table");
    table.replaceChildren();

    if (!campaigns.length) {
        const row = table.insertRow();
        const cell = row.insertCell();

        cell.colSpan = 4;
        cell.textContent = "No campaign activity recorded.";
        return;
    }

    campaigns.forEach(campaign => {
        const row = table.insertRow();

        [
            campaign.source || "Unknown",
            formatLabel(campaign.campaign || "Unspecified"),
            campaign.page_views,
            campaign.sessions,
        ].forEach(value => {
            row.insertCell().textContent = value;
        });
    });
}

async function loadDashboard() {
    const days = dateRange.value;

    refreshButton.disabled = true;
    dateRange.disabled = true;
    dashboardStatus.textContent = "Loading analytics...";

    try {
        const [
            summary,
            projects,
            publications,
            referrers,
            campaigns,
            scrollDepth,
            traffic,
            devices,
        ] = await Promise.all([
            fetchAnalytics("summary", days),
            fetchAnalytics("projects", days),
            fetchAnalytics("publications", days),
            fetchAnalytics("referrers", days),
            fetchAnalytics("campaigns", days),
            fetchAnalytics("scroll-depth", days),
            fetchAnalytics("traffic", days),
            fetchAnalytics("devices", days),
        ]);

        renderSummary(summary);
        renderTraffic(traffic, days);
        renderDevices(devices);

        renderBars("project-list", projects.map(item => ({
            label: formatLabel(item.project),
            value: item.clicks,
        })));

        renderBars("publication-list", publications.map(item => ({
            label: formatLabel(item.publication),
            value: item.clicks,
        })));

        renderBars("referrer-list", referrers.map(item => ({
            label: formatLabel(item.source),
            value: item.views,
        })));

        renderBars("scroll-list", scrollDepth.map(item => ({
            label: `${item.depth}% of page`,
            value: item.percentage,
            suffix: "%",
        })), 100);

        renderBars("interaction-list", [
            { label: "Resume", value: summary.resume_clicks },
            { label: "Projects", value: summary.project_clicks },
            { label: "GitHub profile", value: summary.github_clicks },
            { label: "Publications", value: summary.publication_clicks },
            { label: "Contact", value: summary.contact_clicks },
        ]);

        renderCampaigns(campaigns);

        dashboardStatus.textContent =
            `Last updated at ${new Date().toLocaleTimeString()}`;

    } catch (error) {
        dashboardStatus.textContent =
            "Unable to refresh analytics. Previously loaded data may be outdated.";

        console.error("Dashboard error:", error);

    } finally {
        refreshButton.disabled = false;
        dateRange.disabled = false;
    }
}

let trafficChart = null;
let deviceChart = null;

Chart.defaults.color = "#929bae";
Chart.defaults.borderColor = "#252c3a";
Chart.defaults.font.family = "system-ui, sans-serif";

function renderTraffic(traffic, days) {
    if (trafficChart) trafficChart.destroy();

    const rows = new Map(
        traffic.map(item => [item.date, item])
    );

    const dates = [];
    const views = [];
    const sessions = [];

    for (let i = Number(days) - 1; i >= 0; i--) {
        const date = new Date();

        date.setUTCDate(date.getUTCDate() - i);

        const key = date.toISOString().slice(0, 10);
        const row = rows.get(key);

        dates.push(key);
        views.push(row?.page_views ?? 0);
        sessions.push(row?.sessions ?? 0);
    }

    trafficChart = new Chart(
        document.getElementById("traffic-chart"),
        {
            type: "line",
            data: {
                labels: dates,
                datasets: [
                    {
                        label: "Page views",
                        data: views,
                        borderColor: "#9b87f5",
                        backgroundColor: "rgba(155,135,245,0.12)",
                        fill: true,
                        tension: 0.35,
                        borderWidth: 2,
                        pointRadius: 3,
                    },
                    {
                        label: "Sessions",
                        data: sessions,
                        borderColor: "#60a5fa",
                        tension: 0.35,
                        borderWidth: 2,
                        pointRadius: 3,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: "index",
                    intersect: false,
                },
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: {
                            usePointStyle: true,
                            padding: 20,
                        },
                    },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { precision: 0 },
                    },
                    x: {
                        grid: { display: false },
                        ticks: { maxTicksLimit: 7 },
                    },
                },
            },
        }
    );
}

function renderDevices(devices) {
    if (deviceChart) deviceChart.destroy();

    const colors = {
        desktop: "#9b87f5",
        mobile: "#60a5fa",
        tablet: "#34d399",
        unknown: "#64748b",
    };

    const total = devices.reduce(
        (sum, item) => sum + item.views, 0
    );

    deviceChart = new Chart(
        document.getElementById("device-chart"),
        {
            type: "doughnut",
            data: {
                labels: total
                    ? devices.map(item => formatLabel(item.device))
                    : ["No activity"],
                datasets: [{
                    data: total
                        ? devices.map(item => item.views)
                        : [1],
                    backgroundColor: total
                        ? devices.map(item =>
                            colors[item.device] || colors.unknown
                        )
                        : ["#252c3a"],
                    borderWidth: 0,
                    hoverOffset: 6,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "72%",
                plugins: {
                    tooltip: { enabled: total > 0 },
                    legend: {
                        position: "bottom",
                        labels: {
                            usePointStyle: true,
                            padding: 18,
                        },
                    },
                },
            },
        }
    );
}

refreshButton.addEventListener("click", loadDashboard);
dateRange.addEventListener("change", loadDashboard);

document.querySelectorAll(".nav-link").forEach(link => {
    link.addEventListener("click", () => {
        document.querySelectorAll(".nav-link").forEach(item => {
            item.classList.remove("active");
        });

        link.classList.add("active");
    });
});

loadDashboard();

const logoutButton = document.getElementById("logout-btn");

logoutButton.addEventListener("click", async () => {
    logoutButton.disabled = true;

    try {
        const response = await fetch("/auth/logout", {
            method: "POST",
            credentials: "same-origin",
        });

        if (!response.ok) {
            throw new Error("Logout failed");
        }

        window.location.replace("/login");

    } catch {
        dashboardStatus.textContent =
            "Unable to sign out. Please try again.";

        logoutButton.disabled = false;
    }
});

window.addEventListener("pageshow", async (event) => {
    if (!event.persisted) return;

    try {
        const response = await fetch("/auth/me", {
            cache: "no-store",
            credentials: "same-origin",
        });

        if (!response.ok) {
            window.location.replace("/login");
        }
    } catch {
        window.location.replace("/login");
    }
});