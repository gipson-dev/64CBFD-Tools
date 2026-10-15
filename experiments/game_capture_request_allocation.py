"""Inspect the capture request's real compiler phases without changing codegen."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_capture_request_slot as source
from tools.experiments import game_remaining_donor_candidates as build
from tools.experiments import game_text_measurer_frontend_trace as capture
from tools.experiments import game_text_measurer_uopt_trace as allocation
from tools.pad_generated_object import parse_object

BUILD=source.BUILD+'/allocation'


def array_end_variants():
    for name,body in (('ordered',source.SELECTED),('original-order',source.ARCHIVE_LOOP)):
        yield name+'-same-array',body.replace('request == D_800DD3FC','request == &D_800DD348[3]')
        yield name+'-array-add',body.replace('request == D_800DD3FC','request == D_800DD348 + 3')
        yield name+'-register-cursor',body.replace('CaptureRequest1A11B0 *request =',
            'register CaptureRequest1A11B0 *request =')


def role_variants():
    for label,body in (('ordered',source.SELECTED),('original-order',source.ARCHIVE_LOOP)):
        yield label+'-shared-declarator',body.replace('CaptureRequest1A11B0 *request = D_800DD348;',
            'CaptureRequest1A11B0 *end = D_800DD3FC, *request = D_800DD348;').replace(
                'request == D_800DD3FC','request == end')
        yield label+'-commuted-end',body.replace('request == D_800DD3FC','D_800DD3FC == request')
        yield label+'-word-callback',body.replace('s8 callback, s32 value','s32 callback, s32 value')
        for integer in ('s32','u32'):
            yield label+'-'+integer+'-payload',body.replace('const CapturePayload1A11B0 *payload',integer+' payload').replace(
                'payload != NULL','payload != 0').replace('request->payload = *payload',
                    'request->payload = *(const CapturePayload1A11B0 *)payload')
        prefix='f32 zCopy = z;\n    s8 callbackCopy = callback;\n    s32 valueCopy = value;\n    '
        current=body.replace('CaptureRequest1A11B0 *request = D_800DD348;',prefix+'CaptureRequest1A11B0 *request = D_800DD348;')
        for old,new in (('request->z = z','request->z = zCopy'),('request->callback = callback','request->callback = callbackCopy'),
                ('request->value = value','request->value = valueCopy')):
            current=current.replace(old,new)
        yield label+'-entry-snapshots',current


def screen(root,out,roles=False):
    source.freeze(root,root/source.BUILD)
    out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for name,body in (role_variants() if roles else array_end_variants()):
        _,_,row=source.measure(root,out,name,body)
        rows.append(row)
        print(json.dumps({key:value for key,value in row.items() if key!='differing_words'}),flush=True)
    (out/('role-screens.json' if roles else 'array-end-screens.json')).write_text(json.dumps(rows,indent=2)+'\n')


def analysis_packet(root,out):
    if {key:hashlib.sha256((root/path).read_bytes()).hexdigest() for key,path in source.PATHS.items()}!=source.BASELINE:
        raise ValueError('Changed production input before capture request review')
    source.freeze(root,root/source.BUILD)
    original=(root/source.BUILD/'before-request_original').read_text()
    block=original.split('glabel '+source.FUNCTION,1)[1].split('endlabel '+source.FUNCTION,1)[0]
    raw=subprocess.run(['mips-linux-gnu-objdump','-dr','--disassemble='+source.FUNCTION,
        str(root/source.BUILD/'qualified.o')],capture_output=True,text=True,check=True).stdout
    packet='''Read-only, packet-only analysis. No tools, commands, edits, builds, Git mutations, installs,
other agents, or exploration outside this packet. Codex is the only writer and validator.
Target: US N64 func_151745F0, VA151745F0, ROM1A1AA0, 40-word slot, IDO5.3 -O2 -g3.
Consumer baseline62b7cc2e/tools10ccd75; all26 production inputs still equal pinned hashes.
Decision: identify a small, semantically faithful source change to recover the retail cursor/end
allocation and early parameter loads. Do not suggest instruction replacement, volatile/restrict,
physical register binding, undefined behavior, fixed fake addresses, or shrinking the input domain.

Measured: selected C emits39 body words, zero frame/diagnostics/calls/pools; one real alignment NOP;
22 differences remain. A2's home store is first. Native32 2048/profile and low-word guest14336
paired-SP cases agree publicly, but8288 private outcomes and306/322 prefixes differ.
All64 occupancy triples from bytes00/01/80/FF, callback truncation, exact self/disjoint/null payloads
are supported. No partially overlapping struct-copy contract or concurrency/FCSR claim.

Fresh owned-child CFE/UOPT/UGEN probes leave complete text/relocs/pools unchanged and agree
with the full owner. Cursor's frontend variable is M-4; UOPT assigns it R2 (MIPS V0). The
end address is materialized as rlda R3 (MIPS V1). UGEN receives these wrong-for-retail roles.
Mode5 cursor expression0/identity88|0/color1 has forbidden[6], interference[39,38,37,23,20,17].
Endpoint39/identity1589|0/color2 has forbidden[1,6], interference[23,0]. Do not infer an
intrinsic register constraint from these post-coloring sets. Numeric cost/timing output is suppressed
and cannot be interpreted. The colors' mapping is established only by the actual UOPT/raw words.
Parameter P8/P19/P20 remain memory loads in optimized code. X/Y stay R44/R46 (F12/F14).

Already screened54 forms (loop/store ordering, preloads, pointer-byte/scalar layouts, shared returns,
void/typed payloads, explicit end locals, O2/no-unroll/O1-g3), none improves22. Six new same-array
end (&base[3],base+3) / source-register keyword forms also do not improve22. Do not repeat them.
The selected copy loop at+58..+78 and successful return+7C/+80 already match; the duplicated
increment+84 is unreachable but still counts for byte matching. Production remains a zero stub.

Questions (under700 words total):
1. Give an independent explanation of which source/IR property could make the end get V0 first.
2. Propose at most three new smallest discriminating, semantic-preserving C tests; label hypotheses.
3. Explain whether the stack-parameter reload/copy-setup schedule suggests a separate alias or
   access-shape issue, and what observation would discriminate it without normalizing code.

Complete candidate declarations/body:
'''+source.TYPES+'\n'+source.SELECTED+'\nComplete retail body (39 words; final slot word is alignment NOP):\n'+block+\
        '\nComplete selected raw object disassembly/relocations:\n'+raw
    out.mkdir(parents=True,exist_ok=True)
    path=out/'analysis-packet.txt'
    path.write_text(packet)
    return dict(path=str(path),bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def compile_target(root,out,name,body):
    text='#include <ultra64.h>\n'+source.TYPES+'\n'+body+'\n'
    obj,diagnostics=build.compile_owner(root,out,text,name)
    data,functions=build.link_owner(root,out,obj,source.OWNER)
    info=functions[source.FUNCTION]
    words=list(struct.unpack_from('>%dI'%(info['size']//4),data,info['value']))
    truth=list(struct.unpack_from('>40I',(root/'conker/conker.us.bin').read_bytes(),source.ROM))
    complete=words+([0] if len(words)==39 and truth[-1]==0 else [])
    return dict(words=len(words),frame=0 if words[0]>>16!=0x27BD else (-words[0])&65535,
        differences=sum(a!=b for a,b in zip(complete,truth))+abs(len(complete)-40),
        diagnostics=diagnostics,profile=['-O2','-g3']),complete


def verify_owner(root,work,body):
    obj,diagnostics=build.compile_owner(root,work,source.recover(
        (root/source.BUILD/'before-request_owner').read_text(),body),'complete-owner')
    isolated,af,ar=parse_object(work/'baseline.o')
    owner,bf,br=parse_object(obj)
    a,b=af[source.FUNCTION],bf[source.FUNCTION]
    relative=lambda rel,f:{at-f['value']:v for at,v in rel.items() if f['value']<=at<f['value']+f['size']}
    if diagnostics or (a['size'],isolated[a['value']:a['value']+a['size']],relative(ar,a)) != \
            (b['size'],owner[b['value']:b['value']+b['size']],relative(br,b)):
        raise ValueError('Capture request trace differs from its complete-owner target')


def phase_summary(record,text):
    if record.get('code_unchanged') is not True or record.get('standalone_matches_complete_owner_target') is not True:
        raise ValueError('Unqualified capture request compiler phases')
    lines=text.splitlines()
    def line_for(statement):
        values=[i+1 for i,line in enumerate(lines) if line.strip()==statement]
        if len(values)!=1:
            raise ValueError('Ambiguous capture request source role')
        return values[0]
    initial=line_for('CaptureRequest1A11B0 *request = D_800DD348;')
    endpoint=line_for('if (request == D_800DD3FC) {')
    def rows_at(rows,line,name,storage):
        current=None
        result=[]
        for row in rows:
            if row['name']=='loc':
                current=row['words'][1]
            if current==line and row['name']==name and row['storage']==storage:
                result.append(row)
        return result
    frontend=record['records']
    starts=rows_at(frontend,initial,'lda','S')
    ends=rows_at(frontend,endpoint,'lda','S')
    homes=rows_at(frontend,initial,'str','M')
    registers=rows_at(record['optimizer_records'],initial,'str','R')
    if any(len(items)!=1 for items in (starts,ends,homes,registers)):
        raise ValueError('Incomplete capture request source bindings')
    bound=[row for row in record['optimizer_records'] if row['name']=='rlda'
        and row['storage']=='S' and row['block']==ends[0]['block'] and row['offset']==ends[0]['offset']]
    if len(bound)!=1 or starts[0]['block']==ends[0]['block']:
        raise ValueError('Incomplete capture request end invariant')
    cursor,end=registers[0]['offset'],bound[0]['words'][2]
    observed={event['raw44']//4 for event in record['complete']['events'] if event['type_storage']>>5==3}
    if cursor not in observed or end not in observed:
        raise ValueError('Capture request assigned registers not observed in UGEN')
    return dict(frontend_cursor_home=homes[0]['offset'],optimizer_cursor_register=cursor,
        optimizer_end_register=end,ugen_observed_registers=sorted(observed),
        frontend_records=record['record_count'],optimizer_records=record['optimizer_record_count'],
        ugen_events=record['complete']['event_count'],assignment_precedes_ugen=True,
        code_unchanged=True,not_numeric_allocation_cost_evidence=True)


def trace_frontend(root,out,label,body=source.SELECTED):
    source.freeze(root,root/source.BUILD)
    with patch.object(capture.trace.screen,'compile_candidate',side_effect=compile_target),\
            patch.dict(capture.trace.screen.PROFILES,owner=('-O2','-g3')):
        record=capture.capture_frontend(root,out,label,body)
    verify_owner(root,out/label,body)
    record['standalone_matches_complete_owner_target']=True
    (out/label/'frontend.json').write_text(json.dumps(record,indent=2)+'\n')
    summary=phase_summary(record,(out/label/'baseline.c').read_text())
    (out/label/'phase-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return record


def trace_allocation(root,out,label,body=source.SELECTED):
    source.freeze(root,root/source.BUILD)
    with patch.object(allocation.screen,'compile_candidate',side_effect=compile_target),\
            patch.dict(allocation.screen.PROFILES,owner=('-O2','-g3')):
        record=allocation.trace_uopt(root,out,label,body,mode=5)
    verify_owner(root,out/label,body)
    text=(out/label/'uoptlist').read_text()
    record.update(variables=allocation.variable_expressions(text),constraints=allocation.allocation_constraints(text),
        standalone_matches_complete_owner_target=True)
    (out/label/'allocation.json').write_text(json.dumps(record,indent=2)+'\n')
    return record


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allocation',action='store_true')
    parser.add_argument('--array-ends',action='store_true')
    parser.add_argument('--roles',action='store_true')
    parser.add_argument('--packet',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    out=root/BUILD
    if args.packet:
        print(json.dumps(analysis_packet(root,out),indent=2))
        return
    if args.array_ends:
        screen(root,out)
        return
    if args.roles:
        screen(root,out,roles=True)
        return
    if args.allocation:
        record=trace_allocation(root,out,'selected-mode5')
        print(json.dumps(dict(variables=record['variables'],constraints=len(record['constraints']),
            code_unchanged=record['code_unchanged'],baseline=record['baseline'],caveat=record['caveat']),indent=2))
    else:
        record=trace_frontend(root,out,'selected-frontend')
        print(json.dumps(dict(frontend_records=record['record_count'],optimizer_records=record['optimizer_record_count'],
            ugen_events=record['complete']['event_count'],code_unchanged=record['code_unchanged'],
            baseline=record['complete']['baseline'],standalone_owner_agreement=True),indent=2))


if __name__=='__main__':
    main()
