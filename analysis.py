"""Offline analysis of independently verified REAL responses. No simulated data."""
import argparse
import importlib.util
import json
from collections import Counter
from pathlib import Path
from common import ROOT
from verify import verify_run

def source(name):
    path=ROOT/('sources/gpt-5.4-shrt-prerequisite-'+name+'-analysis/analysis.py')
    spec=importlib.util.spec_from_file_location(name+'_statistics',path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def analyze(folder):
    evidence=verify_run(folder)
    rows=evidence.pop('rows')
    report={'verification':evidence,'studies':{},'mixed_script_outputs':[r for r in rows if r['class']=='MX']}
    for study,cells in [('gate','ABCD'),('reassignment','EFGH')]:
        stats=source(study)
        counts={c:Counter(r['class'] for r in rows if r['cell']==c) for c in cells}
        totals={c:sum(counts[c].values()) for c in cells}
        ys=[counts[c]['V0']+counts[c]['V2'] for c in cells]
        ns=[totals[c] for c in cells]
        classes=['T1','T0','GEMINI_ORIGINAL','HE','SHART','SHAMS','MX','OT','V0','V2','V1','VU','SAFETY','REFUSAL','TOOL','ERROR']
        out={'endpoint':'NSTOP = V0 + V2','counts':{c:{k:counts[c][k] for k in classes} for c in cells},'recorded':totals,'cell_wilson95':{c:{k:stats.wilson_interval(counts[c][k],totals[c]) for k in classes} for c in cells},'decision':'INCONCLUSIVE'}
        report['studies'][study]=out
        if all(ns):
            out['I_rule' if study=='gate' else 'I_reassign']=-ys[0]/ns[0]+ys[1]/ns[1]+ys[2]/ns[2]-ys[3]/ns[3]
            out['directional_contrasts']=[ys[1]/ns[1]-ys[0]/ns[0],ys[2]/ns[2]-ys[3]/ns[3]]
        if evidence['phase']=='pilot':
            out['decision']='DESCRIPTIVE ONLY' if evidence['status']=='PASS' else 'INCONCLUSIVE'
            continue
        if evidence['status']!='PASS' or ns!=[200]*4:
            continue
        try:
            # Source functions label their generic binary outcome V0. Here their
            # input counts are explicitly NSTOP; no source evidence is changed.
            firth=stats.firth_interaction(ys,ns)
            firth['model']=firth['model'].replace('V0','NSTOP')
            primary=stats.interaction_estimate(ys,ns,stats.V0_SIGNS) if study=='gate' else stats.interaction_estimate(ys,ns)
            out.update(firth=firth,primary=primary)
            if study=='gate':
                supported=primary['interaction']>0 and firth['profile_ci95'][0]>0
            else:
                adapted={c:Counter({'V0':y}) for c,y in zip(cells,ys)}
                tests=stats.pairwise_tests(adapted,totals)
                for t in tests['tests']:
                    t['outcome']='NSTOP'
                out['stratified_tests']=tests
                supported=(primary['interaction']>0 and all(v['estimate']>0 and v['ci95'][0]>0 for v in primary['contrasts'].values()) and all(t['p_holm_family2']<.05 for t in tests['tests']) and firth['profile_ci95'][1]<0 and firth['p_two_sided']<.05)
            out['decision']='SUPPORTED' if supported else 'NOT SUPPORTED'
        except (ArithmeticError,ValueError) as exc:
            out['statistical_error']=str(exc)
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('run',type=Path)
    print(json.dumps(analyze(parser.parse_args().run),ensure_ascii=False,indent=2,allow_nan=False))
