'use client';
import {useEffect,useMemo,useState} from 'react';import Link from 'next/link';import {ArrowRight,Search,Building2,Camera,HardHat,ShieldCheck,Loader2} from 'lucide-react';import {api,searchRequest,type Match,type SearchResponse} from '../lib/api';
const examples=['Which AI startups are based in Singapore?','Find computer vision solutions for construction progress monitoring.','Show overseas solutions with a local Singapore reseller.','which vendors have PSG pre-approved solutions'];
const challenges=[{icon:Camera,title:'Monitor site progress',query:'Find AI solutions for construction progress monitoring',desc:'Track site progress and compare with plans'},{icon:HardHat,title:'Improve site safety',query:'Find AI tools for construction site safety monitoring',desc:'Identify risks and unsafe behaviours'},{icon:Building2,title:'Improve facility operations',query:'Find AI solutions for predictive building maintenance',desc:'Predict faults and optimise maintenance'}];
function plainExplanation(m:Match):string {
  // Only describe evidence supplied by the backend. No invented capabilities.
  const useful=(m.reasons||[]).filter(x=>!/(imported|not independently verified|provisional|workbook|candidate found|score)/i.test(x));
  if(useful.length) return useful.slice(0,2).join(' ').trim();
  const categories=[...(m.use_cases||[]),...(m.technologies||[])].filter(Boolean);
  if(categories.length) return Listed in the directory under ${categories.slice(0,3).join(', ')}. Review the solution profile to assess its suitability.;
  return 'This solution was returned by the directory search. Its detailed capabilities have not yet been documented.';
}
function readableStatus(value:string|undefined){if(!value||value==='unknown')return 'Not confirmed';return value.replaceAll('_',' ')}
export default function Home(){const [query,setQuery]=useState('');const [data,setData]=useState<SearchResponse|null>(null);const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [messages,setMessages]=useState<{role:'user'|'assistant';text:string}[]>([]);const [lastMessage,setLastMessage]=useState('');

const [backendReady, setBackendReady] = useState(false);
const [backendChecking, setBackendChecking] = useState(true);
const [retryCount, setRetryCount] = useState(0);

useEffect(() => {
  let cancelled = false;
  const controller = new AbortController();

  async function wakeBackend() {
    setBackendChecking(true);
    setBackendReady(false);

    // Allow time for Render Free to wake the backend.
    for (let attempt = 1; attempt <= 3; attempt++) {
      if (cancelled) return;

      try {
        const response = await fetch("/api/backend-status", {
          cache: "no-store",
          signal: controller.signal
        });

        if (response.ok) {
          const result = await response.json();

          if (result.ready === true) {
            if (!cancelled) {
              setBackendReady(true);
              setBackendChecking(false);
            }
            return;
          }
        }
      } catch {
        // Retry if the backend is still starting.
      }

      if (attempt < 3) {
        await new Promise(resolve => setTimeout(resolve, 3000));
      }
    }

    if (!cancelled) {
      setBackendReady(false);
      setBackendChecking(false);
    }
  }

  void wakeBackend();

  return () => {
    cancelled = true;
    controller.abort();
  };
}, [retryCount]);
                     
                               
async function run(text:string,page=1,continueSession=true){
  if(!text.trim() || !backendReady || backendChecking)return;setBusy(true);setError('');try{const response=await searchRequest(text,continueSession?data?.session_id:undefined,page,10);setData(response);setLastMessage(text);if(page===1){setMessages(old=>[...old,{role:'user',text},{role:'assistant',text:response.clarification||response.message||${response.total_solutions} matching solutions}]);}}catch(e){setError(e instanceof Error?e.message:'Unable to search')}finally{setBusy(false)}}
async function changePage(page:number){if(!data)return;setBusy(true);setError('');try{const result=await api<SearchResponse>('/v1/sessions/'+encodeURIComponent(data.session_id)+'/results?page='+page+'&page_size=10');setData(result)}catch(e){setError(e instanceof Error?e.message:'Unable to load page')}finally{setBusy(false)}}
function submit(e:React.FormEvent){e.preventDefault();void run(query);setQuery('')}
return <main className="container">
{backendChecking && (
  <div className="status" role="status">
    <Loader2 size={16} />
    Starting search service... This may take up to a minute.
  </div>
)}

{!backendChecking && !backendReady && (
  <div className="status error" role="alert">
    Search service is temporarily unavailable.
    <button
      type="button"
      className="button secondary"
      style={{ marginLeft: 12 }}
      onClick={() => setRetryCount(n => n + 1)}
    >
      Retry connection
    </button>
  </div>
)}
<section className="hero"><h1>Find the right technology for your built environment challenge.</h1><form className="searchbox" onSubmit={submit}><Search color="#63798c"/><input aria-label="Describe your challenge" value={query} onChange={e=>setQuery(e.target.value)} placeholder="e.g. I need AI to monitor progress across construction sites"/><button className="button" disabled={busy || backendChecking || !backendReady || !query.trim()}>{busy?<Loader2 size={16}/>:<ArrowRight size={16}/>} Find solutions</button></form><div className="chips">{examples.map(e=><button key={e} className="chip" disabled={!backendReady || backendChecking || busy}
onClick={()=>void run(e)}>{e}</button>)}</div></section>
{!data&&<section className="section"><h2>What would you like to improve?</h2><div className="challenge-grid">{challenges.map(({icon:Icon,...c})=><button key={c.title} className="challenge" disabled={!backendReady || backendChecking || busy}
onClick={()=>void run(c.query)}><Icon size={24}/><strong>{c.title}</strong><span>{c.desc}</span></button>)}</div></section>}
<section className="section workspace refined-workspace"><div className="results-column"><div className="panel"><div className="flex space"><h2 style={{margin:0}}>Conversation</h2></div>{messages.length===0?<p className="muted">Your conversation will appear here. Ask a question or select an example above.</p>:<div className="chat-log" aria-live="polite">{messages.slice(-8).map((m,i)=><div className={'bubble '+(m.role==='user'?'user':'')} key={i}>{m.text}</div>)}</div>}{data?.clarification&&<div className="status">Clarification: {data.clarification}</div>}<form className="searchbox" style={{margin:'15px 0 0',boxShadow:'none'}} onSubmit={submit}><input aria-label="Follow-up question" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Ask a follow-up, e.g. only those with local support"/><button className="button" disabled={busy || backendChecking || !backendReady || !query.trim()}>Send</button></form></div>
{error&&<div className="status error" role="alert">{error}</div>}
<div className="section"><div className="flex space"><div><h2 style={{marginBottom:2}}>Matching solutions</h2><span className="muted small">{data?${data.total_solutions} solutions from ${data.total_companies} companies:'Search to see results from the connected database'}</span></div></div>
{data?.matches.map(m=><article className="result-card refined-card" key={m.solution_id}><div className="result-head"><div><div className="small muted">{m.company}</div><h3>{m.solution}</h3></div></div><div className="divider"/><div className="result-facts"><span><strong>Country:</strong> {m.origin_label||m.origin_country||'Not specified'}</span><span><strong>Use case:</strong> {m.use_cases?.join(', ')||'Not specified'}</span><span><strong>Technology:</strong> {m.technologies?.join(', ')||'Not specified'}</span><span><strong>PSG:</strong> {readableStatus(m.psg_status)}</span><span><strong>Singapore presence:</strong> {readableStatus(m.singapore_presence_status)}</span></div><div className="flex">{m.source_urls.slice(0,2).map((u,i)=><a className="link small" key={i} href={u} target="_blank" rel="noopener noreferrer">Vendor website {i+1} ↗</a>)}</div></article>)}
{data&&data.matches.length===0&&<div className="empty"><ShieldCheck size={24}/><h3>No confirmed matches</h3><p>Try removing a mandatory filter or ask for clearly labelled alternatives. Unknown attributes are never treated as verified.</p></div>}{!data&&<div className="empty">Search for solutions using the box above.</div>}
{data&&data.total_solutions>data.page*data.page_size&&<button className="button secondary" disabled={busy} onClick={()=>void changePage(data.page+1)}>Next page →</button>}{data&&data.page>1&&<button className="button secondary" style={{marginLeft:8}} disabled={busy} onClick={()=>void changePage(data.page-1)}>← Previous</button>}
</div></div></section>
</main>
);
}
