"""
SCET Metadata Wrapper - Integration Example
============================================
Shows how to integrate the metadata wrapper with existing SCET backend.

This file demonstrates:
1. Basic usage of the wrapper
2. Integration with existing search pipeline
3. Fallback handling
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from metadata_wrapper import get_enriched_metadata, fetch_metadata, MetadataWrapper


def example_basic_usage():
    """
    Basic usage example - get enriched metadata for a title.
    """
    print("=" * 60)
    print("EXAMPLE 1: Basic Usage")
    print("=" * 60)
    
    # Simple usage with get_enriched_metadata
    metadata = get_enriched_metadata("Harry Potter and the Philosopher's Stone")
    
    print(f"\nTitle: {metadata.get('title')}")
    print(f"Creator: {metadata.get('creator')}")
    print(f"Publication Year: {metadata.get('publication_year')}")
    print(f"Content Type: {metadata.get('content_type')}")
    print(f"Source: {metadata.get('source')}")
    print(f"Source URL: {metadata.get('source_url')}")
    print(f"Confidence: {metadata.get('confidence_score')}")
    print(f"Last Verified: {metadata.get('last_verified')}")


def example_with_alternatives():
    """
    Example showing how to get alternatives.
    """
    print("\n" + "=" * 60)
    print("EXAMPLE 2: With Alternatives")
    print("=" * 60)
    
    # Full result with alternatives
    result = fetch_metadata("Romeo and Juliet")
    
    if result.get("success"):
        print(f"\nBest Match:")
        meta = result["metadata"]
        print(f"  Title: {meta.get('title')}")
        print(f"  Creator: {meta.get('creator')}")
        print(f"  Confidence: {meta.get('confidence_score'):.2f}")
        
        if result.get("alternatives"):
            print(f"\nAlternatives ({len(result['alternatives'])}):")
            for i, alt in enumerate(result["alternatives"][:3], 1):
                print(f"  {i}. {alt.get('title')} ({alt.get('source')}) - {alt.get('confidence_score'):.2f}")
    else:
        print(f"No results: {result.get('reason')}")


def example_with_jurisdiction():
    """
    Example with jurisdiction-specific search.
    """
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Jurisdiction-Specific Search")
    print("=" * 60)
    
    # Search with Indian jurisdiction
    result_in = fetch_metadata("Gitanjali", jurisdiction="IN")
    print(f"\nIndian Jurisdiction Search:")
    if result_in.get("success"):
        meta = result_in["metadata"]
        print(f"  Title: {meta.get('title')}")
        print(f"  Source: {meta.get('source')}")
        print(f"  Jurisdiction: {meta.get('jurisdiction', 'N/A')}")
    
    # Search with US jurisdiction
    result_us = fetch_metadata("The Great Gatsby", jurisdiction="US")
    print(f"\nUS Jurisdiction Search:")
    if result_us.get("success"):
        meta = result_us["metadata"]
        print(f"  Title: {meta.get('title')}")
        print(f"  Source: {meta.get('source')}")


def example_integration_with_scet():
    """
    Example showing integration with existing SCET search flow.
    
    Existing flow:
        User Input → SCET Search → Scraper → ML → Result
    
    New flow with wrapper:
        User Input → SCET Search → Metadata Wrapper → Scraper → ML → Result
    """
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Integration with SCET Pipeline")
    print("=" * 60)
    
    def enhanced_scet_search(user_query: str, jurisdiction: str = "US"):
        """
        Enhanced SCET search function with metadata wrapper.
        
        This function shows how to integrate the metadata wrapper
        into the existing SCET search pipeline.
        """
        # Step 1: Get enriched metadata from wrapper
        enriched_metadata = get_enriched_metadata(
            title=user_query,
            jurisdiction=jurisdiction
        )
        
        # Step 2: If metadata found with good confidence, use it
        if enriched_metadata.get("confidence_score", 0) > 0.5:
            print(f"  ✓ Metadata enriched from: {enriched_metadata.get('source')}")
            
            # Step 3: Continue with existing SCET pipeline
            # (This would call your existing scraper/ML code)
            # existing_result = scet_scraper.search(enriched_metadata)
            # ml_result = scet_ml.analyze(existing_result)
            
            return {
                "status": "enriched",
                "metadata": enriched_metadata,
                "ready_for_ml": True
            }
        else:
            print(f"  ✗ Low confidence metadata, using fallback")
            
            # Step 4: Fallback to existing SCET pipeline without enrichment
            return {
                "status": "fallback",
                "metadata": enriched_metadata,
                "ready_for_ml": True
            }
    
    # Test the integration
    print("\nSearching: 'Pride and Prejudice'")
    result = enhanced_scet_search("Pride and Prejudice")
    print(f"  Status: {result['status']}")
    print(f"  Title: {result['metadata'].get('title')}")
    print(f"  Creator: {result['metadata'].get('creator')}")
    print(f"  Year: {result['metadata'].get('publication_year')}")


def example_wrapper_configuration():
    """
    Example showing custom wrapper configuration.
    """
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Custom Configuration")
    print("=" * 60)
    
    # Create wrapper with custom settings
    wrapper = MetadataWrapper(
        timeout=15,      # 15 second timeout per source
        max_workers=3    # 3 concurrent source queries
    )
    
    # Use the configured wrapper
    result = wrapper.fetch_metadata("1984", content_type="book")
    
    if result.get("success"):
        print(f"\nCustom wrapper result:")
        print(f"  Sources checked: {result.get('sources_checked')}")
        print(f"  Title: {result['metadata'].get('title')}")
        print(f"  Creator: {result['metadata'].get('creator')}")


def example_failsafe():
    """
    Example showing failsafe behavior.
    """
    print("\n" + "=" * 60)
    print("EXAMPLE 6: Failsafe Behavior")
    print("=" * 60)
    
    # Even with an unusual query, wrapper returns gracefully
    result = get_enriched_metadata("xyznonexistent12345")
    
    print(f"\nUnusual query result:")
    print(f"  Title: {result.get('title')}")
    print(f"  Confidence: {result.get('confidence_score')}")
    print(f"  Source: {result.get('source')}")
    print("\n  ✓ Wrapper returned gracefully without crashing")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("SCET METADATA WRAPPER - INTEGRATION EXAMPLES")
    print("=" * 60)
    
    try:
        example_basic_usage()
        example_with_alternatives()
        example_with_jurisdiction()
        example_integration_with_scet()
        example_wrapper_configuration()
        example_failsafe()
        
        print("\n" + "=" * 60)
        print("ALL EXAMPLES COMPLETED SUCCESSFULLY")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()
