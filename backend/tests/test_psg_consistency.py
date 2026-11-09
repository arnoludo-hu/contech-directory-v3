from fastapi.testclient import TestClient
from app.main import app
from app.interpreter import fallback
from app.excel_store import ExcelStore

client=TestClient(app)

def test_verified_phrasings_identical():
    phrasings=['psg-verified solutions','Which vendors have verified PSG-approved solutions?',
               'show currently verified PSG solutions','find official PSG approved products']
    for query in phrasings:
        plan=fallback(query)
        assert len(plan.hard)==1,query
        assert plan.hard[0].any_of[0].field=='psg_current',query
        res=client.post('/api/v1/search',json={'message':query}).json()
        assert res['total_solutions']==0,query
        assert 'historical' in res['message'].lower()

def test_recorded_phrasings_identical():
    for query in ['historical PSG claims','PSG pre-approved solutions','solutions marked PSG Yes']:
        plan=fallback(query)
        assert plan.hard[0].any_of[0].field=='psg_recorded'
        assert len(ExcelStore().filter(plan.hard)[0])==23

def test_psg_followup_replaces_old_psg_filter():
    a=client.post('/api/v1/search',json={'message':'show PSG pre-approved solutions'}).json()
    b=client.post('/api/v1/search',json={'message':'show verified PSG-approved solutions','session_id':a['session_id']}).json()
    assert b['total_solutions']==0
    assert b['applied_filters'][0]['any_of'][0]['field']=='psg_current'
