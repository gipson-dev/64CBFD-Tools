"""Observe frozen baseline/selected overlay allocation without installing code."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from unittest.mock import patch

from tools.experiments import game_view_overlay_pass as source
from tools.experiments import game_text_measurer_uopt_trace as qualified
from tools.tests import view_overlay_checkpoint as checkpoint
from tools.experiments import game_view_overlay_match as matched

BUILD='conker/build/game-view-overlay-uopt-trace'


def procedure_block(text):
    first='IN LOCAL OPTIMIZATION OF '+source.FUNCTION
    last='IN REEMISSION OF '+source.FUNCTION
    if text.count(first)!=1 or text.count(last)!=1:raise ValueError('Missing/duplicate view-overlay trace procedure')
    start=text.index(first);end=text.index(last,start)+len(last)
    return text[start:end]


def live_inputs(root):
    return {key:hashlib.sha256((root/source.PATHS[key]).read_bytes()).hexdigest()
        for key in ('elf','dispatch_owner','guards')}


def trace_owner(root,mode=6,variant='baseline'):
    if variant not in ('baseline','selected'):raise ValueError('Unknown view-overlay trace variant')
    live=live_inputs(root)
    frozen=root/source.BUILD/'after-dispatch_owner'
    if hashlib.sha256(frozen.read_bytes()).hexdigest()!=checkpoint.AFTER['dispatch_owner']:
        raise ValueError('Changed frozen view-overlay trace source')
    content=frozen.read_text()
    if variant=='selected':content=matched.recovered_owner(content)
    expected=source if variant=='baseline' else matched
    def compile_baseline(root,work,name,body):
        if body!=content:raise ValueError('Unexpected view-overlay trace source')
        obj,diag=source.build.compile_owner(root,work,body,name)
        expected.checked_object(obj)
        return dict(owner=source.OWNER,function=source.FUNCTION,flags=['-O2','-g3'],
            raw_sha256=expected.RAW_SHA256,diagnostics=diag),None
    with patch.object(qualified.screen,'compile_candidate',compile_baseline),patch.dict(
            qualified.screen.PROFILES,owner=('-O2','-g3')):
        name=variant+'-mode-'+str(mode)
        result=qualified.trace_uopt(root,root/BUILD,name,content,mode)
    if live_inputs(root)!=live:raise ValueError('View-overlay trace changed live inputs')
    log=(root/BUILD/name/'debugger.txt').read_text()
    if log.splitlines().count('Allocate diagnostic stream buffer')!=1 or 'Suppress diagnostic real-number printer' not in log:
        raise ValueError('View-overlay UOPT diagnostic probe did not fire')
    result.update(installable=False,variant=variant,live_inputs_unchanged=live)
    block=procedure_block((root/BUILD/name/'uoptlist').read_text())
    variables=qualified.variable_expressions(block)
    view=[v for v in variables if v['storage']=='P' and v['offset']==4]
    if len(view)!=1:raise ValueError('Missing/ambiguous full-view UOPT variable')
    result.update(view_variable=view[0],constraints=qualified.allocation_constraints(block) if mode==5 else [],
        integer_scale_nodes=re.findall(r'^.*isop\s+(?:umpy|ushl|usub).*$',block,re.M))
    (root/BUILD/name/'trace.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',type=int,choices=qualified.MODES,default=6)
    parser.add_argument('--variant',choices=('baseline','selected'),default='baseline')
    args=parser.parse_args()
    result=trace_owner(Path(__file__).resolve().parents[2],args.mode,args.variant)
    print(json.dumps({key:result[key] for key in ('variant','mode','code_unchanged','bytes',
        'trace_sha256','source_sha256','view_variable','installable')},indent=2))


if __name__=='__main__':main()
