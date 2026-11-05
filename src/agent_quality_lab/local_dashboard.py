"""Built-in offline observability view. Not a Prometheus server or Grafana replacement.

Reads only local generated artifacts; external integration verification is never inferred
from the presence of configuration files or successful mock HTTP contract tests.
"""
from __future__ import annotations
import json
import os
from pathlib import Path

EXTERNAL = ('docker', 'kind', 'ollama', 'nim', 'nemo', 'kwok', 'gpu')


def _report(root: Path, name: str) -> dict:
    path = root / name
    try:
        result = json.loads(path.read_text(encoding='utf-8'))
        return result if isinstance(result, dict) else {}
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}


def collect_evidence() -> dict:
    root = Path(os.getenv('AQ_ARTIFACT_DIR', 'artifacts'))
    offline = _report(root, 'local-demo-report.json')
    eval_report = _report(root, 'eval-report.json')
    advanced = _report(root, 'advanced-report.json')
    mutations = _report(root, 'mutation-report.json')
    traceability = _report(root, 'requirements-traceability.json')
    perf = _report(root, 'slo-gate-report.json')
    synthetic = _report(root, 'local-scheduling-simulation.json')
    policy = _report(root, 'local-policy-fixtures.json')
    external_audit = _report(root, 'integration-audit.json').get('checks', {})
    platforms = {}
    for item in EXTERNAL:
        state = external_audit.get(item, {}) if isinstance(external_audit, dict) else {}
        status = state.get('status', 'NOT_VERIFIED')
        # Preflight means only prerequisites exist; it never means the service ran.
        if status not in {'VERIFIED', 'BLOCKED', 'FAILED', 'READY_NOT_RUN'}:
            status = 'NOT_VERIFIED'
        platforms[item] = {'status': status, 'reason': state.get('reason', 'Live integration not executed on this host')}
    gh = _report(root, 'github-actions-report.json')
    productivity = _report(root, 'qa-productivity-report.json')
    platforms['github_actions'] = {'status': 'VERIFIED' if gh.get('verified') is True else 'NOT_VERIFIED',
                                    'reason': 'Requires a successful remote workflow for the exact pushed commit'}
    platforms['human_productivity'] = {'status': 'VERIFIED' if productivity.get('paired_tasks', 0) >= 4 and productivity.get('evidence') == 'USER_RECORDED_PAIRED_TASK_TIMINGS' else 'NOT_VERIFIED',
                                        'reason': 'Requires actual paired human QA task measurements'}
    summary = {
        'scope': 'Real local Python evaluation and synthetic simulations, NOT accelerator NIM/GPU or Grafana proof',
        'local_gate': 'VERIFIED_OFFLINE' if offline.get('overall') == 'VERIFIED_OFFLINE' else 'NOT_RUN',
        'golden': eval_report.get('summary', {}),
        'advanced': advanced.get('summary', {}),
        'mutations': {'detected': mutations.get('full_detected'), 'total': mutations.get('total_mutations')},
        'traceability': {'passed': traceability.get('offline_tests_passed'), 'tracked': traceability.get('requirements_tracked'),
                         'gate_passed': traceability.get('offline_gate_passed', False)},
        'slo': {'passed': perf.get('passed'), 'metrics': perf.get('observed', {})},
        'local_guardrail_fixture': {'passed': policy.get('passed'), 'total': policy.get('total'), 'scope': policy.get('scope')},
        'local_scheduler': {'passed': synthetic.get('passed'), 'rescheduled_pods': synthetic.get('rescheduled_pods'), 'scope': synthetic.get('scope')},
        'platforms': platforms,
    }
    return summary


