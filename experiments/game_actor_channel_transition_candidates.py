"""Complete channel arbitration and transition, preserving live callback reads."""
import json
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_record_constructor_candidates as compiler

ENTRY,ROM,WORDS=0x1507E7E4,0xABC94,73
FUNCTION,SOURCE='func_1507E7E4','conker/src/game/generated_AB760.c'
ORIGINAL='#pragma GLOBAL_ASM("asm/nonmatchings/generated_AB760/func_1507E7E4.s")'
DECLARATIONS='''s32 func_1507E968(u8 *);
u8 *func_1507E908(u8 *, s32);
u8 *func_1507E9F8(u8 *, s32 *);
void func_150302F0(s32, s32);
void func_1507E5C8(u8 *, s32);
'''
SYMBOLS={name:int(name[5:],16) for name in
    ('func_1507E968','func_1507E908','func_1507E9F8','func_150302F0','func_1507E5C8')}
SELECTED='''void func_1507E7E4(u8 *actor, u8 channel, u8 priority, u16 duration, s32 amount) {
    u8 *definition;
    u8 *animations;
    s32 oldChannel = actor[0x6F];

    if (oldChannel == channel && actor[0x71] == priority &&
        *(u16 *)(actor + 0x72) == duration) {
        return;
    }
    if (priority == 3 || actor[0x70] == oldChannel || channel == oldChannel ||
        *(u16 *)(actor + 0x72) == 0 || actor[0x71] < priority) {
        if (channel < func_1507E968(actor)) {
            definition = func_1507E908(actor, actor[0x6F]);
            if (definition[4] != 0) {
                animations = func_1507E9F8(actor, 0);
                if (animations != 0) {
                    func_150302F0((s32)actor, animations[definition[4] - 1]);
                }
            }
            actor[0x6F] = channel;
            *(u16 *)(actor + 0x72) = duration;
            actor[0x71] = priority;
            func_1507E5C8(actor, amount);
        }
    }
}'''

# A closed t8/t9 swap and symmetric equality operands; no control-flow change.
PATCHES=((15,0x97B8003E,0x97B9003E),(16,0x14CF0004,0x15E60004),
    (18,0x96190072,0x96180072),(24,0x5069000A,0x5123000A),
    (26,0x50680008,0x51030008))


def normalize(words):
    if len(words)!=WORDS:raise ValueError('stale channel transition length')
    result=list(words)
    for index,expected,replacement in PATCHES:
        if result[index]!=expected:raise ValueError(('stale channel transition word',index,hex(result[index])))
        result[index]=replacement
    return result


def guard_rows():
    return [dict(filename='generated_AB760',function=FUNCTION,offset='0x%X'%(i*4),
        expected='0x%08X'%a,replacement='0x%08X'%b,expected_relocations='-',replacement_relocations='-',
        note='Normalize closed channel arbitration register swap and symmetric equality operands',
        insert_after='',insert_after_relocations='',omit='false') for i,a,b in PATCHES]


def candidates():
    yield 'selected',SELECTED
    for width in ('s32','u32'):
        yield 'old-'+width,SELECTED.replace('u8 oldChannel',width+' oldChannel')


def compile_candidate(root,out,name,body=SELECTED,profile='o2g3'):
    with patch.multiple(compiler,ENTRY=ENTRY,ROM=ROM,WORDS=WORDS,FUNCTION=FUNCTION,
            RECORD='',DECLARATIONS=DECLARATIONS,SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root,out,name,body,profile)


def install(before,body=SELECTED):
    if before.count(ORIGINAL)!=1:raise ValueError('stale channel transition owner')
    return before.replace(ORIGINAL,DECLARATIONS+'\n'+body)


def main():
    root=Path(__file__).resolve().parents[2];out=root/'conker/build/game-actor-channel-transition'
    records=[]
    for name,body in candidates():
        meta,_=compile_candidate(root,out,name,body);records.append(meta)
        print(name,meta['body_words'],meta['frame'],meta['differences'],flush=True)
    (out/'measurements.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':main()
