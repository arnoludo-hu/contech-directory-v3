"""Regression tests against the controlled imported funding-stage fields."""
import pytest
from app.interpreter import interpret
from app.excel_store import ExcelStore
from app.excel_api import search
from app.models import SearchRequest

@pytest.fixture(scope='module')
def store():
    return ExcelStore()

@pytest.mark.parametrize('query,expected',[
    ('Which startups are Series A?',set()),
    ('Which startups are Series B?',{'Cupix'}),
    ('Which startups are at Seed?',{'Formas.AI','Wenti Labs'}),
    ('Which startups are Pre-Seed?',set()),
    ('Show Series A or Series B startups',{'Cupix'}),
    ('Show early-stage startups',{'Neuron Factory','Nomic','BIMLOGIQ'}),
])
def test_exact_stage_query(store,query,expected):
    plan=interpret(query)
    assert plan.hard and plan.hard[0].any_of[0].field=='funding_stage'
    rows,unknown,excluded=store.filter(plan.hard)
    assert {r['company'] for r in rows}==expected

def test_missing_stage_not_seed(store):
    unknown=[r for r in store.all() if r['funding_stage'] is None]
    assert len(unknown)>0
    plan=interpret('Which startups are at Seed?')
    rows,_,_=store.filter(plan.hard)
    assert all(r['funding_stage']=='Seed' for r in rows)

def test_raising_series_c_does_not_imply_series_c(store):
    cupix=next(r for r in store.all() if r['company']=='Cupix')
    assert cupix['funding_stage']=='Series B'
    assert 'Series C' in cupix['funding_stage_raw']
    rows,_,_=store.filter(interpret('Which startups are Series C?').hard)
    assert cupix not in rows

def test_company_count_not_semantic_top_k():
    r=search(SearchRequest(message='How many startups are at Seed?',page_size=1))
    assert r.total_companies==2
    assert r.total_solutions==2
    assert len(r.matches)==1

def test_existing_presence_and_psg_not_regressed(store):
    for q in ('Show solutions with local reseller','Show PSG pre-approved solutions'):
        p=interpret(q)
        rows,_,_=store.filter(p.hard)
        assert len(rows)>0
