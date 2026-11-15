"""Matched sender: closed GPR roles and one non-escaping pointer-cache home."""
from pathlib import Path
import csv,hashlib,io,json,os,re,struct
from tools.experiments import game_actor_effect_binding_150c4120_recovery as old
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve()
BUILD='conker/build/game-actor-effect-binding-150c4120-match';OUT=ROOT/BUILD
SOURCE,NAME,ENTRY,ROM,SIZE=old.SOURCE,old.NAME,old.ENTRY,old.ROM,old.SIZE
PREAMBLE='''typedef struct { f32 x, y, z; } BindingVector150C4120;
typedef struct { s32 values[4]; } BindingPalette150C4120;
typedef struct {
    u8 *actor;
    u8 identity;
    u8 pad05[3];
    f32 zero08;
    u8 *effect;
    f32 zero10;
    s16 selector;
    s8 state;
    u8 pad17;
    s32 zero18;
} BindingPayload150C4120;
typedef struct {
    u8 first, second, width, height;
    f32 scale, horizontal, vertical;
} BindingRandom150C4120;
typedef struct {
    u32 flags00, zero04;
    s16 code08, lifetime;
    u32 zero0C, zero10;
    u8 rgba14[4], rgba18[4];
    u8 value1C, paletteIndex;
    s16 value1E, value20, value22;
    f32 scale, extentX, extentY;
    BindingVector150C4120 first, second, third;
    f32 zero54;
    u32 flags58, zero5C;
    u8 value60, value61, value62;
    s8 value63, value64, value65;
    u8 value66, pad67;
    s16 zero68;
    u8 pad6A[2];
    f32 coefficient;
} BindingDefinition150C4120;
extern BindingPalette150C4120 D_800A0340;
extern BindingVector150C4120 D_800A5480;
extern f32 D_800A03AC, D_800A03B0, D_800A03B4;
u8 *func_15149130(s16, s8, s8, s8, u8, u8, s32, u8, s32);
u8 *func_15130280(BindingDefinition150C4120 *, u8, void *, s32, u8, s32);
s32 func_150ADA20(void);
f32 func_150ADA68(void);
void *memcpy(void *, const void *, u32);
'''
BODY='''/* Bind the actor record to its randomized effect; either allocation may fail. */
void func_150C4120(u8 *actor, s16 requestedLifetime, u8 priority, s32 context) {
    BindingPayload150C4120 binding;
    s32 lifetime;
    s32 active;
    BindingDefinition150C4120 definition;
    BindingRandom150C4120 random;
    BindingPalette150C4120 palette;
    BindingPayload150C4120 *destination;
    u32 firstFlag;

    binding.actor = actor;
    binding.identity = actor[0x3B];
    binding.zero08 = 0.0f;
    binding.effect = 0;
    binding.zero10 = 0.0f;
    binding.selector = -1;
    binding.state = 0;
    binding.zero18 = 0;
    if (actor[4] == 0x34) {
        binding.selector = 0x54;
        binding.state = 1;
    }
    lifetime = requestedLifetime == -1 ? 300 : requestedLifetime;
    active = requestedLifetime == -1 ? 0 : 1;
    destination = (BindingPayload150C4120 *)func_15149130(lifetime, -1, 0x53, -1, active, 0x40,
                          sizeof(binding), priority, context);
    if (destination != 0) {
        destination = (BindingPayload150C4120 *)((u8 *)destination + 0x28);
        memcpy(destination, &binding, sizeof(binding));
        palette = D_800A0340;
        random.first = func_150ADA20();
        random.second = func_150ADA20();
        definition.extentY = 700.0f;
        definition.extentX = 700.0f;
        random.scale = 700.0f;
        random.width = (u32)func_150ADA20() % 6U + 5;
        random.height = (u32)func_150ADA20() % 6U + 5;
        random.horizontal = (func_150ADA68() * 0.25f + D_800A03AC) * random.scale;
        random.vertical = (func_150ADA68() * 0.25f + D_800A03B0) * random.scale;
        definition.paletteIndex = palette.values[(u32)func_150ADA20() & 3];
        definition.code08 = 0x2203;
        definition.flags00 = 0x200005;
        definition.zero04 = 0;
        definition.zero0C = 0;
        definition.zero10 = 0;
        definition.rgba14[0] = 0;
        definition.rgba14[1] = 0;
        definition.rgba14[2] = 0;
        definition.rgba14[3] = 255;
        definition.rgba18[0] = 0;
        definition.rgba18[1] = 0;
        definition.rgba18[2] = 0;
        definition.rgba18[3] = 255;
        definition.value1C = 255;
        definition.first = D_800A5480;
        definition.second = D_800A5480;
        definition.third = D_800A5480;
        definition.value22 = 1;
        definition.zero54 = 0.0f;
        definition.scale = 1.0f;
        firstFlag = ((u32)func_150ADA20() & 1) ? 0x40 : 0;
        definition.flags58 = (((u32)func_150ADA20() & 1) ? 0x80 : 0) | firstFlag | 0xC000;
        definition.lifetime = 300;
        definition.value1E = 1;
        definition.value20 = 255;
        definition.value60 = 6;
        definition.value61 = 8;
        definition.value64 = -1;
        definition.value62 = 0x26;
        definition.value63 = -1;
        definition.value65 = 0;
        definition.zero5C = 0;
        definition.value66 = 255;
        definition.zero68 = 0;
        definition.coefficient = D_800A03B4;
        if ((destination->effect = func_15130280(&definition, 1, 0, sizeof(random), priority, context)) != 0) {
            memcpy(destination->effect + 0xA8, &random, sizeof(random));
        }
    }
}'''
PATCHES={
    55:(0xAFA40038,0xAFA40030),
    79:(0x00005810,0x00006810),
    80:(0x256C0005,0x25AE0005),
    82:(0xA3AC004E,0xA3AE004E),
    85:(0x00006810,0x00007810),
    86:(0x25AE0005,0x25E90005),
    88:(0xA3AE004F,0xA3A9004F),
    109:(0x304F0003,0x30480003),
    110:(0x000F4880,0x0008C080),
    111:(0x03A94021,0x03B8C821),
    112:(0x8D08003C,0x8F39003C),
    116:(0x3C190020,0x3C0B0020),
    117:(0x24182203,0x240A2203),
    118:(0x37390005,0x356B0005),
    119:(0x240A00FF,0x240C00FF),
    120:(0x240B00FF,0x240D00FF),
    121:(0x240C00FF,0x240E00FF),
    122:(0xA7B80064,0xA7AA0064),
    123:(0xAFB9005C,0xAFAB005C),
    130:(0xA3AA0073,0xA3AC0073),
    134:(0xA3AB0077,0xA3AD0077),
    135:(0xA3AC0078,0xA3AE0078),
    136:(0x27AD008C,0x27AF008C),
    137:(0xA3A80079,0xA3B90079),
    138:(0xADA10000,0xADE10000),
    139:(0x8C690004,0x8C780004),
    140:(0x27A80098,0x27B90098),
    141:(0x27AB00A4,0x27AD00A4),
    142:(0xADA90004,0xADF80004),
    145:(0xADA10008,0xADE10008),
    147:(0x240D0001,0x240F0001),
    148:(0xAD010000,0xAF210000),
    149:(0x8C6A0004,0x8C6C0004),
    150:(0xAD0A0004,0xAF2C0004),
    152:(0xAD010008,0xAF210008),
    154:(0xAD610000,0xADA10000),
    155:(0x8C6E0004,0x8C690004),
    156:(0xAD6E0004,0xADA90004),
    158:(0xAD610008,0xADA10008),
    161:(0xA7AD007E,0xA7AF007E),
    165:(0x30490001,0x30580001),
    166:(0x11200003,0x13000003),
    172:(0x30590001,0x304B0001),
    173:(0x13200003,0x11600003),
    178:(0x0043C025,0x0043C825),
    179:(0x3708C000,0x372CC000),
    180:(0x240A012C,0x2408012C),
    181:(0xAFA800B4,0xAFAC00B4),
    182:(0xA7AA0066,0xA7A80066),
    185:(0x8FAA00FC,0x8FA800FC),
    186:(0x93A800FB,0x93AC00FB),
    187:(0x240F0001,0x240E0001),
    188:(0x240C00FF,0x240D00FF),
    189:(0x240B0006,0x24090006),
    190:(0x240E0008,0x240F0008),
    191:(0x240DFFFF,0x2418FFFF),
    192:(0x24090026,0x240B0026),
    193:(0x2419FFFF,0x240AFFFF),
    194:(0x241800FF,0x241900FF),
    195:(0xA7AF007A,0xA7AE007A),
    196:(0xA7AC007C,0xA7AD007C),
    197:(0xA3AB00BC,0xA3A900BC),
    198:(0xA3AE00BD,0xA3AF00BD),
    199:(0xA3AD00C0,0xA3B800C0),
    200:(0xA3A900BE,0xA3AB00BE),
    201:(0xA3B900BF,0xA3AA00BF),
    204:(0xA3B800C2,0xA3B900C2),
    211:(0xAFAA0014,0xAFA80014),
    213:(0xAFA80010,0xAFAC0010),
    214:(0x8FA30038,0x8FA30030),
}

