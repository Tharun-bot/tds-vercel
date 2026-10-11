
import json
import math
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

DATA_FILE = Path(__file__).with_name("telemetry.json")


def load_telemetry():
    with DATA_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def percentile95(values):
    values = sorted(values)

    if len(values) == 1:
        return values[0]

    # Linear interpolation, as used by NumPy's default percentile.
    position = 0.95 * (len(values) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)

    return (
        values[lower]
        + (position - lower) * (values[upper] - values[lower])
    )


class MetricsRequest(BaseModel):
    regions: list[str]
    threshold_ms: float = Field(default=180)


@app.get("/")
def health():
    return {"status": "ok"}


@app.post("/")
def calculate_metrics(request: MetricsRequest):
    records = load_telemetry()
    result = {}

    for region in request.regions:
        selected = [
            row for row in records
            if row["region"].lower() == region.lower()
        ]

        if not selected:
            result[region] = {
                "error": "No telemetry records found"
            }
            continue

        latencies = [
            float(row["latency_ms"]) for row in selected
        ]

        uptimes = [
            float(row["uptime_pct"]) for row in selected
        ]

        result[region] = {
            "avg_latency": round(
                sum(latencies) / len(latencies), 2
            ),
            "p95_latency": round(
                percentile95(latencies), 2
            ),
            "avg_uptime": round(
                sum(uptimes) / len(uptimes), 3
            ),
            "breaches": sum(
                latency > request.threshold_ms
                for latency in latencies
            ),
        }

    return result
