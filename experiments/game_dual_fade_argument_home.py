"""Qualify the real argument-home recovery, not the still-missing S0 lifetime."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from types import SimpleNamespace
from unittest.mock import patch

from tools.experiments import game_dual_buffer_fade as previous
from tools.experiments import game_text_measurer_frontend_trace as front
from tools.experiments import game_text_measurer_uopt_trace as uopt
from tools.experiments.game_graphics_task_submit import same_functions

BUILD='conker/build/game-dual-fade-argument-home'
OWNER,FUNCTION,ENTRY,ROM,SIZE=previous.OWNER,previous.FUNCTION,previous.ENTRY,previous.ROM,previous.SIZE
PATHS,BASELINE=dict(previous.PATHS),dict(previous.BASELINE)
for key,path,sha in (
    ('fade_source','tools/experiments/game_dual_buffer_fade.py','b4c924b330991ee211914742b8831cf5f40bf2df20b0c1e5765a2d9036260f7b'),
    ('fade_tests','tools/tests/test_game_dual_buffer_fade.py','b8cfe89b710ef7776331ad980dfcc8356c73937af61ee34fee36f60292786538'),
    ('fade_allocator_trace','tools/experiments/game_text_measurer_uopt_trace.py','f26cd23e5df523961ff8d6605223aeb2a3be3f1959ccac3eac05667545b7361b')):
    PATHS[key],BASELINE[key]=path,sha
build,compile_owner,projection,parse_object=previous.build,previous.compile_owner,previous.projection,previous.parse_object
PROTOTYPES=previous.PROTOTYPES
SELECTED=previous.SELECTED.replace('/* Blend the live text buffer and its predecessor using the signed countdown. */',
    '/* Retain the real argument object copied by the legacy variadic text wrapper. */')
for old,new in (
    ('countdown = *(s8 **)(record + 0x48);','countdown = *(s8 **)(*(u8 **)&record + 0x48);'),
    ('record[0x30]','(*(u8 **)&record)[0x30]'),
    ('record + 0x40 + record[0x3D] * 4','*(u8 **)&record + 0x40 + (*(u8 **)&record)[0x3D] * 4'),
    ('state = record + 0x28','state = *(u8 **)&record + 0x28')):
    if SELECTED.count(old)!=1:raise ValueError('Unknown fade argument-home predecessor')
    SELECTED=SELECTED.replace(old,new,1)
RAW_SHA='f061b64f4df1f19e93fc1570b41e99b88b5c873afbcba6a5feab50f202c89a8a'
BINDINGS={56:[('R_MIPS_HI16','D_800BE9E4')],72:[('R_MIPS_LO16','D_800BE9E4')],
    120:[('R_MIPS_26','func_1504332C')],156:[('R_MIPS_26','func_15042D94')],
    204:[('R_MIPS_26','func_1504332C')],244:[('R_MIPS_26','func_15042D94')]}
BRANCH=previous.SELECTED.replace('s32 previousWeight = 0;','s32 previousWeight;').replace(
    's32 currentWeight = 255;','u8 currentWeight;').replace('*countdown = count - (u32) D_800BE9E4;\n    }',
    '*countdown = count - (u32) D_800BE9E4;\n    } else {\n        previousWeight = 0;\n        currentWeight = 255;\n    }')


def freeze(root,out):
    with patch.multiple(previous,PATHS=PATHS,BASELINE=BASELINE):previous.freeze(root,out)


def recovered_owner(before,body=SELECTED):return previous.recovered_owner(before,body)
parts,padded_object=previous.parts,previous.padded_object


def checked_parts(raw,bindings):
    if len(raw)!=272 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Changed argument-home words/bindings')


def require_installable(words):
    if len(words)!=69:raise ValueError('Argument home recovered, but retail extent/S0 lifetime unresolved')
    raise ValueError('Retail S0/private/fault/image gates remain unqualified')


def qualify(root,out):
    freeze(root,out);before=(out/'before-tile_owner').read_text()
    obj,diag=compile_owner(root,out,recovered_owner(before),'candidate')
    old,old_diag=compile_owner(root,out,before,'owner-before')
    if diag or old_diag:raise ValueError('Argument-home compiler diagnostics')
    checked_parts(*parts(obj))
    pools=lambda p:{n:d for n,(_,d) in projection.sections(p).items() if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss'))}
    if pools(old)!=pools(obj):raise ValueError('Argument-home owner pools changed')
    neighbors=same_functions(old,obj,(FUNCTION,));padded=padded_object(root,out,obj,'candidate')
    if same_functions(padded_object(root,out,old,'owner-before'),padded,(FUNCTION,))!=neighbors:
        raise ValueError('Argument-home padded neighbors changed')
    images=[]
    for path in (obj,padded):
        data,fs=build.link_owner(root,out,path,OWNER);f=fs[FUNCTION]
        images.append(list(struct.unpack_from('>68I',data,f['value'])))
    if images[0]!=images[1]:raise ValueError('Unexpected argument-home normalization')
    if (images[0][2],images[0][3],images[0][31],images[0][48])!=(0xAFA40030,0x8FAE0030,0xAFA90024,0xAFA2001C):
        raise ValueError('Unknown recovered argument or unresolved private homes')
    row=dict(words=68,retail_words=69,frame=48,record_home=48,previous_weight_home=36,state_home=28,
        saves_s0=False,new_guards=0,bindings=6,unchanged_raw_padded_neighbors=neighbors,installable=False)
    (out/'candidate-audit.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,padded,images,row


def compiler_screen(root,out):
    def compile_candidate(root,work,name,body):
        obj,diag=compile_owner(root,work,recovered_owner((out/'before-tile_owner').read_text(),body),name)
        if diag:raise ValueError(diag)
        raw,fs,_=parse_object(obj);f=fs[FUNCTION];data=raw[f['value']:f['value']+f['size']]
        return dict(words=len(data)//4,frame=(-struct.unpack_from('>I',data)[0])&65535,
            target_sha256=hashlib.sha256(data).hexdigest()),obj
    return SimpleNamespace(compile_candidate=compile_candidate,PROFILES={'owner':('-O2','-g3')},
        compiler=SimpleNamespace(parse_object=parse_object,sections=projection.sections))


def procedure(records,obj):
    _,fs,_=parse_object(obj);names=sorted(fs,key=lambda n:fs[n]['value'])
    starts=[i for i,r in enumerate(records) if r['name']=='ent']
    if len(names)!=25 or len(starts)!=len(names):raise ValueError('Unknown fade owner procedure inventory')
    selected=[]
    for r in records[starts[names.index(FUNCTION)]:]:
        selected.append(r)
        if r['name']=='end':return selected
    raise ValueError('Unterminated fade procedure')


def capture(root,out,label,body):
    freeze(root,out)
    with patch.object(front.trace,'screen',compiler_screen(root,out)):
        record=front.capture_frontend(root,out,'capture-'+label,body)
    work=out/('capture-'+label);obj=work/'baseline.o'
    cfe,optimized=(procedure(record[key],obj) for key in ('records','optimizer_records'))
    definitions=lambda rows:[r['length'] for r in rows if r['name']=='def' and r['storage']=='M']
    formals=[r for r in cfe if r['name']=='pdef']
    if definitions(cfe)!=[20] or len(formals)!=1 or any(formals[0][k]!=v for k,v in dict(dtype='A',storage='P',offset=0,length=4).items()):
        raise ValueError('Changed real formal or automatic object inventory')
    summary=dict(procedure=cfe[0]['block'],automatic_bytes=20,optimized_automatic_bytes=definitions(optimized),
        cfe_formal_lda=sum(r['name']=='lda' and r['storage']=='P' and r['offset']==0 for r in cfe),
        optimized_formal_loads=sum(r['name']=='lod' and r['storage']=='P' and r['offset']==0 for r in optimized),
        frontend_exits=record['frontend']['producer_exits'],optimizer_exits=record['optimizer']['producer_exits'],
        code_unchanged=record['code_unchanged'],baseline=record['complete']['baseline'])
    (work/'target-rows.json').write_text(json.dumps(dict(cfe=cfe,uopt=optimized),indent=2)+'\n')
    (work/'target-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return record,summary


def allocation(root,out,label,body,procedure_block):
    freeze(root,out)
    with patch.object(uopt,'screen',compiler_screen(root,out)):
        record=uopt.trace_uopt(root,out,'allocation-'+label,body,5)
    work=out/('allocation-'+label);log=(work/'debugger.txt').read_text()
    if 'Allocate diagnostic stream buffer' not in log or 'Suppress diagnostic real-number printer' not in log:
        raise ValueError('Missing positively fired allocation diagnostic probes')
    text=allocation_procedure((work/'uoptlist').read_text())
    variables=[v for v in uopt.variable_expressions(text) if v['procedure']==procedure_block]
    wanted={v['identity'] for v in variables};constraints=[c for c in uopt.allocation_constraints(text) if c['identity'] in wanted]
    if len(variables)!=6 or not constraints:raise ValueError('Unknown fade variable or allocation inventory')
    final=[]
    for storage,offset in (('P',0),('M',-12)):
        var=next(v for v in variables if (v['storage'],v['offset'])==(storage,offset))
        matches=[c for c in constraints if (c['identity'],c['expression'])==(var['identity'],var['expression'])]
        if not matches:raise ValueError('Missing matching live-range allocation constraint')
        final.append(dict(variable=var,constraint=matches[-1]))
    result=dict(code_unchanged=record['code_unchanged'],variables=variables,constraints=constraints,final=final,
        baseline=record['baseline'],numeric_costs_or_timings_not_valid=True)
    (work/'target-constraints.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def allocation_procedure(text):
    lines=text.splitlines();start=[i for i,s in enumerate(lines) if s.endswith(' IN LOCAL OPTIMIZATION OF '+FUNCTION)]
    end=[i for i,s in enumerate(lines) if s.endswith(' IN REEMISSION OF '+FUNCTION)]
    if len(start)!=1 or len(end)!=1 or start[0]>=end[0]:raise ValueError('Unknown target allocation procedure boundaries')
    return '\n'.join(lines[start[0]:end[0]+1])+'\n'


def profiles(root,out):
    freeze(root,out);rows=[]
    for label,body in (
        ('array-parameter',previous.SELECTED.replace('u8 *record)','u8 record[])')),
        ('home-register',SELECTED.replace('s32 previousWeight','register s32 previousWeight')),
        ('home-half',SELECTED.replace('s32 previousWeight','u16 previousWeight')),
        ('home-branch',SELECTED.replace('s32 previousWeight = 0;','s32 previousWeight;').replace('s32 currentWeight = 255;','u8 currentWeight;').replace(
            '*countdown = count - (u32) D_800BE9E4;\n    }',
            '*countdown = count - (u32) D_800BE9E4;\n    } else {\n        previousWeight = 0;\n        currentWeight = 255;\n    }'))):
        obj,diag=compile_owner(root,out,recovered_owner((out/'before-tile_owner').read_text(),body),'screen-'+label)
        if diag:raise ValueError(diag)
        raw,bindings=parts(obj);words=list(struct.unpack('>%dI'%(len(raw)//4),raw))
        rows.append(dict(label=label,words=len(words),frame=(-words[0])&65535,sha256=hashlib.sha256(raw).hexdigest(),
            saves_s0=0xAFB00018 in words,bindings=bindings,installable=False))
    (out/'profiles.json').write_text(json.dumps(rows,indent=2)+'\n')
    return rows


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--trace',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2];out=root/BUILD
    if args.trace:
        summaries={label:capture(root,out,label,body)[1] for label,body in (('normal',previous.SELECTED),('branch',BRANCH),('home',SELECTED))}
        allocations={label:allocation(root,out,label,body,summaries[label]['procedure']) for label,body in (('normal',previous.SELECTED),('home',SELECTED))}
        print(json.dumps(dict(captures=summaries,allocation_final={label:r['final'] for label,r in allocations.items()}),indent=2),flush=True)
    else:print(json.dumps(qualify(root,out)[-1],indent=2),flush=True)
