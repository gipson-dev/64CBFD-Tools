"""Observe the fade allocator's real native costs and compare flags, without edits."""
import argparse
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_dual_fade_argument_home as home
from tools.experiments import game_text_measurer_uopt_trace as trace

BUILD='conker/build/game-dual-fade-allocation-choice'
ADDRESSES=(0x47fe70,0x4353c0,0x481500,0x481503)
ORIGINAL_SCRIPT=trace.debugger_script
PROBES=r'''
import json
def reg(name): return int(gdb.parse_and_eval('$'+name))
def word(base, at): return int.from_bytes(gdb.selected_inferior().read_memory(base+at,4),'little')
def byte(base, at): return int.from_bytes(gdb.selected_inferior().read_memory(base+(at^3),1),'little')
def emit(kind, **row): gdb.write('FADE_CHOICE '+json.dumps(dict(kind=kind,**row))+'\n')
def selected(base, lr):
    ic=word(base,lr)
    location=word(base,ic+0x14)
    # This prepared 5.3 binary packs block/memtype/level as 16/8/8 bits.
    return byte(base,ic)==3 and word(base,ic+0x10) in (0,0xfffffff4) and location>>16==882
class GlobalEnd(gdb.FinishBreakpoint):
    def __init__(self,base):
        super().__init__(internal=True);self.base=base
    def stop(self):
        for lr in sorted(targets): emit('final',lr=lr,color=byte(self.base,lr+0x20))
        targets.clear()
        return False
class GlobalStart(gdb.Breakpoint):
    def stop(self):
        GlobalEnd(reg('rdi'))
        return False
class CupEnd(gdb.FinishBreakpoint):
    def __init__(self,row):
        super().__init__(internal=True);self.row=row
    def stop(self):
        emit('cost',**self.row,cost_bits=word(0,0x4b0b00))
        return False
class CupStart(gdb.Breakpoint):
    def stop(self):
        base=reg('rdi');lr=reg('esi')
        if selected(base,lr):
            targets.add(lr);ic=word(base,lr)
            emit('identity',lr=lr,ichain=ic,header=word(base,ic),identity=word(base,ic+4),
                 location=word(base,ic+0x14),offset=word(base,ic+0x10),
                 first_use_bits=word(0,0x4b0ab0),static_nodes=word(base,0x1001c904))
            CupEnd(dict(lr=lr,reg=reg('edx'),caller=reg('ecx')))
        return False
class Compare(gdb.Breakpoint):
    def stop(self):
        base=reg('r14');lr=reg('ebp')
        if selected(base,lr) and reg('r13d')==14:
            emit('compare',lr=lr,reg=reg('r13d'),at=reg('pc'),
                 cost_bits=reg('xmm0.v4_int32[0]')&0xffffffff,
                 best_bits=reg('xmm1.v4_int32[0]')&0xffffffff,flags=reg('eflags'))
        return False
targets=set()
def install_choice():
    GlobalStart('*0x47fe70',internal=True)
    CupStart('*0x4353c0',internal=True)
    Compare('*0x481500',internal=True)
    Compare('*0x481503',internal=True)
'''


def debugger_script(root):
    text=ORIGINAL_SCRIPT(root)
    old='python\ndef trace_exit(event):'
    if text.count(old)!=1:raise ValueError('Unknown owned debugger preamble')
    text=text.replace(old,'python\n'+PROBES+'\ndef trace_exit(event):',1)
    old="    gdb.execute('set follow-fork-mode parent')"
    if text.count(old)!=1:raise ValueError('Unknown owned exec gate')
    text=text.replace(old,"    install_choice()\n"+old,1)
    old="('*0x422830', '*0x484590')"
    if text.count(old)!=1:raise ValueError('Unknown owned cleanup gate')
    return text.replace(old,str(tuple('*0x%x'%n for n in (0x422830,0x484590,*ADDRESSES))),1)


def events(text):
    try:return [json.loads(line[len('FADE_CHOICE '):]) for line in text.splitlines() if line.startswith('FADE_CHOICE ')]
    except (ValueError,TypeError) as exc:raise ValueError('Malformed native choice event') from exc


