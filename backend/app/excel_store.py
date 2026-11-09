"""Read-only Excel v4 adapter. Imported claims are searchable, not verified facts."""
from __future__ import annotations
import os,re,threading
from pathlib import Path
from openpyxl import load_workbook
from difflib import SequenceMatcher

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_FILE=ROOT/'ConTech_Public_Staging_v4.xlsx'
COUNTRY_NAMES={'SG':'Singapore','US':'United States','AU':'Australia','JP':'Japan','GB':'United Kingdom','CN':'China','MY':'Malaysia','IN':'India','DE':'Germany','FR':'France','KR':'South Korea','HK':'Hong Kong','CA':'Canada','NZ':'New Zealand','ES':'Spain'}
def clean(v):
    if v is None:return None
    s=str(v).strip()
    return s if s and s.lower() not in ('none','nan','#n/a','n/a') else None
def code(s):return re.sub(r'[^a-z0-9]+','_',str(s or '').lower()).strip('_')
def yes(v):return str(v or '').strip().lower() in ('yes','true','pre-approved','pre approved')
def read_sheet(wb,name):
    it=iter(wb[name].values);headers=[str(x).strip() for x in next(it)]
    return [dict(zip(headers,row)) for row in it if any(x is not None for x in row)]
def split_tags(s):return list(dict.fromkeys(t.strip() for t in str(s or '').split(';') if t.strip()))

