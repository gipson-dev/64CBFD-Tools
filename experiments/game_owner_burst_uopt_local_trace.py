"""Observe UOPT local-area reservations in an unchanged owned burst compile."""
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_owner_burst_frame_trace as frame

BUILD='conker/build/game-owner-burst-uopt-local-trace'
CURSOR=0x1001C4B4

PROBES=r'''
burst_probes=[]
burst_pending=0
def burst_u32(mem,address):
    return struct.unpack('<I',gdb.selected_inferior().read_memory(mem+address,4))[0]
def burst_stack():
    rows=[];current=gdb.newest_frame()
    for _ in range(6):
        if current is None:break
        rows.append(dict(name=current.name(),pc=current.pc()));current=current.older()
    return rows
def burst_tree(mem,node,depth=0,seen=None):
    seen=set() if seen is None else seen
    if node in seen or depth>3:raise gdb.GdbError('Unbounded burst expression tree')
    seen=seen|{node}
    words=[burst_u32(mem,node+i*4) for i in range(10)]
    result=dict(node=node,words=words,operands=[])
    if words[0]>>24==4 and depth<3:
        opcode=words[4]>>24
        pointers=words[5:7] if opcode==1 else words[5:6] if opcode in (24,54) else []
        result['operands']=[burst_tree(mem,p,depth+1,seen) for p in pointers if p]
    return result
def burst_local(event,mem,**extra):
    parents=burst_stack()
    if event=='cursor-write' and parents[0]['name']=='f_spilltemps':
        cell=int(gdb.parse_and_eval('$r15'))-mem
        node=burst_u32(mem,cell)
        extra.update(node_cell=cell,node=node,
            node_words=[burst_u32(mem,node+i*4) for i in range(10)],tree=burst_tree(mem,node),
            descriptor=int(gdb.parse_and_eval('$r8d')),
            requested=int(gdb.parse_and_eval('$r11d')))
    row=dict(event=event,cursor=burst_u32(mem,0x1001C4B4),
        head=burst_u32(mem,0x1001C4B8),tail=burst_u32(mem,0x1001C4BC),
        parents=parents,**extra)
    gdb.write('BURST_LOCAL '+json.dumps(row,sort_keys=True)+'\n')
def burst_pool(mem):
    pointer=burst_u32(mem,0x1001C4B8);seen=set();rows=[]
    while pointer:
        if pointer in seen or len(rows)>=16:raise gdb.GdbError('Unbounded UOPT temporary list')
        seen.add(pointer)
        fields=[burst_u32(mem,pointer+i*4) for i in range(5)]
        rows.append(dict(pointer=pointer,fields=fields));pointer=fields[4]
    return rows
def burst_removed(event):
    if event.inferior.progspace.filename==str(compiler_dir/'uopt'):
        for probe in burst_probes:
            if probe.is_valid():probe.delete()
        gdb.write('BURST_REMOVED '+json.dumps(dict(pending=burst_pending,
            probes=len(burst_probes),exit_code=getattr(event,'exit_code','unknown')))+'\n')
gdb.events.exited.connect(burst_removed)
class BurstLocalChanged(gdb.Breakpoint):
    def __init__(self,mem):
        self.mem=mem
        super().__init__('*(unsigned int*)%d' % (mem+0x1001C4B4),
            type=gdb.BP_WATCHPOINT,wp_class=gdb.WP_WRITE,internal=True)
    def stop(self):
        burst_local('cursor-write',self.mem)
        return False
class BurstCursorBegin(gdb.Breakpoint):
    def stop(self):
        mem=int(gdb.parse_and_eval('$rdi'))
        burst_local('cursor-watch-installed',mem)
        burst_probes.append(BurstLocalChanged(mem));self.enabled=False
        return False
class BurstSpillReturned(gdb.FinishBreakpoint):
    def __init__(self,mem):
        global burst_pending
        self.mem=mem;burst_pending+=1
        super().__init__(gdb.newest_frame(),internal=True)
    def stop(self):
        global burst_pending
        burst_local('spilltemps-return',self.mem,pool=burst_pool(self.mem))
        burst_pending-=1
        return False
class BurstSpillBegin(gdb.Breakpoint):
    def stop(self):
        mem=int(gdb.parse_and_eval('$rdi'))
        burst_local('spilltemps-entry',mem)
        BurstSpillReturned(mem)
        return False
'''


def debugger_script(original,root,work):
    text=original(root,work)
    anchor='class FrameChanged(gdb.Breakpoint):'
    start='if gdb.current_progspace().filename == '
    if text.count(anchor)!=1 or text.count(start)!=1:
        raise ValueError('Changed shared frame debugger anchors')
    text=text.replace(anchor,PROBES+'\n'+anchor)
    uopt=json.dumps(str((root/'ido/ido5.3_recomp/uopt').resolve()))
    return text.replace(start,'if gdb.current_progspace().filename == '+uopt+':\n    burst_probes.extend((BurstCursorBegin(\'f_readuinstr.constprop.0\'),BurstSpillBegin(\'f_spilltemps\',internal=True)))\n'+start)


