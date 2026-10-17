"""Observe burst image reservations before and after global register coloring."""
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_owner_burst_uopt_local_trace as local

BUILD='conker/build/game-owner-burst-allocation-stages'
BASE_DEBUGGER=local.debugger_script
STAGES=(('local-entry',0x434130),('spill-entry',0x450490),('global-entry',0x47FE70),
    ('global-return',0x436060),('reemit-entry',0x448A80))
PROBES=r'''
stage_probes=[]
def burst_stage(event,mem):
    table=burst_u32(mem,0x1001CC30)
    pointer=burst_u32(mem,0x1001CBE4)
    mask=burst_u32(mem,pointer) if pointer else None
    nodes=[]
    for bit in (4,30,31):
        node=burst_u32(mem,table+bit*8)
        live=burst_u32(mem,table+bit*8+4)
        words=[burst_u32(mem,node+i*4) for i in range(10)]
        row=dict(bit=bit,node=node,words=words,live=live,
            selected=None if mask is None else bool(mask & (1<<(31-bit))))
        if live:
            row.update(live_image=burst_u32(mem,live),live_bit=burst_u32(mem,live+4),
                assigned_word=burst_u32(mem,live+0x20),forbidden=[burst_u32(mem,live+0x28),burst_u32(mem,live+0x2C)])
        nodes.append(row)
    gdb.write('BURST_STAGE '+json.dumps(dict(event=event,host_pc=int(gdb.parse_and_eval('$pc')),
        cursor=burst_u32(mem,0x1001C4B4),table=table,selector=pointer,selector_word=mask,nodes=nodes))+'\n')
class BurstStage(gdb.Breakpoint):
    def __init__(self,name,address):
        self.name=name
        super().__init__('*%d'%address,internal=True)
    def stop(self):
        burst_stage(self.name,int(gdb.parse_and_eval('$rdi')))
        return False
def stage_removed(event):
    if event.inferior.progspace.filename==str(compiler_dir/'uopt'):
        for probe in stage_probes:
            if probe.is_valid():probe.delete()
        gdb.write('BURST_STAGE_REMOVED '+json.dumps(dict(probes=len(stage_probes),exit_code=getattr(event,'exit_code','unknown')))+'\n')
gdb.events.exited.connect(stage_removed)
'''


def debugger_script(original,root,work):
    script=BASE_DEBUGGER(original,root,work)
    anchor='class BurstLocalChanged(gdb.Breakpoint):'
    install="    burst_probes.extend((BurstCursorBegin('f_readuinstr.constprop.0'),BurstSpillBegin('f_spilltemps',internal=True)))"
    if script.count(anchor)!=1 or script.count(install)!=1:raise ValueError('Changed local trace adapter anchors')
    script=script.replace(anchor,PROBES+'\n'+anchor)
    return script.replace(install,install+'\n    stage_probes.extend(BurstStage(name,address) for name,address in '+repr(STAGES)+')')


