'use client';
import {useEffect,useRef,useState} from 'react';import {ArrowRight,Search,Building2,Camera,HardHat,ShieldCheck,Loader2} from 'lucide-react';import {api,searchRequest,type Match,type SearchResponse} from '../lib/api';
const examples=['Which AI startups are based in Singapore?','Find computer vision solutions for construction progress monitoring.','Show overseas solutions with a local Singapore reseller.','which vendors have PSG pre-approved solutions'];
const challenges=[{icon:Camera,title:'Monitor site progress',query:'Find AI solutions for construction progress monitoring',desc:'Track site progress and compare with plans'},{icon:HardHat,title:'Improve site safety',query:'Find AI tools for construction site safety monitoring',desc:'Identify risks and unsafe behaviours'},{icon:Building2,title:'Improve facility operations',query:'Find AI solutions for predictive building maintenance',desc:'Predict faults and optimise maintenance'}];
function readableStatus(value:string|undefined){if(!value||value==='unknown')return 'Not confirmed';return value.replaceAll('_',' ')}
const sleep = (ms: number) => new Promise<void>(resolve => setTimeout(resolve, ms));

async function waitForBackend(): Promise<void> {
  // One health request can take time while Render wakes a sleeping service.
  for (let attempt = 0; attempt < 4; attempt++) {
    try {
      const response = await fetch(`/api/backend-status?t=${Date.now()}`, {
        cache: 'no-store',
        signal: AbortSignal.timeout(85000),
      });
      if (response.ok) {
        const status = await response.json();
        if (status.ready === true) return;
      }
    } catch {
      // A transient gateway error can occur during cold start.
    }
    if (attempt < 3) await sleep(4000);
  }
  throw new Error('The search service is still starting. Please try again shortly.');
}

function isExpiredSession(error: unknown): boolean {
  const message = error instanceof Error ? error.message : String(error);
  return /\b(404|410)\b|session.*(not found|expired|invalid)/i.test(message);
}

export default function Home() {
  const [query,setQuery] = useState('');
  const [data,setData] = useState<SearchResponse|null>(null);
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState('');
  const [messages,setMessages] = useState<{role:'user'|'assistant';text:string}[]>([]);
  const [backendChecking,setBackendChecking] = useState(true);
  const [backendReady,setBackendReady] = useState(false);
  const [serviceMessage,setServiceMessage] = useState('Starting search service...');
  const [retryCount,setRetryCount] = useState(0);
  const busyRef = useRef(false);

  useEffect(() => {
    let active = true;
    setBackendChecking(true);
    setServiceMessage('Starting search service...');
    void waitForBackend().then(() => {
      if (active) { setBackendReady(true); setBackendChecking(false); }
    }).catch(() => {
      if (active) { setBackendReady(false); setBackendChecking(false); }
    });
    return () => { active = false; };
  }, [retryCount]);

  async function run(text: string, page = 1, continueSession = true) {
    if (!text.trim() || busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    setError('');
    setServiceMessage('Checking search service...');
    try {
      await waitForBackend();
      setBackendReady(true);
      setBackendChecking(false);
      setServiceMessage('Searching solutions...');
      const sessionId = continueSession ? data?.session_id : undefined;
      let response: SearchResponse;
      try {
        response = await searchRequest(text, sessionId, page, 10);
      } catch (firstError) {
        // An in-memory FastAPI session may disappear after Render restarts.
        // Do not replay arbitrary failed POST requests automatically.
        if (sessionId && isExpiredSession(firstError)) {
          setError('The previous conversation session may have expired after the server restarted. Select "Start a new search" to retry without the old session.');
          return;
        }
        throw firstError;
      }
      setData(response);
      if (page === 1) {
        setMessages(old => [...old,
          {role:'user',text},
          {role:'assistant',text:response.clarification || response.message || `${response.total_solutions} matching solutions`}
        ]);
      }
      setQuery('');
    } catch (e) {
      setBackendReady(false);
      setError(e instanceof Error ? e.message : 'Unable to search. Please retry.');
    } finally {
      busyRef.current = false;
      setBusy(false);
      setServiceMessage('');
    }