class ExcelStore:
    def __init__(self,path=None):
        self.path=Path(path or os.getenv('CONTECH_EXCEL_PATH') or DEFAULT_FILE)
        self.lock=threading.RLock();self.stamp=None;self.rows=[];self.by_id={};self.tax={}
        self.refresh()
    def refresh(self):
        with self.lock:
            if not self.path.exists():raise FileNotFoundError(f'Excel database missing: {self.path}')
            stamp=self.path.stat().st_mtime_ns
            if self.stamp==stamp:return
            wb=load_workbook(self.path,read_only=True,data_only=True)
            try:
                needed={'Companies','Solutions','Solution_Taxonomy','SG_Presence','PSG_Verification','Search_Flags'}
                missing=needed-set(wb.sheetnames)
                if missing:raise ValueError(f'Expected v4 workbook; missing worksheets: {sorted(missing)}')
                companies={str(r['Company_ID']):r for r in read_sheet(wb,'Companies')}
                funding_by_company={str(r['Company_ID']):r for r in read_sheet(wb,'Funding_Stages')} if 'Funding_Stages' in wb.sheetnames else {}
                pres={str(r['Company_ID']):r for r in read_sheet(wb,'SG_Presence')}
                psg={str(r['Solution_ID']):r for r in read_sheet(wb,'PSG_Verification')}
                flags={str(r['Solution_ID']):r for r in read_sheet(wb,'Search_Flags')}
                tags={}
                for r in read_sheet(wb,'Solution_Taxonomy'):
                    sid=str(r['Solution_ID']); typ=str(r.get('Mapping_Type') or '').lower()
                    key='technologies' if typ=='technology' else 'use_cases' if typ=='use case' else None
                    if key and clean(r.get('Tag')):tags.setdefault(sid,{'technologies':[],'use_cases':[]})[key].append(str(r['Tag']))
                rows=[]
                for s in read_sheet(wb,'Solutions'):
                    sid=str(s['Solution_ID']);cid=str(s['Company_ID']);c=companies.get(cid)
                    if not c:continue
                    p=pres.get(cid,{});g=psg.get(sid,{});f=flags.get(sid,{})
                    funding=funding_by_company.get(cid,{})
                    funding_stage=clean(funding.get('Funding_Stage_Normalized')) or clean(c.get('Funding_Stage_Recorded'))
                    origin=clean(c.get('Origin_Country_Code'))
                    origin=origin.upper() if origin and len(origin)==2 else None
                    tech=list(dict.fromkeys(tags.get(sid,{}).get('technologies',[]) or split_tags(s.get('Technology_Tags_Imported'))))
                    uses=list(dict.fromkeys(tags.get(sid,{}).get('use_cases',[]) or split_tags(s.get('Use_Case_Tags_Imported'))))
                    url=clean(s.get('Website')) or clean(c.get('Website'))
                    if url and not url.startswith(('https://','http://')):url=None
                    recorded_presence=yes(f.get('SG_Entity_Or_Reseller_Recorded'))
                    recorded_reseller=yes(f.get('SG_Reseller_Recorded'))
                    recorded_psg=yes(f.get('PSG_Recorded_Preapproval'))
                    current_psg=yes(f.get('PSG_Current_Verified')) and str(g.get('Current_PSG_Status') or '').lower()=='verified'
                    rows.append({
                        'solution_id':sid,'company_id':cid,'company':str(c['Company_Name']),'solution':str(s['Solution_Name']),
                        'summary':clean(s.get('Source_Description_Excerpt')) or '',
                        'origin_country':origin,'origin_label':COUNTRY_NAMES.get(origin,origin),
                        'headquarters_country':clean(c.get('HQ_Country_Code')),
                        'funding_stage':funding_stage,'funding_stage_raw':clean(funding.get('Funding_Stage_Raw')) or clean(c.get('Funding_Stage_Raw')),
                        'funding_stage_verification':'imported_unverified' if funding_stage else 'unknown',
                        'product_url':url,'company_website':url,'material_ai_description':None,'maturity':'unknown',
                        'technologies':tech,'use_cases':uses,'customer_segments':[],
                        'source_category':clean(s.get('Technology_Tags_Imported')),
                        'source_use_cases':clean(s.get('Use_Case_Tags_Imported')),
                        'source_technology':clean(s.get('Technology_Tags_Imported')),
                        'source_urls':[url] if url else [],
                        'singapore_entity':None,'singapore_reseller':None,'singapore_support':None,
                        'singapore_presence':None,
                        'singapore_presence_recorded':recorded_presence,
                        'singapore_reseller_recorded':recorded_reseller,
                        'psg_recorded':recorded_psg,'psg_current':True if current_psg else None,
                        'psg_status':'verified' if current_psg else 'recorded_preapproval' if recorded_psg else 'unknown','psg_verified_at':None,
                        'price_tier':None,'publication_status':'staging','ai_eligibility':'pending_verification',
                        'source_references':clean(s.get('Source_References')),
                        'local_presence_claim':clean(p.get('Historical_Presence_Raw')),
                        'historical_psg_claim':clean(g.get('Historical_PSG_Claim')),
                        'recorded_presence_type':clean(p.get('Recorded_Presence_Type')),
                        'verified_source_urls':[]
                    })
                self.rows=rows;self.by_id={r['solution_id']:r for r in rows}
                self.tax={
                    'technologies':[{'code':code(r['Technology']),'label':str(r['Technology'])} for r in read_sheet(wb,'Technology_Taxonomy') if clean(r.get('Technology'))],
                    'use_cases':[{'code':code(r['Use_Case']),'label':str(r['Use_Case'])} for r in read_sheet(wb,'Use_Case_Taxonomy') if clean(r.get('Use_Case'))],
                    'countries':[{'code':c,'label':COUNTRY_NAMES.get(c,c)} for c in sorted({r['origin_country'] for r in rows if r['origin_country']})],
                    'customer_segments':[],
                    'funding_stages':[{'code':code(v),'label':v} for v in sorted({r['funding_stage'] for r in rows if r['funding_stage']})]}
                self.stamp=stamp
            finally:wb.close()
    def all(self):self.refresh();return list(self.rows)
    def get(self,sid):self.refresh();return self.by_id.get(sid)
    def taxonomy(self):self.refresh();return self.tax

    @staticmethod
    def matches(row,predicate):
        f=predicate.field;op=predicate.op;values=predicate.values
        value=row.get(f)
        if f=='technology':value=row['technologies']
        elif f=='use_case':value=row['use_cases']
        elif f=='customer_segment':value=row['customer_segments']
        elif f=='funding_stage':value=row.get('funding_stage')
        if f=='company_name':value=row['company']
        elif f=='solution_name':value=row['solution']
        if value is None or value==[]:return None
        fields=value if isinstance(value,list) else [value]
        normalized=[code(v) for v in fields]
        targets=[code(v) for v in values]
        if f=='use_case':normalized += [code(row.get('source_use_cases'))]
        if f=='technology':normalized += [code(row.get('source_category'))]
        # Controlled category aliases, matching imported taxonomy names without asserting verified capability.
        aliases={
          'progress_monitoring':['progress_monitoring','digital_progress_monitoring','ai_enabled_site_monitoring','site_progress'],
          'quality_inspection':['quality_inspection','quality_and_inspection','defect','inspection'],
          'safety_monitoring':['safety_monitoring','site_safety','video_analytics'],
          'generative_design':['generative_design','feasibility_design','visualisation_and_design','design_optimisation'],
          'quantity_takeoff':['quantity_takeoff','quantity_take_off','automated_takeoff'],
          'facilities_management':['facilities_management','facility_management','predictive_maintenance'],
          'computer_vision':['computer_vision','video_analytics','image_analytics'],
          'robotics':['robotics','robotic'],
        }
        def equivalent(a,b):
            if a==b:return True
            if f not in ('technology','use_case'):return False
            variants=aliases.get(b,[b])
            return any(x in a or a in x for x in variants if len(x)>4)
        equal=any(equivalent(a,b) for a in normalized for b in targets)
        contained=any(b in a for a in normalized for b in targets)
        if op in ('eq','in'):return equal
        if op=='contains':return contained
        if op=='not_in':return not equal
        if op=='not_contains':return not contained
        return False

    def filter(self,groups):
        confirmed=[];unknown=[];excluded=[]
        for r in self.all():
            unknown_fields=[];failed=[]
            for group in groups:
                vals=[self.matches(r,p) for p in group.any_of]
                if True in vals:continue
                if None in vals:unknown_fields += [p.field for p,v in zip(group.any_of,vals) if v is None]
                else:failed += [p.field for p in group.any_of]
            if failed:excluded.append((r,failed))
            elif unknown_fields:unknown.append((r,sorted(set(unknown_fields))))
            else:confirmed.append(r)
        return confirmed,unknown,excluded
