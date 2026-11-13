
"""Conservative capability eligibility for specific operational discovery queries.

Only fields describing a product's use case/capability can establish eligibility.
Generic words such as 'digital' and vendor names never establish digital twins.
"""
import re

TWIN = re.compile(r'\b(?:digital[\s_-]*twin(?:s)?|operational[\s_-]*twin(?:s)?|asset[\s_-]*twin(?:s)?)\b', re.I)
FM = re.compile(r'\b(?:facilit(?:y|ies)\s+management|facility\s+operations|building\s+operations|building\s+management|asset\s+management|fm|bms|maintenance)\b', re.I)

def specific_intent(query: str):
    q=query.lower()
    if TWIN.search(q):
        return 'fm_digital_twin' if FM.search(q) else 'digital_twin'
    return None

def capability_text(row):
    return ' '.join(str(x or '') for x in (
        row.get('summary'), row.get('source_use_cases'), row.get('source_technology'),
        *row.get('use_cases',[]), *row.get('technologies',[])
    ))

def eligible(row, intent: str):
    text=capability_text(row)
    if intent in ('digital_twin','fm_digital_twin'):
        if not TWIN.search(text): return False
        if intent == 'fm_digital_twin' and not FM.search(text): return False
    return True
