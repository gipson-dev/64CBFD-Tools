"""Semantic literal-pool recovery and 22 checked motion-effect normalizations."""
from pathlib import Path
import csv,hashlib,io,json,os,struct
from tools.experiments import game_motion_effect_150c2c00_recovery as old
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve()
BUILD='conker/build/game-motion-effect-150c2c00-match';OUT=ROOT/BUILD
SOURCE,NAME,ENTRY,ROM,SIZE=old.SOURCE,old.NAME,old.ENTRY,old.ROM,old.SIZE
PREAMBLE='void func_1514373C(f32, f32, f32 *, f32 *);\n'
BODY='''/* Consume motion-gated emission attempts and copy each successful heading. */
void func_150C2C00(u8 *owner) {
    f32 firstScale, secondScale;
    f32 *accumulator;
    RadialEffectPacket150C29F0 packet;
    f32 *motion;
    f32 heading;
    f32 angleLimit, headingBase, headingScale, effectScale;
    void *created;

    accumulator = (f32 *)(owner + 0x28);
    firstScale = func_150ADA68();
    *accumulator +=
        (((firstScale * 20.0f) * 9.99999972e-10f) * D_800BE9A4) * 36447764.0f;
    if (1.0f < *accumulator) {
        motion = func_15144B34(D_80082FA4);
        /* Reuse the draw scalars for the motion gate before their size values. */
        secondScale = motion[0];
        firstScale = motion[2];
        secondScale = secondScale * secondScale + firstScale * firstScale;
        if (2500000.0f < secondScale) {
            packet.y = -390.0f;
            packet.value40 = 0.0450000018f;
            packet.value44 = 0.699999988f;
            angleLimit = 0.400000006f;
            headingBase = 0.957203984f;
            headingScale = 5.86594248f;
            packet.value3C = 0.0f;
            packet.code0 = 0x6231;
            packet.code1 = 0x1A4D;
            packet.firstColor[0] = 0;
            packet.firstColor[1] = 0;
            packet.firstColor[2] = 0;
            packet.alpha = 255;
            packet.secondColor[1] = 255;
            packet.secondColor[2] = 20;
            packet.enabled = 1;
            /* This packet variant uses word 0x30 as mode four. */
            packet.zero30 = 4;
            packet.flags2A = 1;
            packet.kind34 = 25;
            effectScale = 0.00100000005f;
            do {
                heading = func_150ADA68();
                heading = heading * headingScale + headingBase;
                secondScale = func_150484A0(motion[0], motion[2]);
                secondScale = func_15144C8C(secondScale, heading);
                if (secondScale < angleLimit) {
                    secondScale = func_150ADA68();
                    func_1514373C(heading,
                        secondScale * 1278.0f + 3900.0f,
                        &packet.x, &packet.z);
                    firstScale = func_150ADA68();
                    firstScale = (firstScale * 1991.0f + 1985.0f) * effectScale;
                    secondScale = func_150ADA68();
                    packet.size0 = 22.6000004f * firstScale;
                    packet.size1 = 13.7860003f * firstScale;
                    secondScale = (secondScale * 1493.0f + 3000.0f) * effectScale;
                    packet.delta0 = 57.9690018f * secondScale;
                    packet.delta1 = 42.7140007f * secondScale;
                    packet.delta2 = 118.763f * secondScale;
                    packet.duration = (u32)func_150ADA20() % 151U + 50;
                    secondScale = func_150ADA68();
                    packet.zero38 = (secondScale * 500.0f) * effectScale;
                    packet.secondColor[0] = (u32)func_150ADA20() % 156U + 100;
                    created = func_15149550(&packet, 10, 1, 0, owner[0xC], owner[1]);
                    if (created != 0) {
                        memcpy((u8 *)created + 0x160, &heading, sizeof(heading));
                    }
                }
                *accumulator -= 1.0f;
            } while (1.0f < *accumulator);
        } else {
            do {
                *accumulator -= 1.0f;
            } while (1.0f < *accumulator);
        }
    }
}'''
RAW_SHA256='fea76614f958e051351b365170fabaa1bf6651de21e4e6e14738686ab5bb7111'
PATCHES={
    1: (0xAFB20054, 0xAFB30058, 'closed owner-motion roles'),
    2: (0x00809025, 0x00809825, 'closed owner-motion roles'),
    8: (0xAFB30058, 0xAFB20054, 'closed owner-motion roles'),
    30: (0x26500028, 0x26700028, 'closed owner-motion roles'),
    47: (0xC4540008, 0xC4420008, 'closed motion FP scratch'),
    51: (0x00409825, 0x00409025, 'closed owner-motion roles'),
    52: (0x4614A102, 0x46021102, 'closed motion FP scratch'),
    53: (0x3C01C3C3, 0x240E6231, 'independent setup schedule'),
    54: (0x240E6231, 0x240F1A4D, 'independent setup schedule'),
    55: (0x240F1A4D, 0x3C01C3C3, 'independent setup schedule'),
    59: (0x46049000, 0x46049300, 'closed motion FP scratch'),
    63: (0x4600403C, 0x460C403C, 'closed motion FP scratch'),
    71: (0xC42A000C, 0xC430000C, 'closed packet FP scratch'),
    73: (0xC4300010, 0xC4320010, 'closed packet FP scratch'),
    78: (0x44809000, 0x44805000, 'closed packet FP scratch'),
    98: (0xE7AA00D4, 0xE7B000D4, 'closed packet FP scratch'),
    99: (0xE7B000D8, 0xE7B200D8, 'closed packet FP scratch'),
    100: (0xE7B200D0, 0xE7AA00D0, 'closed packet FP scratch'),
    106: (0xC66E0008, 0xC64E0008, 'closed owner-motion roles'),
    108: (0xC66C0000, 0xC64C0000, 'closed owner-motion roles'),
    191: (0x9259000C, 0x9279000C, 'closed owner-motion roles'),
    196: (0x92480001, 0x92680001, 'closed owner-motion roles'),
}
def symbols():return dict(old.symbols(),**{'.rodata':0x800a02c0})