HTML = r'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agent Quality | Local Dashboard</title><style>
:root{font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#eaf1fa;background:#0c1424;font-synthesis:none}
*{box-sizing:border-box}body{margin:0}main{max-width:1200px;margin:auto;padding:34px 24px 70px}.top{display:flex;align-items:center;justify-content:space-between;gap:15px;flex-wrap:wrap;margin-bottom:36px}
.brand{letter-spacing:.15em;font-size:12px;font-weight:800;color:#7fa7d5}.chip{border:1px solid #354a64;background:#16253a;border-radius:999px;font-size:12px;padding:8px 14px;color:#a9c4df}
h1{font-size:clamp(29px,4vw,48px);letter-spacing:-.04em;margin:0 0 12px}h2{font-size:19px;letter-spacing:-.015em;margin:0 0 20px}.sub{color:#98a9bf;max-width:740px;line-height:1.65;margin:0 0 32px}
.card{background:#142236;border:1px solid #293d54;border-radius:16px;padding:22px;box-shadow:0 4px 18px #0002}.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:0 0 30px}.metric-label{font-size:12px;color:#a1b5c9;margin-bottom:14px}.metric-value{font-size:34px;font-weight:750;letter-spacing:-.03em}.metric-note{font-size:11px;color:#7792af;margin-top:8px}
.pill{display:inline-block;border-radius:20px;padding:5px 9px;font-size:11px;font-weight:750;letter-spacing:.04em}.ok{background:#164a3b;color:#7ce3b1}.warn{background:#483718;color:#f6cb7f}.bad{background:#542638;color:#ff9db0}.muted{background:#26364a;color:#b7cadf}
.table{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.platform{border:1px solid #2b425a;padding:15px;border-radius:12px;background:#101c2d}.platform-head{display:flex;align-items:center;justify-content:space-between;gap:12px;font-weight:650;font-size:13px}.platform small{display:block;color:#8197ae;line-height:1.5;margin-top:10px;min-height:32px}.row{display:grid;grid-template-columns:1.2fr .8fr;gap:20px;margin-top:24px}.row > .card{min-width:0}
label{display:block;font-size:12px;font-weight:650;color:#aec3d8;margin-bottom:9px}textarea{width:100%;min-height:90px;padding:13px;background:#0a1525;border:1px solid #38516c;border-radius:10px;color:#eaf3fc;font:inherit;resize:vertical}button{cursor:pointer;border:0;border-radius:9px;background:#7dcbb0;padding:12px 18px;font-weight:750;color:#0d2430;margin-top:13px}button:hover{background:#9fe8cf}pre{margin:16px 0 0;background:#0a1525;color:#bcebd8;padding:13px;border-radius:10px;overflow:auto;font-size:12px;line-height:1.6;max-height:280px;white-space:pre-wrap}code{color:#a4d6bf}.note{font-size:13px;color:#94acc2;line-height:1.65}footer{color:#718ba5;margin-top:34px;font-size:12px}
@media(max-width:950px){.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.table{grid-template-columns:repeat(2,minmax(0,1fr))}.row{grid-template-columns:1fr}}@media(max-width:560px){.table,.metrics{grid-template-columns:1fr}main{padding:25px 16px}}
</style></head><body><main><header class="top"><div class="brand">AGENTIC QUALITY / RELIABILITY LAB</div><span class="chip">LOCAL-FIRST · NO CLOUD REQUIRED</span></header>
<h1>Local Quality Dashboard</h1><p class="sub">Real Python agent QA evidence, an interactive incident triage endpoint, and honest platform verification status. This is a built-in local dashboard, <strong>not Grafana</strong>. Prometheus exposition is available at <code>/metrics</code>.</p>
<div id="stats" class="metrics"><div class="card">Loading evidence…</div></div>
<section class="card"><h2>Integration evidence</h2><p class="note">Only actual executions count as verified. Mocked NIM/Ollama, local policy checks, and virtual scheduling do not establish accelerator SDK/GPU/Kubernetes execution.</p><div id="platforms" class="table"></div></section>
<div class="row"><section class="card"><h2>Try the agent</h2><label for="prompt">Synthetic incident</label><textarea id="prompt">The database query failed and customers cannot sign in.</textarea><button id="run">Run local triage</button><pre id="output">Enter a synthetic issue and run the agent.</pre></section>
<section class="card"><h2>Local evidence</h2><div id="details" class="note">Loading…</div><p class="note">To refresh all reports, run <code>make demo-check</code> in your Terminal. The core demo uses deterministic inference by default and does not silently claim model execution.</p><p class="note">For full independent dashboards, Kubernetes, and real LLMs, optional original integrations remain in the repository.</p></section></div>
<footer>Portfolio engineering demonstration using synthetic incidents and controlled faults. No production customer access, accelerator ownership or GPU performance is implied.</footer></main>
<script>
const el=id=>document.getElementById(id); const stateLabel=s=>s==='VERIFIED'?'Verified':s==='BLOCKED'?'Blocked':s==='FAILED'?'Failed':s==='READY_NOT_RUN'?'Ready, not run':'Not verified';
function pill(s){const span=document.createElement('span');span.className='pill '+(s==='VERIFIED'?'ok':s==='FAILED'?'bad':s==='BLOCKED'?'warn':'muted');span.textContent=stateLabel(s);return span;}
function stat(label,value,note){const c=document.createElement('div');c.className='card';const l=document.createElement('div');l.className='metric-label';l.textContent=label;const v=document.createElement('div');v.className='metric-value';v.textContent=value;const n=document.createElement('div');n.className='metric-note';n.textContent=note;c.append(l,v,n);return c;}
async function refresh(){try{const r=await fetch('/api/evidence',{cache:'no-store'});if(!r.ok)throw Error('HTTP '+r.status);const d=await r.json();el('stats').replaceChildren(stat('Golden evaluation',d.golden.passed==null?'—':d.golden.passed+'/'+d.golden.total,'Deterministic baseline · not LLM inference'),stat('Advanced evaluation',d.advanced.passed==null?'—':d.advanced.passed+'/'+d.advanced.cases,'Adversarial / repeat checks'),stat('Requirement traces',d.traceability.passed==null?'—':d.traceability.passed+'/'+d.traceability.tracked,'Mapped to executed pytest results'),stat('Local suite',d.local_gate==='VERIFIED_OFFLINE'?'PASS':'NOT RUN','Re-run: make demo-check'));
const plats=el('platforms');plats.replaceChildren();const names={docker:'Docker + Grafana + Prometheus',kind:'Kubernetes kind',ollama:'Ollama real model',nim:'accelerator NIM',nemo:'NeMo Guardrails SDK',kwok:'KWOK cluster',gpu:'accelerator GPU / CUDA',github_actions:'GitHub Actions remote',human_productivity:'Human QA productivity'};for(const [key,obj] of Object.entries(d.platforms)){const c=document.createElement('div');c.className='platform';const h=document.createElement('div');h.className='platform-head';const n=document.createElement('span');n.textContent=names[key]||key;h.append(n,pill(obj.status));const more=document.createElement('small');more.textContent=obj.reason||'';c.append(h,more);plats.appendChild(c);}
el('details').textContent=`Offline guardrail fixtures: ${d.local_guardrail_fixture.passed??'—'}/${d.local_guardrail_fixture.total??'—'} (not NeMo SDK)\n\nVirtual node-loss scheduling: ${d.local_scheduler.passed===true?'PASS':'NOT RUN'} (not KWOK)\n\nSLO gate: ${d.slo.passed===true?'PASS':d.slo.passed===false?'FAIL':'NOT RUN'}\n\naccelerator GPU and real AI productivity remain unverified until actual evidence is collected.`;
}catch(e){el('stats').textContent='Evidence unavailable: '+e.message;}}
el('run').onclick=async()=>{el('output').textContent='Running…';try{const r=await fetch('/api/triage',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({incident_id:'LOCAL-DEMO',message:el('prompt').value})});const j=await r.json();el('output').textContent=JSON.stringify(j,null,2)}catch(e){el('output').textContent='Request failed: '+e.message}};refresh();setInterval(refresh,12000);
</script></body></html>'''