def observations(log):
    rows=[json.loads(line.removeprefix('BURST_LOCAL ')) for line in log.splitlines()
          if line.startswith('BURST_LOCAL ')]
    if not rows or not any(r.get('event')=='cursor-write' for r in rows):
        raise ValueError('No UOPT local cursor observation probe')
    return rows


def facts(log,summary,wire,content):
    rows=observations(log);layout=frame.checked_layout(summary)
    if frame.phase_summary(wire,content)['procedure']!=summary['procedure']:
        raise ValueError('Changed burst local procedure')
    local=layout['frontend_local_bytes'];procedure=summary['procedure']
    kinds=('cursor-watch-installed','cursor-write','spilltemps-entry',
        'cursor-write','cursor-write','cursor-write','spilltemps-return')
    if tuple(r.get('event') for r in rows)!=kinds or [r.get('cursor') for r in rows]!=[
            0,local,local,local+4,local+8,local+12,local+12]:
        raise ValueError('Missing/reordered UOPT local reservations')
    lines=log.splitlines();end=[json.loads(x[14:]) for x in lines if x.startswith('BURST_REMOVED ')]
    if end!=[dict(pending=0,probes=3,exit_code=0)]:raise ValueError('Incomplete UOPT local probe cleanup')
    inputs=[json.loads(x[12:]) for x in lines if x.startswith('FRAME_INPUT ')]
    capture=next(i for i,x in enumerate(lines) if x.startswith('FRAME_INPUT ') and json.loads(x[12:])['stage']=='uopt')
    finish=lines.index('TRACE_EXIT inferior=%d code=0'%inputs[0]['inferior'])
    removal=next(i for i,x in enumerate(lines) if x.startswith('BURST_REMOVED '))
    next_capture=next(i for i,x in enumerate(lines) if x.startswith('FRAME_INPUT ') and json.loads(x[12:])['stage']=='ugen')
    positions=[i for i,x in enumerate(lines) if x.startswith('BURST_LOCAL ')]
    if not capture<positions[0]<positions[-1]<finish<removal<next_capture:
        raise ValueError('UOPT local observations outside completed child lifetime')
    writes=rows[3:6];pool=rows[-1].get('pool',[])
    if len(pool)!=3:raise ValueError('Incomplete UOPT temporary descriptor list')
    descriptors=[r['descriptor'] for r in writes]
    if len(set(descriptors))!=3 or any(type(p) is not int or not 0<p<=0xffffffff or p%4 for p in descriptors):
        raise ValueError('Invalid UOPT temporary identities')
    for i,(row,slot) in enumerate(zip(writes,pool)):
        expected=[i,(-(local+4*(i+1)))&0xffffffff,4,0,descriptors[i+1] if i<2 else 0]
        if (row['requested']!=4 or slot!=dict(pointer=descriptors[i],fields=expected)
                or row['parents'][0]!=dict(name='f_spilltemps',pc=0x450CF3)
                or row['head']!=descriptors[0] or row['tail']!=(descriptors[i-1] if i else 0)
                or row['node_cell']!=0x0FFFFF50):
            raise ValueError('Changed UOPT reservation writer/descriptor binding')
        tree=row['tree'];words=row['node_words']
        if (tree['node']!=row['node'] or tree['words']!=words or len(words)!=10
                or any(type(w) is not int or not 0<=w<=0xffffffff for w in words)
                or words[0]>>24!=4 or words[4]>>24!=(1,54,24)[i]
                or [child['node'] for child in tree['operands']]!=[p for p in words[5:7 if i==0 else 6] if p]):
            raise ValueError('Changed UOPT reserved-expression binding')
    address,state,conversion=[r['tree'] for r in writes]
    actor,constant=address['operands'];owner=state['operands'][0];loaded=conversion['operands'][0]
    if (actor['words'][0]>>24!=3 or actor['words'][4:6]!=[0,(procedure<<16)|0x0202]
            or constant['words'][0]>>24!=2 or constant['words'][4]!=40
            or owner['words'][0]>>24!=3 or owner['words'][4:6]!=[((-local+4)&0xffffffff),(procedure<<16)|0x0102]
            or state['words'][7]!=0x222 or state['words'][0]>>16&255!=8
            or conversion['words'][0]>>16&255!=6 or conversion['words'][9]>>24!=8
            or loaded['node']!=state['node'] or loaded['words'][8]!=descriptors[1]
            or loaded['operands']!=state['operands']
            or any(loaded['words'][i]!=state['words'][i] for i in range(10) if i!=8)):
        raise ValueError('UOPT reservations no longer bind actor base and owner state')
    source_lines=content.splitlines();matches=[i+1 for i,s in enumerate(source_lines) if s.strip()=='owner = data->owner;']
    if len(matches)!=1:raise ValueError('Ambiguous owner-home source marker')
    current=None;owner_stores=[]
    for row in wire['records']['frontend']:
        if row['name']=='loc':current=row['words'][1]
        if current==matches[0] and row['name']=='str' and row['storage']=='M':owner_stores.append(row['offset'])
    if owner_stores!=[-local+4]:raise ValueError('Reserved owner-state operand has wrong source home')
    accesses=[r for r in wire['records']['optimizer'] if r['storage']=='M' and r['offset'] is not None and r['offset']< -local]
    if accesses:raise ValueError('Reserved slots now have explicit output M operands')
    if rows[-1]['head']!=descriptors[0] or rows[-1]['tail']!=descriptors[-1]:
        raise ValueError('Incomplete final UOPT descriptor chain')
    return dict(reserved_bytes=12,slots=3,slot_size=4,writer_host_pc=0x450CF3,
        operations=['actor-plus-0x28','owner-byte-0x222','owner-byte-integer-conversion'],
        caller_relative_slots=[-local-4,-local-8,-local-12],explicit_output_M_accesses_to_slots=0,
        normal_object_identity_verified=True,installable=False,matching_credit=0)


