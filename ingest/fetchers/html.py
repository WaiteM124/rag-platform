from __future__ import annotations

import re

from bs4 import BeautifulSoup

from ingest.fetchers.base import polite_get

PMC_ARTICLE = re.compile(r"pmc\.ncbi\.nlm\.nih\.gov/articles/(PMC\d+)")


def fetch_html_markdown(url: str) -> str:
    if "journals.plos.org" in url:
        return _fetch_plos(url)
    if pmc := PMC_ARTICLE.search(url):
        return _fetch_pmc_oa(pmc.group(1))
    if "libretexts.org" in url:
        return _fetch_libretexts(url)
    resp = polite_get(url)
    soup = BeautifulSoup(resp.text, "lxml")
    article = soup.find("article") or soup.find("main") or soup.body
    if not article:
        raise RuntimeError(f"No article body for {url}")
    return article.get_text("\n", strip=True)


def _fetch_plos(url: str) -> str:
    article_id = url.split("id=")[-1]
    xml_url = f"https://journals.plos.org/plosone/article/file?id={article_id}&type=manuscript"
    resp = polite_get(xml_url)
    soup = BeautifulSoup(resp.content, "xml")
    body = soup.find("body")
    return body.get_text("\n", strip=True) if body else resp.text[:200000]


def _fetch_pmc_oa(pmc_id: str) -> str:
    url = (
        f"https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_xml/{pmc_id}/unicode"
    )
    resp = polite_get(url, timeout=90.0)
    return resp.text[:500000]


def _fetch_libretexts(url: str) -> str:
    resp = polite_get(url)
    soup = BeautifulSoup(resp.text, "lxml")
    main = soup.select_one("#elm-main-content") or soup.find("main")
    if not main:
        raise RuntimeError(f"No LibreTexts content at {url}")
    return main.get_text("\n", strip=True)
