"""Literal owner/image checks and independent effect-call/native contracts."""
import csv,io,itertools,json,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_randomized_direction_effect_151b4ea4_match as match
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests import game_randomized_direction_effect_151b4ea4_oracle as guest
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_projected_packet_draw import native_command
ROOT=match.ROOT

def cases():
 for byte,mutation,phase in itertools.product(range(256),(0,3,7),(0,8)):
  yield guest.Case(selector=byte,mode=byte^255,integers=(byte,(byte*1664525+1013904223)&0xFFFFFFFF,(~byte)&0xFFFFFFFF),coordinates=byte%4,mutation=mutation,phase=phase,alias=byte%3)
 for field,value in itertools.product(range(3),(0,1,30,31,32,100,101,102,0x7FFFFFFF,0x80000000,0xFFFFFFFF)):
  a=[0,0,0];a[field]=value;yield guest.Case(integers=tuple(a))
 for first,second in itertools.product((0,1,0x80000000,0x3F000000,0x3F7FFF00,0x3F800000),(0,0x3F000000,0x3F800000)):yield guest.Case(floats=(first,second))

def controls():
 b=match.SELECTED
 result={n:b.replace(a,z)for n,a,z in(('no_reverse','-x * scale','x * scale'),('wrong_axis','-y * scale','-x * scale'),('signed_mod','u32 alpha, duration','s32 alpha, duration'),('duration_range','% 31','% 30'),('alpha_range','% 101','% 100'),('duration_bias','+ 20','+ 19'),('alpha_bias','+ 155','+ 154'),('wrong_variant','variant & 1','variant & 2'),('wrong_selector','velocity, selector','velocity, mode'),('wrong_mode','0, mode, 1','0, selector, 1'),('second_scale','152.0f','151.0f'),('second_bias','109.0f','108.0f'),('first_bias','+ -1.0f','+ -2.0f'),('unequal_sizes','size, size','size, 0.0f'))}
 result['early_size']=b.replace('    size = D_800AA3D8;','').replace('    first = func_150ADA68();','    size = D_800AA3D8;\n    first = func_150ADA68();')
 result['late_scale']=b.replace('    velocity[0] = -x * scale;','').replace('    size = D_800AA3D8;','    scale = D_800AA3D4;\n    velocity[0] = -x * scale;\n    size = D_800AA3D8;')
 assert all(v!=b for v in result.values());return result

