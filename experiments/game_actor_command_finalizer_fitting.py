"""Bounded source-layout screens and owned frame observations for the finalizer."""
import argparse
import difflib
import itertools
import json
import struct
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tools.experiments import game_actor_command_finalizer_candidates as recovery
from tools.experiments import game_actor_callback_frame_trace as observer

BASE=recovery.SELECTED
FIELDS='''typedef struct {
    u8 prefix[4];
    u8 type;
    u8 gap[0x1F9];
    u8 primaryValue, primaryState, primaryTimer, primaryScale;
    s8 primaryNoise, primaryVelocity;
    s16 secondaryValue;
    u8 secondaryState, secondaryTimer;
    s8 secondaryScale, secondaryVelocity;
} ActorFinalizerFields;
'''
COMMAND='typedef struct { s16 tag, value; } ActorFinalizerCommand;\n'


def field_view(body):
    body=body.replace('    s32 suppressed;','    ActorFinalizerFields *fields = (ActorFinalizerFields *)actor;\n    s32 suppressed;')
    names={4:'type',0x1FE:'primaryValue',0x1FF:'primaryState',0x200:'primaryTimer',
        0x201:'primaryScale',0x202:'primaryNoise',0x203:'primaryVelocity',
        0x204:'secondaryValue',0x206:'secondaryState',0x207:'secondaryTimer',
        0x208:'secondaryScale',0x209:'secondaryVelocity'}
    for offset,name in names.items():
        token='4' if offset==4 else '0x%X'%offset
        body=body.replace('actor['+token+']','fields->'+name)
        for kind in ('s8','s16'):
            body=body.replace('*('+kind+' *)(actor + '+token+')','fields->'+name)
    return body


def halfword_view(body,parameter=False):
    if parameter:
        body=body.replace('u8 *output,','s16 *output,')
    else:
        body=body.replace('u8 *output,','u8 *storage,').replace('    s32 suppressed;',
            '    s16 *output = (s16 *)storage;\n    s32 suppressed;')
    return body.replace('*(s16 *)(output + 2)','output[1]').replace('*(s16 *)output','output[0]').replace(
        'output += 4','output += 2')


def command_view(body):
    return body.replace('u8 *output,','u8 *storage,').replace('    s32 suppressed;',
        '    ActorFinalizerCommand *output = (ActorFinalizerCommand *)storage;\n    s32 suppressed;').replace(
        '*(s16 *)(output + 2)','output->value').replace('*(s16 *)output','output->tag').replace(
        'output += 4','output++')


def clamp_local(body):
    return body.replace('        value = value < 256 ? value : limit;',
        '        current = value < 256 ? value : limit;\n        value = current;')


def parameter_homes(body,gate=True,tags=True):
    body=body.replace('s32 first,','volatile s32 first,')
    if gate:
        body=body.replace('    s32 type = actor[4];',
            '    s32 type = actor[4];\n    s32 firstGate = first;')
        body=body.replace('    if (first != limit)','    if (firstGate != limit)')
    if tags:
        body=body.replace('    s32 suppressed;','    s32 primaryIndex;\n    s32 suppressed;')
        body=body.replace('        value = (s32)((f32)(u32)actor[0x1FE]',
            '        primaryIndex = first;\n        value = (s32)((f32)(u32)actor[0x1FE]',1)
        body=body.replace('        value = (s32)((f32)(*(s8 *)(actor + 0x202)',
            '        primaryIndex = first;\n        value = (s32)((f32)(*(s8 *)(actor + 0x202)',1)
        body=body.replace('(u32)first * 6','(u32)primaryIndex * 6')
    return body


def control_flow(body,noise=0,late_lower=False,tail=False,value_type=False):
    old='''    if (type == 0x69 || type == 0x7C || type == 0x87) {
        noise = 0;
    } else {
        noise = 10;
    }'''
    if noise==1:
        new='''    noise = 10;
    if (type == 0x69 || type == 0x7C || type == 0x87) {
        noise = 0;
    }'''
        body=body.replace(old,new)
    elif noise==2:
        new='''    noise = 0;
    if (type != 0x69 && type != 0x7C && type != 0x87) {
        noise = 10;
    }'''
        body=body.replace(old,new)
    if late_lower:
        body=body.replace('    lower = 40;\n','',1).replace('        primaryIndex = first;\n',
            '        lower = 40;\n        primaryIndex = first;\n',1)
    if tail:
        marker='\n        delta = *(s8 *)(actor + 0x209);\n        *(s16 *)(actor + 0x204) += delta;\n'
        assert body.count(marker)==1
        head,body=body.split(marker,1)
        body=body.replace('        current = *(s16 *)(actor + 0x204);\n        if (sign > 0) {',
            '        if (sign > 0) {\n            value = *(s16 *)(actor + 0x204);')
        body=body.replace('            if (current < 0 && delta < 0)','            if (value < 0 && delta < 0)').replace(
            '            } else if (current >= 256)','            } else if (value >= 256)')
        body=body.replace('        } else {\n            if (current > 0 && delta > 0)',
            '        } else {\n            value = *(s16 *)(actor + 0x204);\n            if (value > 0 && delta > 0)').replace(
            '            } else if (current < -255)','            } else if (value < -255)')
        body=head+marker+body
    if value_type:
        body=body.replace('    s16 value;','    s16 value = actor[4];').replace('    s32 type = actor[4];\n','')
        body=body.replace('type ==','value ==').replace('type !=','value !=')
    return body


