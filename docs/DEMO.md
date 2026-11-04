# PickPilot: 90-second demo

The accompanying `demo.html` is an interactive screenshot tour of the running app. Open it locally; use the arrows or Play tour. It is a screenshot walkthrough, not a screen recording. Use this script to record a narrated portfolio demo.

**0–15 seconds · Problem and overview**
“Warehouse supervisors need to spot risk without digging through exports. PickPilot uses 10,000 synthetic WMS-style records to show available stock, replenishment risk and picking exceptions in one desk.” Point to the metrics and replenishment watchlist.

**15–35 seconds · Inventory question**
Open Ask inventory. Run “Which SKUs have less than 7 days of cover?” Show the SQL, returned rows, and CSV download. “This recording uses fixed demo queries. Live mode connects a language model to the same read-only execution boundary. The model generates SQL; SQLite provides the answer.”

**35–55 seconds · Stockout risk**
Open Stockout risk. Change the threshold and category. “A random forest uses available stock, observed demand, lead time and inbound to score seven-day synthetic stockout scenarios. Supervisors can export a review list. These are synthetic estimates, not proven operational predictions.”

**55–75 seconds · Picking workflow**
Open Slotting & routes. “These moves use vacant nearer bins with adequate capacity. This route compares bin order against a distance heuristic. Savings are modeled; this route visits both storage bins for illustration and is not an executable pick plan.”

**75–90 seconds · Validation and next step**
Open Validation. “A future-period holdout, a purged cutoff, and baseline comparison check model behavior. Automated tests check data integrity and SQL restrictions. The next step is a supervisor pilot with reconciled stock history and an inbound feed.”
