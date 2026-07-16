"""
IW-11 GoogleScholar — Google Scholar Papers
Iron Warrior #11 — Académique, citations + abstracts.
Aucun dédié sur RapidAPI.
"""
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import sys
sys.path.insert(0, '/home/user/iron_warriors/shared')
from base import create_app, fetch_html, clean_text, get_timestamp, measure_latency
import time

app = create_app("IW-11 GoogleScholar", "Google Scholar papers — citations + abstracts")

class ScholarResult(BaseModel):
    title: str
    url: str
    authors: Optional[str] = None
    year: Optional[str] = None
    citations: Optional[str] = None
    snippet: Optional[str] = None
    pdf_url: Optional[str] = None
    position: int

class ScholarResponse(BaseModel):
    query: str
    engine: str
    results: List[ScholarResult]
    timestamp: str
    latency_ms: int

@app.get("/search", response_model=ScholarResponse)
async def google_scholar(
    q: str = Query(..., description="Scholar search query"),
    num: int = Query(10, ge=1, le=20),
    hl: str = Query("en"),
    as_ylo: int = Query(0, ge=1900, le=2030, description="Year from"),
    as_yhi: int = Query(0, ge=1900, le=2030, description="Year to"),
):
    start = time.time()
    params = f"q={quote_plus(q)}&hl={hl}&num={num}"
    if as_ylo > 0:
        params += f"&as_ylo={as_ylo}"
    if as_yhi > 0:
        params += f"&as_yhi={as_yhi}"
    url = f"https://scholar.google.com/scholar?{params}"
    try:
        html = await fetch_html(url)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Google Scholar fetch failed: {e}")

    soup = BeautifulSoup(html, 'html.parser')
    results = []
    seen = set()

    for div in soup.find_all('div', class_='gs_ri'):
        h3 = div.find('h3', class_='gs_rt')
        link = h3.find('a', href=True) if h3 else None
        author_tag = div.find('div', class_='gs_a')
        snippet_tag = div.find('div', class_='gs_rs')
        citations_tag = div.find('a', string=lambda t: t and 'Cited by' in t)
        pdf_link = div.find('div', class_='gs_or_ggsm').find('a', href=True) if div.find('div', class_='gs_or_ggsm') else None

        if h3 and link:
            href = link['href']
            if href in seen:
                continue
            seen.add(href)
            authors = clean_text(author_tag.get_text()) if author_tag else ""
            year = ""
            if authors:
                parts = authors.split(',')
                for p in parts:
                    p = p.strip()
                    if p.isdigit():
                        year = p
                        break
            results.append(ScholarResult(
                title=clean_text(h3.get_text()),
                url=href,
                authors=authors if authors else None,
                year=year if year else None,
                citations=clean_text(citations_tag.get_text()) if citations_tag else None,
                snippet=clean_text(snippet_tag.get_text()) if snippet_tag else None,
                pdf_url=pdf_link['href'] if pdf_link else None,
                position=len(results) + 1,
            ))
            if len(results) >= num:
                break

    return ScholarResponse(
        query=q, engine="google_scholar", results=results,
        timestamp=get_timestamp(), latency_ms=measure_latency(start),
    )