def linked(obj,entry,label,out,defs=None):
 defs=guest.symbols()if defs is None else defs;t,fs,rs=parse_object(obj);f=fs[match.FUNCTION];assembly,unknown=emit_function(t,f,rs,match.FUNCTION,defs);assert not unknown;p=out/label
 p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%(n,a)for n,a in defs.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True)
 return list(struct.unpack_from('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1]))

class DirectionEffectTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/'conker/conker.us.bin').read_bytes();cls.truth=list(struct.unpack_from('>79I',cls.rom,match.ROM));cls.raw=linked(cls.out/'qualified-owner.o',match.ENTRY,'raw-suite',cls.out);cls.fitted=linked(cls.prepared['qualified_object'],match.ENTRY,'fitted-suite',cls.out);cls.blob,cls.refs=match.function_blob(cls.out/'qualified-owner.o');assert cls.truth==cls.fitted
 def receipt(self,n,v):(self.out/(n+'.json')).write_text(json.dumps(v,indent=2)+'\n')
 def check(self,c,images=None,entry=match.ENTRY,s=None):
  s=guest.symbols()if s is None else s;initial=guest.fixture(c,s);expected,calls,vector,draws=guest.reference(initial,c,s);pair=[]
  for w in(self.truth,self.raw,self.fitted)if images is None else images:
   m=guest.Oracle(w,initial,c,entry,s).run();self.assertEqual((guest.public(m.memory),m.calls,m.submissions[0][:2]),(guest.public(expected),calls,(calls[-1][1],vector)),c);pair.append(m)
  if images is None:self.assertEqual(guest.state(pair[0]),guest.state(pair[2]));self.assertEqual(guest.state(pair[0]),guest.canonical_state(pair[1]))
  else:self.assertEqual(guest.canonical_state(pair[0]),guest.state(pair[1]))
  return pair
 def test_01_owner_Make_guards_and_strict_image(self):
  q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['raw_neighbors'],q['padded_neighbors'],q['diagnostics']),(79,112,7,5,5,0));self.assertEqual((q['actual_Make']['commands'],q['actual_Make']['functions'],q['strict_changed_bytes'],q['exclusions'],q['named_metadata_rows']),(5,6,280,0,6))
  for at in range(316):
   b=bytearray(self.blob);b[at]^=1
   with self.assertRaises(ValueError):match.normalize(bytes(b),self.refs)
  for at in self.refs:
   refs=dict(self.refs);refs[at]=[(refs[at][0][0],'wrong')]
   with self.assertRaises(ValueError):match.normalize(self.blob,refs)
  rows=list(csv.DictReader(io.StringIO((self.out/'qualified-guards.csv').read_text())));indices=[i for i,r in enumerate(rows)if r['function']==match.FUNCTION];self.assertEqual(len(indices),7)
  for index in indices:
   altered=[dict(r)for r in rows];altered[index]['expected']='0x%08X'%(int(altered[index]['expected'],16)^1);p=self.out/'rejected-guard.csv'
   with p.open('w',newline='')as stream:w=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(altered)
   with self.assertRaises(ValueError):emit_padded_assembly(self.out/'qualified-owner.o',ROOT/'conker/asm/1E2180.s',filename=match.OWNER,word_patches_path=p)
  before,after=self.prepared['predecessor_elf'].read_bytes(),self.prepared['qualified_elf'].read_bytes()
  for at in(0x80,len(after)-1,match.elf_slot_offset(before,match.ENTRY,316)):
   bad=bytearray(after);bad[at]^=1
   with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),self.rom[match.ROM:match.ROM+316])
 def test_02_byte_domains_ordered_draws_and_live_values(self):
  n=0;seen=set()
  for c in cases():seen.update(self.check(c)[0].visits);n+=1
  self.assertEqual(seen,set(range(match.ENTRY,match.ENTRY+316,4)));self.receipt('guest-contract',dict(cases_per_body=n,visited_words=79,all_selector_mode_bytes=True,unsigned_moduli=True,five_ordered_draws=True,all16_arguments_and_vector=True,live_size_spread_and_incoming_homes=True,raw_end_state_equal_after_explicit_prologue_trace_permutation=True))
 def test_03_closed_prologue_and_literal_fitted_faults(self):
  def prefix(words,c,s):
   m=guest.Oracle(words,guest.fixture(c,s),c,s=s);m.code=WindowCode(m.code,m);m.code.ends=(match.ENTRY+32,)
   with self.assertRaises(WindowBoundary):m.run()
   return m
  c=guest.Case();s=guest.symbols();a,b=prefix(self.truth,c,s),prefix(self.raw,c,s);self.assertEqual(guest.state(a),guest.canonical_state(b))
  home=guest.STACK;frame=home-112;slots=match.check_prologue_addresses(home,s);protected=self.prepared['report']['protected_data'];self.assertTrue(protected['address']<=s['D_800AA3D4']<protected['address']+protected['bytes'])
  counters=0
  for slot in slots:
   alias=dict(s,D_800AA3D4=slot)
   with self.assertRaises(ValueError):match.check_prologue_addresses(home,alias)
   images=[linked(p,match.ENTRY,'alias-%X-%d'%(slot,i),self.out,alias)for i,p in enumerate((self.prepared['qualified_object'],self.out/'qualified-owner.o'))];a,b=(prefix(w,c,alias)for w in images);self.assertNotEqual(a.f[0],b.f[0]);counters+=1
  prefixes=0
  for words,retail in((self.truth,True),(self.raw,False)):
   for cut in range(4):
    initial=guest.fixture(c,s);m=guest.Oracle(words,initial,c,s=s);expected=dict(m.memory);operations=[('W',slots[0],4,m.r[31]),('W',slots[1],4,m.r[4]),('W',slots[2],4,m.r[7])];load=('R',s['D_800AA3D4'],4,guest.read(initial,s['D_800AA3D4']));operations=[load,*operations]if retail else[*operations,load];m.cut=cut
    with self.assertRaises(faults.AccessBoundary):m.run()
    self.assertEqual(m.trace,operations[:cut])
    for kind,address,width,value in operations[:cut]:
     if kind=='W':guest.put(expected,address,value,width)
    self.assertEqual(m.memory,expected);prefixes+=1
  cuts=delay=0
  for c in(guest.Case(),guest.Case(mutation=7,coordinates=1),guest.Case(coordinates=2,selector=255,mode=0)):
   initial=guest.fixture(c);done=guest.Oracle(self.truth,initial,c).run()
   for cut in range(done.all_accesses):
    pair=[]
    for w in(self.truth,self.fitted):
     m=guest.Oracle(w,initial,c);m.cut=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     pair.append(m)
    self.assertEqual(guest.state(pair[0]),guest.state(pair[1]));cuts+=1;delay+=pair[0].delay_of is not None
  self.receipt('aliases-faults',dict(alias_counterexamples=counters,independently_predicted_prologue_prefixes=prefixes,fired_fitted_retail_prefix_pairs=cuts,delay_slot_cuts=delay,raw_prologue_reconvergence=True,raw_literal_fault_equivalence_claimed=False,prologue_requires_disjoint_global_and_private_stores=True,portable_C_private_home_mutation_claimed=False))
 def test_04_complete_original_caller(self):
  words=list(struct.unpack_from('>22I',self.rom,0x1E22FC));n=0
  for selector,mode,mutation,phase in itertools.product((0,64,103,255),(0,255),(0,7),(0,8)):
   c=guest.Case(selector=selector,mode=mode,mutation=mutation,phase=phase);initial=guest.fixture(c);home=guest.STACK+phase
   coord=guest.COORDS[c.coordinates];arguments=(0,0,coord[2],*coord,guest.ACTOR)
   for i,v in enumerate(arguments[4:]):guest.put(initial,home+16+i*4,v)
   pair=[]
   for w in(self.truth,self.raw,self.fitted):
    m=guest.Oracle(words,initial,c,entry=0x151B4E4C,arguments=arguments,connected=dict(zip(range(match.ENTRY,match.ENTRY+316,4),w)));m.f[12],m.f[14]=coord[:2];m.run();self.assertEqual(m.submissions[0][2],struct.pack('>3I',*(v^0x80000000 if mutation&4 else v for v in coord)));pair.append(m)
   self.assertEqual(guest.state(pair[0]),guest.state(pair[2]));self.assertEqual(guest.state(pair[0]),guest.canonical_state(pair[1]));n+=1
  self.receipt('callers',dict(cases_per_body=n,complete_original_words=22,one_aligned_JAL=True,aligned_function_pointers=0,six_arguments=True,return_ignored=True))
 def test_05_original_RNG_and_complete_constructor(self):
  before=self.prepared['predecessor_elf'].read_bytes();globals={}
  for a,n in((guest.SCALE,12),(0x800A5480,12),(0x800AB330,256),(0x800AB43C,16),(guest.FACTOR,4)):
   at=match.elf_slot_offset(before,a,n);globals.update({a+i:b for i,b in enumerate(before[at:at+n])})
  n=0;visited=set()
  for selector,outcome,seed,consumer in itertools.product((0,64,103,255),(0,1),guest.SEEDS[:4],(False,True)):
   c=guest.Case(selector=selector,seed=seed,outcome=outcome,connected=1);initial=guest.fixture(c,globals=globals);expected,calls,vector,_=guest.reference(initial,c);pair=[]
   for w in(self.truth,self.raw,self.fitted):
    m=guest.Oracle(w,initial,c,connected=guest.helpers(self.rom,consumer)).run();self.assertEqual(m.submissions[0][:2],(calls[-1][1],vector));seed1=c.seed
    for _ in range(m.ordinal):seed1=guest.next_seed(seed1)
    self.assertEqual(guest.read(m.memory,guest.SEED,8),seed1);visited.update(m.visits);pair.append(m)
   self.assertEqual(guest.state(pair[0]),guest.state(pair[2]));self.assertEqual(guest.state(pair[0]),guest.canonical_state(pair[1]));n+=1
  for e,p,words in((guest.RI,0xDAED0,18),(guest.RF,0xDAF18,25),(guest.CREATE,0x2064C4,248),(guest.COPY,0x22EC0,11)):
   at=match.elf_slot_offset(before,e,words*4);self.assertEqual(before[at:at+words*4],self.rom[p:p+words*4])
  self.receipt('connections',dict(cases_per_body=n,original_integer_RNG_words=18,original_float_RNG_words=25,original_constructor_words=248,original_memcpy_words=11,constructor_words_visited=len(visited&set(range(guest.CREATE,guest.CREATE+992,4))),all_four_helper_baselines_exact=True,seed_updates_equal_independent_reference=True,selector_callbacks_and_factory_bounded=True,synthetic_callback_registry=True))
 def test_06_independent_rebases(self):
  n=0
  for j,entry in enumerate((0x15007FF0,0x16008010,0x1700FFF0)):
   s=dict(D_800AA3D4=0x81007FFC+j*0x10000,D_800AA3D8=0x82008004+j*0x10000,D_800AA3DC=0x8300FFF0+j*0x10000,func_150ADA20=entry+0x10004,func_150ADA68=entry+0x20008,func_151D9014=entry+0x3000C)
   images=[linked(p,entry,'rebase-%d-%d'%(j,i),self.out,s)for i,p in enumerate((self.out/'qualified-owner.o',self.prepared['qualified_object']))]
   for c in list(cases())[::127]:match.check_prologue_addresses(guest.STACK+c.phase,s);self.check(c,images,entry,s);n+=1
  self.receipt('rebases',dict(independent_GNU_links=6,cases_per_body=n,three_HI_LO_pairs_and_six_calls=True,raw_prologue_permutation_explicit=True))
 def test_07_compiled_semantic_negatives(self):
  rows={};quick=[guest.Case(),guest.Case(integers=(0x80000000,0xFFFFFFFF,2),mutation=3),guest.Case(selector=255,mode=0,mutation=1)]
  for name,fragment in controls().items():
   obj,diag=compile_owner(ROOT,self.out,match.ISOLATED_HEADER+fragment,'negative-'+name);self.assertFalse(diag);ws=linked(obj,match.ENTRY,'negative-link-'+name,self.out);killed=False
   for c in quick:
    initial=guest.fixture(c);expected,calls,vector,_=guest.reference(initial,c)
    try:m=guest.Oracle(ws,initial,c).run();killed=(m.calls,m.submissions[0][:2])!=(calls,(calls[-1][1],vector))
    except(AssertionError,KeyError):killed=True
    if killed:break
   self.assertTrue(killed,name);rows[name]=dict(compiled=True,public_counterexample=True)
  self.receipt('compiled-controls',rows)
 def test_08_native32(self):
  text,n=native_program();p=self.out/'native.c';p.write_text(text)
  for opt in('-O0','-O2','-O3'):
   binary=self.out/('native'+opt);v=subprocess.run(native_command(opt)+['-fno-builtin','-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(v.returncode,0,v.stderr);self.assertEqual(subprocess.run([str(binary)],capture_output=True).returncode,0,opt)
  self.receipt('native-contract',dict(cases_per_profile=n,profiles=['O0','O2','O3'],compiled_controls=len(controls()),all_controls_effective=True,all16_arguments_vector_and_position_payload=True,UBSan_traps=True,guest_private_home_cases_excluded=True))

def native_program():
 rows=[];quick=[guest.Case(),guest.Case(integers=(0x80000000,0xFFFFFFFF,2),mutation=3),guest.Case(selector=255,mode=0,mutation=1)]
 native_cases=list(dict.fromkeys(quick+[replace(c,phase=0,mutation=c.mutation&3)for c in cases()if c.coordinates!=2 and c.alias!=2]))
 def array(values):return'{'+','.join('0x%08Xu'%v for v in values)+'}'
 for c in native_cases:
  expected,calls,vector,_=guest.reference(guest.fixture(c),c);position=guest.position(c);row=[str(c.selector),str(c.mode),str(c.mutation),str(c.alias),array(c.integers),array(c.floats),array(guest.COORDS[c.coordinates]),array(calls[-1][1][2:]),array(vector),array(struct.unpack('>3I',guest.data(expected,position,12))),array(guest.read(expected,a)for a in(guest.SCALE,guest.SIZE,guest.SPREAD))];rows.append('{'+','.join(row)+'}')
 text=match.ISOLATED_HEADER+r'''
typedef char float_width[sizeof(f32)==4?1:-1];
typedef char pointer_width[sizeof(void*)==4?1:-1];
typedef union {u32 u;f32 f;} Bits;
typedef struct {u32 selector,mode,mutation,alias,integers[3],floats[2],coordinates[3],expected[14],vector[3],position[3],globals[3];} Row;
static const Row rows[]={
'''+',\n'.join(rows)+r'''
};
f32 D_800AA3D4,D_800AA3D8,D_800AA3DC;
static f32 positions[2][3];static const Row *current;static u32 ordinal,submitted,bad;
static f32 real(u32 value){Bits b;b.u=value;return b.f;}
static u32 word(f32 value){Bits b;b.f=value;return b.u;}
static void effect(void){u32 i;if(ordinal==1&&(current->mutation&1)){D_800AA3D4=4.0f;D_800AA3D8=0.5f;D_800AA3DC=3.0f;for(i=0;i<3;i++)positions[0][i]=real(0x3F800000+i*0x800000);}if(ordinal==5&&(current->mutation&2)){D_800AA3D8=0.75f;D_800AA3DC=4.0f;}}
f32 func_150ADA68(void){u32 i=ordinal++;if(i!=0&&i!=3)bad=1;effect();return real(current->floats[i==3]);}
s32 func_150ADA20(void){u32 i=ordinal++,j=i==1?0:i==2?1:2;if(i!=1&&i!=2&&i!=4)bad=1;effect();return(s32)current->integers[j];}
void *func_151D9014(f32 *position,f32 *vector,u8 selector,f32 first,s16 duration,u8 alpha,f32 second,u8 variant,f32 size0,f32 size1,u8 flag10,s32 word11,u8 flag12,u8 flag13,u8 mode,s32 word15){
 u32 i,a[14]={selector,word(first),(u32)(s32)duration,alpha,word(second),variant,word(size0),word(size1),flag10,(u32)word11,flag12,flag13,mode,(u32)word15};submitted++;
 if(ordinal!=5||position!=positions[current->alias]||submitted!=1)bad=1;
 for(i=0;i<14;i++)if(a[i]!=current->expected[i])bad=1;
 for(i=0;i<3;i++)if(word(vector[i])!=current->vector[i]||word(position[i])!=current->position[i])bad=1;
 return(void*)0x81234560u;
}
'''
 names=['selected',*controls()]
 for name,fragment in dict(selected=match.SELECTED,**controls()).items():text+=fragment.replace(match.FUNCTION,name,1)+'\n'
 text+=r'''
static int check(void(*fn)(f32*,f32,f32,f32,u8,u8),const Row *r){u32 i;current=r;bad=ordinal=submitted=0;D_800AA3D4=real(0x3DCCCCCD);D_800AA3D8=0.25f;D_800AA3DC=2.0f;
 for(i=0;i<3;i++){positions[0][i]=real(r->coordinates[i]);positions[1][i]=real(r->coordinates[i]^0x80000000u);}
 fn(positions[r->alias],real(r->coordinates[0]),real(r->coordinates[1]),real(r->coordinates[2]),r->selector,r->mode);
 if(submitted!=1||ordinal!=5||word(D_800AA3D4)!=r->globals[0]||word(D_800AA3D8)!=r->globals[1]||word(D_800AA3DC)!=r->globals[2])bad=1;return !bad;}
static int run(void){u32 i,j,killed['''+str(len(names))+r''']={0};void(*functions[])(f32*,f32,f32,f32,u8,u8)={'''+','.join(names)+r'''};
 for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){if(!check(functions[0],rows+i))return 1;for(j=1;j<sizeof(functions)/sizeof(functions[0]);j++)if(!killed[j]&&!check(functions[j],rows+i))killed[j]=1;}
 for(j=1;j<sizeof(functions)/sizeof(functions[0]);j++)if(!killed[j])return 80+j;return 0;}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''
 return text,len(native_cases)

if __name__=='__main__':unittest.main()