def qualify_events(rows,listing,label):
    if label not in ('normal','home'):raise ValueError('Unknown allocation source')
    scoped=home.allocation_procedure(listing)
    variables={v['identity']:v for v in trace.variable_expressions(scoped) if v['procedure']==882}
    constraints=trace.allocation_constraints(scoped)
    expected_roles=('record','weight') if label=='normal' else ('weight',)
    specifications=dict(record=(0x03000008,1589<<16,(882<<16)|0x202,0,14),
                        weight=(0x03060000,373<<16,(882<<16)|0x102,0xfffffff4,8))
    grouped={role:[] for role in expected_roles};pointers={};ichains={}
    for row in rows:
        if not isinstance(row,dict) or row.get('kind') not in ('identity','cost','compare','final'):
            raise ValueError('Unknown native allocation event')
        lr=row.get('lr')
        if row['kind']=='identity':
            matches=[role for role in expected_roles if tuple(row.get(k) for k in ('header','identity','location','offset'))==specifications[role][:4]]
            if len(matches)!=1:raise ValueError('Unknown native procedure/variable identity')
            role=matches[0]
            if lr in pointers and pointers[lr]!=role:raise ValueError('Reused native live-range pointer')
            if role in ichains and ichains[role]!=(lr,row.get('ichain')):raise ValueError('Changed native variable pointer')
            pointers[lr]=role;ichains[role]=(lr,row.get('ichain'))
        if lr not in pointers:raise ValueError('Native event before its scoped identity')
        grouped[pointers[lr]].append(row)
    roles={}
    for role,group in grouped.items():
        header,identity,location,offset,color=specifications[role]
        var=variables.get(str(identity>>16)+'|0')
        if var is None or (var['storage'],var['offset'],var['expression'],var['virtual_register'])!=(
                'P' if role=='record' else 'M',0 if role=='record' else -12,header&0xffff,True):
            raise ValueError('Native identity disagrees with mode5 variable table')
        final=[c for c in constraints if (c['identity'],c['expression'])==(var['identity'],var['expression'])]
        if not final or final[-1]['color']!=color:raise ValueError('Native final color disagrees with mode5')
        comparison=role=='record' or label=='home'
        if (14 in final[-1]['forbidden'])!=(role=='weight' and label=='normal'):
            raise ValueError('Unexpected color14 availability')
        expected=[];normalized=[]
        lr,ic=ichains.get(role,(None,None))
        if not isinstance(lr,int) or not isinstance(ic,int) or not lr or not ic:
            raise ValueError('Missing live native variable')
        for reg,caller,bits in ((2,1,0x60ad78ec if role=='record' else 0x40000000),
                               (13,1,0x60ad78ec if role=='record' else 0x40000000),
                               (14,0,0x3dcccccd if role=='record' else 0)):
            expected.extend([dict(kind='identity',header=header,identity=identity,location=location,offset=offset,
                                  first_use_bits=0x40800000,static_nodes=13),
                             dict(kind='cost',reg=reg,caller=caller,cost_bits=bits)])
        comps=[]
        if comparison:
            cost,best=(0x40833333,0x60ad78ec) if role=='record' else (0x40800000,0x40000000)
            for at in (0x481500,0x481503):
                comp=dict(at=at,cost_bits=cost,best_bits=best)
                if at==0x481503:comp.update(cf=int(role=='weight'),pf=0,zf=0)
                expected.append(dict(kind='compare',reg=14,**comp));comps.append(comp)
        expected.append(dict(kind='final',color=color))
        for row in group:
            r=dict(row);r.pop('lr');r.pop('ichain',None)
            if r['kind']=='compare':
                flags=r.pop('flags',None)
                if not isinstance(flags,int):raise ValueError('Missing native comparison flags')
                if r['at']==0x481503:r.update(cf=flags&1,pf=(flags>>2)&1,zf=(flags>>6)&1)
            normalized.append(r)
        if normalized!=expected:raise ValueError('Missing, duplicate or changed native allocation witness')
        roles[role]=dict(color=color,first_use_bits=0x40800000,comparisons=comps,
                         costs=[r for r in expected if r['kind']=='cost'])
    return roles


def observe(root,out,label):
    if label not in ('normal','home'):raise ValueError('Unknown allocation source')
    if trace.compiler_fingerprints(root)!=trace.COMPILERS:raise ValueError('Prepared compiler fingerprint mismatch')
    home.freeze(root,out)
    body=home.previous.SELECTED if label=='normal' else home.SELECTED
    with patch.object(trace,'debugger_script',debugger_script),patch.object(trace,'screen',home.compiler_screen(root,out)):
        record=trace.trace_uopt(root,out,label,body,5)
    expected=home.previous.RAW_SHA if label=='normal' else home.RAW_SHA
    if record['baseline']['target_sha256']!=expected:raise ValueError('Changed allocation candidate')
    work=out/label;log=(work/'debugger.txt').read_text()
    if log.splitlines().count('Allocate diagnostic stream buffer')!=1 or 'Suppress diagnostic real-number printer' not in log:
        raise ValueError('Required diagnostic gates did not fire')
    roles=qualify_events(events(log),(work/'uoptlist').read_text(),label)
    home.freeze(root,out)
    result=dict(roles=roles,code_unchanged=record['code_unchanged'],baseline=record['baseline'],
        source_flags=['-O2','-g3'],installable=False,native_debugger_bits_not_suppressed_prints=True,
        debugger_log_sha256=hashlib.sha256(log.encode()).hexdigest())
    (work/'choice.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',choices=('normal','home'),default='home');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    print(json.dumps(observe(root,root/BUILD,args.source),indent=2),flush=True)
