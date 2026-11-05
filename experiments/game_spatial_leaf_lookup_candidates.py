"""Recover the inclusive point lookup through signed relative spatial records."""
import hashlib,json,struct
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner
from tools.pad_generated_object import parse_object
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_1510FD20','generated_13BB20'
SOURCE='conker/src/game/generated_13BB20.c'
ENTRY,ROM,WORDS=0x1510FD20,0x13D1D0,68
BUILD='conker/build/game-spatial-leaf-lookup-1510FD20-match'
PLACEHOLDER='u8 *func_1510FD20() {\n    return 0;\n}'
SELECTED='''/* Keep the N64's wrapping absolute difference, including INT_MIN. */
#define SPATIAL_ABS_13BB20(value) ((value) < 0 ? (s32)(0u - (u32)(value)) : (value))

/* Find the first containing leaf in the signed-relative spatial record chain. */
u8 *func_1510FD20(s32 x, s32 z) {
    u8 *node = D_800DBE48;
    s32 child;
    s32 offset;

    while (node != NULL) {
        child = *(s16 *)(node + 12);
        if (child != 0) {
            if (SPATIAL_ABS_13BB20((s32)((u32)x - (u32)*(s16 *)(node + 8))) <= *(u16 *)(node + 6) &&
                SPATIAL_ABS_13BB20((s32)((u32)z - (u32)*(s16 *)(node + 10))) <= *(u16 *)(node + 6)) {
                node += child;
            } else {
                offset = *(s16 *)(node + 4);
                if (offset != 0) node += offset;
                else node = NULL;
            }
        } else {
            if (SPATIAL_ABS_13BB20((s32)((u32)x - (u32)*(s16 *)(node + 8))) <= *(u16 *)(node + 6) &&
                SPATIAL_ABS_13BB20((s32)((u32)z - (u32)*(s16 *)(node + 10))) <= *(u16 *)(node + 6)) {
                return node;
            } else {
                offset = *(s16 *)(node + 4);
                if (offset != 0) node += offset;
                else node = NULL;
            }
        }
    }
    return NULL;
}

#undef SPATIAL_ABS_13BB20'''

REPAIRS={
 'conker/include/functions.h':(('s32  func_1510FD20(s32 arg0, s32 arg1);','u8 *func_1510FD20(s32 x, s32 z); /* First containing spatial leaf. */',1),),
 'conker/src/game/generated_10E240.c':(('s32 func_1510FD20(s32,s32);','u8 *func_1510FD20(s32, s32);',1),('packet.handle = func_1510FD20(','packet.handle = (s32)func_1510FD20(',1)),
 'conker/src/game/generated_1B6DB0.c':(('s32 func_1510FD20(s32, s32);','u8 *func_1510FD20(s32, s32);',1),('effect->spatialHandle = func_1510FD20(','effect->spatialHandle = (s32)func_1510FD20(',1)),
 'conker/src/game/done/game_3DB80.c':(('tmp.unk8 = func_1510FD20(','tmp.unk8 = (s32)func_1510FD20(',1),),
 'conker/src/game/done/game_3E460.c':(('D_800D9A40 = func_1510FD20(','D_800D9A40 = (s32)func_1510FD20(',1),),
 'conker/src/game_40490.c':(('*(s32 *)(data + 0xC) = func_1510FD20(','*(s32 *)(data + 0xC) = (s32)func_1510FD20(',1),('data.unk8 = func_1510FD20(','data.unk8 = (s32)func_1510FD20(',2)),
}

def repair_states(path,live):
    before=after=live;states=[]
    for old,new,count in REPAIRS[path]:
        if live.count(new)==count:before=before.replace(new,old);states.append(True)
        elif live.count(old)==count and new not in live:after=after.replace(old,new);states.append(False)
        else:raise ValueError('Spatial lookup interface changed: '+path)
    if len(set(states))!=1:raise ValueError('Partial spatial lookup interface installation: '+path)
    return before,after,states[0]

def source_states(live):
    if live.count(PLACEHOLDER)==1:
        after=live.replace(PLACEHOLDER,SELECTED,1).replace('u8 *func_1510FD20();','u8 *func_1510FD20(s32, s32);',1)
        return live,after,False
    if live.count(SELECTED)==1 and live.count('u8 *func_1510FD20(s32, s32);')==1:
        return live.replace(SELECTED,PLACEHOLDER,1).replace('u8 *func_1510FD20(s32, s32);','u8 *func_1510FD20();',1),live,True
    raise ValueError('Spatial leaf lookup source state changed')

def compare(body=SELECTED,label='selected'):
    out=ROOT/BUILD;out.mkdir(parents=True,exist_ok=True)
    source=source_states((ROOT/SOURCE).read_text())[1].replace(SELECTED,body,1)
    obj,diag=compile_owner(ROOT,out,source,label);text,fs,rs=parse_object(obj);f=fs[FUNCTION];start,size=f['value'],f['size']
    raw=text[start:start+size];linked,_=link_owner(ROOT,out,obj,OWNER);ours=linked[start:start+size];truth=(ROOT/'conker/conker.us.bin').read_bytes()[ROM:ROM+272]
    result=dict(words=size//4,raw_sha256=hashlib.sha256(raw).hexdigest(),retail_sha256=hashlib.sha256(truth).hexdigest(),diagnostics=diag,
      differences=[(i*4,hex(a),hex(b))for i,(a,b)in enumerate(zip(struct.unpack('>%dI'%(size//4),ours),struct.unpack('>68I',truth)))if a!=b],
      bindings={at-start:r for at,r in rs.items()if start<=at<start+size})
    (out/(label+'-screen.json')).write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':print(json.dumps(compare(),indent=2))