def facts(record,log,wire,words):
    rows=[json.loads(line[12:]) for line in log.splitlines() if line.startswith('BURST_STAGE ')]
    if [r.get('event') for r in rows]!=[name for name,_ in STAGES]:raise ValueError('Incomplete allocation-stage observations')
    removed=[json.loads(line[20:]) for line in log.splitlines() if line.startswith('BURST_STAGE_REMOVED ')]
    if removed!=[dict(probes=5,exit_code=0)]:raise ValueError('Incomplete allocation-stage cleanup')
    lines=log.splitlines();positions=[i for i,s in enumerate(lines) if s.startswith('BURST_STAGE ')]
    start=next(i for i,s in enumerate(lines) if s.startswith('FRAME_INPUT ') and json.loads(s[12:])['stage']=='uopt')
    finish=lines.index('TRACE_EXIT inferior=3 code=0');cleanup=next(i for i,s in enumerate(lines) if s.startswith('BURST_STAGE_REMOVED '))
    consumer=next(i for i,s in enumerate(lines) if s.startswith('FRAME_INPUT ') and json.loads(s[12:])['stage']=='ugen')
    if not start<positions[0]<positions[-1]<finish<cleanup<consumer:raise ValueError('Wrong allocation-stage child ordering')
    local_bytes=record['layout']['frontend_local_bytes'];allocations=record['events'][3:6]
    expected_nodes=[r['node'] for r in allocations];expected_live=None
    for index,(row,(_,pc)) in enumerate(zip(rows,STAGES)):
        if (row['host_pc']!=pc or row['cursor']!=local_bytes+(12 if index>=2 else 0)
                or row['selector_word']!=0x08000003 or [n['bit'] for n in row['nodes']]!=[4,30,31]
                or [n['node'] for n in row['nodes']]!=expected_nodes
                or row['table']!=rows[0]['table'] or row['selector']!=rows[0]['selector']):
            raise ValueError('Changed allocation-stage selector/cursor/identities')
        live=[n['live'] for n in row['nodes']]
        if expected_live is None:expected_live=live
        if live!=expected_live or len(set(live))!=3 or any(not v or v%4 for v in live):
            raise ValueError('Changed allocation-stage live-range identities')
        for j,node in enumerate(row['nodes']):
            baseline=allocations[j]['node_words'];now=node['words']
            if (node['selected'] is not True or node['live_image']!=node['node'] or node['live_bit']!=node['bit']
                    or node['words'][0]&65535!=node['bit']
                    or any(now[i]!=baseline[i] for i in range(10) if i!=8)
                    or now[8]!=(allocations[j]['descriptor'] if index>=2 else 0)
                    or node['assigned_word']>>24!=([14,2,1][j] if index>=3 else 0)):
                raise ValueError('Changed allocation-stage image/color/descriptor binding')
    optimized=wire['records']['optimizer']
    def reg(r,name,kind,value):return r['name']==name and r['storage']=='R' and r['dtype']==kind and r['offset']==value
    address=sum(reg(a,'lod','A',19) and b['name']=='ldc' and b['constants'][0]==40 and c['name']=='add' and reg(d,'str','A',16)
        for a,b,c,d in zip(optimized,optimized[1:],optimized[2:],optimized[3:]))
    state=sum(reg(a,'lod','A',17) and b['name']=='ilod' and b['words'][1]==0x222 and b['length']==1
        and reg(c,'str','L',3) and reg(d,'lod','L',3) and e['name']=='cvt' and reg(f,'str','J',2)
        for a,b,c,d,e,f in zip(optimized,optimized[1:],optimized[2:],optimized[3:],optimized[4:],optimized[5:]))
    if address!=1 or state!=1 or words.count(0x26700028)!=1 or 0x92230222 not in words or words.count(0x00601025)!=1:
        raise ValueError('Global colors do not agree with output wire/machine roles')
    return dict(stages=5,selector_bits=[4,30,31],colors_before_global=[0,0,0],
        colors_after_global=[14,2,1],output_GPRs=[16,3,2],reserved_bytes_before_global=12,
        reserved_bytes_after_global=12,output_wire_and_machine_roles_equal=True,
        no_actual_spill_or_original_allocator_claim=True,installable=False,matching_credit=0)


def trace(root,out,form='aligned-pairs'):
    with patch.object(local,'debugger_script',debugger_script):record=local.trace(root,out,form)
    work=out/form;log=(work/'debugger.txt').read_text()
    events=[json.loads(line[12:]) for line in log.splitlines() if line.startswith('BURST_STAGE ')]
    if not events:raise ValueError('No burst allocation-stage probe fired')
    words=list(struct.unpack_from('>288I',local.frame.source.projection.sections(work/'baseline-linked.elf')['.text'][1]))
    measured=facts(record,log,json.loads((work/'receipt.json').read_text()),words)
    result=dict(form=form,local_facts=record['facts'],events=events,facts=measured,installable=False)
    (work/'stages.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2];record=trace(root,root/BUILD)
    print(json.dumps(record,indent=2),flush=True)
