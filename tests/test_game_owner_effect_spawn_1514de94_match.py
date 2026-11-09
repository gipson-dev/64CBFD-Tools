"""Direct C owner effect spawner: complete owner/image, O32 calls and native ABI."""
import csv,io,itertools,json,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_owner_effect_spawn_1514de94_match as match
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests import game_owner_effect_spawn_1514de94_oracle as guest
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_projected_packet_draw import native_command
ROOT=match.ROOT

def corpus():
 for mode in range(256):
  for mutation in(0,2,4,6):yield guest.Case(mode=mode,mutation=mutation,seed=mode%len(guest.PATTERNS),phase=8*(mode%2))
 for owner,effect,record,mode,mutation,phase,seed in itertools.product((0,guest.OWNER),(guest.EFFECT,guest.OWNER),(0,guest.RECORD,guest.OWNER),(0,1,128,255),range(8),(0,8),(0,13)):
  yield guest.Case(owner=owner,effect=effect,record=record,mode=mode,mutation=mutation,phase=phase,seed=seed)

def controls():
 b=match.SELECTED;first=b.index('func_15160CDC(');end=b.index(';',first)+1
 args=['owner','12','&D_800A58AC','&D_800A58B8','D_800A5E04','2','300','255','255','255','255','0','1','1','255','1']
 wrong=['NULL','11','&D_800A58B8','&D_800A58AC','0.0f','3','299','254','254','254','254','1','0','0','254','0'];rows={}
 for i,v in enumerate(wrong):
  a=list(args);a[i]=v;rows['first_argument_'+str(i)]=b[:first]+'func_15160CDC('+', '.join(a)+');'+b[end:]
 rows.update(animation=b.replace('owner, 60, 1.0f, 0','owner, 59, 1.0f, 0'),scale=b.replace('60, 1.0f','60, 0.5f'),animation_mode=b.replace('60, 1.0f, 0','60, 1.0f, 1'),wrong_flag=b.replace('D_800BE9B4 == 0','D_800BE9B4 != 0'),wrong_timer=b.replace('= 2400','= 2401'),wrong_offset=b.replace('+ 0x38','+ 0x3C'),wrong_record=b.replace('owner, 0, &D_800A58C4, 2, 300, 11','owner, 0, &D_800A58C4, 2, 300, 12'),wrong_key=b.replace('0x19);','0x18);'),missing_link=b.replace('    func_1514EC1C((s32)created, (s32)owner, 0x19);','    (void)created;'),cached_mode=b.replace('    u8 *effect;','    u8 cachedMode = D_800BE9B4;\n    u8 *effect;').replace('if (D_800BE9B4 == 0)','if (cachedMode == 0)'))
 return rows

