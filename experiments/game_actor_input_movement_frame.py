"""Trace complete movement local homes with unchanged compiler and object gates."""
import hashlib
import json
from pathlib import Path
import re
import struct
from types import SimpleNamespace
from unittest.mock import patch

from tools.experiments import game_actor_input_movement_recovery as source
from tools.experiments import game_actor_callback_frame_trace as shared
from tools.experiments.game_frame_timing_frontend import procedure_records

BUILD='conker/build/game-actor-input-movement-frame'
PATHS,BASELINE=dict(source.PATHS),dict(source.BASELINE)
for key,path,sha in (
    ('movement_frame_predecessor_0','tools/experiments/game_actor_input_movement_recovery.py','f3e4060c0eda2b63f335c90e4d2862bc560dfe6efe359a1a79be837ae981554d'),
    ('movement_frame_predecessor_1','tools/tests/game_actor_input_movement_oracle.py','b7ea733ca1c364a84e16621e23c4077b40be68db6532d79542fc64dc2d624cd0'),
    ('movement_frame_predecessor_2','tools/tests/game_actor_input_movement_native.py','952c01b5f67a4628b42ef89dd8b159d7d9094a312533e5501701307f88356b68'),
    ('movement_frame_predecessor_3','tools/tests/test_game_actor_input_movement_recovery.py','5f715e3816d7f66bd1de7a8999094577183e8db4dc47089685a38fc4d9c27570'),
    ('movement_frame_predecessor_4','tools/experiments/game_actor_callback_frame_trace.py','b8e4ee3f4e562687dfd985b389a628cfec94142b0a2331c38e1a2af0cb62d717'),
    ('movement_frame_predecessor_5','tools/experiments/game_frame_timing_frontend.py','adbca97b506c263210a75ce08dec3abd17c96f8e2a5914b1ecce3aa33790298d'),
):
    if key in PATHS:raise ValueError('Duplicate movement frame input key')
    PATHS[key],BASELINE[key]=path,sha
RAW_SHA='704bac447c0f4f30022a305d7f24ec2c315766bfff235294704c1148da1fff3f'
MARKERS={
    'contact':'contactHeight = 0.0f;',
    'speed':'speed = actor->speed;',
    'input':'input = (f32)D_800CC284->y * 1.25f;',
    'angle':'angle = func_1505A630((f32)D_800CC284->x, (f32)D_800CC284->y, 0);',
    'distance':'distance = 1000.0f;',
    'index':'index = 0;',
    'record':'record = (MovementActor34F4 *)D_800CC2D0;',
    'distanceCall':'value = func_1505A6F8(D_800D154C, record);',
    'turn':'func_150599C8(actor, 8, angle);',
    'accelerationCall':'func_1505A3A8(actor->valueC0, actor, speed, rate, 1);',
}


