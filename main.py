
import json
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from google import genai

from analytics import (
    total_revenue,
    highest_revenue_product,
    revenue_by_region,
    monthly_revenue,
    data_quality_summary,
    revenue_change_between_months,
)

load_dotenv()

app = FastAPI(
    title="RSG Mini AI Business Intelligence Assistant",
    description="AI-powered sales analytics backed by SQLite",
    version="1.0.0",
)

# Gemini is optional at startup; configure the key in .env.
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

class QuestionRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


ANALYTICS_FUNCTIONS = {
    "total_revenue": total_revenue,
    "highest_revenue_product": highest_revenue_product,
    "revenue_by_region": revenue_by_region,
    "monthly_revenue": monthly_revenue,
    "data_quality_summary": data_quality_summary,
    "revenue_change_between_months": revenue_change_between_months,
}

def fallback_classify_question(question: str):
    """Recognize supported questions if Gemini is temporarily unavailable."""
    q = question.lower()

    if any(word in q for word in [
        "data quality", "missing", "invalid records"
    ]):
        return "data_quality_summary"

    if any(word in q for word in [
        "highest revenue product", "top product",
        "which product", "best selling product"
    ]):
        return "highest_revenue_product"

    if any(word in q for word in [
        "revenue by region", "which region",
        "region has the highest"
    ]):
        return "revenue_by_region"

    # Revenue change between two months
    if "revenue" in q and any(
        word in q for word in [
            "change", "increased", "decreased",
            "compare", "comparison", "growth"
        ]
    ):
        return "revenue_change_between_months"

    # Monthly revenue trend
    if any(word in q for word in [
        "monthly revenue", "revenue by month",
        "month-wise revenue"
    ]):
        return "monthly_revenue"

    # Total revenue
    if any(word in q for word in [
        "total revenue", "overall revenue",
        "revenue in total"
    ]):
        return "total_revenue"

    return None



def classify_question(question: str) -> str:
    """Use Gemini when available; otherwise use safe local classification."""
    if client is not None:
        prompt = f"""
Choose exactly one intent for this sales analytics question.

Allowed intents:
- total_revenue
- highest_revenue_product
- revenue_by_region
- monthly_revenue
- data_quality_summary
- unsupported

Return only a JSON object such as {{"intent": "total_revenue"}}.
Do not generate SQL.

Question: {json.dumps(question)}
"""
        try:
            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": {
                        "type": "OBJECT",
                        "properties": {
                            "intent": {"type": "STRING"}
                        },
                        "required": ["intent"],
                    },
                },
            )

            result = json.loads(response.text or "{}")
            intent = result.get("intent")

            if intent in ANALYTICS_FUNCTIONS:
                return intent

            if intent == "unsupported":
                raise HTTPException(
                    status_code=422,
                    detail="That question is not supported yet.",
                )

        except HTTPException:
            raise
        except Exception as exc:
            print(f"Gemini temporarily unavailable: {type(exc).__name__}: {exc}")

    # Reliable local fallback for supported business questions.
    fallback_intent = fallback_classify_question(question)
    if fallback_intent:
        return fallback_intent

    raise HTTPException(
        status_code=422,
        detail=(
            "That question is not supported. "
            "Try asking about total revenue, the top product, regions, "
            "monthly revenue, or data quality."
        ),
    )
@app.get("/")
def home():
    return {
        "message": "RSG Business Intelligence Assistant API is running",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "gemini_configured": client is not None,
    }


@app.get("/analytics/revenue")
def get_total_revenue():
    return total_revenue()


@app.get("/analytics/top-product")
def get_top_product():
    return highest_revenue_product()


@app.get("/analytics/regions")
def get_region_revenue():
    return revenue_by_region()


@app.get("/analytics/monthly")
def get_monthly_revenue():
    return monthly_revenue()

@app.get("/analytics/revenue-change")
def get_revenue_change(month_a: str, month_b: str):
    try:
        return revenue_change_between_months(month_a, month_b)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/analytics/data-quality")
def get_data_quality():
    return data_quality_summary()




@app.post("/ask")
def ask_question(request: QuestionRequest):
    if not request.question.strip():
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty.",
        )

    intent = classify_question(request.question)

    # Reject unsupported questions safely
    if (
        intent != "revenue_change_between_months"
        and intent not in ANALYTICS_FUNCTIONS
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "Sorry, I cannot answer that question yet. "
                "Try asking about total revenue, the top product, "
                "revenue by region, monthly revenue, data quality, "
                "or revenue change between two months."
            ),
        )

    if intent == "revenue_change_between_months":
        import re

        
        month_pattern = (
            r"\b(?:20\d{2}-(?:0[1-9]|1[0-2])|"
            r"(?:January|February|March|April|May|June|"
            r"July|August|September|October|November|December)"
            r"(?:\s+20\d{2})?)\b"
        )

        found_months = re.findall(
            month_pattern,
            request.question,
            re.IGNORECASE,
        )

        import calendar

        months = []
        for month in found_months:
            month = month.strip()

            if re.fullmatch(r"20\d{2}-(?:0[1-9]|1[0-2])", month):
                months.append(month)
            else:
                month_name, *year_part = month.split()
                month_number = list(calendar.month_name).index(
                    month_name.capitalize()
                )

                if year_part:
                    year = year_part[0]
                else:
                    year = "2026"  # Default year for month names

                months.append(f"{year}-{month_number:02d}")
        if len(months) != 2:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Please specify two months in YYYY-MM format, "
                    "for example: How did revenue change from "
                    "2026-01 to 2026-02?"
                ),
            )

        try:
            answer = revenue_change_between_months(
                months[0], months[1]
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=str(exc),
            )
    else:
        answer = ANALYTICS_FUNCTIONS[intent]()

    return {
        "question": request.question,
        "intent": intent,
        "answer": answer,
        "source": "Intent classification + SQLite analytics",
    }