def trace(root,out,form='aligned-pairs'):
    root,out=Path(root).resolve(),Path(out).resolve()
    original=frame.shared.debugger_script
    with patch.object(frame.shared,'debugger_script',lambda r,w:debugger_script(original,r,w)):
        record=frame.trace(root,out,form,form)
    work=out/form;log=(work/'debugger.txt').read_text()
    measured=facts(log,record,json.loads((work/'receipt.json').read_text()),(work/'baseline.c').read_text())
    result=dict(form=form,layout=record['layout'],events=observations(log),facts=measured,
        normal_object_identity_verified=record['code_unchanged'],installable=False)
    (out/form/'local-receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def source_forms():
    from tools.experiments import game_owner_burst_storage_candidates as storage
    _,body,types=next(storage.forms())
    yield 'aligned-pairs',body,types
    yield 'component-vector-copy',body.replace('request.fields.vector28 = D_800A5480;',
        'request.fields.vector28.x = D_800A5480.x;\n                    request.fields.vector28.y = D_800A5480.y;\n                    request.fields.vector28.z = D_800A5480.z;'),types
    direct=body.replace('    Generated11FF10Payload *data;\n','').replace(
        '    data = (Generated11FF10Payload *)(actor + 0x28);\n    savedData = data;',
        '    savedData = (Generated11FF10Payload *)(actor + 0x28);').replace(
        'data->','((Generated11FF10Payload *)(actor + 0x28))->')
    yield 'direct-data-base',direct,types
    yield 'direct-data-copy-phase',*storage.copy_phase(direct,types)
    literal=body.replace('    f32 multiplier;\n','').replace('                multiplier = D_800A196C;\n','').replace(
        'payload.multiplier = multiplier;','payload.multiplier = 58.14f;')
    yield 'literal-scale',literal,types


def screen(root,out):
    from tools.experiments import game_owner_burst_storage_candidates as storage
    rows=[]
    for label,body,types in source_forms():
        try:
            row=storage.measure(root,out,label,body,types)[-1]
        except ValueError as error:
            if label!='literal-scale' or str(error)!="Unknown owner-burst bindings ['.rodata']":raise
            obj=out/(label+'.o');pool=frame.source.projection.sections(obj)['.rodata'][1]
            retail=(out/'before-retail_rom').read_bytes()[0x24642C:0x246430]
            if pool!=retail+b'\0'*12 or retail.hex()!='42688f5c':raise ValueError('Unqualified literal scale pool')
            raw,bindings=frame.source.parts(obj);words=struct.unpack('>%dI'%(len(raw)//4),raw)
            row=dict(rejected=str(error),raw_words=len(words),raw_frame=(-words[0])&65535,
                literal_pool_matches_retail_bytes=True,unqualified_binding='.rodata',installed=False)
        rows.append(dict(label=label,**row))
        print(label,json.dumps({k:v for k,v in row.items() if k!='bindings'}),flush=True)
    (out/'source-screens.json').write_text(json.dumps(rows,indent=2)+'\n')
    return rows


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--form',choices=('selected','descriptor-align8','aligned-pairs'),default='aligned-pairs')
    parser.add_argument('--screens',action='store_true')
    args=parser.parse_args();root=Path(__file__).resolve().parents[2]
    if args.screens:screen(root,root/BUILD)
    else:print(json.dumps(trace(root,root/BUILD,args.form),indent=2),flush=True)