def freeze(root,out):
    out.mkdir(parents=True,exist_ok=True)
    for key,path in PATHS.items():
        data=(root/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:raise ValueError('Changed movement frame predecessor: '+key)
        dest=out/('before-'+key)
        if not dest.exists():dest.write_bytes(data)
        if dest.read_bytes()!=data:raise ValueError('Changed movement frame frozen input: '+key)


def isolated(body):return '#include <ultra64.h>\n'+source.TYPE+'\n'+body+'\n'


DECLARATIONS=(('u16','angle'),('f32','input'),('f32','speed'),('f32','contactHeight'),
    ('f32','distance'),('f32','value'),('f32','amount'),('f32','rate'),('f32','magnitude'),
    ('f32','acceleration'),('f32','velocity'),('s32','index'),('s32','count'),('s32','animation'),
    ('MovementActor34F4 *','record'),('MovementInput34F4 *','controller'))


def declarations(items):return '\n'.join('    '+kind+('' if kind.endswith('*') else ' ')+name+';' for kind,name in items)


def reorder(body,items):
    before=declarations(DECLARATIONS)
    if body.count(before)!=1:raise ValueError('Changed movement local declarations')
    return body.replace(before,declarations(items),1)


def rename_region(body,start,end,name):
    if body.count(start)!=1 or body.count(end)!=1:raise ValueError('Changed movement split boundaries')
    lo=body.index(start);hi=body.index(end,lo)
    segment=body[lo:hi]
    if not re.search(r'\bvalue\b',segment):raise ValueError('No movement value to split')
    return body[:lo]+re.sub(r'\bvalue\b',name,segment)+body[hi:]


def forms():
    types=dict((name,kind) for kind,name in DECLARATIONS)
    ordered=('angle','amount','rate','magnitude','input','speed','acceleration','velocity',
             'value','contactHeight','distance','index','count','animation','record','controller')
    yield 'selected',source.SELECTED
    yield 'ordered-homes',reorder(source.SELECTED,[(types[n],n) for n in ordered])
    body=source.SELECTED
    splits=(('        value = func_1505A5CC(D_800CC284);','        if ((D_800CC288 & 0xC000)','initialMagnitude'),
        ('                    value = func_1505A6F8(D_800D154C, record);','                index++;','nearestDistance'),
        ('        value = actor->valueC4;','        actor->turnStep = 25;','previousInput'),
        ('        actor->flagAD = 10;','        speed = actor->verticalVelocity;','pitchValue'))
    for start,end,name in splits:body=rename_region(body,start,end,name);types[name]='f32'
    extra=tuple(('f32',n) for _,_,n in splits)
    yield 'split-values',reorder(body,(*DECLARATIONS,*extra))
    names=('angle','amount','rate','magnitude','input','speed','acceleration','velocity','value',
        'contactHeight','initialMagnitude','index','nearestDistance','distance','previousInput','pitchValue',
        'count','animation','record','controller')
    yield 'split-ordered-homes',reorder(body,[(types[n],n) for n in names])


def screens(root,out):
    freeze(root,out);rows=[]
    for name,body in forms():
        _,_,row=source.measure(root,out,name,body)
        rows.append(dict(name=name,**row))
        print(name,json.dumps({k:v for k,v in row.items() if k!='bindings'}),flush=True)
    (out/'screens.json').write_text(json.dumps(rows,indent=2)+'\n')
    return rows


def fitting_forms():
    base=dict(forms())['split-ordered-homes']
    yield 'fitted-layout',base
    cast=base.replace('animation & 0xFFFF','(u16)animation')
    direct=base.replace('animation & 0xFFFF','animation')
    yield 'animation-cast',cast
    yield 'animation-implicit',direct
    for name,body in (('heading-wide',base),('heading-wide-cast',cast),('heading-wide-implicit',direct)):
        body=body.replace('    MovementInput34F4 *controller;',
            '    MovementInput34F4 *controller;\n    u32 heading;')
        body=body.replace('        angle = actor->heading - (s32)',
            '        heading = (u32)actor->heading - (u32)(s32)')
        body=body.replace('        actor->heading = angle;\n        func_150599C8(actor, 8, angle);',
            '        actor->heading = heading;\n        func_150599C8(actor, 8, (u16)heading);')
        yield name,body
    typed=cast.replace('(MovementActor34F4 *)(D_800CC2D0 + (actor->held - 100) * 0x32C)',
        '(MovementActor34F4 *)D_800CC2D0 + (actor->held - 100)').replace(
        '(MovementActor34F4 *)(D_800CC2D0 +\n                              (actor->held - 100) * 0x32C)',
        '(MovementActor34F4 *)D_800CC2D0 + (actor->held - 100)')
    if typed==cast:raise ValueError('Movement typed-array control made no change')
    yield 'typed-link-addresses',typed


def fitting_screens(root,out):
    freeze(root,out);rows=[]
    for name,body in fitting_forms():
        _,_,row=source.measure(root,out,name,body)
        rows.append(dict(name=name,**row))
        print(name,json.dumps({k:v for k,v in row.items() if k!='bindings'}),flush=True)
    (out/'fitting-screens.json').write_text(json.dumps(rows,indent=2)+'\n')
    return rows


FITTED_NAME='heading-wide-cast'
FITTED_SHA='ee524ca5c671259f8ab349b7e6da08682ffc07fb09077428c8cdf659d5f50eb7'


def fitted_body():return dict(fitting_forms())[FITTED_NAME]


def global_controller_body():
    body=fitted_body()
    before='    controller = *D_800BE728;\n    D_800CC284 = controller;'
    if body.count(before)!=1 or body.count('        controller->x = 0;')!=1:
        raise ValueError('Changed initial movement controller snapshot')
    return body.replace('    MovementInput34F4 *controller;\n','',1).replace(
        before,'    D_800CC284 = *D_800BE728;',1).replace(
        '        controller->x = 0;','        D_800CC284->x = 0;',1)


def summary(record,content,markers=MARKERS):
    if record.get('code_unchanged') is not True:raise ValueError('Unqualified movement compiler capture')
    phases=record['records'];entries=[r for r in phases['frontend'] if r['name']=='ent']
    if len(entries)!=1:raise ValueError('Movement trace must contain one procedure')
    procedure=entries[0]['block']
    positions={}
    for key,statement in markers.items():
        lines=[i+1 for i,line in enumerate(content.splitlines()) if line.strip()==statement]
        if len(lines)!=1:raise ValueError('Missing/ambiguous movement marker: '+key)
        positions[key]=lines[0]
    result=dict(procedure=procedure,source_lines=positions,events=record['events'],phases={})
    for name in ('frontend','optimizer'):
        rows=procedure_records(phases[name],procedure);current=None;selected={key:[] for key in markers}
        for row in rows:
            if row['name']=='loc':current=row['words'][1]
            for key,line in positions.items():
                if current==line and row['name'] in ('lda','lod','str','rlda','def','vreg','par','cup'):
                    selected[key].append(row)
        result['phases'][name]=dict(records=len(rows),definitions=[r for r in rows if r['name']=='def'],markers=selected)
    return result


def trace(root,out,name='selected',body=source.SELECTED,shape=(962,112,RAW_SHA)):
    freeze(root,out)
    expected,_,row=source.measure(root,root/source.BUILD,name,body)
    if (row['words'],row['frame'],row['raw_sha'])!=shape:raise ValueError('Changed complete movement trace source')
    def compile_candidate(root,work,label,body):
        content=isolated(body)
        obj,diagnostics=source.compile_owner(root,work,content,label)
        if diagnostics:raise ValueError('Movement isolated compiler diagnostics: '+repr(diagnostics))
        if source.parts(obj)!=source.parts(expected):raise ValueError('Movement isolation changed words or relocations')
        _,functions,_=source.parse_object(obj)
        if set(functions)!={source.FUNCTION}:raise ValueError('Extra isolated movement procedure')
        words=source.linked(root,work,obj,label+'-linked')
        return dict(words=len(words),frame=(-words[0])&65535,raw_sha=shape[2],whole_owner_target_identical=True),words
    with patch.object(shared,'screen',SimpleNamespace(compile_candidate=compile_candidate)):
        record=shared.trace(root,out,name,body)
    work=out/name;content=(work/'baseline.c').read_text()
    if content!=isolated(body):raise ValueError('Changed movement source capture')
    markers=dict(MARKERS)
    if 'nearestDistance = func_1505A6F8' in body:
        markers['distanceCall']='nearestDistance = func_1505A6F8(D_800D154C, record);'
    if '    u32 heading;' in body:
        markers['turn']='func_150599C8(actor, 8, (u16)heading);'
    result=summary(record,content,markers)
    result.update(source_sha=hashlib.sha256(content.encode()).hexdigest(),compiler_sha256=record['compiler_sha256'],
        code_unchanged=True,whole_owner_target_identical=True,installable=False)
    words=list(struct.unpack_from('>%dI'%shape[0],source.projection.sections(work/'baseline-linked.elf')['.text'][1]))
    result['layout']=check_layout(result,words,name)
    freeze(root,out)
    (work/'movement-summary.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def check_layout(result,words,form):
    expected={
        'selected':(64,60,112,{'contact':-16,'speed':-12,'input':-8,'angle':-2,'distance':-20,'index':-48,'record':-60,'distanceCall':-24}),
        'split-values':(80,60,112,{'contact':-16,'speed':-12,'input':-8,'angle':-2,'distance':-20,'index':-48,'record':-60,'distanceCall':-72}),
        'split-ordered-homes':(80,76,128,{'contact':-40,'speed':-24,'input':-20,'angle':-2,'distance':-56,'index':-48,'record':-76,'distanceCall':-52}),
        FITTED_NAME:(84,76,128,{'contact':-40,'speed':-24,'input':-20,'angle':-2,'distance':-56,'index':-48,'record':-76,'distanceCall':-52})}
    if form not in expected or result.get('code_unchanged') is not True or result.get('whole_owner_target_identical') is not True:
        raise ValueError('Unqualified movement layout form')
    front,opt,frame,homes=expected[form]
    def unique(rows):
        if len(rows)!=1:raise ValueError('Ambiguous movement storage operand')
        return rows[0]
    phases=result['phases']
    observed=[unique([r['length'] for r in phases[p]['definitions'] if r['storage']=='M']) for p in ('frontend','optimizer')]
    actual={}
    for name in homes:
        row=unique([r for r in phases['frontend']['markers'][name] if r['name']=='str' and r['storage']=='M'])
        kind,size=('L',2) if name=='angle' else ('J',4) if name=='index' else ('A',4) if name=='record' else ('R',4)
        if (row['dtype'],row['length'])!=(kind,size):raise ValueError('Changed movement storage width/type: '+name)
        actual[name]=row['offset']
    events=result['events'];last=events[-1] if events else {}
    if (observed!=[front,opt] or actual!=homes
            or [e['event'] for e in events]!=['frame-watch-installed','frame-write','frame-write','frame-write']
            or [e['frame'] for e in events]!=[0,16,48,frame]
            or [e['host_pc'] for e in events]!=[4268224,4566873,4523375,4523375]
            or [(e['saved'],e['outgoing'],e['locals']) for e in events]!=[(0,0,0),(16,0,0),(16,32,0),(16,32,(opt+7)&~7)]
            or any(e['pool'] or e['temporary'] or e['temp_base'] for e in events)
            or (last['saved'],last['outgoing'],last['locals'])!=(16,32,(opt+7)&~7)
            or words[0]!=(0x27BD0000|((-frame)&65535))
            or words[5]!=(0xE7B00000|((frame+homes['contact'])&65535))):
        raise ValueError('Changed movement wire/frame/contact-home evidence')
    call=words.index(0x0D41698C);following=words.index(0x0D416973)
    angle=(frame+homes['angle'])&65535
    if sum(w>>26==41 and w>>21&31==29 and w&65535==angle for w in words[call+1:following+2])!=1:
        raise ValueError('Movement angle home does not match emitted store')
    call=words.index(0x0D4169BE);window=words[call-5:call+2]
    for name,op in (('index',43),('record',43),('distance',57)):
        if sum(w>>26==op and w>>21&31==29 and w&65535==(frame+homes[name])&65535 for w in window)!=1:
            raise ValueError('Movement live call-save home disagrees with UCODE: '+name)
    return dict(frontend_local_bytes=front,optimizer_local_bytes=opt,ugen_aligned_local_bytes=(opt+7)&~7,
        frame=frame,saved_area_budget=16,outgoing_area_budget=32,caller_relative=homes,
        emitted_contact_angle_and_three_call_save_homes_checked=True,late_frame_growth=False,
        original_source_declarations_not_proven=True,installable=False)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--screens',action='store_true')
    parser.add_argument('--fitting-screens',action='store_true')
    parser.add_argument('--form',choices=('selected','split-values','split-ordered-homes',FITTED_NAME),default='selected')
    args=parser.parse_args();root=Path(__file__).resolve().parents[2]
    if args.screens:
        screens(root,root/BUILD)
        raise SystemExit(0)
    if args.fitting_screens:
        fitting_screens(root,root/BUILD)
        raise SystemExit(0)
    bodies=dict(forms());bodies[FITTED_NAME]=fitted_body()
    shapes={'selected':(962,112,RAW_SHA),
        'split-values':(962,112,'b49516a6dd5dbff2f60cabc3766d49bc826f5fa084f0111f809a018bfab97b50'),
        'split-ordered-homes':(962,128,'36e000ec396e357d5a92fce7faac1f70fe0f584da5982b4f956d468b99004de7'),
        FITTED_NAME:(959,128,FITTED_SHA)}
    result=trace(root,root/BUILD,args.form,bodies[args.form],shapes[args.form])
    print(json.dumps(dict(procedure=result['procedure'],events=result['events'],
        phases={k:dict(records=v['records'],definitions=v['definitions']) for k,v in result['phases'].items()},
        code_unchanged=result['code_unchanged']),indent=2),flush=True)
