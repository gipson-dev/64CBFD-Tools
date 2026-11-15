"""Recover the complete view reset, retaining private and uncredited screens."""
from pathlib import Path
import hashlib,json,os,struct,subprocess
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools.experiments.game_path_heading_turn_roles import bound_blob

SOURCE='conker/src/game_44A90.c'
NAME='func_15017640'
ENTRY,ROM,SIZE,SLOT=0x15017640,0x44af0,328,336
BUILD='conker/build/game-view-reset-15017640-private'
# Use accurate local storage declarations instead of the old generic scalar
# placeholders for the matrix, normalization halfword and 192-byte scratch area.
# The other function's existing declarations and semantics remain identical.
DECLARATIONS='''extern u8 D_800BE616, D_800D2456, D_800D2457, D_800D2458;
extern struct102 *D_800D2E4C;
extern Mtx D_800D23D0;
extern u16 D_800D2454;
extern f32 D_800D2410[6], D_800D2428[3], D_800D2438[3];
extern s16 D_8009DCB4[3];
extern s32 D_800D2444, D_800D2588, D_800D24C0;
extern struct256 *D_800D245C;
extern u8 D_800D2460[6][16];
extern u8 D_800D24C8[0xC0];
extern f32 D_800968B0;
'''
BODY='''/* Reset view motion, six scale/record entries, and perspective state. */
void func_15017640(void) {
    s32 index;

    D_800D2458 = 0;
    D_800D2588 = 0;
    D_800D2438[0] = 0.0f;
    D_800D2438[1] = 0.0f;
    D_800D2438[2] = 0.0f;
    D_800D2428[0] = D_8009DCB4[0];
    D_800D2428[1] = D_8009DCB4[1];
    D_800D2428[2] = D_8009DCB4[2];
    D_800D2444 = 0;
    D_800D245C = 0;
    for (index = 0; index < 6; index++) {
        D_800D2410[index] = 1.0f;
    }
    for (index = 0; index < 6; index++) {
        D_800D2460[index][13] = 0;
    }
    D_800D24C0 = 0;
    bzero(D_800D24C8, sizeof(D_800D24C8));
    guPerspective(&D_800D23D0, &D_800D2454,
                  50.0f, 60.6f, 53.0f, D_800968B0, 1.0f);
}'''

def recover(before,body=BODY):
 before=before.replace('#include "variables.h"',DECLARATIONS.rstrip())
 start=before.index('/* Non-matching C placeholders for asm/nonmatchings/game_44A90/func_15017640.s. */')
 result=before[:start]+body.rstrip()+'\n'
 return result.replace('s32 func_15017640();','void func_15017640(void);')

def pointer_body():
 return BODY.replace('    s32 index;','    s32 index;\n    f32 *scale;').replace('    for (index = 0; index < 6; index++) {\n        D_800D2410[index] = 1.0f;\n    }','    for (scale = D_800D2410; scale < D_800D2410 + 6; scale++) {\n        *scale = 1.0f;\n    }')

def symbols(root):
 text=subprocess.check_output(['mips-linux-gnu-nm','-n',str(root/'conker/build/conker.us.elf')],text=True)
 return {p[2]:int(p[0],16) for row in text.splitlines() if len(p:=row.split())==3}

def programs(root):
 out=root/BUILD;rom=(root/'conker/conker.us.bin').read_bytes();s=symbols(root)
 return [(list(struct.unpack_from('>82I',rom,ROM)),ENTRY)]+[(bound_blob(*payload(out/(label+'.o'),NAME),s),0x14000000) for label in ('selected','pointer-scales')]

def main():
 root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();out=root/BUILD;out.mkdir(parents=True,exist_ok=True)
 frozen=out/'production-baseline';record=json.loads((frozen/'fingerprints.json').read_text());sha=lambda b:hashlib.sha256(b).hexdigest()
 for name,want in record['inputs'].items():assert sha((root/name).read_bytes())==want,name
 before=(frozen/SOURCE).read_text();baseline,diagnostics=compile_owner(root,out,before,'baseline');assert not diagnostics
 rows=[]
 for label,body in (('selected',BODY),('pointer-scales',pointer_body())):
  obj,diagnostics=compile_owner(root,out,recover(before,body),label);assert not diagnostics,diagnostics
  assert same_functions(baseline,obj,(NAME,))==1 and normalized_pools(baseline)==normalized_pools(obj)
  raw,refs=payload(obj,NAME)
  rows.append(dict(label=label,words=len(raw)//4,frame=(-struct.unpack_from('>I',raw)[0])&65535,bindings=sum(len(v) for v in refs.values()),owner_neighbors=1,raw_sha256=sha(raw)))
 for name,want in record['inputs'].items():assert sha((root/name).read_bytes())==want,name
 truth=programs(root)[0][0]
 for row,(words,_) in zip(rows,programs(root)[1:]):row['real_word_differences']=sum(a!=b for a,b in zip(truth,words))+abs(len(truth)-len(words))
 (out/'screen.json').write_text(json.dumps(dict(candidates=rows,private=True,c_match_credit=0),indent=2)+'\n');print(json.dumps(rows),flush=True)
if __name__=='__main__':main()
