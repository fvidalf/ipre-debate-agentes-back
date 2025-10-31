
class SearchResult:
    def __init__(self, title: str, url: str, snippet: str, content: str = "", source: str = ""):
        self.title = title
        self.url = url
        self.snippet = snippet
        self.content = content
        self.source = source
    
    def __repr__(self):
        return f"<SearchResult: {self.title[:50]}...>"