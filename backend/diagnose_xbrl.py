import sys
sys.path.insert(0, '.')

from app.config import get_settings
from edgar import Company, set_identity
from edgar.xbrl import XBRL

settings = get_settings()
set_identity(settings.sec_user_agent)

company = Company('0000320193')
filings = company.get_filings(form='10-K')
filing = filings.latest(1)
filing = filing[0] if isinstance(filing, list) else filing
xbrl = XBRL.from_filing(filing)

facts = xbrl.facts

# Test get_facts_by_concept
result = facts.get_facts_by_concept('NetIncomeLoss')
print('get_facts_by_concept type:', type(result))

import pandas as pd
if isinstance(result, pd.DataFrame):
    print('columns:', list(result.columns))
    print('shape:', result.shape)
    print('head:')
    print(result.head(3).to_string())
else:
    print('not a DataFrame, dir:', [x for x in dir(result) if not x.startswith('_')])
