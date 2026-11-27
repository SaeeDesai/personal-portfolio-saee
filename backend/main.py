from fastapi import FastAPI

app = FastAPI(
    title="PortfolioPulse API",
    description="Privacy-conscious portfolio analytics platform",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "portfoliopulse"
    }