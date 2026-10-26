"""Complete classifier: widths, priority, stack aliases, caller ABI and strict image."""
from dataclasses import dataclass
from pathlib import Path
import itertools,json,struct,subprocess,unittest
from tools.experiments import game_two_key_state_classifier_match as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import floating
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2]
ACTOR,CARRIER=0x30000,0x40000
FLOATS=(0,0x80000000,0x3F800000,0xBF800000,1,0x7F800000,0xFF800000,0x7FC00001,0x7F7FFFFF)

@dataclass(frozen=True)
class Case:
 kind:int=0x3B
 mode:int=0
 flag:int=0
 motion:int=0
 keys:int=0x3B3C
 phase:int=0
 alias:int=0

def address(c):
 sp=STACK+c.phase
 return(ACTOR,sp-12-0x84,sp+4-0x84,sp-12-0x28,sp+4-0x28,sp-4-0x84,source.TABLE-0x84)[c.alias]

def get(m,a,n=4):return sum(m[a+i]<<(8*(n-i-1))for i in range(n))

def fixture(c,table=source.TABLE):
 sp=STACK+c.phase;actor=address(c);m={STACK+i:(i*17+0xA5)&255 for i in range(-512,768)}
 for base,size in((actor,0xC0),(CARRIER,0x100),(table,16)):
  for i in range(size):m.setdefault(base+i,(i*29+0x5A)&255)
 put(m,actor+0x84,c.kind,2);m[actor+0xAD]=c.flag;put(m,actor+0x28,c.motion);put(m,table,c.keys,2)
 return m

def reference(initial,c,actor=None,table=source.TABLE,local=-12):
 m=dict(initial);sp=STACK+c.phase;actor=address(c)if actor is None else actor;put(m,sp+4,c.mode&0xFFFFFFFF);matched=0
 if(c.mode&255)==0:
  put(m,sp+local,get(m,table,2),2);kind=get(m,actor+0x84,2)
  for i in(1,0):
   if kind==m[sp+local+i]:matched=1;break
 if matched:result=3
 elif m[actor+0xAD]:result=2
 elif floating(get(m,actor+0x28))==0.0:result=4
 else:result=1
 return m,result

def public(m):return{a:b for a,b in m.items()if not STACK-512<=a<STACK+768}

class Boundary(Exception):pass
class EndCode(faults.TrackedCode):
 def __contains__(self,pc):return pc in self.owner.ends or super().__contains__(pc)
 def __getitem__(self,pc):
  if pc in self.owner.ends:raise Boundary
  return super().__getitem__(pc)

class ClassifierOracle(TimingOracle):
 def __init__(self,words,memory,c=Case(),entry=source.ENTRY,connected=None,ends=()):
  super().__init__(words,memory,phase=c.phase,entry=entry,arguments=(address(c),c.mode),connected=connected)
  self.ends=set(ends);self.target_calls=[];self.hi,self.lo=0x12345678,0x89ABCDEF
  if ends:self.code=EndCode(self.code,self)
 def record_call(self,target):
  assert target==source.ENTRY,hex(target)
  args=self.arguments(2);self.target_calls.append(args);self.calls.append((target,args));self.events.append(('CALL',target,args))
 def hook(self,target):raise AssertionError(('Unexpected classifier provider',target))

def controls():
 b=source.SELECTED
 return dict(wrong_mode=b.replace('mode == 0','mode == 1'),
  truncated_type=b.replace('actorType = *(u16 *)(actor + 0x84);','actorType = actor[0x85];'),
  skipped_key=b.replace('cursor = (u32)((u8 *)keys + 1);','cursor = (u32)(u8 *)keys;'),
  wrong_special=b.replace('result = 3;','result = 2;'),wrong_flag=b.replace('result = 2;','result = 3;'),
  wrong_float=b.replace('0.0f != *(f32 *)(actor + 0x28)','0.0f > *(f32 *)(actor + 0x28)'),
  flag_priority=b.replace('    if (mode == 0) {','    if (actor[0xAD]) return 2;\n    if (mode == 0) {'),
  hardcoded_table=b.replace('keys[0] = D_8008B040;','keys[0] = 0x3B3C;'),
  actor_write=b.replace('    return result;','    actor[0xAD] = 0;\n    return result;'))

