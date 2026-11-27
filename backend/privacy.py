ALLOWED_TARGETS = {
    "resume_click": {
        "resume",
    },
    "github_click": {
        "github_profile",
    },
    "project_click": {
        "inference_reliability_gateway",
        "agentic_rag_research_assistant",
        "post_quantum_pharmacovigilance",
        "multimodal_emotion_to_art",
        "reddit_moderation",
        "facial_expression_recognition",
    },
    "publication_click": {
        "pqc_technical_paper",
        "pqc_arxiv",
        "quantum_cryptography_springer",
    },
    "contact_click": {
        "email",
        "linkedin",
    },
}

ALLOWED_REFERRERS = {
    "linkedin.com",
    "github.com",
    "google.com",
    "bing.com",
    "duckduckgo.com",
    "indeed.com",
    "handshake.com",
    "joinhandshake.com",
}

ALLOWED_CAMPAIGNS = {
    "utm_source": {
        "linkedin", "github", "email", "handshake", "google"
    },
    "utm_medium": {
        "social", "email", "referral", "organic"
    },
    "utm_campaign": {
        "portfolio_test", "job_search", "recruiter_outreach", "networking"
    },
}


def sanitize_referrer(value: str | None) -> str | None:
    if not value:
        return None

    value = value.strip().lower().removeprefix("www.")

    if value in ALLOWED_REFERRERS:
        return value

    return "other"


def sanitize_campaign(
    field: str, value: str | None
) -> str | None:
    if not value:
        return None

    value = value.strip().lower()

    if value in ALLOWED_CAMPAIGNS[field]:
        return value

    return "other"