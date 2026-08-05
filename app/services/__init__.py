"""
Business logic services. Each maps to a pipeline stage:

  ingestion.py  -> Phase 5: trend collection (RSS / Google Trends)
  calendar.py   -> Phase 5: monthly calendar draft (human checkpoint #1)
  copy.py       -> Phase 3: headline + description variants (human checkpoint #2)
  image.py      -> Phase 4: branded image draft to Drive review folder (checkpoint #3)
"""