def native_harness():
 text=source.HEADERS+'#include <stddef.h>\n'+source.DECLARATIONS+source.SELECTED+'\n'
 for name,b in controls().items():text+=b.replace(source.FUNCTION,'negative_'+name)+'\n'
 names=','.join('negative_'+n for n in controls())
 return text+r'''
u16 D_8008B040;
typedef struct { u8 pad0[0x28]; f32 motion; u8 pad2C[0x58]; u16 type; u8 pad86[0x27]; u8 flag; u8 tail[2]; } NativeActor;
typedef char ptr32[sizeof(void*)==4 ? 1:-1];
typedef char offsets[(__builtin_offsetof(NativeActor,motion)==0x28 && __builtin_offsetof(NativeActor,type)==0x84 && __builtin_offsetof(NativeActor,flag)==0xAD)?1:-1];
static NativeActor actor;
static unsigned hash(const void *p,unsigned n){const u8*b=p;unsigned h=2166136261u;while(n--)h=(h^*b++)*16777619u;return h;}
static int expected(unsigned kind,unsigned mode,unsigned flag,u32 bits,unsigned keys){
 union {u32 bits;f32 f;}x;x.bits=bits;
 if(!mode && (kind==(keys>>8)||kind==(keys&255)))return 3;
 if(flag)return 2;
 return x.f==0.0f?4:1;
}
static int trial(s32(*fn)(u8*,u8),unsigned kind,unsigned mode,unsigned flag,u32 value,unsigned keys){
 unsigned i,before;union{u32 bits;f32 f;}x;u8*p=(u8*)&actor;
 for(i=0;i<sizeof(actor);i++)p[i]=(u8)(i*29+0x5A);
 actor.type=(u16)kind;actor.flag=(u8)flag;x.bits=value;actor.motion=x.f;D_8008B040=(u16)keys;
 before=hash(&actor,sizeof(actor));i=fn((u8*)&actor,(u8)mode);
 return i!=(unsigned)expected(kind,mode,flag,value,keys)||before!=hash(&actor,sizeof(actor))||D_8008B040!=keys;
}
static int run(void){
 static const u32 f[]={0,0x80000000u,0x3F800000,0xBF800000,1,0x7F800000,0xFF800000,0x7FC00001,0x7F7FFFFF};
 static const unsigned kinds[]={0,1,58,59,60,61,255,256,315,316,0xFF3B,0xFFFF};
 static const unsigned keys[]={0x3B3C,0,0xFFFE,0x003B,0x3C3C};
 static s32(*negative[])(u8*,u8)={''' + names + r'''};
 unsigned k,m,fl,v,t,n,hit;
 for(k=0;k<65536;k++)for(m=0;m<3;m++)for(fl=0;fl<2;fl++)for(v=0;v<3;v++)
  if(trial(func_151592B8,k,m==0?0:m==1?1:255,fl,v==0?0:v==1?0x3F800000:0x7FC00001,0x3B3C))return 1;
 for(m=0;m<256;m++)for(k=0;k<12;k++)for(fl=0;fl<2;fl++)for(v=0;v<9;v++)for(t=0;t<5;t++)
  if(trial(func_151592B8,kinds[k],m,fl?255:0,f[v],keys[t]))return 2;
 for(n=0;n<sizeof(negative)/sizeof(*negative);n++){
  hit=0;
  for(m=0;m<2;m++)for(k=0;k<12;k++)for(fl=0;fl<2;fl++)for(v=0;v<9;v++)for(t=0;t<5;t++)
   hit+=trial(negative[n],kinds[k],m,fl,f[v],keys[t]);
  if(!hit)return 3+n;
 }
 return 0;
}
''' + START

class ClassifierTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;source.verify_prepared(cls.out);cls.values=source.snapshot(cls.out);rom=cls.values['conker/conker.us.bin']
  cls.truth=list(struct.unpack_from('>46I',rom,source.ROM));data,fs=source.link_owner(ROOT,cls.out,cls.out/'qualified-padded.o',source.OWNER)
  cls.words=list(struct.unpack_from('>46I',data,fs[source.FUNCTION]['value']));data,fs=source.link_owner(ROOT,cls.out,cls.out/'after-owner.o',source.OWNER)
  cls.raw=list(struct.unpack_from('>46I',data,fs[source.FUNCTION]['value']))
 def compare(self,c,raw=True):
  initial=fixture(c);expected,value=reference(initial,c);pair=[]
  for words in(self.truth,self.words):
   m=ClassifierOracle(words,initial,c).run();self.assertEqual(m.r[2],value,c);self.assertEqual(m.memory,expected,c);self.assertFalse(m.calls);pair.append(m)
  self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].r[29],STACK+c.phase)
  if raw and not c.alias:
   m=ClassifierOracle(self.raw,initial,c).run();self.assertEqual(m.r[2],value,c);self.assertEqual(public(m.memory),public(expected),c)
  return pair[0]
 def test_01_literal_owner_and_actual_Make(self):
  self.assertEqual(self.words,self.truth);q=json.loads((self.out/'qualification.json').read_text())
  self.assertEqual((q['body_words'],q['frame'],q['new_guards'],q['bindings']),(46,24,9,2));self.assertEqual(q['Make']['commands'],5)
  self.assertTrue(q['Make']['complete_padded_object_equal']);self.assertGreater(q['preserved_neighbors'],0)
  rom=self.values['conker/conker.us.bin'];jal=0x0C000000|((source.ENTRY>>2)&0x3FFFFFF)
  direct=[i+0x14FD2B50 for i in range(0,len(rom)-3,4)if struct.unpack_from('>I',rom,i)[0]==jal]
  literals=[i for i in range(0,len(rom)-3,4)if struct.unpack_from('>I',rom,i)[0]==source.ENTRY]
  self.assertEqual(direct,[0x15158E20]);self.assertFalse(literals)
  self.assertEqual(rom[0x22FB00:0x22FB10],bytes.fromhex('3B3C0000000000000000000000000000'))
  self.receipt['owner']=dict(words=46,frame=24,guards=9,bindings=2,neighbors=q['preserved_neighbors'],GLOBAL_ASM=q['preserved_global_asm'],actual_Make_commands=5,direct_calls=direct)
 def test_02_guest_modes_types_priorities_and_float_bits(self):
  count=0;visited=set()
  for mode,kind in itertools.product(range(256),(0,0x3B,0x3C,0xFF3B)):
   for flag,motion in((0,0),(0,0x80000000),(0,0x3F800000),(1,0xBF800000)):
    m=self.compare(Case(kind,mode,flag,motion));visited.update(m.visits);count+=1
  for kind,flag,motion in itertools.product(range(256),(0,255),FLOATS):
   m=self.compare(Case(kind,0,flag,motion));visited.update(m.visits);count+=1
  for keys,kind in itertools.product((0,0x003B,0xFFFE,0x3C3C),(0,0x3B,0x3C,254,255,256,65535)):
   self.compare(Case(kind,0,0,0,keys));count+=1
  self.assertEqual(visited,set(range(source.ENTRY,source.ENTRY+184,4))-{source.ENTRY+4*29,source.ENTRY+4*34})
  self.receipt['guest']=dict(cases=count,all_mode_bytes=True,all_low_kind_bytes=True,high_kind_controls=True,signed_zero_NaN_infinity_subnormal=True,priority_checked=True,dead_words=[29,34],raw_public_states_equal=True,fitted_complete_states_equal=True)
 def test_03_stack_aliases_high_argument_homes_and_gates(self):
  count=0
  for alias,phase,mode in itertools.product(range(1,7),(0,8),(0,1,0x100,0x12340000,0x123400FF)):
   for kind,flag,motion in((0x3B,0,0),(0x3C,1,0xBF800000),(0xFF3B,0,0x80000000),(1,0,0x7FC00001)):
    self.compare(Case(kind,mode,flag,motion,0x3B3C,phase,alias),False);count+=1
  c=Case(mode=1,flag=1);m=fixture(c)
  for i in range(16):m.pop(source.TABLE+i)
  for i in range(2):m.pop(ACTOR+0x84+i)
  for i in range(4):m.pop(ACTOR+0x28+i)
  a=ClassifierOracle(self.truth,m,c).run();b=ClassifierOracle(self.words,m,c).run();self.assertEqual(a.r[2],2);self.assertEqual(complete(a),complete(b))
  self.receipt['aliases']=dict(cases=count,layouts=6,phases=2,full_incoming_mode_homes=True,late_flag_and_motion_reads=True,disabled_scan_needs_no_table_or_kind_mapping=True,guest_stack_aliases_only=True,raw_stack_placement_not_claimed_equal=True)
 def test_04_original_caller_window_and_two_argument_ABI(self):
  rom=self.values['conker/conker.us.bin'];entry,end,skip=0x15158E00,0x15158E40,0x15158F74
  words=list(struct.unpack_from('>16I',rom,entry-0x14FD2B50));count=0
  for mode,kind,flag,motion,layout,enabled,phase in itertools.product((0,1,255),(0x3B,0x3C,0xFF3B),(0,1),(0,0x3F800000),(0,1,2),(0,1),(0,8)):
   c=Case(kind,mode,flag,motion,phase=phase);initial=fixture(c);owner=(CARRIER,ACTOR,ACTOR-8)[layout]
   for i,x in enumerate((0x3F000000,0x40000000,0xBF800000)):put(initial,ACTOR+0x14+4*i,x)
   put(initial,owner+0x18,ACTOR);initial[owner+0x1D]=mode;initial[owner+0x31]=enabled
   prior=(kind+mode+flag)%3;expected=dict(initial);actor=get(expected,owner+0x18);expected[owner+0x2F]=prior;arg=expected[owner+0x1D]
   for i in range(3):put(expected,owner+0x20+4*i,get(expected,actor+0x14+4*i))
   rc=Case(kind,arg,flag,motion,phase=phase);expected,value=reference(expected,rc,actor);expected[owner+0x30]=value
   pair=[]
   for target in(self.truth,self.words):
    connected={source.ENTRY+4*i:w for i,w in enumerate(target)};m=ClassifierOracle(words,initial,c,entry,connected,(end,skip));m.r[17]=owner;m.r[2]=prior
    with self.assertRaises(Boundary):m.run()
    self.assertEqual(m.target_calls,[(actor,arg)]);self.assertEqual(m.memory,expected);pair.append(m)
   self.assertEqual(complete(pair[0]),complete(pair[1]));count+=1
  self.receipt['caller']=dict(cases=count,site=0x15158E20,actual_entered_calls=count*2,two_arguments=True,delay_slot_position_store=True,return_byte_store=True,caller_owner_unchanged=True,whole_parent_acceptance=False,previous_component_return_bounded=[0,1,2])
 def test_05_native32_SDK_and_effective_compiled_negatives(self):
  text=native_harness()
  for opt in('-O0','-O2','-O3'):
   p=self.out/('native-'+opt[1:]+'.c');p.write_text(text);exe=p.with_suffix('');result=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr);self.assertEqual(subprocess.run([str(exe)],timeout=120).returncode,0,opt)
  self.receipt['native']=dict(profiles=['O0','O2','O3'],all_u16_kinds=True,all_u8_modes=True,cases_per_profile=65536*3*2*3+256*12*2*9*5,compiled_negatives=len(controls()),trap_UBSan=True,SDK_widths_offsets=True,typed_actor_fields=True,readonly_actor_and_table=True,stack_aliases_not_claimed_portable_C=True)
 def test_06_fired_guest_access_fault_prefixes(self):
  count=0
  for c in(Case(),Case(kind=1),Case(kind=1,mode=1,flag=1),Case(alias=1),Case(alias=2),Case(alias=3),Case(alias=4),Case(mode=0x100,alias=5)):
   m=self.compare(c,c.alias==0)
   for at in range(m.root_accesses):
    pair=[]
    for words in(self.truth,self.words):
     x=ClassifierOracle(words,fixture(c),c);x.root_fault=at
     with self.assertRaises(faults.AccessBoundary):x.run()
     self.assertEqual(x.root_accesses,at);pair.append(x)
    self.assertEqual(complete(pair[0]),complete(pair[1]));count+=1
  self.assertGreater(count,0);self.receipt['faults']=dict(fired_prefix_pairs=count,complete_states_equal=True,portable_C_fault_semantics_claimed=False)
 def test_07_guard_controls_actual_padder_and_GNU_rebases(self):
  raw,rs=source.payload(self.out/'selected.o',source.FUNCTION)
  for i in range(46):
   bad=bytearray(raw);bad[4*i+3]^=1
   with self.assertRaises(ValueError):source.normalized(bytes(bad),rs)
  with self.assertRaises(ValueError):source.normalized(raw,{})
  with self.assertRaises(ValueError):source.normalized(raw[:-4],rs)
  with self.assertRaises(ValueError):source.guard_bytes(self.values['conker/retail_word_patches.us.csv']+b'\n',raw,rs)
  import csv,io
  rows=list(csv.DictReader(io.StringIO((self.out/'qualified-guards.csv').read_text())));rows[-1]['expected']='0x%08X'%(int(rows[-1]['expected'],16)^1)
  bad=self.out/'negative-real-padder.csv'
  with bad.open('w',newline='')as stream:
   writer=csv.DictWriter(stream,fieldnames=list(rows[-1]));writer.writeheader();writer.writerows(rows)
  with self.assertRaises((ValueError,RuntimeError)):source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=bad,filename=source.OWNER)
  fit,bind=source.normalized(raw,rs);asm,missing=emit_function(fit,dict(value=0,size=184),bind,source.FUNCTION,dict(D_8008B040=source.TABLE));self.assertFalse(missing)
  p=self.out/'independent-fitted.s';p.write_text(asm);obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-mabi=32','-o',str(obj),str(p)],capture_output=True,check=True)
  links=0
  for index,(entry,table)in enumerate(((source.ENTRY,source.TABLE),(source.ENTRY+0x200000,source.TABLE+0x7FF0),(source.ENTRY+0x500000,source.TABLE+0x17000))):
   images=[]
   for k,target in enumerate((source.original(ROOT,self.out),obj)):
    script=self.out/('rebase-%d-%d.ld'%(index,k));elf=script.with_suffix('.elf');script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
    subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,'--defsym=D_8008B040=0x%X'%table,'-o',str(elf),str(target)],capture_output=True,check=True)
    images.append(list(struct.unpack_from('>46I',sections(elf)['.text'][1])));links+=1
   self.assertEqual(images[0],images[1])
   for c in(Case(),Case(kind=1),Case(kind=0x3C,mode=255)):
    initial=fixture(c,table);models=[ClassifierOracle(w,initial,c,entry).run()for w in images];self.assertEqual(complete(models[0]),complete(models[1]))
  self.receipt['guards']=dict(raw_word_controls=46,bindings_extent_history=True,actual_padder_negative=True,GNU_links=links,layouts=3,HI_LO_carry=True,local_pair_translation=-8,live_roles=2)
 def test_08_strict_image_neighbors_and_protected_data(self):
  before=self.values['conker/build/conker.us.elf'];truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+184];expected=source.predicted_image(before,truth)
  source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);audit=source.linked_function_audit(self.out/'before-conker_build_conker.us.elf',self.out/'first-linked.elf')
  target=next(off for off,n,_,_ in source.symbol_rows(before)if n==source.FUNCTION)
  for at in(0,len(expected)-1,source.elf_slot_offset(before,source.ENTRY,184),source.elf_slot_offset(before,source.TABLE,16),target+8,before.index(b'D_800991D0\0'),before.index(b'D_8009E6E0\0')):
   bad=bytearray(expected);bad[at]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  data=source.audit_layout(self.out/'first-linked.elf',ROOT/'conker');self.assertTrue(data['exact']);self.assertEqual((data['owner_count'],data['bytes'],data['different_bytes']),(720,189088,0))
  source.check_inputs(ROOT,self.out,(ROOT/source.SOURCE).read_bytes()!=self.values[source.SOURCE])
  self.receipt['strict']=dict(changed_bytes=137,code_bytes=122,metadata_bytes=15,exclusions=0,corruptions=7,functions=audit['functions'],other_bodies_fixed=audit['other_bodies_fixed'],protected_data=data)

if __name__=='__main__':unittest.main()
