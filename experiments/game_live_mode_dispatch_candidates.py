"""Recover the live mode callback, input suppression and transition timer."""
import hashlib,json,struct
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner
from tools.pad_generated_object import parse_object
ROOT=Path(__file__).resolve().parents[2]
FUNCTION,OWNER='func_151E51EC','generated_20AE20'
SOURCE='conker/src/game/generated_20AE20.c'
ENTRY,ROM,WORDS=0x151E51EC,0x21269C,72
BUILD='conker/build/game-live-mode-dispatch-151E51EC-match'
PLACEHOLDER='s32 func_151E51EC() {\n    return 0;\n}'
DECLARATIONS='''extern s32 D_8003C8E0;
extern u8 D_800E0BDC;
extern u16 D_800BE930;
extern void (*D_8008FDEC[])(void);
void func_15042D78(u8);
s32 func_151E6964();

'''
SELECTED='''/* Run the live mode callback and account for time outside mode 7. */
void func_151E51EC(void) {
    u8 previous = D_800E0B94;

    D_8003C8E0 = 0x08000000;
    D_800E0BDC = 255;
    func_15042D78(0x81);
    D_800E0B9A = D_800BE930;
    if (D_8008FE28 != 0) {
        D_8008FE28--;
        D_800E0B9A = 0;
    }
    if (D_800E0B94 == 0) {
        func_151E6964(2);
    } else if (D_800E0B94 == 8) {
        func_151E6964(4);
    } else {
        func_151E6964(1);
    }
    D_8008FDEC[D_800E0B94]();
    if (D_800E0B94 != 7) {
        D_800E0A90 = (u32)D_800E0A90 + (u32)D_800BE9E4;
        if (D_800E0B94 != previous) {
            D_800E0B95 = previous;
            D_800E0A90 = 0;
        }
    }
    D_8003C8E0 = 0;
}'''
def source_states(live):
    old_decl='extern u8 D_8008FE28;';new_decl='extern s8 D_8008FE28;'
    if live.count(PLACEHOLDER)==1 and DECLARATIONS not in live and live.count(old_decl)==1:
        return live,live.replace(old_decl,new_decl,1).replace(PLACEHOLDER,DECLARATIONS+SELECTED,1),False
    if live.count(DECLARATIONS+SELECTED)==1 and PLACEHOLDER not in live and live.count(new_decl)==1:
        return live.replace(new_decl,old_decl,1).replace(DECLARATIONS+SELECTED,PLACEHOLDER,1),live,True
    raise ValueError('Live mode dispatcher source state changed')
def caller_states(live):
    old='s32 func_151E51EC(void);';new='void func_151E51EC(void);'
    if live.count(old)==1:return live,live.replace(old,new,1),False
    if live.count(new)==1:return live.replace(new,old,1),live,True
    raise ValueError('Live mode dispatcher caller declaration changed')
def compare(body=SELECTED,label='selected',declarations=DECLARATIONS):
    out=ROOT/BUILD;out.mkdir(parents=True,exist_ok=True);text=source_states((ROOT/SOURCE).read_text())[1].replace(DECLARATIONS+SELECTED,declarations+body,1)
    obj,diag=compile_owner(ROOT,out,text,label);raw,fs,rs=parse_object(obj);f=fs[FUNCTION];start,size=f['value'],f['size'];body_bytes=raw[start:start+size]
    linked,_=link_owner(ROOT,out,obj,OWNER);ours=linked[start:start+size];truth=(ROOT/'conker/conker.us.bin').read_bytes()[ROM:ROM+288]
    r=dict(words=size//4,raw_sha256=hashlib.sha256(body_bytes).hexdigest(),retail_sha256=hashlib.sha256(truth).hexdigest(),diagnostics=diag,
      differences=[(i*4,hex(a),hex(b))for i,(a,b)in enumerate(zip(struct.unpack('>%dI'%(size//4),ours),struct.unpack('>72I',truth)))if a!=b],
      bindings={at-start:r for at,r in rs.items()if start<=at<start+size})
    (out/(label+'-screen.json')).write_text(json.dumps(r,indent=2)+'\n');return r
if __name__=='__main__':print(json.dumps(compare(),indent=2))
