"""Private recovery of per-record payload pointers/status, without installation."""
from pathlib import Path
import hashlib,json,os,struct,subprocess
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve()
BUILD='conker/build/game-record-payload-tables-15017114-private';OUT=ROOT/BUILD
SOURCE='conker/src/game/generated_43D00.c';NAME='func_15017114'
ENTRY=0x15017114;ROM=0x445c4;BODY_SIZE=484;SIZE=492;RAW_ENTRY=0x14000000
SELECTED='''typedef struct RecordPayloadMetadata15017114 {
    u32 offset, status;
} RecordPayloadMetadata15017114;
extern u8 **D_800D2104;
extern u8 *D_800D2108;

/* Initialize player payloads and resolve appended records' relative metadata. */
void func_15017114(s32 category) {
    u8 count;
    u8 *metadata;
    s32 index;
    u8 *playerPayload;

    metadata = 0;
    count = D_800D2100;
    D_800D2104 = allocate_memory(count * 4, 1, 0, 0);
    D_800D2108 = allocate_memory(count, 1, 0, 0);
    bzero(D_800D2104, count * 4);
    bzero(D_800D2108, count);
    for (index = 0; index < D_8008FD8C; index++) {
        playerPayload = allocate_memory(16, 1, 2, 0);
        D_800D2104[index] = playerPayload;
        bzero(D_800D2104[index], 16);
        D_800D2108[index] = 2;
    }
    if (func_1502B7F0((void **)&metadata, 2, 16, category)) {
        for (index = D_800D2101; index < D_800D2100; index++) {
            if (((RecordPayloadMetadata15017114 *)metadata)[index - D_800D2101].offset != 0) {
                D_800D2108[index] = ((RecordPayloadMetadata15017114 *)metadata)[index - D_800D2101].status;
                D_800D2104[index] = metadata + ((RecordPayloadMetadata15017114 *)metadata)[index - D_800D2101].offset;
            }
        }
    }
}
'''

def proposed(before):
    assert before.count('s32 func_15017114();')==1
    assert body(before,NAME)=='s32 func_15017114() {\n    return 0;\n}'
    return before.replace('/* Non-matching placeholders for the text-only asm slice asm/43D00.s. */','/* Category records, resource caching, and per-record payload tables. */').replace('s32 func_15017114();','void func_15017114(s32 category);').replace(body(before,NAME),SELECTED).rstrip()+'\n'

def symbols():
    rows=subprocess.check_output(['mips-linux-gnu-nm','-n',str(ROOT/'conker/build/conker.us.elf')],text=True)
    return{parts[2]:int(parts[0],16)for row in rows.splitlines()if len(parts:=row.split())==3}

def programs():
    rom=(ROOT/'conker/conker.us.bin').read_bytes();truth=list(struct.unpack_from('>121I',rom,ROM))
    words=bound_blob(*payload(OUT/'selected.o',NAME),symbols())
    return((truth,ENTRY),(words,RAW_ENTRY))

def main():
    record=json.loads((OUT/'production-baseline/fingerprints.json').read_text())
    for name,want in record['inputs'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==want,name
    before=(OUT/'production-baseline'/SOURCE).read_text();assert(ROOT/SOURCE).read_text()==before
    base,d1=compile_owner(ROOT,OUT,before,'baseline');obj,d2=compile_owner(ROOT,OUT,proposed(before),'selected')
    assert d1==d2==''and same_functions(base,obj,(NAME,))==2 and normalized_pools(base)==normalized_pools(obj)
    raw,refs=payload(obj,NAME);truth,words=programs();a,b=truth[0],words[0]
    assert a[:9]==[0x27bdffb8,0xafbf002c,0xafb50028,0xafb40024,0xafb30020,0xafb2001c,0xafb10018,0xafb00014,0xafa40048]
    def frame(ws):return(-(((ws[0]&65535)^32768)-32768))
    def saves(ws):return[(w>>16&31,w&65535)for w in ws if w>>26==43 and w>>21&31==29 and 16<=w>>16&31<=23]
    report=dict(words=len(b),retail_words=121,slot_words=123,frame=frame(b),retail_frame=72,save_homes=saves(b),retail_save_homes=saves(a),differences=sum(x!=y for x,y in zip(a,b))+abs(len(a)-len(b)),binding_sites=len(refs),neighbors=2,raw_sha256=hashlib.sha256(raw).hexdigest(),inputs_unchanged=len(record['inputs']),uninstalled=True,uncredited=True)
    (OUT/'raw-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
