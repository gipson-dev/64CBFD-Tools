"""Effect-actor constructor bytes and complete qualification gates."""
from collections import Counter
import hashlib,json,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,same_functions,symbol_rows
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions

BUILD='conker/build/game-effect-actor-constructor-15154884-match'
FUNCTION='func_15154884';OWNER='generated_17CAF0';ENTRY=0x15154884;ROM=0x181D34;WORDS=129;SIZE=516
FRAME=192;RAW_FRAME=184;GUARDS=10
BASELINE=LINKED='752feb861f0a37a4ce3ee397f1a52952a048048aff9c3521ad2b3ff3d9b122da'
RAW_SHA='2928aca1c9b3c1784c71bd02c9b4e109b82e8b4afdc376117c414482aea361cf'
NORMALIZED_SHA='c47339d343812ae28a46b1f71b195a21c40e23f28c0742244f0e030de1c0a96a'

TYPE_DECL='''typedef struct { f32 x, y, z; } EffectVector15154884;
typedef struct {
    f32 field00;
    f32 field04;
    f32 field08;
    f32 field0C;
    f32 rotation[3];
    f32 scale[3];
    EffectVector15154884 position;
    EffectVector15154884 velocity;
    f32 field40;
    f32 field44;
    f32 field48;
    f32 field4C;
    u32 flags;
    s16 duration;
    s16 resource;
    u8 field58;
    u8 reserved59[3];
    u32 field5C;
    u8 field60;
    u8 field61;
    u8 field62;
    u8 field63;
    u8 field64;
    u8 field65;
    u8 field66;
    u8 field67;
    u8 field68;
    u8 reserved69;
    u8 field6A;
    u8 reserved6B;
    u32 field6C;
    u8 field70;
    u8 reserved71;
    s16 field72;
    s16 field74;
    u8 reserved76[2];
} EffectActorDescriptor15154884;
typedef struct {
    f32 lifetime;
    f32 amplitude;
    f32 height;
    f32 phase;
    f32 rate;
} EffectActorPayload15154884;
extern f32 D_800A601C;
extern f32 D_800A6020;
extern f32 D_800A6024;
extern f32 D_800A6028;
extern f32 D_800A602C;
f32 func_150ADA68(void);
void *func_15132A4C(void *, s32, s32, s32, u8, s32);
void *memcpy(void *, const void *, u32);

'''
HEADERS='#include <ultra64.h>\n\n'+TYPE_DECL
SELECTED='''void *func_15154884(EffectVector15154884 *position, f32 lifetime,
                      f32 amplitude, f32 height, u8 slot, s32 context) {
    EffectActorDescriptor15154884 descriptor;
    EffectActorPayload15154884 payload;
    void *created;

    if (lifetime <= 0.0f) {
        return NULL;
    }
    payload.lifetime = lifetime;
    payload.amplitude = amplitude;
    payload.height = height;
    payload.phase = 0.0f;
    payload.rate = D_800A601C / lifetime;
    descriptor.field00 = 1.0f;
    descriptor.field04 = 1.0f;
    descriptor.field08 = 0.0f;
    descriptor.field0C = 0.0f;
    descriptor.rotation[0] = func_150ADA68() * 360.0f;
    descriptor.rotation[1] = func_150ADA68() * 360.0f;
    descriptor.rotation[2] = func_150ADA68() * 360.0f;
    descriptor.scale[0] = 1.0f;
    descriptor.scale[1] = 1.0f;
    descriptor.scale[2] = 1.0f;
    descriptor.position = *position;
    descriptor.velocity.x = 0.0f;
    descriptor.velocity.y = 0.0f;
    descriptor.velocity.z = 0.0f;
    descriptor.field40 = func_150ADA68() * D_800A6020 + D_800A6024;
    descriptor.field44 = 0.0f;
    descriptor.field48 = func_150ADA68() * D_800A6028 + D_800A602C;
    descriptor.field4C = 0.0f;
    descriptor.flags = 0x140;
    descriptor.resource = 0x55;
    descriptor.field58 = 0;
    descriptor.field5C = 0;
    descriptor.field60 = 0xFF;
    descriptor.field61 = 0x12;
    descriptor.field62 = 0;
    descriptor.field63 = 0;
    descriptor.field64 = 0;
    descriptor.field65 = 0;
    descriptor.field66 = 0;
    descriptor.field67 = 0;
    descriptor.field68 = 2;
    descriptor.field6A = 0;
    descriptor.field6C = 0;
    descriptor.field70 = 0;
    descriptor.field72 = 1;
    descriptor.field74 = 0xFF;
    descriptor.duration = 0x12C;
    created = func_15132A4C(&descriptor, 0, 0, sizeof(payload), slot, context);
    if (created != NULL) {
        memcpy((u8 *)created + 0x170, &payload, sizeof(payload));
    }
    return created;
}

'''

def sha(data):return hashlib.sha256(data).hexdigest()

def checked_payload(raw,bindings):
 if len(raw)!=SIZE or sha(raw)!=RAW_SHA or len(bindings)!=17:raise ValueError('Effect-actor constructor payload or bindings changed')
 return raw,bindings

def check_image(before,actual):
 if actual!=before or sha(actual)!=LINKED:raise ValueError('Effect-actor constructor entire image differs')

