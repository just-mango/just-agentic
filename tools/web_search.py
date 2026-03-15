from langchain_core.tools import tool


@tool
def web_search(query: str) -> str:
    """Search the web using DuckDuckGo and return top results.

    Use for: looking up documentation, searching error messages, finding examples.
    Returns up to 5 results with title, URL, and snippet.
    """
    try:
        from duckduckgo_search import DDGS

        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=5):
                results.append(
                    f"Title: {r.get('title', '')}\n"
                    f"URL: {r.get('href', '')}\n"
                    f"Snippet: {r.get('body', '')}\n"
                )
        if not results:
            return "No results found."
        return "\n---\n".join(results)
    except ImportError:
        return "ERROR: duckduckgo-search not installed. Run: pip install duckduckgo-search"
    except Exception as e:
        return f"ERROR: {e}"
