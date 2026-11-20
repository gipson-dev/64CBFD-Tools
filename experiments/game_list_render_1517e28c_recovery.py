"""Raw list-flare renderer recovery: 132 words versus retail's 135.

Public and final-private agreement is not byte-exact, instruction-fault or
hardware credit. The separate match layer qualifies installation and guarded output.
"""
from pathlib import Path
import hashlib,json,os,struct,subprocess
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_map_trail_update_1510608c_recovery import bound_blob
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools

ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',str(Path(__file__).resolve().parents[2]))).resolve()
OUT=ROOT/'conker/build/game-list-render-1517e28c-private'
FUNCTION='func_1517E28C'
SOURCE='conker/src/game/generated_1AB530.c'
CALLER='conker/src/game_45B80.c'
ENTRY,ROM,WORDS=0x1517E28C,0x1AB73C,135
STUB='s32 func_1517E28C() {\n    return 0;\n}'
INPUTS={'conker/src/game/generated_1AB530.c': 'da1ec4e235ec22bce3c409959530eadf43e353fc94ff7a39a7caeb67421f9839', 'conker/src/game_45B80.c': '6acc8d74b26ce28aea4b29436214e556492fbfeb146d343b4de8285aa176bcdc', 'conker/conker.us.bin': 'f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382', 'conker/asm/1AB530.s': 'b0ae73c9d414ae85d1ddf5cf760001c670eb8ecab6a86e669204e5993111152a', 'conker/asm/data/231AB0.rodata.s': 'e42aaf7b701dd524957988514eaf4658a991b03a4c1d4598572da86341e1a734', 'conker/retail_word_patches.us.csv': '19e754d377629ab13f9e559ce4832e17d0d567ba65f05b818869fa2ad1ae50bd', 'conker/Makefile': '94141fe5474af30f4aa757fdf09bfb023bab819e4bf4d7ada94a89ac89ac1766'}
RECORD=r'''typedef struct ListRecord1AB530 {
    f32 position[3];
    f32 valueC;
    f32 value10;
    f32 direction[3];
    f32 facingThreshold;
    struct ListRecord1AB530 *next;
    s16 state28;
    u16 sample2A;
    u16 depth2C;
    u8 flags2E;
    u8 first2F;
    u8 second30;
    u8 opaque31[3];
} ListRecord1AB530;'''
PREAMBLE=r'''typedef struct { u8 values[2]; } ListFlarePair1AB530;
extern const ListFlarePair1AB530 D_8008D004, D_8008D008, D_8008D00C;
extern u8 D_800DDD60, D_800DCDD0, D_800DD2D0;
extern u8 *D_800B0DF0;
extern f32 *D_8008CFFC[2];
s32 func_1517EAAC(f32, f32, f32, f32 *, f32 *);
s32 func_1517EC1C(ListRecord1AB530 *, u32 *);
Gfx *func_1517E4A8();
'''
BODY=r'''/* Project enabled list records, choose their flare parameters, and submit them. */
Gfx *func_1517E28C(Gfx *commands, s32 unusedCategory) {
    /* Keep the retail carry slots; the depth helper can leave its output untouched. */
    s32 strength;
    s32 skip;
    u32 sampleDepth;
    s32 flags;
    ListRecord1AB530 *node;
    ListFlarePair1AB530 groups = D_8008D004;
    ListFlarePair1AB530 counts = D_8008D008;
    ListFlarePair1AB530 falloffs = D_8008D00C;

    node = D_800DDD64;
    D_800DDD60 = 0;
    while (node != NULL) {
        if (node->second30 != 0) {
            skip = 0;
            flags = node->flags2E;
            if (flags & 1) {
                if (D_800DCDD0 == 0) {
                    skip = 1;
                } else {
                    f32 *position = D_8008CFFC[D_800B0DF0[0x10]];
                    if (func_1517EAAC(position[0], position[1], position[2],
                                      &node->valueC, &node->value10) != 1) {
                        skip = 1;
                    }
                    strength = 255;
                    if (node->sample2A != 0xFFFC) {
                        strength = -1;
                    }
                    flags = node->flags2E;
                }
            } else {
                if (func_1517EC1C(node, &sampleDepth) != 1) {
                    skip = 1;
                }
                strength = -1;
                if ((s32)((u32)node->depth2C - sampleDepth) < 30) {
                    strength = 256;
                }
                flags = node->flags2E;
            }
            {
                u8 *intensity = (flags & 2) ? &D_800DD2D0 : NULL;
                if (skip == 0) {
                    commands = func_1517E4A8(commands, node, groups.values[node->first2F],
                        counts.values[node->first2F], falloffs.values[node->first2F], strength, intensity);
                } else if (intensity != NULL) {
                    *intensity = 0;
                }
            }
        }
        node = node->next;
    }
    return commands;
}'''