def linked(obj,entry,label,out,defs=None):
 defs=guest.symbols()if defs is None else defs;text,functions,refs=parse_object(obj);f=functions[match.FUNCTION];assembly,unknown=emit_function(text,f,refs,match.FUNCTION,defs);assert not unknown;p=out/label
 p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%(n,a)for n,a in defs.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack_from('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1]))

def native_harness(body):
 header=match.ISOLATED_HEADER
 support=r'''
union Buffer { s32 words[256]; u8 bytes[1024]; } ownerMem,effectMem,recordMem;
GameEffectVector D_800A58AC,D_800A58B8,D_800A58C4;
f32 D_800A5E04;u8 D_800BE9B4;
static u32 patterns[]={0,0x80000000,1,0x007FFFFF,0x00800000,0x3F800000,0xBF800000,0x7F7FFFFF,0xFF7FFFFF,0x7F800000,0xFF800000,0x7FC01234,0x7F801234,0xFFFFFFFF};
static u8 *actor,*answer,*record;static u32 stage,error,mutation,initialWord,seed;static u32 expected[3][3],parameter;
static u32 word(f32 f){union {f32 f;u32 u;}v;v.f=f;return v.u;}
#define value(v) (((union {u32 bits; f32 f;}){.bits=(v)}).f)
static void verify(u32 *a,u32 *b,u32 n){u32 i;for(i=0;i<n;i++)if(a[i]!=b[i])error=1;}
static void observe(void){u32 i,j;GameEffectVector *v[3]={&D_800A58AC,&D_800A58B8,&D_800A58C4};for(i=0;i<3;i++){u32 w[3]={word(v[i]->x),word(v[i]->y),word(v[i]->z)};verify(w,expected[i],3);}if(word(D_800A5E04)!=parameter)error=1;
 if(stage<2&&*(s32*)(answer+56)!=(s32)initialWord)error=1;
 if(stage>=2&&*(s32*)(answer+56)!=(s32)(D_800BE9B4?initialWord:2400))error=1;
 if(mutation&4){for(i=0;i<3;i++){for(j=0;j<3;j++)expected[i][j]^=0x5A5A5A5A;v[i]->x=value(expected[i][0]);v[i]->y=value(expected[i][1]);v[i]->z=value(expected[i][2]);}parameter=0xBF800000;D_800A5E04=value(parameter);}
 if((mutation&2)&&stage==1)D_800BE9B4^=255;stage++;
}
void *func_15160CDC(u8*o,u8 type,GameEffectVector*a,GameEffectVector*b,f32 f,u8 kind,s16 duration,s32 r,s32 g,s32 blue,s32 alpha,u8 flag1,u8 field,u8 flag2,u8 slot,s32 context){u32 got[]={(u32)o,type,(u32)a,(u32)b,word(f),kind,(u32)duration,(u32)r,(u32)g,(u32)blue,(u32)alpha,flag1,field,flag2,slot,(u32)context};u32 want[]={(u32)actor,12,(u32)&D_800A58AC,(u32)&D_800A58B8,parameter,2,300,255,255,255,255,0,1,1,255,1};if(stage!=0)error=1;verify(got,want,16);observe();return (void*)0xDEADBEEF;}
u8 *func_15083568(u8*o,s32 animation,f32 scale,s32 mode){if(stage!=1||o!=actor||animation!=60||word(scale)!=0x3F800000||mode)error=1;observe();return answer;}
struct225 *func_15160A58(u8*o,u8 type,void*v,u8 kind,s16 duration,s32 subtype,s32 r,s32 g,s32 b,s32 count,s32 zero,s8 tag,s32 z2,u8 z3,u8 slot,s32 context){u32 got[]={(u32)o,type,(u32)v,kind,(u32)duration,(u32)subtype,(u32)r,(u32)g,(u32)b,(u32)count,(u32)zero,(u32)tag,(u32)z2,z3,slot,(u32)context};u32 want[]={(u32)actor,0,(u32)&D_800A58C4,2,300,11,255,255,255,2,0,0xFFFFFFFF,0,0,255,1};if(stage!=2)error=1;verify(got,want,16);observe();return (struct225*)record;}
s32 func_1514EC1C(s32 r,s32 o,s16 key){if(stage!=3||(u32)r!=(u32)record||(u32)o!=(u32)actor||key!=25)error=1;observe();return (s32)0xABCD1234;}
'''
 tail=r'''
static int run(void){u32 mode,mut,alias,rec,own,i,j;for(seed=0;seed<14;seed++)for(mode=0;mode<256;mode+=(seed?85:1))for(mut=0;mut<4;mut++)for(alias=0;alias<2;alias++)for(rec=0;rec<3;rec++)for(own=0;own<2;own++){
 actor=own?ownerMem.bytes:0;answer=alias?ownerMem.bytes:effectMem.bytes;record=rec==0?0:rec==1?recordMem.bytes:ownerMem.bytes;stage=error=0;mutation=mut*2;D_800BE9B4=mode;initialWord=0x87654321;*(s32*)(answer+56)=(s32)initialWord;
 for(i=0;i<3;i++)for(j=0;j<3;j++)expected[i][j]=patterns[(seed+3*i+j)%14];
 D_800A58AC.x=value(expected[0][0]);D_800A58AC.y=value(expected[0][1]);D_800A58AC.z=value(expected[0][2]);D_800A58B8.x=value(expected[1][0]);D_800A58B8.y=value(expected[1][1]);D_800A58B8.z=value(expected[1][2]);D_800A58C4.x=value(expected[2][0]);D_800A58C4.y=value(expected[2][1]);D_800A58C4.z=value(expected[2][2]);parameter=seed?patterns[seed]:0x3C088723;D_800A5E04=value(parameter);
 func_1514DE94(actor);if(error||stage!=4)return 1;}return 0;}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''
 return header+support+'\n'+body+'\n'+tail

class OwnerEffectTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/'conker/conker.us.bin').read_bytes();cls.truth=list(struct.unpack_from('>79I',cls.rom,match.ROM));cls.raw=linked(cls.out/'qualified-owner.o',match.ENTRY,'raw-suite',cls.out);cls.fitted=linked(cls.prepared['qualified_object'],match.ENTRY,'padded-suite',cls.out);cls.blob,cls.refs=match.function_blob(cls.out/'qualified-owner.o');assert cls.truth==cls.raw==cls.fitted
 def receipt(self,n,v):(self.out/(n+'.json')).write_text(json.dumps(v,indent=2)+'\n')
 def compare(self,c,images=None,entry=match.ENTRY,defs=None,initial=None):
  initial=guest.fixture(c,defs)if initial is None else initial;expected,calls,snaps=guest.reference(initial,c,defs);pair=[]
  for words in images or(self.truth,self.raw,self.fitted):
   m=guest.Oracle(words,initial,c,entry,defs).run();self.assertEqual((guest.public(m.memory),m.calls,m.snaps),(guest.public(expected),calls,snaps),c);pair.append(m)
  self.assertTrue(all(guest.state(m)==guest.state(pair[0])for m in pair));return pair
 def test_01_complete_owner_Make_and_literal_image(self):
  q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['raw_neighbors'],q['padded_neighbors'],q['diagnostics']),(79,72,0,77,77,4));self.assertEqual((q['actual_Make']['commands'],q['actual_Make']['functions']),(3,78));self.assertEqual((q['exclusions'],q['named_metadata_rows']),(0,2));self.assertTrue(q['direct_C']);self.assertEqual(match.certificate(self.blob,self.refs)['guards'],0)
  for at in range(316):
   b=bytearray(self.blob);b[at]^=1
   with self.assertRaises(ValueError):match.normalize(bytes(b),self.refs)
  for at in self.refs:
   refs=dict(self.refs);refs[at]=[(refs[at][0][0],'wrong')]
   with self.assertRaises(ValueError):match.normalize(self.blob,refs)
  before,after=self.prepared['predecessor_elf'].read_bytes(),self.prepared['qualified_elf'].read_bytes()
  for at in(0x80,len(after)-1,match.elf_slot_offset(before,match.ENTRY,316),2980264,3228124):
   b=bytearray(after);b[at]^=1
   with self.assertRaises(ValueError):match.strict_image(before,bytes(b),self.rom[match.ROM:match.ROM+316])
 def test_02_guest_live_mode_all_arguments_and_aliases(self):
  count=0;seen=set()
  for c in corpus():seen.update(self.compare(c)[0].visits);count+=1
  self.assertEqual(seen,set(range(match.ENTRY,match.ENTRY+316,4)));self.receipt('guest-contract',dict(cases_per_body=count,visited_words=79,all_mode_bytes=True,guest_home_mutations=True,owner_effect_record_aliases=True,all_16_argument_words=True,complete_private_state_equal=True))
 def test_03_fault_prefixes_and_null_result_boundary(self):
  count=delay=0
  for mode,mut,phase in itertools.product((0,1,255),(0,1,2,7),(0,8)):
   c=guest.Case(mode=mode,mutation=mut,phase=phase);initial=guest.fixture(c);m=guest.Oracle(self.truth,initial,c).run()
   for cut in range(m.all_accesses):
    pair=[guest.Oracle(w,initial,c)for w in(self.truth,self.raw,self.fitted)]
    for v in pair:
     v.cut=cut
     with self.assertRaises(faults.AccessBoundary):v.run()
    self.assertTrue(all(guest.state(v)==guest.state(pair[0])for v in pair));count+=1;delay+=pair[0].delay_of is not None
  pair=[];c=guest.Case(effect=0)
  for w in(self.truth,self.raw,self.fitted):
   m=guest.Oracle(w,guest.fixture(c),c)
   with self.assertRaisesRegex(AssertionError, "unmapped store"):m.run()
   pair.append(m)
  self.assertTrue(all(guest.state(v)==guest.state(pair[0])for v in pair));self.assertEqual(len(pair[0].calls),2)
  self.compare(guest.Case(effect=0,mode=1));self.receipt('aliases-faults',dict(fired_prefix_triples=count,delay_slot_cuts=delay,null_effect_mode_zero_fault_after_two_calls=True,null_effect_nonzero_mode_valid=True,portable_C_fault_claimed=False))
 def test_04_real_caller_window_and_frozen_helper_status(self):
  words=list(struct.unpack_from('>4I',self.rom,0xC6BE4));self.assertEqual(words,[0x0D4537A5,0x02202025,0x10000130,0x24020001]);count=0
  for mode,mut,phase,record in itertools.product((0,1,128,255),(0,1,2,7),(0,8),(0,guest.RECORD)):
   c=guest.Case(mode=mode,mutation=mut,phase=phase,record=record);initial=guest.fixture(c);expected,calls,snaps=guest.reference(initial,c);pair=[]
   for body in(self.truth,self.raw,self.fitted):
    code=dict(zip(range(match.ENTRY,match.ENTRY+316,4),body));code[guest.END]=0;m=guest.Oracle(words,initial,c,guest.WINDOW,connected=code);m.r[17]=c.owner;m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(guest.END,)
    with self.assertRaises(WindowBoundary):m.run()
    self.assertEqual((guest.public(m.memory),m.calls,m.snaps,m.r[2]),(guest.public(expected),[(match.ENTRY,(c.owner,))]+calls,snaps,1));pair.append(m)
   self.assertTrue(all(guest.state(m)==guest.state(pair[0])for m in pair));count+=1
  ws=struct.unpack_from('>%dI'%(len(self.rom)//4),self.rom);self.assertEqual([4*i for i,w in enumerate(ws)if w>>26 in(2,3)and match.ENTRY<=(((w&0x3FFFFFF)<<2)|0x10000000)<match.ENTRY+316],[0xC6BE4]);self.assertFalse([w for w in ws if match.ENTRY<=w<match.ENTRY+316])
  before=self.prepared['predecessor_elf'].read_bytes();status=[]
  for e,p,n,exact in((0x15083568,0xB0A18,89,True),(0x1514EC1C,0x17C0CC,49,True),(0x15160A58,0x18DF08,71,True),(0x15160CDC,0x18E18C,85,False)):
   at=match.elf_slot_offset(before,e,n*4);self.assertEqual(before[at:at+n*4]==self.rom[p:p+n*4],exact);status.append(dict(entry=hex(e),literal_words=n,baseline_exact=exact))
  self.receipt('callers',dict(cases_per_body=count,actual_window_words=4,parent='func_15097A8C',full_parent_qualified=False,return_ignored_and_continuation_one=True,aligned_callers=1,helpers=status,all_four_callees_bounded=True))
 def test_05_bounded_original_first_factory_ABI(self):
  from tools.tests.game_two_vector_effect_oracle import EffectOracle,Case,provider_reference,public
  from tools.experiments import game_two_vector_effect_match as source
  body=list(struct.unpack_from('>85I',self.rom,0x18E18C));count=0;seen=set()
  for owner,allocated,mode,phase,duration,flag in itertools.product((0,guest.OWNER),(False,True),(0,1),(0,8),(300,0xFFFF8000),(0,255)):
   c=Case(owner=owner,allocated=allocated,mode=mode,phase=phase);initial=guest.fixture(guest.Case(phase=phase));args=(owner,12,0x800A58AC,0x800A58B8,0x3C088723,2,duration,255,255,255,255,flag,1,flag,255,1)
   for i,v in enumerate(args[4:],4):guest.put(initial,guest.STACK+phase+4*i,v)
   expected,calls,obs,result=provider_reference(initial,args,c,guest.STACK+phase);m=EffectOracle(body,initial,c,entry=source.EFFECT,arguments=args[:4]).run();self.assertEqual((public(m.memory),m.calls,m.factory_observations,m.r[2]),(public(expected),calls,obs,result));seen.update(m.visits);count+=1
  self.assertEqual(len(seen),85);self.receipt('connections',dict(cases=count,original_first_factory_words=85,visited_words=85,baseline_factory_C_unmatched=True,production_integration_claimed=False,bounded_providers=['func_151602C0','memcpy']))
 def test_06_independent_relocations(self):
  count=0
  for j,entry in enumerate((0x15007FF0,0x16008010,0x1700FFF0)):
   defs={n:(entry+0x10004*(i+1)if n.startswith('func_')else(0x81007FF0+j*0x10000+i*0x10020)&0xFFFFFFFF)for i,n in enumerate(guest.symbols())};defs['D_800BE9B4']+=3
   images=[linked(p,entry,'rebase-%d-%d'%(j,i),self.out,defs)for i,p in enumerate((self.out/'qualified-owner.o',self.prepared['qualified_object']))];self.assertEqual(images[0],images[1])
   for mode,mut,seed in itertools.product((0,1,255),(0,1,2,7),(0,13)):self.compare(guest.Case(mode=mode,mutation=mut,seed=seed),images,entry,defs);count+=1
  self.receipt('rebases',dict(cases_per_body=count,independent_GNU_links=6,code_data_and_four_calls_rebased=True))
 def test_07_compiled_semantic_negatives(self):
  receipts={};cases=[guest.Case(),guest.Case(mode=255),guest.Case(mutation=2),guest.Case(seed=7),guest.Case(effect=guest.OWNER,record=0,mutation=6)]
  for name,body in controls().items():
   self.assertNotEqual(body,match.SELECTED);obj,diag=compile_owner(ROOT,self.out,match.ISOLATED_HEADER+body,'negative-'+name);self.assertFalse(diag);ws=linked(obj,match.ENTRY,'negative-link-'+name,self.out);killed=False
   for c in cases:
    initial=guest.fixture(c);expected,calls,snaps=guest.reference(initial,c)
    try:
     m=guest.Oracle(ws,initial,c).run();killed=(guest.public(m.memory),m.calls,m.snaps)!=(guest.public(expected),calls,snaps)
    except(KeyError,AssertionError):killed=True
    if killed:break
   self.assertTrue(killed,name);receipts[name]=dict(compiled=True,public_counterexample=True)
  self.receipt('compiled-controls',receipts)
 def test_08_native32_complete_typed_packets(self):
  rows=[]
  for opt in('-O0','-O2','-O3'):
   p=self.out/('native'+opt+'.c');p.write_text(native_harness(match.SELECTED));binary=p.with_suffix('');cmd=native_command(opt)+['-fno-builtin','-fno-strict-aliasing','-mstackrealign',str(p),'-o',str(binary)];v=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True);self.assertEqual(v.returncode,0,v.stdout+v.stderr);self.assertEqual(subprocess.run([str(binary)],capture_output=True).returncode,0,opt);rows.append(opt)
  for name,body in controls().items():
   p=self.out/('native-negative-'+name+'.c');p.write_text(native_harness(body));binary=p.with_suffix('');v=subprocess.run(native_command('-O2')+['-fno-builtin','-fno-strict-aliasing','-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(v.returncode,0,v.stderr);self.assertNotEqual(subprocess.run([str(binary)],capture_output=True).returncode,0,name)
  self.receipt('native-contract',dict(profiles=rows,cases_per_profile=(256+13*4)*4*2*3*2,compiled_negatives=len(controls()),SDK_types=True,defined_aligned_storage=True,UBSan_traps=True,guest_home_mutations_excluded=True,all_float_transport_bits=True))

if __name__=='__main__':unittest.main()
