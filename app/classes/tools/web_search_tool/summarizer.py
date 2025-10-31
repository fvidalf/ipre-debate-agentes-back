from typing import List, Optional
from .search_result import SearchResult
import logging
import dspy

logger = logging.getLogger(__name__)


class WebSearchSummarySignature(dspy.Signature):
    """Summarize web search results into a concise, informative response for research purposes."""
    query: str = dspy.InputField(desc="The original search query that was performed.")
    content: str = dspy.InputField(desc="Combined content from all web search results and AI snippets.")
    sources: str = dspy.InputField(desc="List of source URLs and titles for reference.")

    summary: str = dspy.OutputField(desc="A concise, well-structured summary that directly answers the query using the provided content. Should be informative but significantly shorter than the input content. Less than 1000 characters.")


def aggregate_results(results: List[SearchResult], google_ai_summary: str, google_ai_snippets: List[str], query: str) -> str:
    # logger.info(f"📖 Aggregate: Creating summary for query: '{query}'")
    # logger.info(f"📊 Aggregate: Input data - {len(results)} content results, {len(google_ai_snippets)} AI snippets")
    
    if not results and not google_ai_snippets and not google_ai_summary:
        logger.warning("⚠️ Aggregate: No content available for summarization")
        return f"No results found for query: {query}"

    all_content = []
    source_info = []

    # Add Google AI summary if available
    if google_ai_summary:
        all_content.append(f"Google AI Overview: {google_ai_summary}")

    # Log the actual content we extracted - NO TRUNCATION, let DSPy handle it
    for i, result in enumerate(results, 1):
        if result.content:
            all_content.append(f"Source {i} ({result.source}): {result.content}")
            source_info.append(f"{i}. {result.title} ({result.source}): {result.url}")

    # Add Google AI snippets
    if google_ai_snippets:
        for j, snippet in enumerate(google_ai_snippets, 1):
            all_content.append(f"Google AI Snippet {j}: {snippet}")

    combined_content = "\n\n".join(all_content)
    sources_text = "\n".join(source_info) if source_info else "No sources available"

    # Use DSPy to generate the summary
    summary = generate_dspy_summary(query, combined_content, sources_text)
    
    return summary


def generate_dspy_summary(query: str, content: str, sources: str) -> str:
    """Generate a concise summary using DSPy for intelligent content compression."""
    if not content.strip():
        return "No relevant content found for this search query."
    
    try:
        # Initialize the DSPy predictor
        summarizer = dspy.Predict(WebSearchSummarySignature)
        
        # Generate summary using DSPy
        result = summarizer(
            query=query,
            content=content,
            sources=sources
        )
        
        final_summary = result.summary
        if sources and sources != "No sources available":
            final_summary += f"\n\nSources:\n{sources}"
        
        return final_summary
        
    except Exception as e:
        logger.error(f"❌ DSPy summarization failed: {e}")
        # Fallback to simple truncation if DSPy fails
        return generate_fallback_summary(query, content, sources)


def generate_fallback_summary(query: str, content: str, sources: str) -> str:
    """Fallback summary method if DSPy fails."""
    # Truncate content if too long (keep first 2000 chars for summary)
    truncated_content = content[:2000] + "..." if len(content) > 2000 else content
    
    # Return formatted summary
    summary = f"""Search Query: {query}
Key Information:
{truncated_content}

Sources:
{sources}"""
    
    return summary