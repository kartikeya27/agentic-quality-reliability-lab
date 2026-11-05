#!/usr/bin/env python3
"""Verify real GitHub Actions jobs for the local Git HEAD; no inferred success.

Requires `gh auth login`, a pushed commit, and a completed green workflow.
"""
import argparse
import json
import shutil
import subprocess
from datetime import datetime,timezone
from pathlib import Path


def command(*args):
    r=subprocess.run(args,capture_output=True,text=True,timeout=30)
    if r.returncode: raise RuntimeError(f"{' '.join(args[:3])}: {r.stderr.strip()[:240]}")
    return r.stdout.strip()


def check(repo=None):
    if not shutil.which('gh'): raise RuntimeError('GitHub CLI missing: brew install gh')
    try: command('gh','auth','status')
    except RuntimeError as e: raise RuntimeError('Sign in with gh auth login') from e
    sha=command('git','rev-parse','HEAD')
    origin=command('git','remote','get-url','origin')
    if not repo:
        repo=command('gh','repo','view','--json','nameWithOwner','-q','.nameWithOwner')
    base=f'repos/{repo}'
    raw=command('gh','api',f'{base}/actions/workflows/quality.yml/runs','-X','GET','-f','per_page=100')
    runs=json.loads(raw).get('workflow_runs',[])
    matches=[r for r in runs if r.get('head_sha')==sha and r.get('event') in ('push','pull_request','workflow_dispatch')]
    if not matches: raise RuntimeError('No workflow run for local HEAD; push and await completed Actions')
    run=max(matches,key=lambda x:x['id'])
    jobs=json.loads(command('gh','api',f'{base}/actions/runs/{run["id"]}/jobs','-X','GET','-f','per_page=100')).get('jobs',[])
    names={j.get('name',''):j.get('conclusion') for j in jobs}
    relevant={name:state for name,state in names.items() if any(key in name for key in ('deterministic agent QA', 'Real container', 'Actual Kubernetes'))}
    all_three=len([k for k in relevant if 'deterministic agent QA' in k])>=3 and any('Real container' in k for k in relevant) and any('Actual Kubernetes' in k for k in relevant)
    verified=bool(all_three and all(v=='success' for v in relevant.values()) and run.get('conclusion')=='success' and run.get('status')=='completed')
    return {"checked_at":datetime.now(timezone.utc).isoformat(),"repository":repo,"origin":origin,"commit":sha,
            "run_id":run['id'],"run_url":run.get('html_url'),"status":run.get('status'),"conclusion":run.get('conclusion'),"jobs":relevant,"verified":verified}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',help='owner/repository if gh cannot infer it')
    p.add_argument('--out',default='artifacts/github-actions-report.json')
    args=p.parse_args()
    try: result=check(args.repo)
    except (RuntimeError,ValueError,KeyError,subprocess.TimeoutExpired) as e:
        result={'verified':False,'status':'BLOCKED','reason':str(e)}
    out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    if not result['verified']:raise SystemExit(1)

if __name__=='__main__': main()
