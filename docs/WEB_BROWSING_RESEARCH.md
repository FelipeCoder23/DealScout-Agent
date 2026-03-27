# Web Browsing & Scraping Research for DealScout Agent

> Research conducted 2026-03-27. Focused on product price comparison in the LangChain/LangGraph ecosystem, with Chilean e-commerce considerations.

---

## Table of Contents

1. [Tavily Search API](#1-tavily-search-api)
2. [Playwright + LangChain](#2-playwright--langchain)
3. [Other Web Tools for Agents](#3-other-web-tools-for-agents)
4. [Best Practices for Web-Browsing Agents](#4-best-practices-for-web-browsing-agents)
5. [Docker Considerations](#5-docker-considerations)
6. [Recommendation for DealScout](#6-recommendation-for-dealscout)

---

## 1. Tavily Search API

### What It Is

Tavily is a real-time search engine built specifically for AI agents and RAG workflows. It was acquired by Nebius in February 2026. It provides Search, Extract, Map, and Crawl APIs that return results optimized for LLM consumption (summaries, citations, structured content).

### Capabilities

| API | What It Does | Credit Cost |
|-----|-------------|-------------|
| **Search (Basic)** | Web search with AI-optimized results | 1 credit |
| **Search (Advanced)** | Deeper search with more sources | 2 credits |
| **Extract** | Clean markdown/text from URLs | 1 credit per 5 URLs (basic) |
| **Map** | Site mapping, discover URLs on a domain | 1 credit per 10 pages |
| **Crawl** | Traverse sites, pull content from many pages | Combined map + extract cost |
| **Research** | Multi-step deep research (Pro model) | 15-250 credits per request |

### Pricing

| Plan | Credits/month | Cost | Per-Credit |
|------|--------------|------|------------|
| Researcher (Free) | 1,000 | $0 | -- |
| Project | 4,000 | $30/mo | $0.0075 |
| Bootstrap | 15,000 | $100/mo | $0.0067 |
| Startup | 38,000 | $220/mo | $0.0058 |
| Growth | 100,000 | $500/mo | $0.005 |
| Pay-as-you-go | Variable | -- | $0.008 |

### Product Search Suitability

- **Good for discovery**: Finding which sites sell a product and getting summaries of results.
- **Weak for structured extraction**: Does not natively return structured product data (price, seller, stock status). You would need additional LLM calls to parse the text output into structured fields, which drops accuracy to ~72% compared to schema-based extractors.
- **No ecommerce-specific features**: Unlike SerpAPI, Tavily does not have a dedicated shopping/product API.

### Chilean Sites

- No specific documentation exists for Chilean or Spanish-language site coverage.
- Tavily uses general web search, so it will find Chilean sites (Falabella, Ripley, Paris, MercadoLibre Chile) if they rank in search results.
- **Limitation**: Regional search tuning is not well-documented. You cannot specify `country=CL` or similar locale filtering the way SerpAPI/Google Shopping can.
- The Extract and Crawl APIs should work on any accessible URL regardless of language.

### Verdict for DealScout

Tavily is **useful as a discovery layer** (finding product pages and URLs), but not sufficient as the sole extraction tool for structured price data. Best combined with Firecrawl or direct scraping for the actual data extraction step.

---

## 2. Playwright + LangChain

### LangChain PlayWrightBrowserToolkit

LangChain provides a built-in `PlayWrightBrowserToolkit` with 7 tools:

| Tool | Function |
|------|----------|
| `navigate_browser` | Go to a URL |
| `previous_page` | Navigate back |
| `click_element` | Click via CSS selector |
| `extract_text` | Get page text (uses BeautifulSoup) |
| `extract_hyperlinks` | Get all links on page |
| `get_elements` | Query DOM elements by CSS selector |
| `current_page` | Get the current URL |

### Setup

```python
pip install playwright lxml
playwright install  # downloads browser binaries (Chromium by default)
```

```python
from langchain_community.agent_toolkits import PlayWrightBrowserToolkit
from langchain_community.tools.playwright.utils import create_async_playwright_browser

async_browser = create_async_playwright_browser()
toolkit = PlayWrightBrowserToolkit.from_browser(async_browser=async_browser)
tools = toolkit.get_tools()
```

### Key Considerations

- **Async required**: The async browser is strongly recommended. Sync browser does not work in Jupyter.
- **Structured chat agents**: Several tools are `StructuredTool` (multiple arguments), so you need agents that support structured tool calling (not the old ReAct text-based agents).
- **JavaScript rendering**: Full Chromium rendering -- handles SPAs, dynamic content, infinite scroll.
- **Limitations**: The built-in toolkit is relatively basic. No form-filling tool out of the box (though Playwright itself supports it). No screenshot tool in the default toolkit.

### LangGraph Integration Pattern

The recommended pattern is a ReAct loop in LangGraph:

```
1. Agent receives goal (e.g., "find PS5 price on Falabella.com")
2. Agent calls navigate_browser to go to the site
3. Agent calls extract_text or get_elements to read the page
4. Agent reasons about what it found
5. Agent may click_element to interact (e.g., search bar, filters)
6. Agent extracts structured data and returns it
```

### When to Use Playwright Directly

- Sites that require JavaScript rendering (React/Vue/Angular SPAs)
- Sites that require interaction (clicking "Load More", filling search forms)
- Sites behind login walls (session management)
- When you need to handle anti-bot challenges like Cloudflare

### Alternatives to LangChain's Toolkit

- **browser-use**: Leading open-source Python/TypeScript SDK with stealth technology, session management, and multi-LLM support. More capable than LangChain's built-in toolkit.
- **Stagehand v3** (by Browserbase): Natural language commands for browser automation, 44% faster than v2, self-healing selectors. Essentially "an OSS alternative to Playwright that's easier to use and lets AI reliably read and write on the web."
- **Microsoft Playwright MCP Server**: Uses accessibility snapshots instead of screenshots, works with non-vision models. Official Microsoft release.

---

## 3. Other Web Tools for Agents

### 3.1 Firecrawl

**What**: Web scraping API that handles JavaScript rendering, anti-bot detection, and returns clean markdown or structured JSON.

**Key Advantages over Tavily for DealScout**:
- **94% accuracy** on structured ecommerce extraction (vs ~72% for Tavily + post-processing)
- **77.2% URL coverage** vs Tavily's 67.8% in benchmark tests
- **Schema-based extraction**: Define a JSON schema, get typed structured data back
- Built-in JavaScript rendering via pre-warmed headless Chromium
- Multiple output formats: markdown, JSON, HTML, screenshots, links

**Pricing**: Starts at $16/month. At 100K pages: ~$83/month vs Tavily's ~$500-800.

**LangGraph Integration**: Firecrawl provides `@tool`-decorated functions that plug directly into LangGraph agents:
- `scrape_markdown` -- clean page content
- `extract_data` -- structured extraction with JSON schema
- `search_web` -- web search
- `crawl_docs` -- multi-page crawling
- `take_screenshot` -- visual capture

**DealScout Verdict**: Strong choice for the extraction layer. The schema extraction feature is exactly what a price comparison agent needs.

### 3.2 Browserbase

**What**: Cloud-hosted browser infrastructure for AI agents. Provides managed headless browsers with anti-detection, proxy rotation, and session management.

**Key Features**:
- Serverless -- no need to manage browser containers yourself
- Built-in anti-bot evasion (stealth mode, fingerprint rotation)
- Session persistence for multi-step workflows
- Raised $40M Series B (June 2025), valued at $300M

**When to Use**: When you need reliable cloud browsers at scale, particularly for sites with aggressive anti-bot protections. An ecommerce company used Browserbase-powered agents to extract daily price updates from dozens of supplier websites.

**Cost**: Usage-based pricing; more expensive than self-hosted Playwright but eliminates infrastructure complexity.

### 3.3 SerpAPI / Google Shopping API

**What**: API that scrapes Google search results, including Google Shopping, Amazon, eBay, Walmart, Home Depot, and Bing Shopping.

**Key Features for DealScout**:
- **Google Shopping API** returns: position, title, product_link, product_id, price, extracted_price, old_price, rating, reviews, thumbnail, delivery info
- **Price monitoring** across 6 marketplaces simultaneously
- Supports targeting specific Google domains, country codes, and languages -- **can target Google Chile (google.cl) and Spanish results**
- Free tier: 250 searches/month

**DealScout Verdict**: Excellent for initial product discovery and getting a cross-marketplace price overview. The Google Shopping API naturally aggregates prices from many retailers. However:
- Chilean local retailers (Falabella, Ripley, Paris) may not always appear in Google Shopping results
- Best combined with direct scraping of specific Chilean sites

### 3.4 Ecommerce-Specific Tools

| Tool | Focus | Notes |
|------|-------|-------|
| **Bright Data** | Enterprise web data platform | Proxies, unlocker, scraping browser, ecommerce datasets |
| **Oxylabs** | Web scraping infrastructure | Real-time crawler, AI-powered parsing |
| **ScrapingBee** | Web scraping API | JavaScript rendering, proxy rotation, CAPTCHA handling |
| **Apify** | Web scraping platform | Pre-built "actors" for Amazon, eBay, etc. |
| **Crawlee** (by Apify) | Open-source scraping framework | Python + Node.js, integrates with Playwright |

### 3.5 Emerging: Model Context Protocol (MCP)

MCP is becoming the standard for giving AI agents web access. Google donated it to the Linux Foundation (December 2025). Key MCP servers for web browsing:
- **Microsoft Playwright MCP**: Official, uses accessibility snapshots
- **WebFetch/WebSearch**: Direct page reading and search
- Multiple community Puppeteer-based implementations

---

## 4. Best Practices for Web-Browsing Agents

### 4.1 JavaScript-Heavy Sites

- **Always use a real browser engine** (Playwright/Chromium) for SPA sites. Standard HTTP requests return empty HTML for React/Vue/Angular apps.
- Firecrawl abstracts this away with pre-warmed headless Chromium.
- For LangGraph agents: add wait logic after navigation (wait for selectors, network idle) before extracting content.
- Consider `browser-use` or `Stagehand` for more reliable interaction with dynamic content.

### 4.2 Anti-Bot Protections

Modern anti-bot systems (Cloudflare, DataDome, Kasada, PerimeterX) use:
- AI-driven fingerprinting and behavioral analysis
- TLS fingerprint detection
- JavaScript challenge pages
- CAPTCHA challenges

**Mitigation strategies**:
1. **Rotate user agents** -- but ensure the entire header set is consistent (Sec-Ch-Ua, Accept-Language, etc.). Mismatched headers are a red flag.
2. **Use residential proxies** for sites with aggressive IP-based blocking.
3. **Use stealth browser tools** (browser-use, Browserbase, Steel) that handle fingerprint evasion.
4. **Respect robots.txt** and rate limits -- ethical scraping reduces blocking risk.
5. **Use APIs when available** -- many Chilean retailers (MercadoLibre) have official APIs.
6. **Consider managed scraping services** (Bright Data, ScrapingBee) that handle anti-bot at the infrastructure level.

### 4.3 Rate Limiting

- Implement delays between requests (1-3 seconds minimum for polite scraping).
- Use exponential backoff on failures (429, 503 responses).
- Distribute requests across time windows.
- In LangGraph: model rate limiting as state in the agent graph, with conditional edges for retry logic.
- Cache results aggressively -- product prices do not change every second.

### 4.4 Extracting Structured Product Data

**Recommended approach for DealScout**:

1. **Define a Pydantic schema** for product data:
```python
class ProductListing(BaseModel):
    name: str
    price: float
    currency: str  # CLP, USD
    seller: str
    url: HttpUrl
    in_stock: bool
    original_price: Optional[float] = None  # for discount detection
    shipping_cost: Optional[float] = None
    rating: Optional[float] = None
    last_checked: datetime
```

2. **Use schema-based extraction** (Firecrawl `extract_data` or LLM `with_structured_output`) to map raw HTML/text to this schema.

3. **Validate with Pydantic** -- reject entries with missing required fields or nonsensical prices.

4. **LLM as parser**: When structured extractors fail, pass raw page text to an LLM with the schema and ask it to extract the product data. This handles unexpected page layouts gracefully.

### 4.5 Agent Architecture for Price Comparison

Recommended LangGraph architecture:

```
[START]
   |
   v
[Search Node] -- Use Tavily/SerpAPI to find product URLs
   |
   v
[Plan Node] -- Agent decides which URLs to scrape
   |
   v
[Scrape Node] -- Use Firecrawl/Playwright to extract data per URL
   |              (parallel execution for multiple URLs)
   v
[Parse Node] -- LLM structures raw data into ProductListing schema
   |
   v
[Compare Node] -- Sort by price, calculate savings, flag best deals
   |
   v
[Output Node] -- Format comparison table
   |
   v
[END]
```

Key LangGraph features to leverage:
- **Checkpointing**: Resume long-running scrape jobs on failure
- **Parallel execution**: Scrape multiple sites concurrently
- **Conditional edges**: Skip sites that are down, retry on transient failures
- **State management**: Track which sites have been scraped, accumulate results
- **`with_structured_output`**: Force LLM responses into Pydantic models

---

## 5. Docker Considerations

### Official Playwright Docker Images

Published to Microsoft Artifact Registry:

```
mcr.microsoft.com/playwright/python:v1.58.0-noble   # Ubuntu 24.04
mcr.microsoft.com/playwright/python:v1.58.0-jammy    # Ubuntu 22.04
```

### Dockerfile for DealScout

```dockerfile
FROM python:3.12-bookworm

# Install Playwright and browser dependencies
RUN pip install playwright==1.58.0 && \
    playwright install --with-deps chromium

# Install project dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Security: create non-root user for web scraping
RUN useradd -m -s /bin/bash scraper

COPY src/ /app/src/
WORKDIR /app

USER scraper
```

### Running the Container

```bash
# For web scraping (security-hardened):
docker run -it --rm \
    --ipc=host \
    --user scraper \
    --security-opt seccomp=seccomp_profile.json \
    dealscout-agent

# For development/testing (simpler):
docker run -it --rm \
    --ipc=host \
    dealscout-agent
```

### Critical Docker Flags

| Flag | Why |
|------|-----|
| `--ipc=host` | Prevents Chromium out-of-memory crashes (shared memory) |
| `--init` | Prevents zombie processes from browser subprocesses |
| `--user scraper` | Non-root for security; enables Chromium sandbox |
| `--security-opt seccomp=...` | Allows user namespace cloning for sandbox |
| `--cap-add=SYS_ADMIN` | Alternative to seccomp (less secure, simpler) |

### Version Pinning

Always pin the Playwright version in both `requirements.txt` and the Dockerfile. Mismatched versions between the Python package and browser binaries cause silent failures.

### Alpine Linux

**Not supported**. Playwright requires glibc-based distributions (Ubuntu/Debian). Alpine uses musl which is incompatible with Firefox and WebKit builds.

### Resource Considerations

- Each Chromium instance uses ~100-300MB RAM.
- For parallel scraping of N sites, budget N * 300MB.
- Consider using a browser pool with max concurrency limits.
- Headless mode is mandatory in containers (no display server).

---

## 6. Recommendation for DealScout

### Recommended Tool Stack

| Layer | Tool | Rationale |
|-------|------|-----------|
| **Product Discovery** | SerpAPI Google Shopping | Best structured product data out-of-the-box; supports Google Chile (google.cl); returns prices, ratings, links |
| **URL Discovery** | Tavily Search (free tier) | Find product pages on specific Chilean retailers not in Google Shopping |
| **Structured Extraction** | Firecrawl | 94% accuracy on ecommerce schema extraction; handles JS rendering; cost-effective at scale |
| **Fallback / JS-heavy sites** | Playwright (via LangChain toolkit) | For sites that block Firecrawl or need interaction (search forms, filters) |
| **Agent Framework** | LangGraph | Stateful graph with checkpointing, parallel scraping, conditional retry logic |
| **Data Validation** | Pydantic | Enforce ProductListing schema on all extracted data |

### Cost Estimate (MVP)

| Service | Tier | Monthly Cost |
|---------|------|-------------|
| Tavily | Free | $0 |
| SerpAPI | Free (250 searches) | $0 |
| Firecrawl | Hobby | $16 |
| LLM (Claude/GPT) | Pay-per-use | ~$5-20 |
| **Total** | | **~$16-36/month** |

### Chilean Site Strategy

1. **Google Shopping (via SerpAPI)**: Target `google.cl` domain with Spanish queries for broad price overview.
2. **Direct scraping targets**: Falabella.com, Ripley.cl, Paris.cl, MercadoLibre.cl -- these are the dominant Chilean retailers.
3. **MercadoLibre API**: MercadoLibre has a public API that returns structured product data. Use it directly instead of scraping.
4. **Firecrawl for the rest**: Schema-based extraction from Falabella, Ripley, Paris product pages.
5. **Playwright fallback**: For any site that blocks API-based scraping or requires JS interaction.

---

## Sources

- [Tavily Pricing](https://www.tavily.com/pricing)
- [Tavily API Credits Documentation](https://docs.tavily.com/documentation/api-credits)
- [Firecrawl vs Tavily Comparison 2026](https://www.firecrawl.dev/compare/firecrawl-vs-tavily)
- [Firecrawl vs Tavily (Apify analysis)](https://blog.apify.com/firecrawl-vs-tavily/)
- [5 Tavily Alternatives](https://www.firecrawl.dev/blog/tavily-alternatives)
- [LangChain Playwright Toolkit](https://docs.langchain.com/oss/python/integrations/tools/playwright)
- [PlayWrightBrowserToolkit API Reference](https://python.langchain.com/api_reference/community/agent_toolkits/langchain_community.agent_toolkits.playwright.toolkit.PlayWrightBrowserToolkit.html)
- [Browser Automation Agent (LangGraph + Playwright)](https://github.com/leoch95/playwright-browser-agent)
- [Visual Web Agents with LangGraph](https://learnopencv.com/langgraph-building-a-visual-web-browser-agent/)
- [SerpAPI Google Shopping API](https://serpapi.com/google-shopping-api)
- [SerpAPI Price Monitoring](https://serpapi.com/use-cases/price-monitoring)
- [Browser Use (GitHub)](https://github.com/browser-use/browser-use)
- [Browserbase](https://www.browserbase.com/)
- [The Agentic Browser Landscape in 2026](https://nohacks.co/blog/agentic-browser-landscape-2026)
- [Web Scraping Agent with LangGraph + Firecrawl](https://www.firecrawl.dev/blog/web-scraping-agent-langgraph-firecrawl)
- [AI Agent Frameworks 2026: LangGraph vs AutoGen vs CrewAI](https://use-apify.com/blog/ai-agent-frameworks-2026-langgraph-autogen-crewai)
- [Web Scraping Best Practices 2026 (ScrapingBee)](https://www.scrapingbee.com/blog/web-scraping-best-practices/)
- [Playwright Docker (Python)](https://playwright.dev/python/docs/docker)
- [Best Web Search APIs for AI 2026](https://www.firecrawl.dev/blog/best-web-search-apis)
- [Best Browser Agents 2026](https://www.firecrawl.dev/blog/best-browser-agents)