def source():
    live=(ROOT/SOURCE).read_text()
    before=live
    if hashlib.sha256((ROOT/SOURCE).read_bytes()).hexdigest()!=INPUTS[SOURCE]:
        frozen=OUT/'committed-baseline'/SOURCE
        assert hashlib.sha256(frozen.read_bytes()).hexdigest()==INPUTS[SOURCE]
        before=frozen.read_text()
    assert before.count(STUB)==1
    selected=before.replace(STUB,PREAMBLE+'\n'+BODY).replace('s32 func_1517E4A8() {','Gfx *func_1517E4A8() {')
    assert live in(before,selected),"Recovery source changed"
    return before,selected

def bind(raw,refs):
    symbols={}
    for entries in refs.values():
        for kind,name in entries:
            if name.startswith(('D_','func_')):symbols[name]=int(name.split('_')[1],16)
            else:raise ValueError('Unexpected renderer binding: '+name)
    return tuple(bound_blob(raw,refs,symbols))

def screen():
    manifest=json.loads(Path(__file__).with_name('game_list_render_1517e28c_match_manifest.json').read_text())
    accepted={SOURCE:manifest['selected_source_sha256'],CALLER:manifest['selected_caller_sha256'],
        'conker/retail_word_patches.us.csv':manifest['guards_sha256']}
    for name,digest in INPUTS.items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()in(digest,accepted.get(name)),name
    where=OUT/'banked-screen';where.mkdir(parents=True,exist_ok=True)
    before,selected=source();old,bd=compile_owner(ROOT,where,before,'before')
    obj,diag=compile_owner(ROOT,where,selected,'candidate');assert not bd and not diag,(bd,diag)
    raw,refs=payload(obj,FUNCTION);words=bind(raw,refs)
    retail=struct.unpack_from('>135I',(ROOT/'conker/conker.us.bin').read_bytes(),ROM)
    assert normalized_pools(old)==normalized_pools(obj)
    frozen_caller=OUT/'committed-baseline'/CALLER
    assert hashlib.sha256(frozen_caller.read_bytes()).hexdigest()==INPUTS[CALLER]
    caller=frozen_caller.read_text()
    revised=caller.replace('s32  func_1517E28C(s32 arg0, s32 arg1);','Gfx *func_1517E28C(Gfx *commands, s32 category);').replace('commands = (Gfx *)func_1517E28C((s32)commands, D_800BE9F0);','commands = func_1517E28C(commands, D_800BE9F0);')
    assert revised!=caller
    a,ad=compile_owner(ROOT,where,caller,'caller-before');b,dd=compile_owner(ROOT,where,revised,'caller-typed')
    assert ad.replace('caller-before.c','caller.c')==dd.replace('caller-typed.c','caller.c'),(ad,dd)
    assert ad.count('cfe: Warning 712:')==3 and 'Error' not in ad,ad
    caller_functions=same_functions(a,b,())
    assert normalized_pools(a)==normalized_pools(b)
    report=dict(words=len(words),frame=(-words[0])&65535,
        positional_differences=sum(a!=b for a,b in zip(words,retail))+abs(len(words)-WORDS),
        raw_sha256=hashlib.sha256(raw).hexdigest(),unchanged_neighbors=same_functions(old,obj,(FUNCTION,)),
        pools_unchanged=True,typed_caller_functions_unchanged=caller_functions,diagnostics='',
        caller_existing_warnings_unchanged=3,
        installed=(ROOT/SOURCE).read_text()==selected,matching_credit=0)
    (where/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

def census():
    rom=(ROOT/'conker/conker.us.bin').read_bytes()
    jal=0x0C000000|((ENTRY&0x0FFFFFFF)>>2)
    hits={label:[offset for offset in range(0,len(rom)-3,4)if rom[offset:offset+4]==struct.pack('>I',word)]
          for label,word in (('aligned_JAL_ROM_offsets',jal),('aligned_literal_ROM_offsets',ENTRY))}
    hits['computed_callers_unexcluded']=True
    hits['readonly_selector_words']=list(struct.unpack_from('>2I',rom,0x231ABC))
    hits['readonly_palette_bytes']=rom[0x231AC4:0x231AD0].hex()
    return hits
if __name__=='__main__':print(json.dumps(screen()))
