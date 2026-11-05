#!/usr/bin/env python3
"""Single executable evidence index across local and external checks.

Pass means observed real service behavior. BLOCKED means unavailable prerequisites.
Never re-label mocked NIM or a fake KWOK pod as production verification.
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'artifacts'


def run(name, command, proof=None, checker=None, env=None):
    if proof:
        (ART/proof).unlink(missing_ok=True)
    try:
        result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=2000,env=env)
        (ART/f'full-check-{name}.log').write_text(result.stdout[-20000:]+'\n===STDERR===\n'+result.stderr[-8000:])
        value=None
        if proof and (ART/proof).is_file():
            value=json.loads((ART/proof).read_text())
        good=result.returncode==0 and (checker(value) if checker else True)
        status='VERIFIED' if good else ('BLOCKED' if isinstance(value, dict) and value.get('status')=='BLOCKED' else 'FAILED')
        return {"status":status, "proof":str(ART/proof) if value is not None else None,
                "return_code":result.returncode, "log":f'artifacts/full-check-{name}.log'}
    except (Exception) as exc:
        return {'status':'FAILED','reason':f'{type(exc).__name__}: {str(exc)[:250]}'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--local-only',action='store_true',help='Only run self-contained local validation')
    p.add_argument('--strict',action='store_true',help='Fail unless every requested platform is verified')
    args=p.parse_args()
    ART.mkdir(exist_ok=True)
    report={'generated_at':datetime.now(timezone.utc).isoformat(),'host_scope':'local host plus separately authenticated remote services','requested_scope':'offline_only' if args.local_only else 'all_integrations','checks':{}}
    report['checks']['offline']=run('offline',['bash','scripts/verify_local.sh'],'requirements-traceability.json',lambda r: bool(r and r.get('offline_gate_passed')))
    if not args.local_only:
        # The audit removes prior evidence and preflights each external service.
        profile=run('external',['python','scripts/audit_integrations.py'],'integration-audit.json',lambda r:bool(r and r.get('failed',0)==0))
        if profile['status']=='VERIFIED':
            audit=json.loads((ART/'integration-audit.json').read_text())
            report['checks'].update(audit['checks'])
        else: report['checks']['external_audit']=profile
        report['checks']['github_actions']=run('github_actions',['python','scripts/verify_github_actions.py'],'github-actions-report.json',lambda r: bool(r and r.get('verified')))
        report['checks']['human_qa_productivity']=run('human_qa_productivity',['python','scripts/productivity_experiment.py'],'qa-productivity-report.json',lambda r:bool(r and r.get('paired_tasks',0)>=4)) if (ART/'productivity-observations.csv').is_file() else {'status':'BLOCKED','reason':'Collect real paired manual/AI QA task timings; use make productivity-template'}
    def passed(value):return value.get('status')=='VERIFIED'
    report['verified_count']=sum(passed(x) for x in report['checks'].values())
    report['all_requested_verified']=bool(report['checks']) and all(passed(x) for x in report['checks'].values())
    report['all_nine_areas_verified']=not args.local_only and report['all_requested_verified']
    (ART/'FULL_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    if report['checks']['offline']['status']!='VERIFIED' or (args.strict and not report['all_requested_verified']):sys.exit(1)

if __name__=='__main__':main()