def pool_guard(pool):
    manifest=json.loads(Path(__file__).with_name('game_motion_effect_150c2c00_manifest.json').read_text())
    assert len(pool)==80 and hashlib.sha256(pool).hexdigest()==manifest['constant_pool_sha256'],'Motion literal pool changed'
def proposed(source):
    stub=body(source,NAME);assert stub=='s32 func_150C2C00() {\n    return 0;\n}'
    result=source.replace(stub,BODY).replace('s32 func_150C2C00();\n','')
    result=result.replace('/* Generated placeholder declarations. */',PREAMBLE+'\n/* Generated placeholder declarations. */',1)
    result=result.replace('#include <ultra64.h>','#include <ultra64.h>\n#include <string.h>',1)
    result=result.replace('/* Non-matching C placeholders for asm/nonmatchings/game_EF410/func_150C2C00.s. */\n','')
    return result.rstrip()+'\n'
def normalize(raw,refs):
    assert len(raw)==SIZE and hashlib.sha256(raw).hexdigest()==RAW_SHA256,'Motion compiler body changed'
    manifest=json.loads(Path(__file__).with_name('game_motion_effect_150c2c00_manifest.json').read_text())
    assert {str(k):[list(x) for x in v] for k,v in refs.items()}==manifest['raw_relocations'],'Motion relocation set changed'
    words=list(struct.unpack('>243I',raw))
    for i,(expected,replacement,_) in PATCHES.items():
        assert words[i]==expected,(i,words[i]);words[i]=replacement
    return struct.pack('>243I',*words),refs
def programs():
    truth=list(struct.unpack_from('>243I',(ROOT/'conker/conker.us.bin').read_bytes(),ROM))
    raw,refs=payload(OUT/'recovered.o',NAME);fixed,fr=normalize(raw,refs)
    return truth,bound_blob(raw,refs,symbols()),bound_blob(fixed,fr,symbols())
