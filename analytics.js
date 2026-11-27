(() => {
    "use strict";

    // Local development only. Production tracking is disabled.
    const isLocal = ["localhost", "127.0.0.1"].includes(
        window.location.hostname
    );

    if (!isLocal) return;

    if (navigator.globalPrivacyControl === true ||
        navigator.doNotTrack === "1") return;

    const API_URL = "http://localhost:8001/events";
    const PAGE_PATH = "/personal-portfolio-saee/";

    function getSessionId() {
        try {
            let id = sessionStorage.getItem("pp_session_id");

            if (!id) {
                id = crypto.randomUUID();
                sessionStorage.setItem("pp_session_id", id);
            }

            return id;
        } catch {
            return crypto.randomUUID();
        }
    }

    const sessionId = getSessionId();

    function getDeviceType() {
        const width = window.screen.width;

        if (width <= 767) return "mobile";
        if (width <= 1024) return "tablet";

        return "desktop";
    }

    function getReferrerDomain() {
        try {
            if (!document.referrer) return null;

            const referrer = new URL(document.referrer);

            if (referrer.origin === window.location.origin) {
                return null;
            }

            return referrer.hostname;
        } catch {
            return null;
        }
    }

    const params = new URLSearchParams(window.location.search);

    async function trackEvent(eventType, fields = {}) {
        try {
            await fetch(API_URL, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                credentials: "omit",
                referrerPolicy: "no-referrer",
                keepalive: true,
                body: JSON.stringify({
                    session_id: sessionId,
                    event_type: eventType,
                    page_path: PAGE_PATH,
                    device_type: getDeviceType(),
                    ...fields,
                }),
            });
        } catch {
            // Analytics failures must never disrupt the portfolio.
        }
    }

    trackEvent("page_view", {
        referrer_domain: getReferrerDomain(),
        utm_source: params.get("utm_source"),
        utm_medium: params.get("utm_medium"),
        utm_campaign: params.get("utm_campaign"),
    });

        const trackedLinks = {
        "resume/SaeeDesai_Resume_AIML.pdf":
            ["resume_click", "resume"],

        "https://github.com/SaeeDesai":
            ["github_click", "github_profile"],

        "https://github.com/SaeeDesai/inference-reliability-gateway":
            ["project_click", "inference_reliability_gateway"],

        "https://github.com/SaeeDesai/research-assistant":
            ["project_click", "agentic_rag_research_assistant"],

        "https://huggingface.co/spaces/codemon9102/research-assistant":
            ["project_click", "agentic_rag_research_assistant"],

        "https://github.com/saeedesai-coder/Pharma-PQC":
            ["project_click", "post_quantum_pharmacovigilance"],

        "https://github.com/SaeeDesai/Emotion-To-Art-Generator":
            ["project_click", "multimodal_emotion_to_art"],

        "https://github.com/SaeeDesai/NLP_Reddit":
            ["project_click", "reddit_moderation"],

        "https://github.com/SaeeDesai/Facial-Expression-Recognition":
            ["project_click", "facial_expression_recognition"],

        "papers/PQC_Technical_Paper.pdf":
            ["publication_click", "pqc_technical_paper"],

        "https://arxiv.org/abs/2606.09412":
            ["publication_click", "pqc_arxiv"],

        "https://link.springer.com/chapter/10.1007/978-981-97-9529-1_7":
            ["publication_click", "quantum_cryptography_springer"],

        "mailto:saeedesai.dev@gmail.com":
            ["contact_click", "email"],

        "https://www.linkedin.com/in/saee-desai-237519206":
            ["contact_click", "linkedin"],
    };

    document.addEventListener("click", (event) => {
        const link = event.target.closest("a[href]");

        if (!link) return;

        const href = link.getAttribute("href");

        if (!Object.hasOwn(trackedLinks, href)) return;

        const [eventType, eventTarget] = trackedLinks[href];

        trackEvent(eventType, {
            event_target: eventTarget,
        });
    });

        // Scroll depth tracking
    const scrollThresholds = [25, 50, 75, 100];
    const reportedThresholds = new Set();

    window.addEventListener("scroll", () => {
        const scrollableHeight =
            document.documentElement.scrollHeight - window.innerHeight;

        if (scrollableHeight <= 0) return;

        const depth = Math.min(
            100,
            Math.round((window.scrollY / scrollableHeight) * 100)
        );

        for (const threshold of scrollThresholds) {
            if (depth >= threshold &&
                !reportedThresholds.has(threshold)) {
                reportedThresholds.add(threshold);

                trackEvent("scroll_depth", {
                    scroll_depth: threshold,
                });
            }
        }
    }, { passive: true });

    // Approximate active viewing duration
    let activeSeconds = 0;
    let lastReportedSeconds = 0;
    let lastInteraction = Date.now();

    ["pointerdown", "keydown", "scroll"].forEach((eventType) => {
        window.addEventListener(eventType, () => {
            lastInteraction = Date.now();
        }, { passive: true });
    });

    setInterval(() => {
        if (
            document.visibilityState === "visible" &&
            document.hasFocus() &&
            Date.now() - lastInteraction < 30000
        ) {
            activeSeconds++;
        }
    }, 1000);

    function reportDuration() {
        const seconds = activeSeconds - lastReportedSeconds;

        if (seconds <= 0) return;

        lastReportedSeconds = activeSeconds;

        trackEvent("active_duration", {
            active_seconds: seconds,
        });
    }

    setInterval(reportDuration, 15000);

    document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "hidden") {
            reportDuration();
        }
    });

    window.addEventListener("pagehide", reportDuration);
})();