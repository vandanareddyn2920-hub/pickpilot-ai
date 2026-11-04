# Validation record

Built and executed November 4, 2026. All data is fictional.

- Automated validation: 16 tests passed, including Streamlit AppTest across all five views and a fake-client API integration test.
- Exactly 10,000 primary operational records, 2,400 extra training scenarios; foreign keys checked with SQLite.
- Four demo SQL questions execute against actual tables/view.
- Mutations, chained statements, training-table reads, schema reads, extension calls and write-capable CTEs rejected. Long recursive query interrupted; result rows capped.
- Temporal ML split: train through September 30; October 7 purged; test October 14–28. Twelve training weeks, three test weeks. Fixed random seed.
- Risk output contains all 150 SKUs with scores in [0,1]. Metrics are saved in model-validation.json.
- Ten slotting moves target unique unoccupied bins, fit 1,000-unit capacity, and reduce modeled one-way distance.
- Route heuristic falls back to bin-code baseline if needed; therefore its modeled distance is no worse. This does not prove an optimal or executable route.
- Streamlit browser walkthrough covers all five views, query execution and chart/table rendering; screenshots are from the running app; demo.html presents them as a tour.
- Live OpenAI call not executed: no API key was supplied. API request wiring is checked with a fake client; no claim of live free-form answer accuracy.

Acceptance is technical prototype behavior. Real-world stockout prevention, user adoption, pick productivity and financial impact remain unvalidated.