def recovered_owner(before):
 pragma='#pragma GLOBAL_ASM("asm/nonmatchings/generated_17CAF0/func_15154884.s")'
 if before.count(pragma)!=1:raise ValueError('Effect-actor constructor predecessor changed')
 comment='/* Create a randomized effect actor and attach its complete motion payload. */\n'
 return before.replace(pragma,TYPE_DECL+comment+SELECTED.rstrip(),1)

def expected_map(output):
 data=(output/'private-joint-linked.map').read_bytes();private=(BUILD.removeprefix('conker/')+f'/make-shadow-{OWNER}/src/game/{OWNER}.c.o').encode()
 if data.count(private)!=9:raise ValueError('Effect-actor map owner path changed')
 data=data.replace(private,f'build/src/game/{OWNER}.c.o'.encode());private=(BUILD.removeprefix('conker/')+'/private-joint-linked.elf').encode()
 if data.count(private)!=1:raise ValueError('Effect-actor map output changed')
 return data.replace(private,b'build/conker.us.elf')

def verify_prepared(output):
 q=json.loads((output/'private-layout-v1.json').read_text())
 if(q['words'],q['retail_frame'],q['raw_frame'],q['proposed_closed_normalizations'],q['raw_SHA256'],q['normalized_SHA256'],len(q['layouts']))!=(WORDS,FRAME,RAW_FRAME,GUARDS,RAW_SHA,NORMALIZED_SHA,3):raise ValueError('Effect-actor layout receipt changed')
 raw,refs=checked_payload(*payload(output/'screen-v1.o',FUNCTION));original,orefs=payload(output/f'original-{FUNCTION}.o',FUNCTION);normalized,nrefs=payload(output/'normalized.o',FUNCTION)
 if original!=normalized or orefs!=nrefs or refs!=orefs:raise ValueError('Effect-actor payload bindings changed')
 if sha(raw)!=RAW_SHA or sha(normalized)!=NORMALIZED_SHA or sum(a!=b for a,b in zip(struct.unpack('>129I',raw),struct.unpack('>129I',original)))!=GUARDS:raise ValueError('Effect-actor payload words changed')
 if(output/'proposed-guards.csv').read_bytes().count(b','+FUNCTION.encode()+b',')!=GUARDS:raise ValueError('Effect-actor guards changed')
 for name in('private-guest-v1.json','private-native-v1.json','private-caller-v1.json','private-owner-image-v1.json','native_harness_v1.c',f'qualified-{OWNER}.o','private-joint-linked.elf'):
  if not(output/name).is_file():raise ValueError('Missing effect-actor artifact: '+name)
  if name.endswith('.json')and not json.loads((output/name).read_text())['success']:raise ValueError('Failed effect-actor receipt: '+name)
 return True

def check_inputs(root,output,installed=False):
 verify_prepared(output);baseline={
  f'conker/src/game/{OWNER}.c':(output/f'before-conker_src_game_{OWNER}.c').read_bytes(),f'conker/build/src/game/{OWNER}.c.o':(output/f'before-conker_build_src_game_{OWNER}.c.o').read_bytes(),
  'conker/build/conker.us.elf':(output/'before-conker_build_conker.us.elf').read_bytes(),'conker/build/conker.us.map':(output/'before-conker_build_conker.us.map').read_bytes(),
  'conker/retail_word_patches.us.csv':(output/'before-conker_retail_word_patches.us.csv').read_bytes()}
 changes={}
 if installed:changes={f'conker/src/game/{OWNER}.c':(output/f'proposed-{OWNER}.c').read_bytes(),f'conker/build/src/game/{OWNER}.c.o':(output/f'qualified-{OWNER}.o').read_bytes(),
  'conker/build/conker.us.elf':baseline['conker/build/conker.us.elf'],'conker/build/conker.us.map':expected_map(output),'conker/retail_word_patches.us.csv':(output/'proposed-guards.csv').read_bytes()}
 for name,data in baseline.items():
  if(root/name).read_bytes()!=changes.get(name,data):raise ValueError('Effect-actor live input changed: '+name)
 return baseline

def audit(root,output,installed=False):
 from tools.check_game_data_layout import audit_layout
 values=check_inputs(root,output,installed);path=root/'conker/build/conker.us.elf' if installed else output/'private-joint-linked.elf';actual=path.read_bytes()
 check_image(values['conker/build/conker.us.elf'],actual)
 protected=audit_layout(path,root/'conker');
 if not protected['exact']or protected['bytes']!=189088 or protected['owner_count']!=720:raise ValueError('Effect-actor protected data changed')
 old,_,oo=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');new,_,no=load_elf_functions(str(path),'mips-linux-gnu-objdump')
 if old!=new or oo!=no:raise ValueError('Effect-actor linked definitions changed')
 expected=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(values['conker/build/conker.us.elf']));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
 if expected!=observed:raise ValueError('Effect-actor named definitions changed')
 q=json.loads((output/'private-owner-build-v1.json').read_text());q.update(private_only=not installed,installed=installed,matching_credit=1 if installed else 0,
  strict_whole_image_prediction=True,strict_exclusions=0,entire_linked_image_byte_identical=True,functions=len(old),other_bodies_fixed=len(old)-1,
  all_function_addresses_fixed=True,entire_named_definition_multiset_verified=True,protected_data=protected)
 if installed:(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n')
 return q
