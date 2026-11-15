"""Private semantic perpendicular-offset recovery; all matching credit pending."""
from pathlib import Path
from functools import lru_cache
import hashlib,json,os,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows,elf_slot_offset
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve()
BUILD='conker/build/game-perpendicular-offset-1519ef90-private';OUT=ROOT/BUILD
SOURCE='conker/src/game/generated_1CC440.c';NAME='func_1519EF90'
ENTRY,ROM,SIZE=0x1519ef90,0x1cc440,376
PIN=json.loads(Path(__file__).with_name('game_perpendicular_offset_1519ef90_manifest.json').read_text())

@lru_cache(None)
def symbols():return {row[1]:row[2][1] for row in symbol_rows((ROOT/'conker/build/conker.us.elf').read_bytes())}

def immutable():
    saved=json.loads((OUT/'production-baseline/fingerprints.json').read_text())
    for name,want in saved['inputs'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==want,name
    return len(saved['inputs'])

def recover(before):
    return before.replace('#include "structs.h"','#include "structs.h"\n'+PIN['declarations'],1).replace(body(before,NAME),'/* Query a side-offset point with a sampled-heading fallback. */\n'+PIN['source'])

def programs():
    return {'retail':list(struct.unpack_from('>94I',(ROOT/'conker/conker.us.bin').read_bytes(),ROM)),
            'candidate':bound_blob(*payload(OUT/'qualified.o',NAME),symbols())}

def helper_input():
    image=(ROOT/'conker/build/conker.us.elf').read_bytes();syms=symbols();rom=(ROOT/'conker/conker.us.bin').read_bytes()
    # These complete original helpers are independently checked against the ELF.
    result={};records=[]
    for entry,n in ((0x15143e08,7),(0x151423d8,27)):
        offset=entry-0x15000000+0x2d4b0;raw=rom[offset:offset+4*n]
        assert image[elf_slot_offset(image,entry,4*n):elf_slot_offset(image,entry,4*n)+4*n]==raw
        result.update(zip(range(entry,entry+4*n,4),struct.unpack('>'+str(n)+'I',raw)));records.append((entry,n))
    table=syms['D_8009A220'];at=elf_slot_offset(image,table,65*4)
    data=dict(zip(range(table,table+65*4,4),struct.unpack_from('>65I',image,at)))
    for name in ('D_800A8CE0','D_800A8CE4'):
        address=syms[name];data[address]=struct.unpack_from('>I',image,elf_slot_offset(image,address,4))[0]
    return result,data,records

def main():
    count=immutable();before=(OUT/'production-baseline'/SOURCE).read_text();assert (ROOT/SOURCE).read_text()==before
    baseline,bd=compile_owner(ROOT,OUT,before,'baseline');obj,ad=compile_owner(ROOT,OUT,recover(before),'qualified')
    assert bd==ad==''
    assert same_functions(baseline,obj,(NAME,))==38 and normalized_pools(baseline)==normalized_pools(obj)
    raw,refs=payload(obj,NAME);assert hashlib.sha256(raw).hexdigest()==PIN['raw_sha256'] and {str(k):[list(x) for x in v] for k,v in refs.items()}==PIN['refs']
    streams=programs();assert len(streams['candidate'])==92 and streams['candidate'][0]==0x27bdffc0
    _,data,helpers=helper_input();assert immutable()==count
    report=dict(frozen_inputs=count,raw_words=92,retail_words=94,frame=64,neighbors=38,helpers=helpers,
                literal_words={n:hex(data[symbols()[n]]) for n in ('D_800A8CE0','D_800A8CE4')},production_unchanged=True,c_match_credit=0)
    (OUT/'recovery-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
