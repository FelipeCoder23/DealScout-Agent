# DealScout-Agent Spec

## Description
An autonomous agent that monitors prices and offers for specific products (like a PS5) across multiple e-commerce platforms and compares them to find the best deals.

## MVP Features
-   **Product Search:** Ability to search for a specific product name.
-   **Price Comparison:** Scrape prices from top e-commerce sites (e.g., Amazon, Mercado Libre, local retailers).
-   **Offer Alerts:** Notify when a product hits a target price (optional).
-   **Comparison Table:** Output a clean list of prices, sellers, and links.

## Proposed Stack
-   **Language:** Python 3.11+
-   **Framework:** FastAPI (for any API/UI) or CLI-first.
-   **Agent/Scraping:** LangGraph + Playwright / BeautifulSoup.
-   **Data Validation:** Pydantic.
-   **Testing:** Pytest.

## Structure
-   `src/`: Main logic.
-   `tests/`: Unit and integration tests.
-   `docs/`: Documentation.

