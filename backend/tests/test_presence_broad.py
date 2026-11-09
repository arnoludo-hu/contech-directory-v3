from app.interpreter import fallback, interpret
from app.excel_store import ExcelStore

def test_local_entity_and_reseller_equivalent():
    store=ExcelStore()
    for query in ('which solutions have local reseller', 'which solutions have local entity', 'show Singapore local presence'):
        plan=interpret(query)
        rows,_,_=store.filter(plan.hard)
        assert len(rows)==51, (query,len(rows))

def test_strict_reseller_does_not_claim_recorded_presence_verified():
    plan=interpret('show verified local reseller solutions')
    assert any(p.field=='singapore_reseller' for g in plan.hard for p in g.any_of)
    rows,_,_=ExcelStore().filter(plan.hard)
    assert len(rows)==0

def test_psg_or_local_reseller_is_union():
    store=ExcelStore()
    plan=interpret('Show PSG pre-approved or Singapore reseller solutions')
    rows,_,_=store.filter(plan.hard)
    expected=[r for r in store.all() if r['psg_recorded'] or r['singapore_presence_recorded']]
    assert {r['solution_id'] for r in rows}=={r['solution_id'] for r in expected}