def early_sign(body):
    return body.replace('        sign = 1;\n','',1).replace('    if (second != limit) {',
        '    if (second != limit) {\n        sign = 1;',1)


def explicit_bounds(body):
    return body.replace('        upper = 60;\n','',1).replace('            upper = 120;\n        }',
        '            upper = 120;\n        } else {\n            upper = 60;\n        }',1)


def capture_numeric_inputs(body,primary=False,product=False):
    if primary:
        body=body.replace('        primaryIndex = first;\n        value = (s32)((f32)(u32)actor[0x1FE]',
            '        current = actor[0x1FE];\n        primaryIndex = first;\n        value = (s32)((f32)(u32)current',1)
    if product:
        body=body.replace('        primaryIndex = first;\n        value = (s32)((f32)(*(s8 *)(actor + 0x202) * actor[0x1FE] / limit)',
            '        current = actor[0x1FE] * *(s8 *)(actor + 0x202);\n        primaryIndex = first;\n        value = (s32)((f32)(current / limit)',1)
    return body


def sign_control(body,mode):
    body=body.replace('        sign = 1;\n','',1)
    old='''        if (scale < 0.0f) {
            sign = -1;
        }'''
    choices=(
        '''        if (scale < 0.0f) {
            sign = -1;
        } else {
            sign = 1;
        }''',
        '''        sign = scale < 0.0f ? -1 : 1;''',
        '''        if (!(scale < 0.0f)) {
            sign = 1;
        } else {
            sign = -1;
        }''')
    return body.replace(old,choices[mode])


def switch_noise(body):
    selector='value' if '    s16 value = actor[4];' in body else 'type'
    old='''    if (%s == 0x69 || %s == 0x7C || %s == 0x87) {
        noise = 0;
    } else {
        noise = 10;
    }'''%(selector,selector,selector)
    new='''    switch (%s) {
        case 0x69:
        case 0x7C:
        case 0x87:
            noise = 0;
            break;
        default:
            noise = 10;
            break;
    }'''%selector
    assert old in body
    return body.replace(old,new)


def candidates():
    yield 'baseline',BASE,''
    for name,body,record in (
            ('halfword-local',halfword_view(BASE),''),
            ('halfword-parameter',halfword_view(BASE,True),''),
            ('command-local',command_view(BASE),COMMAND),
            ('actor-fields',field_view(BASE),FIELDS),
            ('actor-fields-halfwords',field_view(halfword_view(BASE)),FIELDS),
            ('actor-fields-commands',field_view(command_view(BASE)),FIELDS+COMMAND)):
        yield name,body,record
        yield name+'-clamp',clamp_local(body),record
    # Width controls are diagnostic only: the banked contract accepts full words.
    for kind in ('s16','u16','s8','u8','register s32'):
        yield kind.replace(' ','-')+'-first',BASE.replace('s32 first,',kind+' first,'),''
    header='''    s32 suppressed;
    s32 primaryBias;
    s32 secondaryBias;
    s32 noise;
    s32 limit;
    s32 lower;
    s32 upper;
    s32 sign;
    s32 choose;
    s32 reverse;
    s32 current;
    s32 delta;
    s16 value;
    f32 scale;
    f32 magnitude;
    s32 type = actor[4];'''
    groups=(('s32 suppressed;','s32 primaryBias;','s32 secondaryBias;','s32 noise;','s32 limit;'),
        ('s32 lower;','s32 upper;','s32 sign;','s32 choose;','s32 reverse;'),
        ('s32 current;','s32 delta;','s16 value;','f32 scale;','f32 magnitude;'))
    for index,order in enumerate(itertools.permutations(range(3))):
        replacement='\n'.join('    '+item for i in order for item in groups[i])+'\n    s32 type = actor[4];'
        yield 'local-groups-'+str(index),BASE.replace(header,replacement),''
    for gate,tags,fields,clamp in itertools.product((False,True),(False,True),(False,True),(False,True)):
        if not gate and not tags:
            continue
        body=parameter_homes(BASE,gate,tags)
        if fields:
            body=field_view(body)
        if clamp:
            body=clamp_local(body)
        name='homes-g%d-t%d-f%d-c%d'%(gate,tags,fields,clamp)
        yield name,body,FIELDS if fields else ''
    for noise,lower,tail,value in itertools.product(range(3),(False,True),(False,True),(False,True)):
        body=control_flow(clamp_local(parameter_homes(BASE,False,True)),noise,lower,tail,value)
        yield 'control-n%d-l%d-t%d-v%d'%(noise,lower,tail,value),body,''
    for noise,sign,bounds in itertools.product(range(3),(False,True),(False,True)):
        body=control_flow(clamp_local(parameter_homes(BASE,False,True)),noise,False,True,True)
        if sign:
            body=early_sign(body)
        if bounds:
            body=explicit_bounds(body)
        yield 'branches-n%d-s%d-b%d'%(noise,sign,bounds),body,''
    for primary,product in itertools.product((False,True),repeat=2):
        body=explicit_bounds(early_sign(control_flow(
            clamp_local(parameter_homes(BASE,False,True)),0,False,True,True)))
        yield 'inputs-p%d-m%d'%(primary,product),capture_numeric_inputs(body,primary,product),''
    base=capture_numeric_inputs(explicit_bounds(early_sign(control_flow(
        clamp_local(parameter_homes(BASE,False,True)),0,False,True,True))),True,False)
    for mode in range(3):
        yield 'sign-'+str(mode),sign_control(base,mode),''
        body=sign_control(base,mode).replace('    s32 current;','    s16 current;')
        yield 'sign-'+str(mode)+'-short-current',body,''
    for gate,primary in itertools.product((False,True),repeat=2):
        body=explicit_bounds(early_sign(control_flow(clamp_local(parameter_homes(BASE,gate,True)),
            0,False,True,True)))
        body=sign_control(capture_numeric_inputs(body,primary,False),0)
        yield 'switch-g%d-p%d'%(gate,primary),switch_noise(body),''


