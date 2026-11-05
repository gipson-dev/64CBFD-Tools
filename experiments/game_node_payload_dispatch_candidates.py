"""Recover the filtered payload dispatcher and its four-word caller interface."""
import hashlib,json,struct
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner
from tools.pad_generated_object import parse_object
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_1514D3B0','generated_179F30'
SOURCE='conker/src/game/generated_179F30.c'
ENTRY,ROM,WORDS=0x1514D3B0,0x17A860,66
BUILD='conker/build/game-node-payload-dispatch-1514D3B0-match'
PLACEHOLDER='s32 func_1514D3B0() {\n    return 0;\n}'
DECLARATIONS='''typedef s32 (*GamePayloadCallback179F30)(s32, s32, s32);
extern GamePayloadCallback179F30 D_8008AB64[];
s32 func_1514D4B8(s16, s16);

'''
SELECTED='''/* Dispatch matching nodes and return the last invoked callback's boolean result. */
s32 func_1514D3B0(u8 *owner, s16 root, s32 first, s32 second) {
    GameListNode *node = *(GameListNode **)(owner + 0x2F4);
    s32 result = 0;
    s16 callback;

    while (node != NULL) {
        if (node->unk1C == root ||
            func_1514D4B8(D_8008ABE8[root][2], node->unk1C)) {
            callback = D_8008ABE8[node->unk1C][0];
            if ((u32)-1 != (u32)callback) {
                if (D_8008AB64[callback](node->unk10, first, second)) {
                    result = 1;
                } else {
                    result = 0;
                }
            }
        }
        node = node->next;
    }
    return result;
}'''
REPAIRS={
 'conker/include/functions.h':(('void func_1514D3B0(s32, s16, u8, u8);','s32 func_1514D3B0(u8 *owner, s16 root, s32 first, s32 second);',1),),
 'conker/src/game/generated_F2820.c':(('#include "structs.h"\n','#include "structs.h"\ns32 func_1514D3B0(u8 *, s16, s32, s32);\n',1),
   ('func_1514D3B0(arg0, 0x15,','func_1514D3B0((u8 *)arg0, 0x15,',2)),
 'conker/src/game_A28B0.c':(('func_1514D3B0(D_800D154C,','func_1514D3B0((u8 *)D_800D154C,',1),
   ('    u8 tmp1 = D_800D1891;\n    u8 tmp2 = D_800D1892;','    s32 tmp1 = D_800D1891;\n    s32 tmp2 = D_800D1892;',1)),
}

def source_states(live):
    if live.count(PLACEHOLDER)==1 and DECLARATIONS not in live:return live,live.replace(PLACEHOLDER,DECLARATIONS+SELECTED,1),False
    if live.count(DECLARATIONS+SELECTED)==1 and PLACEHOLDER not in live:return live.replace(DECLARATIONS+SELECTED,PLACEHOLDER,1),live,True
    raise ValueError('Node payload dispatcher source state changed')

def repair_states(path,live):
    before=after=live;states=[]
    for old,new,count in REPAIRS[path]:
        if live.count(new)==count:before=before.replace(new,old);states.append(True)
        elif live.count(old)==count and new not in live:after=after.replace(old,new);states.append(False)
        else:raise ValueError('Node dispatcher caller interface changed: '+path)
    if len(set(states))!=1:raise ValueError('Partial node dispatcher interface installation: '+path)
    return before,after,states[0]

def compare(body=SELECTED,label='selected',declarations=DECLARATIONS):
    out=ROOT/BUILD;out.mkdir(parents=True,exist_ok=True)
    text=source_states((ROOT/SOURCE).read_text())[1].replace(DECLARATIONS+SELECTED,declarations+body,1)
    obj,diag=compile_owner(ROOT,out,text,label);raw,fs,rs=parse_object(obj);f=fs[FUNCTION];start,size=f['value'],f['size'];body_bytes=raw[start:start+size]
    linked,_=link_owner(ROOT,out,obj,OWNER);ours=linked[start:start+size];truth=(ROOT/'conker/conker.us.bin').read_bytes()[ROM:ROM+264]
    result=dict(words=size//4,raw_sha256=hashlib.sha256(body_bytes).hexdigest(),retail_sha256=hashlib.sha256(truth).hexdigest(),diagnostics=diag,
        differences=[(i*4,hex(a),hex(b))for i,(a,b)in enumerate(zip(struct.unpack('>%dI'%(size//4),ours),struct.unpack('>66I',truth)))if a!=b],
        bindings={at-start:r for at,r in rs.items()if start<=at<start+size})
    (out/(label+'-screen.json')).write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':print(json.dumps(compare(),indent=2))