symbols=old.symbols
def proposed(source):
    result=old.proposed(source)
    assert result.count(old.PREAMBLE)==1 and result.count(old.BODY)==1
    return result.replace(old.PREAMBLE,PREAMBLE).replace(old.BODY,BODY)

def normalize(raw,refs):
    manifest=json.loads(Path(__file__).with_name('game_actor_effect_binding_150c4120_manifest.json').read_text())
    assert len(raw)==SIZE and hashlib.sha256(raw).hexdigest()==manifest['raw_sha256']=='c20a4c21238ca29a334d53130c339685fa5f354c491b6f3f303be2a787cabe04'
    assert {str(k):[list(x) for x in v] for k,v in refs.items()}==manifest['relocations']
    words=list(struct.unpack('>225I',raw))
    for i,(expected,replacement) in PATCHES.items():assert words[i]==expected;words[i]=replacement
    return struct.pack('>225I',*words),refs

def programs():
    truth=list(struct.unpack_from('>225I',(ROOT/'conker/conker.us.bin').read_bytes(),ROM))
    raw,refs=payload(OUT/'recovered.o',NAME);fixed,fr=normalize(raw,refs)
    return truth,bound_blob(raw,refs,symbols()),bound_blob(fixed,fr,symbols())

def main():
    frozen=OUT/'production-baseline';record=json.loads((frozen/'fingerprints.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    before=(frozen/SOURCE).read_text();source=proposed(before);installed=(ROOT/SOURCE).read_text()==source
    plan=json.loads((OUT/'adoption-plan.json').read_text()) if (OUT/'adoption-plan.json').exists() else {}
    for n,h in record['inputs'].items():assert sha(ROOT/n)==(plan.get(n,h) if installed else h),n
    base,d1=compile_owner(ROOT,OUT,before,'baseline');obj,d2=compile_owner(ROOT,OUT,source,'recovered')
    diagnostic=lambda t:re.sub(r'(?:baseline|recovered)\.c, line \d+','owner.c, line N',t)
    assert diagnostic(d1)==diagnostic(d2),(d1,d2)
    assert same_functions(base,obj,(NAME,))==5 and normalized_pools(base)==normalized_pools(obj)
    truth,raw,fixed=programs();assert fixed==truth
    fields=next(csv.reader(io.StringIO((frozen/'conker/retail_word_patches.us.csv').read_text())));stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n')
    for i,(expected,replacement) in PATCHES.items():
        writer.writerow(dict(filename='generated_F15D0',function=NAME,offset='0x%03X'%(i*4),expected='0x%08X'%expected,replacement='0x%08X'%replacement,expected_relocations='-',replacement_relocations='-',note='Normalize actor binding closed temporary roles and pointer cache',insert_after='',insert_after_relocations='',omit='false'))
    (OUT/'proposed-guards.csv').write_bytes((frozen/'conker/retail_word_patches.us.csv').read_bytes()+stream.getvalue().encode())
    report=dict(installed=installed,body_words=225,frame=240,guards=70,register_guards=68,home_guards=2,bindings=23,neighbors=5,c_match_credit=0)
    (OUT/'match-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