def compile_candidate(root,out,name,body,record=''):
    with patch.object(recovery,'DECLARATIONS',recovery.DECLARATIONS+record):
        return recovery.compile_candidate(root,out,name,body)


def trace(root,out,name,body=BASE,record=''):
    def compile_adapter(root,work,name,source):
        return compile_candidate(root,work,name,source,record)
    with patch.object(observer,'screen',SimpleNamespace(compile_candidate=compile_adapter)):
        return observer.trace(root,out,name,body)


def instruction_shape(word):
    op,rs,rt,rd,shift,fn=word>>26,word>>21&31,word>>16&31,word>>11&31,word>>6&31,word&63
    if op==0:
        return op,fn,shift,rs==0,rt==0,rd==0
    if op==17:
        return op,rs,rt if rs==8 else fn
    if op in (1,4,5,6,7,20,21,22,23):
        return op,rt if op==1 else 0,rs==0,rt==0
    if op in (2,3):
        return op,
    return op,word&65535,rs==29,rs==0,rt==0


def shape_differences(original,candidate):
    matcher=difflib.SequenceMatcher(None,list(map(instruction_shape,original)),
        list(map(instruction_shape,candidate)),autojunk=False)
    return [dict(retail=(a*4,b*4),source=(c*4,d*4),
        retail_words=['%08X'%x for x in original[a:b]],source_words=['%08X'%x for x in candidate[c:d]])
        for tag,a,b,c,d in matcher.get_opcodes() if tag!='equal']


FITTED_NAME='sign-0'
FITTED, FITTED_RECORD={name:(body,record) for name,body,record in candidates()}[FITTED_NAME]


def recovered_owner(source):
    if source.count(BASE)==1:
        return source.replace(BASE,FITTED,1)
    if source.count(FITTED)==1:
        return source
    raise ValueError('Expected the banked complete body or known fitting candidate')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace',action='store_true')
    parser.add_argument('--name',default='baseline')
    parser.add_argument('--filter',default='')
    parser.add_argument('--shape',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    out=root/'conker/build/game-actor-command-finalizer-fitting'
    out.mkdir(exist_ok=True)
    forms={name:(body,record) for name,body,record in candidates()}
    if args.shape:
        body,record=forms[args.name]
        meta,words=compile_candidate(root,out,args.name,body,record)
        retail=struct.unpack_from('>405I',(root/'conker/conker.us.bin').read_bytes(),recovery.ROM)
        result=dict(shape=meta,differences=shape_differences(retail,words))
        (out/(args.name+'-shape.json')).write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(dict(shape={k:meta[k] for k in ('body_words','frame','differences')},
            differences=result['differences']),indent=2))
        return
    if args.trace:
        body,record=forms[args.name]
        result=trace(root,out,args.name,body,record)
        text={k:result[k] for k in ('baseline','inputs','events','code_unchanged')}
        text['records']={k:len(v) for k,v in result['records'].items()}
        print(json.dumps(text,indent=2))
        return
    records=[]
    for name,(body,record) in forms.items():
        if args.filter not in name:
            continue
        meta,_=compile_candidate(root,out,name,body,record)
        records.append(meta)
        print(name,meta['body_words'],hex(meta['frame']),meta['differences'],flush=True)
    (out/('measurements-'+(args.filter or 'all')+'.json')).write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':
    main()
