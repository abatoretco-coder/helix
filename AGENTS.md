# Helix product-quality instructions

Helix is an intelligence product, not a feed reader.  Every change to
collection, extraction, enrichment, clustering, briefing or Jarvis delivery
must preserve these non-negotiable conditions:

1. A public result must contain a source-backed fact, not merely a headline,
   teaser, product description or clickbait wording.
2. Sponsored, affiliate, retail, coupon, price-drop and buying-guide content
   must be rejected before Ollama and must not reappear through a legacy row,
   search result, dashboard cache or briefing.
3. An article record must retain its URL, source, publication date, extracted
   text and a concise factual summary.  Summaries state the event, actors,
   location/date or quantified fact when available, and supported impact;
   they must not invent missing facts.
4. A synthesis groups corroborating coverage of the same event and attributes
   its sources.  It never concatenates titles as if that were analysis.
5. Before declaring work complete, run an end-to-end sample using real
   extracted articles, inspect the human-readable result, and report the
   acceptance evidence.  Compilation or a mocked response alone is not an
   acceptance test.

When quality is insufficient, prefer an empty result with an explicit reason
over low-value output.  Do not mass-reprocess history without an explicit,
bounded plan and user approval.
