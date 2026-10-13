"""Screen scalar representations without narrowing selectors or changing ABI."""
import argparse
import json
from pathlib import Path
import struct

from tools.experiments import game_actor_command_finalizer_opening as previous

BASE=previous.SELECTED


def unsigned_value(body):
    body=previous.flow.replace_once(body,'    s16 value = actor[4];','    u16 value = actor[4];')
    for token in ('value < 0','value < 256','value >= 256','value > 0','value < -255'):
        assert token in body,token
        body=body.replace(token,'(s16)'+token)
    return previous.flow.replace_once(body,'? value : limit','? (s16)value : limit')


def unsigned_delta(body):
    body=previous.flow.replace_once(body,'    s32 delta;','    u32 delta;')
    for token in ('delta < 0','delta > 0'):
        assert token in body
        body=body.replace(token,'(s32)'+token)
    return body


def unsigned_predicates(body,which,cast=False):
    head,tail=body.split('    limit = 0xFF;',1)
    literals={'bias':('0x7C',),'noise':('0x69','0x87'),'all':('0x70','0x7C','0x69','0x87')}[which]
    for literal in literals:
        assert literal in head
        head=head.replace(literal,literal+'U')
    if cast:
        head=head.replace('value ==','(u32)value ==').replace('delta ==','(u32)delta ==')
        head=head.replace('(delta = value) ==','(u32)(delta = value) ==')
    return head+'    limit = 0xFF;'+tail


def noise_views(body,first=False,bias=False):
    head,tail=body.split('    limit = 0xFF;',1)
    if first:
        head=previous.flow.replace_once(head,'(delta = value) == 0x69','(u32)(delta = value) == 0x69U')
    if bias:
        head=previous.flow.replace_once(head,'value == 0x7C','(u32)value == 0x7CU')
    for literal in ('0x7C','0x87'):
        head=previous.flow.replace_once(head,'delta == '+literal,'(u32)delta == '+literal+'U')
    return head+'    limit = 0xFF;'+tail


def upper_arms(body,ternary=False):
    old='''        upper = 60;
        if (actor[4] == 0x42) {
            lower = 80;
            upper = 120;
        }'''
    if ternary:
        new='''        if (actor[4] == 0x42) {
            lower = 80;
        }
        upper = actor[4] == 0x42 ? 120 : 60;'''
    else:
        new='''        upper = 120;
        if (actor[4] != 0x42) {
            upper = 60;
        } else {
            lower = 80;
        }'''
    return previous.flow.replace_once(body,old,new)


def cached_noise(body,mode):
    body=previous.flow.replace_once(body,'value == 0x7C','(u32)value == 0x7CU')
    if mode==0:
        head='value == 0x69 || (u32)(delta = value) == 0x7CU'
        tail='(u32)delta == 0x87U'
    elif mode==1:
        head='value == 0x69 || (u32)delta == 0x7CU'
        tail='(u32)delta == 0x87U'
    else:
        assert mode==2
        head='value == 0x69 || (u32)value == 0x7CU'
        tail='(u32)value == 0x87U'
    body=previous.flow.replace_once(body,'(delta = value) == 0x69 || delta == 0x7C',head)
    body=previous.flow.replace_once(body,'delta == 0x87',tail)
    if mode==1:
        marker='    if ('+head+')'
        body=previous.flow.replace_once(body,marker,'    delta = value;\n'+marker)
    return body


def early_lower(body):
    body=previous.flow.replace_once(body,'        lower = 40;\n','')
    return previous.flow.replace_once(body,'    limit = 0xFF;','    limit = 0xFF;\n    lower = 40;')


def category_local(body):
    body=previous.flow.replace_once(body,'    s16 value = actor[4];',
        '    u8 category = actor[4];\n    s16 value;')
    head,tail=body.split('    limit = 0xFF;',1)
    head=head.replace('value ==','category ==').replace('(delta = value)','(delta = category)')
    return head+'    limit = 0xFF;'+tail


