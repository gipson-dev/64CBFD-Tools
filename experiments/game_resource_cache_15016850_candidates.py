"""Private resource-cache recovery; no installation or match credit."""
from pathlib import Path
import hashlib,json,os,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_particle_display_151770c8_match import bound
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
NAME='func_15016850';ENTRY=0x15016850;ROM=0x43D00;SIZE=336
SOURCE='conker/src/game/generated_43D00.c';BUILD='conker/build/game-resource-cache-15016850-match'
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();OUT=ROOT/BUILD
SELECTED='#include "structs.h"\nextern u8 D_800BE590, D_800D2100;\nextern struct258 *D_800D20FC;\nextern u16 D_800BE598[];\nextern void *D_800BE5A8[];\nu32 func_1502B7F0(void **output, u32 depth, ...);\n\n/* Cache each distinct record resource, retaining the loader\'s live output. */\nvoid func_15016850(void) {\n    s32 offset, index, found;\n    void *handle;\n    s32 resource, limit;\n\n    handle = 0;\n    D_800BE590 = 0;\n    offset = 0;\n    if (D_800D2100 > 0) {\n      do {\n        resource = ((u8 *)D_800D20FC)[offset + 4];\n        found = 0;\n        for (index = 0; index < D_800BE590; index++) {\n            if (resource == D_800BE598[index]) {\n                found = 1;\n                break;\n            }\n        }\n        if (!found) {\n            if (resource < 187) func_1502B7F0(&handle, 2, 18, resource);\n            if (handle != 0) {\n                D_800BE5A8[D_800BE590] = handle;\n                D_800BE598[D_800BE590] = resource;\n                D_800BE590++;\n            }\n        }\n        limit = D_800D2100 << 2;\n        limit -= D_800D2100;\n        limit <<= 4;\n        offset += 48;\n      } while (offset < limit);\n    }\n}'

def main():
    before=(OUT/'production-baseline'/SOURCE).read_text();assert(ROOT/SOURCE).read_text()==before
    assert body(before,NAME)=='s32 func_15016850() {\n    return 0;\n}'
    selected=before.replace(body(before,NAME),SELECTED);old,d=compile_owner(ROOT,OUT,before,'baseline');obj,d2=compile_owner(ROOT,OUT,selected,'selected')
    assert d==d2==''and same_functions(old,obj,(NAME,))==2 and normalized_pools(old)==normalized_pools(obj)
    raw,refs=payload(obj,NAME);words=bound(raw,refs);truth=struct.unpack_from('>84I',(ROOT/'conker/conker.us.bin').read_bytes(),ROM)
    assert len(words)==81 and words[0]==0x27bdffa0 and words[-1]==0x27bd0060
    assert words[0x38//4]==0xafa00050 and words[0x5c//4]==0x27b40050
    saved={w>>16&31:w&65535 for w in words if w>>26==43 and w>>21&31==29 and 16<=w>>16&31<=23}
    assert saved=={16:24,17:28,18:32,19:36,20:40,21:44,22:48}
    record=json.loads((OUT/'production-baseline/fingerprints.json').read_text())
    for n,h in record['inputs'].items():assert hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h,n
    asm=(ROOT/'conker/asm/43D00.s').read_text();a=asm.index('glabel '+NAME+'\n');b=asm.index('endlabel '+NAME,a)+len('endlabel '+NAME)
    (OUT/'retail.s').write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+asm[a:b]+'\n.size '+NAME+',.-'+NAME+'\n')
    import subprocess
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(OUT/'retail.o'),str(OUT/'retail.s')],cwd=ROOT/'conker',capture_output=True,check=True)
    assert bound(*payload(OUT/'retail.o',NAME))==list(truth)
    report=dict(words=len(words),frame=96,handle_home=80,saved_registers=7,retail_saved_registers=7,real_word_differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-84),binding_sites=len(refs),neighbors=2,raw_sha256=hashlib.sha256(raw).hexdigest(),inputs_unchanged=len(record['inputs']),uncredited=True)
    (OUT/'raw-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