def main():
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();frozen=OUT/'production-baseline'
    record=json.loads((frozen/'fingerprints.json').read_text());before=(frozen/SOURCE).read_text();source=proposed(before)
    installed=(ROOT/SOURCE).read_text()==source;plan=json.loads((OUT/'adoption-plan.json').read_text()) if (OUT/'adoption-plan.json').exists() else {}
    for n,h in record['inputs'].items():assert sha(ROOT/n)==(plan.get(n,h) if installed else h),n
    base,d1=compile_owner(ROOT,OUT,before,'baseline');obj,d2=compile_owner(ROOT,OUT,source,'recovered');assert d1==d2,(d1,d2)
    assert same_functions(base,obj,(NAME,))==17
    a,b=normalized_pools(base),normalized_pools(obj);pool=(ROOT/'conker/conker.us.bin').read_bytes()[0x244d80:0x244dd0]
    assert a['.rodata'] in (None,(b'',())) and b['.rodata']==(pool,()) and a['.data']==b['.data'],(a,b)
    pool_guard(b['.rodata'][0])
    truth,raw,fixed=programs();assert fixed==truth
    fields=next(csv.reader(io.StringIO((frozen/'conker/retail_word_patches.us.csv').read_text())));stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n')
    _,refs=payload(obj,NAME)
    for i,(expected,replacement,group) in sorted(PATCHES.items()):
        reloc=';'.join(k+':'+n for k,n in refs.get(i*4,[])) or '-'
        writer.writerow(dict(filename='game_EF410',function=NAME,offset='0x%03X'%(i*4),expected='0x%08X'%expected,replacement='0x%08X'%replacement,expected_relocations=reloc,replacement_relocations=reloc,note='Normalize motion effect '+group,insert_after='',insert_after_relocations='',omit='false'))
    (OUT/'proposed-guards.csv').write_bytes((frozen/'conker/retail_word_patches.us.csv').read_bytes()+stream.getvalue().encode())
    make=(frozen/'conker/Makefile').read_bytes();anchor=b'\t$(PYTHON) ../tools/pad_c_object.py $@.compact $(RETAIL_LAYOUT) $(basename $(notdir $<)) '
    start=make.index(b'$(RETAIL_PAD_GLOBAL_ASM_O_FILES): $(BUILD_DIR)/%.c.o:');end=make.index(b'\nendif',start)
    assert make[start:end].count(anchor)==1;at=make.index(anchor,start,end);nl=b'\r\n' if b'\r\n' in make[:100] else b'\n'
    check=b'\t$(if $(RETAIL_POOL_CHECK),$(PYTHON) ../tools/$(RETAIL_POOL_CHECK) $@.compact)'+nl
    addition=b'\nifeq ($(VERSION),us)\n# Verify the compiler pool before binding it to the retained retail block.\n$(BUILD_DIR)/$(SRC_DIR)/game_EF410.c.o: RETAIL_RODATA_SYMBOL := D_800A02C0\n$(BUILD_DIR)/$(SRC_DIR)/game_EF410.c.o: RETAIL_POOL_CHECK := check_motion_effect_150c2c00_pool.py\n$(BUILD_DIR)/$(SRC_DIR)/game_EF410.c.o: ../tools/check_motion_effect_150c2c00_pool.py ../tools/experiments/game_motion_effect_150c2c00_manifest.json\nendif\n'
    proposed_make=make[:at]+check+make[at:]+addition
    assert proposed_make.replace(check,b'',1).removesuffix(addition)==make
    (OUT/'proposed.makefile').write_bytes(proposed_make)
    for n,h in record['inputs'].items():assert sha(ROOT/n)==(plan.get(n,h) if installed else h),n
    report=dict(installed=installed,body_words=243,frame=232,guards=22,groups=4,bindings=len(refs),neighbors=17,constant_pool_bytes=80,raw_word_differences=22,c_match_credit=int(installed))
    (OUT/'match-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