def merged_noise(body,inverted=False):
    old='''    if ((u32)(delta = value) == 0x69U || (u32)delta == 0x7CU) {
        noise = 0;
    } else {
        if ((u32)delta == 0x87U) {
            noise = 0;
        } else {
            noise = 10;
        }
    }'''
    new='''    if ((u32)(delta = value) == 0x69U || (u32)delta == 0x7CU || (u32)delta == 0x87U) {
        noise = 0;
    } else {
        noise = 10;
    }'''
    if inverted:
        new='''    if ((u32)(delta = value) != 0x69U && (u32)delta != 0x7CU && (u32)delta != 0x87U) {
        noise = 10;
    } else {
        noise = 0;
    }'''
    return previous.flow.replace_once(body,old,new)


def candidates():
    yield 'baseline',BASE
    for name,kind in (('value','s16'),('delta','s32'),('current','s32'),('limit','s32'),
            ('choose','s32'),('reverse','s32')):
        token='    '+kind+' '+name
        assert BASE.count(token)==1
        yield 'register-'+name,BASE.replace(token,'    register '+kind+' '+name,1)
    yield 'unsigned-value',unsigned_value(BASE)
    yield 'unsigned-delta',unsigned_delta(BASE)
    yield 'unsigned-value-and-delta',unsigned_delta(unsigned_value(BASE))
    for name in ('noise','lower','upper'):
        yield 'unsigned-'+name,previous.flow.replace_once(BASE,'    s32 '+name+';','    u32 '+name+';')
    for which in ('bias','noise','all'):
        for cast in (False,True):
            yield 'predicates-%s-c%d'%(which,cast),unsigned_predicates(BASE,which,cast)
    for first in (False,True):
        for bias in (False,True):
            yield 'noise-views-f%d-b%d'%(first,bias),noise_views(BASE,first,bias)
    body=noise_views(BASE,True,True)
    yield 'balanced-clamp',previous.flow.clamp(body)
    yield 'balanced-upper-arms',upper_arms(body)
    yield 'balanced-upper-ternary',upper_arms(body,True)
    yield 'balanced-early-lower',early_lower(body)
    for mode in range(3):
        yield 'cache-'+str(mode),cached_noise(BASE,mode)
    for views in (False,True):
        body=BASE if not views else noise_views(BASE,True,True)
        body=category_local(body)
        yield 'category-v%d'%views,body
        yield 'category-v%d-forward'%views,previous.flow.clamp(body)
    body=noise_views(BASE,True,True)
    for inverted in (False,True):
        form=merged_noise(body,inverted)
        yield 'merged-i%d'%inverted,form
        yield 'merged-i%d-early-lower'%inverted,early_lower(form)
    for views in (False,True):
        body=BASE if not views else noise_views(BASE,True,True)
        head,tail=body.split('    limit = 0xFF;',1)
        declarations,logic=head.split('    if (value == 0x70)',1)
        head=declarations+'    if (value == 0x70)'+logic.replace('delta','current')
        yield 'current-cache-v%d'%views,head+'    limit = 0xFF;'+tail


SELECTED_NAME='merged-i1'
SELECTED=dict(candidates())[SELECTED_NAME]


def recovered_owner(source):
    if source.count(BASE)==1:
        return source.replace(BASE,SELECTED,1)
    if source.count(SELECTED)==1:
        return source
    raise ValueError('Expected the banked opening body or selected scalar fit')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter',default='')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    out=root/'conker/build/game-actor-command-finalizer-scalar'
    out.mkdir(exist_ok=True)
    retail=list(struct.unpack_from('>405I',(root/'conker/conker.us.bin').read_bytes(),
        previous.flow.roles.fitting.recovery.ROM))
    records=[]
    for name,body in candidates():
        if args.filter not in name:continue
        record,words=previous.flow.roles.fitting.compile_candidate(root,out,name,body)
        record['opening']=previous.opening(words,retail)
        records.append(record)
        print(name,record['body_words'],hex(record['frame']),record['differences'],
            record['opening']['cut5_GPRs'],record['opening']['retail_selector_load_indices'],flush=True)
    (out/('measurements-'+(args.filter or 'all')+'.json')).write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':
    main()
