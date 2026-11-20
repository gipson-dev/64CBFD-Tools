"""Trace the trail emitter's real frame reservation; no installation or credit."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import hashlib,json,re
from tools.experiments import game_map_trail_emitter_151058b4_recovery as prior
from tools.experiments import game_actor_callback_frame_trace as frame
from tools.experiments import game_text_measurer_uopt_trace as allocation
from tools.experiments import game_remaining_donor_candidates as compiler
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools

ROOT=prior.ROOT
PACKET=ROOT/'conker/build/game-map-trail-emitter-151058b4-frame'
TYPES=prior.TYPES.replace('    f32 value, direction[3], parameter;', '    f32 value;\n    vertex direction;\n    f32 parameter;').replace('void func_15143794(s16, s16, f32, f32 *);','void func_15143794(s16, s16, f32, vertex *);')
FRAGMENT=prior.FRAGMENT.replace('    f32 remaining, randomValue;','    f32 remaining;').replace('        randomValue = func_150ADA68();\n','').replace('randomValue * D_800A23EC','func_150ADA68() * D_800A23EC').replace(', scratch.packet.direction);',', &scratch.packet.direction);')
RAW_SHA='a8d69bbc0d90aeca75ab8696c9fa15d6d088feee88043c9076ca0985f617d386'
ELF_SHA='d3eeddd84c1cd3c6c0877467dfdf37015677dc0a81885ea7f5ed6d528b2f352d'
base_debugger_script=frame.debugger_script

def whole_source(kind):
    if kind=='canonical':return prior.SPEC['selected']
    full=prior.SPEC['selected'];a,b=compiler.function_span(full,prior.FUNCTION)
    full=full[:a]+FRAGMENT+full[b:]
    assert prior.TYPES in full
    full=full.replace(prior.TYPES,TYPES,1)
    if kind=='refined':return full
    if kind=='anonymous-control':
        a,b=compiler.function_span(full,prior.FUNCTION);body=full[a:b]
        body=body.replace('    MapTrailEmitter131F30 *emitter;\n','').replace('        emitter = &record->emitter;\n','').replace('emitter->','record->emitter.')
        return full[:a]+body+full[b:]
    raise ValueError('Unknown trail frame form')

def prepare():
    previous=prior.prepare();out=PACKET/'qualified-frame';out.mkdir(exist_ok=True)
    before,bd=compiler.compile_owner(ROOT,out,prior.SPEC['old_source'],'before')
    obj,diag=compiler.compile_owner(ROOT,out,whole_source('refined'),'refined')
    raw,refs=payload(obj,prior.FUNCTION);words=bound_blob(raw,refs)
    assert hashlib.sha256(raw).hexdigest()==RAW_SHA
    assert len(words)==197 and (-words[0])&65535==248 and sum(a!=b for a,b in zip(words,previous['truth']))==12
    assert bd.count('cfe: Warning')==5 and diag.count('cfe: Warning')==2
    assert same_functions(before,obj,(prior.FUNCTION,))==10 and normalized_pools(before)==normalized_pools(obj)
    assert hashlib.sha256((ROOT/'conker/build/conker.us.elf').read_bytes()).hexdigest()==ELF_SHA
    report=dict(words=197,frame=248,retail_frame=240,differences=12,prior_differences=24,neighbors_unchanged=10,pools_unchanged=True,
        direction_interface='s16, s16, f32, vertex *',source_installed=False,matching_credit=0)
    (out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(out=out,words=words,truth=previous['truth'],raw=raw,refs=refs,report=report)

def isolated_source(kind):
    types=prior.TYPES if kind=='canonical' else TYPES
    a,b=compiler.function_span(types,'func_15105848');types=types[:a]+types[b:]
    full=whole_source(kind);a,b=compiler.function_span(full,prior.FUNCTION)
    prefix='#include <ultra64.h>\n#include "functions.h"\ntypedef struct { f32 x,y,z; } MapParticlePoint131F30;\ntypedef struct MapTrailRecord131F30 MapTrailRecord131F30;\nvoid func_151058B4(MapTrailRecord131F30 *);\n'
    return prefix+types+'\n'+full[a:b]+'\n'

def debugger_script(root,work):
 text=base_debugger_script(root,work)
 extra='''class LocalExtent(gdb.Breakpoint):
    def __init__(self,mem):
        self.mem=mem
        super().__init__('*(unsigned int*)%d'%(mem+0x1001C4B4),type=gdb.BP_WATCHPOINT,wp_class=gdb.WP_WRITE,internal=True)
    def stop(self):
        pc=int(gdb.parse_and_eval('$pc'))
        detail={}
        if pc==0x450cf3:
            pointer=int(gdb.parse_and_eval('$rbp'))
            if not 0<pointer<0x80000000:raise gdb.GdbError('Invalid owned spill image')
            bit=u32(self.mem,pointer+0xBC);image=u32(self.mem,pointer+0xA0)
            if not bit<u32(self.mem,0x1001CB38)<10000 or not 0x10000000<image<0x11000000:raise gdb.GdbError('Invalid owned spill table')
            table=u32(self.mem,0x1001CC30)
            if u32(self.mem,table+bit*8)!=image:raise gdb.GdbError('Spill image/table mismatch')
            detail=dict(stack_base=pointer,expression=bit,image=image,image_words=[u32(self.mem,image+i)for i in range(0,0x28,4)],table=table,allocated_size=int(gdb.parse_and_eval('$r11d')),next_extent=int(gdb.parse_and_eval('$eax')))
        gdb.write('UOPT_EXTENT '+json.dumps(dict(value=u32(self.mem,0x1001C4B4),host_pc=pc,backtrace=gdb.execute('bt 5',to_string=True),**detail))+'\\n')
        return False
class BeginUopt(gdb.Breakpoint):
    def stop(self):
        mem=int(gdb.parse_and_eval('$rdi'))
        gdb.write('UOPT_EXTENT_INSTALLED '+json.dumps(dict(value=u32(mem,0x1001C4B4)))+'\\n')
        LocalExtent(mem)
        self.enabled=False
        return False
'''
 text=text.replace('end\ncatch exec',extra+'end\ncatch exec')
 text=text.replace('capture()\nif gdb.current_progspace()',"capture()\nif Path(gdb.current_progspace().filename).name=='uopt':\n    BeginUopt('f_readuinstr.constprop.0')\nif gdb.current_progspace()")
 return text

def trace(kind):
    out=PACKET/'qualified-frame';out.mkdir(exist_ok=True)
    owner,diag=compiler.compile_owner(ROOT,out,whole_source(kind),'owner-'+kind)
    assert diag.count('cfe: Warning')==2
    expected=payload(owner,prior.FUNCTION);content=isolated_source(kind)
    def compile_candidate(root,work,label,body):
        assert body==content
        obj,diagnostics=compiler.compile_owner(root,work,body,label)
        assert not diagnostics and payload(obj,prior.FUNCTION)==expected
        raw,refs=expected;ws=bound_blob(raw,refs)
        return dict(words=len(ws),frame=(-ws[0])&65535,raw_sha256=hashlib.sha256(raw).hexdigest(),isolated_equals_owner=True),ws
    with patch.object(frame,'screen',SimpleNamespace(compile_candidate=compile_candidate)),patch.object(frame,'debugger_script',debugger_script):
        record=frame.trace(ROOT,out,'trace-'+kind,content)
    work=out/('trace-'+kind);log=(work/'debugger.txt').read_text();lines=log.splitlines()
    assert not any(s in log for s in ('Python Exception','Error in sourced command'))
    observations=[dict(kind=line.split(' ',1)[0],**json.loads(line.split(' ',1)[1]))for line in lines if line.startswith(('UOPT_EXTENT ','UOPT_EXTENT_INSTALLED '))]
    assert observations[0]==dict(kind='UOPT_EXTENT_INSTALLED',value=0)
    consumer=record['inputs'][0]['inferior'];exit_line=lines.index('TRACE_EXIT inferior=%d code=0'%consumer)
    positions=[i for i,line in enumerate(lines)if line.startswith('UOPT_EXTENT')]
    assert max(positions)<exit_line
    localdefs={phase:[row['length']for row in rows if row['name']=='def'and row['storage']=='M']for phase,rows in record['records'].items()}
    expected_shapes={'canonical':(197,248,124,128),'refined':(197,248,120,124),'anonymous-control':(200,240,116,116)}
    words,size,front,opt=expected_shapes[kind]
    assert(record['baseline']['words'],record['baseline']['frame'],localdefs['frontend'],localdefs['optimizer'])==(words,size,[front],[opt])
    extents=[v for v in observations if v['kind']=='UOPT_EXTENT']
    assert extents[0]['value']==front and extents[0]['host_pc']==0x489857
    spills=[v for v in extents if v['host_pc']==0x450cf3]
    if kind=='anonymous-control':assert not spills and len(extents)==1
    else:
        assert len(spills)==1 and len(extents)==2
        s=spills[0];assert(s['value'],s['allocated_size'],s['next_extent'])==(opt,4,opt)
        assert s['image_words'][0]&65535==s['expression'] and 'f_spilltemps'in s['backtrace']
        assert s['expression']==(14 if kind=='canonical'else 9)
    events=record['events']
    assert [e['event']for e in events]==['frame-watch-installed','frame-write','frame-write','frame-write']
    assert[e['frame']for e in events]==[0,96,120,size]
    assert all(not e['pool']and not e['temporary']and not e['temp_base']for e in events)
    assert(events[-1]['saved'],events[-1]['outgoing'],events[-1]['locals'])==(96,24,(opt+7)&~7)
    report=dict(kind=kind,source_installed=False,matching_credit=0,code_unchanged=True,isolated_equals_owner=True,
        local_definitions=localdefs,observations=observations,events=events,compiler_sha256=record['compiler_sha256'],inputs=record['inputs'])
    (work/'qualified-summary.json').write_text(json.dumps(report,indent=2)+'\n');return report

def allocation_listing():
    content=isolated_source('canonical');out=PACKET/'qualified-frame';out.mkdir(exist_ok=True)
    expected=payload(out/'owner-canonical.o',prior.FUNCTION)
    def compile_candidate(root,work,label,body):
        assert body==content
        obj,diag=compiler.compile_owner(root,work,body,label)
        assert not diag and payload(obj,prior.FUNCTION)==expected
        return dict(raw_sha256=hashlib.sha256(expected[0]).hexdigest()),None
    adapter=SimpleNamespace(compile_candidate=compile_candidate,PROFILES={'owner':('-O2','-g3')},compiler=SimpleNamespace(parse_object=compiler.parse_object,sections=compiler.sections))
    with patch.object(allocation,'screen',adapter):record=allocation.trace_uopt(ROOT,out,'canonical-mode5',content,5)
    work=out/'canonical-mode5';text=(work/'uoptlist').read_text();log=(work/'debugger.txt').read_text()
    assert log.count('Allocate diagnostic stream buffer')==1 and 'Suppress diagnostic real-number printer'in log
    assert 'isop    uadd{1350|0} {  40|0}'in text
    variables=allocation.variable_expressions(text);record.update(variables=variables,constraints=allocation.allocation_constraints(text))
    assert any(v['expression']==0 and v['storage']=='P'and v['offset']==0 for v in variables)
    assert any(v['expression']==12 and v['storage']=='M'and v['offset']==-12 for v in variables)
    (work/'qualified-listing.json').write_text(json.dumps(record,indent=2)+'\n');return record

def direction_contract():
    out=PACKET/'qualified-frame';out.mkdir(exist_ok=True)
    source=(ROOT/'conker/src/game_16EE20.c').read_text();a,b=compiler.function_span(source,'func_15143794');body=source[a:b]
    assert body.startswith('void func_15143794(s16 arg0, s16 arg1, f32 arg2, vertex *arg3) {')
    prefix='#include <ultra64.h>\n#include "functions.h"\nf32 func_151423D8(u8);\n'
    good='void func_15143794(s16, s16, f32, vertex *);\n'
    obj,diag=compiler.compile_owner(ROOT,out,prefix+good+body,'direction-contract');assert not diag
    assert payload(obj,'func_15143794')==payload(ROOT/'conker/build/src/game_16EE20.c.o','func_15143794')
    bad='void func_15143794(s16, s32, f32, vertex *);\n'
    try:compiler.compile_owner(ROOT,out,prefix+bad+body,'rejected-pitch-contract')
    except ValueError as exc:
        diagnostic=str(exc);assert 'func_15143794'in diagnostic and 'incompatible'in diagnostic.lower(),diagnostic
    else:raise AssertionError('Widened pitch contract was not rejected by the actual definition')
    report=dict(actual_direction_definition_checked=True,correct_contract_compiles_identically=True,wide_pitch_contract_rejected=True,source_installed=False,matching_credit=0)
    (out/'direction-contract.json').write_text(json.dumps(report,indent=2)+'\n');return report
