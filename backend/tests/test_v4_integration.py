from fastapi.testclient import TestClient
from app.main import app
from app.excel_store import ExcelStore
from app.interpreter import fallback

client=TestClient(app)

def test_v4_record_count():
    assert len(ExcelStore().all())==107

def test_recorded_psg():
    p=fallback('Show PSG pre-approved solutions')
    yes,_,_=ExcelStore().filter(p.hard)
    assert len(yes)==23 and all(r['psg_recorded'] for r in yes)

def test_current_psg_is_unknown():
    p=fallback('Show currently verified PSG solutions')
    yes,unknown,_=ExcelStore().filter(p.hard)
    assert not yes and len(unknown)==107

def test_recorded_sg_presence():
    p=fallback('Show solutions with Singapore local presence')
    yes,_,_=ExcelStore().filter(p.hard)
    assert len(yes)==51

def test_reseller_broad_discovery():
    p=fallback('Show solutions with Singapore reseller')
    yes,_,_=ExcelStore().filter(p.hard)
    assert len(yes)==51

def test_psg_or_reseller():
    p=fallback('Show PSG pre-approved or Singapore reseller solutions')
    assert any(len(g.any_of)==2 for g in p.hard)
    yes,_,_=ExcelStore().filter(p.hard)
    assert len(yes)==max(23, len(yes))
    assert len(yes)==len({r['solution_id'] for r in yes})

def test_geo_or_excludes_sg():
    p=fallback('Show solutions from Australia or the US')
    yes,_,_=ExcelStore().filter(p.hard)
    assert yes and all(r['origin_country'] in ('AU','US') for r in yes)

def test_list_all_paginates():
    a=client.post('/api/v1/search',json={'message':'List all solutions','page_size':10})
    assert a.status_code==200 and a.json()['total_solutions']==107
    sid=a.json()['session_id']
    b=client.get(f'/api/v1/sessions/{sid}/results?page=2&page_size=10')
    assert b.status_code==200
    assert set(x['solution_id'] for x in a.json()['matches']).isdisjoint(x['solution_id'] for x in b.json()['matches'])

def test_api_psg_count():
    a=client.post('/api/v1/search',json={'message':'Show PSG pre-approved solutions','page_size':100})
    assert a.status_code==200 and a.json()['total_solutions']==23

def test_api_verified_zero():
    a=client.post('/api/v1/search',json={'message':'Show currently verified PSG solutions'})
    assert a.status_code==200 and a.json()['total_solutions']==0
