"""Direct C channel command: owner, caller/helpers, native, faults and full image."""
from pathlib import Path
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_actor_channel_command_match as source
from tools.tests import game_actor_channel_command_oracle as oracle
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests.test_game_effect_position_payload import complete
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2]
C=oracle.Case

def controls():
 controls={'nonnegative':source.SELECTED.replace('func_1507E968(actor) > 0','func_1507E968(actor) >= 0'),'mode_release':source.SELECTED.replace('D_800D1928 = 0;','D_800D1928 = 1;'),'short_duration':source.SELECTED.replace('= 20;','= 19;'),'flag':source.SELECTED.replace('= 0xFFFE;','= 0xFFFD;'),'mode_one':source.SELECTED.replace('D_800D1928 = 2;','D_800D1928 = 3;'),'keep_zero':source.SELECTED.replace('if (duration != 0)','if (1)'),'lower_clamp':source.SELECTED.replace('duration = 1;','duration = 0;'),'clear':source.SELECTED.replace('actor[0x1FF] = 0;','actor[0x1FE] = 0;'),'boolean':source.SELECTED.replace('D_800D1928 = channel != 0;','D_800D1928 = channel > 0;')}
 return controls

def native_harness():
 controls_map=controls()
 src=source.HEADERS+source.DECLARATIONS+r'''
 typedef char Pointer32[sizeof(void*)==4?1:-1];
 s32 D_800D1928;
 static u8 *actor;static s32 channel,duration,countValue;static u32 mode,error,ncalls,callKinds[2],callB[2],callD[2];
 static void puthalf(u8*p,u16 v){u8*q=(u8*)&v;p[0]=q[0];p[1]=q[1];}
 __attribute__((noinline,noclone)) s32 func_1507E968(u8*p){
  if(p!=actor||ncalls!=0)error=1;callKinds[ncalls++]=1;
  if(mode&1)D_800D1928=0x12345678;
  if(mode&2){*(u16*)(p+0x72)=0xa5a5;p[0x1ff]=0xc7;}
  return countValue;}
 __attribute__((noinline,noclone)) void func_1507E500(u8*p,s32 b,s32 d){
  if(p!=actor||ncalls!=1)error=1;callKinds[ncalls]=2;callB[ncalls]=b;callD[ncalls]=d;ncalls++;
  if(mode&4)D_800D1928=0x76543210;
  if(mode&8){*(u16*)(p+0x72)=0x4567;p[0x1ff]=0x9a;}}
 '''+source.SELECTED
 for name,body in controls_map.items():src+=body.replace(source.FUNCTION,'negative_'+name)
 src+=r'''
 typedef void(*Update)(u8*,s32,s32);
 static Update volatile good=func_15080430;
 static const s32 values[]={0,1,2,19,20,21,255,0x7fffffff,(-2147483647-1),-1};
 static u8 expected[0x360];static u32 cases;
 static int one(Update fn,u32 seed,u32 nullActor){
  u32 i,wantedCalls=0,b=0,d=0;u32 expectedGlobal=0x5a5b5c5d;
  for(i=0;i<0x360;i++)actor[i]=expected[i]=(u8)(i*13+seed);
  D_800D1928=(s32)expectedGlobal;error=ncalls=0;
  if(!nullActor){
   wantedCalls=1;
   if(mode&1)expectedGlobal=0x12345678;
   if(mode&2){puthalf(expected+0x72,0xa5a5);expected[0x1ff]=0xc7;}
   if(countValue>0){
    if(channel==0){expectedGlobal=0;puthalf(expected+0x72,20);b=0;d=10;wantedCalls=2;}
    else{puthalf(expected+0x72,0xfffe);if(channel==1)expectedGlobal=2;
     else{b=(u32)channel;d=(u32)duration;wantedCalls=2;
      if(duration!=0){if(duration>20)d=20;else if(duration<0)d=1;}}}
    if(wantedCalls==2){if(mode&4)expectedGlobal=0x76543210;if(mode&8){puthalf(expected+0x72,0x4567);expected[0x1ff]=0x9a;}}
   }else{expectedGlobal=channel!=0;if(channel==0)expected[0x1ff]=0;}
  }
  fn(nullActor?0:actor,channel,duration);cases++;
  if(error||ncalls!=wantedCalls||(u32)D_800D1928!=expectedGlobal)return 1;
  if(ncalls&&callKinds[0]!=1)return 2;
  if(ncalls==2&&(callKinds[1]!=2||callB[1]!=b||callD[1]!=d))return 3;
  for(i=0;i<0x360;i++)if(actor[i]!=expected[i])return 4;
  return 0;}
 static int corpus(Update fn,u32 negative){u32 c,d,k,n,seed;int code;
  for(c=0;c<10;c++)for(d=0;d<10;d++)for(k=0;k<10;k++)for(mode=0;mode<16;mode++)for(n=0;n<2;n++){
   channel=values[c];duration=values[d];countValue=values[k];seed=c*17+d;
   code=one(fn,seed,n);if(code)return negative?1:code;}
  for(c=0;c<256;c++)for(k=0;k<2;k++)for(mode=0;mode<16;mode++){
   channel=c;duration=(s32)c;countValue=k;code=one(fn,c,0);if(code)return negative?1:code;}
  return 0;}
 static int run(void){u32 address,requested,i;Update bad[]={'''+','.join('negative_'+n for n in controls_map)+r'''};
  __asm__ volatile("int $0x80":"=a"(address):"a"(45),"b"(0):"memory");requested=(address+15u)&~15u;
  __asm__ volatile("int $0x80":"=a"(address):"a"(45),"b"(requested+0x400):"memory");if(address<requested+0x400)return 90;actor=(u8*)requested;
  if(corpus(good,0))return 91;
  if(cases!=40192)return 92;
  for(i=0;i<sizeof(bad)/sizeof(bad[0]);i++)if(!corpus(bad[i],1))return 93;
  return 0;}
 '''+START
 return src

class ActorChannelCommandTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>51I',cls.rom,source.ROM));data,fs=source.link_owner(ROOT,cls.fresh,cls.out/'selected.o',source.OWNER);cls.words=list(struct.unpack_from('>51I',data,fs[source.FUNCTION]['value']));assert cls.words==cls.truth
 @classmethod
 def tearDownClass(cls):
  (cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def compare(self,c=C()):
  initial=oracle.fixture(c);want,calls=oracle.reference(initial,c);pair=[]
  for words in(self.truth,self.words):
   m=oracle.ChannelOracle(words,initial,c).run();self.assertEqual((oracle.public(m.memory),m.calls),(oracle.public(want),calls),c);pair.append(m)
  self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);return pair[0]
 def test_01_owner_Make_ABI_and_single_direct_caller(self):
  self.assertEqual(self.words,self.truth);self.assertEqual(self.words[0],0x27bdffe8)
  for label in('before','after'):
   obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),4)
  self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),3);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'));self.assertEqual(source.same_functions(self.out/'after-owner.o',self.out/'make-shadow/src/game/generated_AD6B0.c.o.compact'),4)
  self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3);self.assertEqual(source.checked_payload(*source.payload(self.out/'selected.o')),source.payload(self.out/('original-'+source.FUNCTION+'.o')))
  words=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertEqual([4*i for i,w in enumerate(words)if w==0x0c000000|(source.ENTRY>>2&0x3ffffff)],[0xad7b8]);self.assertFalse(any(w==source.ENTRY for w in words));self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()),(self.out/'proposed-owner.c').read_text())
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(words=51,slot_words=52,alignment_words=1,frame=24,bindings=9,call_sites=3,unique_callees=2,guards=0,neighbors=3,compact_functions=4,GLOBAL_ASM_routines=0,Make_commands=3,arguments=3,void_return=True,no_diagnostics=True)
 def test_02_guest_signed_channels_duration_and_null(self):
  count=0;visited=set()
  for c in oracle.corpus():
   if c.alias:continue
   m=self.compare(c);visited.update(m.visits);count+=1
  self.assertEqual(visited,set(range(source.ENTRY,source.ENTRY+204,4)));self.receipt['guest']=dict(cases=count,all51words_visited=True,signed_channels_and_duration=True,null_actor=True,full_state_and_access_trace=True)
 def test_03_complete_original_packet_dispatcher(self):
  count=0;visited=set();parent=list(struct.unpack_from('>72I',self.rom,0xAD6D8));truth=self.truth;compiled=self.words;elf=self.values['conker/build/conker.us.elf'];rom=self.rom
  READ,INDEX,BASE=oracle.READ,oracle.INDEX,oracle.BASE
  for slot,selector,encoded,result,phase,valid in itertools.product((0,3,255),(0,1,2,3,255),(0,1,366,367,734,0xfffffff),(0,1),(0,8),(False,True)):
   owner=BASE+slot*0x32c
   value=encoded;packet=bytes((0x4c if valid else 0x4b,0,0,selector,((value>>21)&127)|128,((value>>14)&127)|128,((value>>7)&127)|128,(value&127)|128))
   duration=value//367
   if duration==0:duration=20
   c=C(owner=owner,channel=(selector-1)&0xffffffff,duration=duration,count=result,phase=phase,mode=(selector+encoded)&15)
   initial=oracle.fixture(c);initial[INDEX]=slot
   for i in range(8):initial[BASE+slot*0x32c+i]=(i+slot)&255
   if valid:wanted,calls=oracle.reference(initial,c)
   else:wanted,calls=dict(initial),[]
   machines=[]
   for body in(truth,compiled):
    m=oracle.ParentOracle(parent,body,initial,c,[bytes(8),packet]).run();assert oracle.public(m.memory)==oracle.public(wanted),(slot,selector,encoded,result,valid)
    actual=[x for x in m.calls if x[0]not in(READ,source.ENTRY)];assert actual==calls,(actual,calls)
    assert m.child_arguments==([(owner,c.channel,c.duration)]if valid else[])
    assert m.packet_index==2;visited.update(m.visits);machines.append(m)
   assert complete(machines[0])==complete(machines[1]);count+=1
  bodyset=set(range(source.PARENT,source.PARENT+288,4));missing=bodyset-visited
  # DIV zero/overflow traps are intentionally unreachable with literal positive divisor367.
  assert missing=={0x150802C4,0x150802D4,0x150802D8,0x150802DC},sorted(hex(x)for x in missing)
  at=source.elf_slot_offset(elf,source.PARENT,288);assert elf[at:at+288]!=rom[0xAD6D8:0xAD7F8]
  self.receipt['integration']=dict(parent_words=72,parent_cases=count,reachable_parent_words=68,parent_current_C_placeholder=True,packet_reader_bounded=True,return_ignored=True)
 def test_04_original_count_and_apply_helpers(self):
  truth=self.truth;compiled=self.words;rom=self.rom;elf=self.values['conker/build/conker.us.elf'];put,read=oracle.put,oracle.read
  TABLE,ARCHIVE,DEFINITION,ANIM=oracle.TABLE,oracle.ARCHIVE,oracle.DEFINITION,oracle.ANIM
  connected={};descriptions=[(source.COUNT,0xABE18,32),(source.APPLY,0xAB9B0,50)]
  for entry,pos,n in descriptions:
   words=list(struct.unpack_from('>%dI'%n,rom,pos));at=source.elf_slot_offset(elf,entry,4*n);assert elf[at:at+4*n]==rom[pos:pos+4*n];connected.update(zip(range(entry,entry+4*n,4),words))
  count=0;seen={e:set()for e,_,_ in descriptions}
  for n,channel,duration,identity,actorId,definitionFlag,animation,phase in itertools.product((0,1,3),(0,1,2,4,0xffffffff),(0,1,20,21,0xffffffff),(3,255),(7,150),(0,2),(False,True),(0,8)):
   c=C(channel=channel,duration=duration,phase=phase);initial=oracle.fixture(c);a=oracle.ACTOR;initial[a+4]=actorId;initial[a+0x6f]=4
   for address,length in((TABLE,1024),(ARCHIVE,32),(DEFINITION,16),(ANIM,16)):
    initial.update({address+i:(i+37)&255 for i in range(length)})
   for ident in (3,150):put(initial,TABLE+4*ident,ARCHIVE+8 if n else 0)
   put(initial,ARCHIVE+4,n*10);initial[DEFINITION+3]=173;initial[DEFINITION+4]=definitionFlag;initial[ANIM+1]=91
   want,calls=oracle.helper_reference(initial,c,identity,animation);pair=[]
   for body in(truth,compiled):
    m=oracle.Helpers(body,initial,c,identity,animation,connected).run();assert(oracle.public(m.memory),m.calls)==(oracle.public(want),calls),(n,channel,duration,identity,actorId,definitionFlag,animation,phase,m.calls,calls)
    for entry,_,length in descriptions:seen[entry].update(set(range(entry,entry+length*4,4))&m.visits)
    pair.append(m)
   assert complete(pair[0])==complete(pair[1]);count+=1
  assert[len(seen[e])for e,_,_ in descriptions]==[31,50],{hex(e):[hex(x)for x in set(range(e,e+4*n,4))-seen[e]]for e,_,n in descriptions}
  self.receipt['helpers']=dict(cases=count,literal_words=82,reachable_words=81,coverage=[31,50],identity_definition_animations_submit_tick_bounded=True,count_current_C_exact=True,apply_original_assembly=True)
 def test_05_native32_and_effective_controls(self):
  unit=self.fresh/'native.c';unit.write_text(native_harness())
  for opt in('O0','O2','O3'):
   exe=self.fresh/('native-'+opt);p=subprocess.run(native_command('-'+opt)+['-mstackrealign',str(unit),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertEqual(subprocess.run([str(exe)],timeout=60).returncode,0,opt)
  self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_each_profile=40192,effective_controls=len(controls()),trapping_UBSan=True,untyped_aligned_owner=True,entry_stack_realigned=True)
 def test_06_fired_fault_prefixes(self):
  cuts=delays=0
  for c in(C(null=True),C(),C(channel=1),C(channel=2,duration=0),C(channel=2,duration=21),C(channel=2,duration=0xffffffff),C(count=0),C(channel=1,count=0),C(mode=15)):
   good=self.compare(c)
   for cut in range(good.root_accesses):
    pair=[]
    for body in(self.truth,self.words):
     m=oracle.ChannelOracle(body,oracle.fixture(c),c);m.root_fault=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     self.assertEqual(m.root_accesses,cut);pair.append(m)
    self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));cuts+=1;delays+=pair[0].delay_of is not None
  self.receipt['faults']=dict(prefix_pairs=cuts,delay_slot_cuts=delays,full_state_trace_PC_delay=True,portable_C_fault_claimed=False)
 def test_07_GNU_rebases_aliases_and_compiled_controls(self):
  def linked(obj,entry,count,apply,global_address,label):
   p=self.fresh/label;p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
   args=['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,'--defsym=func_1507E968=0x%X'%count,'--defsym=func_1507E500=0x%X'%apply,'--defsym=D_800D1928=0x%X'%global_address,'-o',str(p.with_suffix('.elf')),str(obj)]
   subprocess.run(args,capture_output=True,check=True);return list(struct.unpack_from('>51I',sections(p.with_suffix('.elf'))['.text'][1]))
  count=0;layouts=0
  for i,(entry,ct,ap,g)in enumerate(((source.ENTRY,source.COUNT,source.APPLY,source.MODE),(0x17007ffc,0x1707e968,0x1707e500,0x800dfff8),(0x2500fffc,0x2507e968,0x2507e500,0x800e7ffc))):
   images=[linked(self.out/n,entry,ct,ap,g,'layout-%d-%d'%(i,j))for j,n in enumerate(('original-'+source.FUNCTION+'.o','selected.o'))];assert images[0]==images[1];layouts+=1
   for channel,duration,result,null in itertools.product((0,1,2,0xffffffff),(0,20,21,0xffffffff),(0,1),(False,True)):
    c=C(channel=channel,duration=duration,count=result,null=null,mode=15);initial=oracle.fixture(c,g);want,calls=oracle.reference(initial,c,g,ct,ap)
    for body in images:
     m=oracle.ChannelOracle(body,initial,c,entry,ct,ap,g).run();assert(oracle.public(m.memory),m.calls)==(oracle.public(want),calls)
    count+=1
  aliases=0
  for alias in (1,2):
   g=oracle.mode_address(C(alias=alias));images=[linked(self.out/n,source.ENTRY,source.COUNT,source.APPLY,g,'alias-%d-%d'%(alias,j))for j,n in enumerate(('original-'+source.FUNCTION+'.o','selected.o'))];assert images[0]==images[1]
   for c in oracle.corpus():
    if c.alias!=alias:continue
    initial=oracle.fixture(c);want,calls=oracle.reference(initial,c)
    for body in images:
     m=oracle.ChannelOracle(body,initial,c).run();assert(oracle.public(m.memory),m.calls)==(oracle.public(want),calls),c
    aliases+=1
  ns={'controls':controls()}
  negatives=[]
  for name,body in ns['controls'].items():
   obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+'extern s32 D_800D1928;\n'+source.DECLARATIONS+body,'negative-'+name);assert not diag
   data,fs=source.link_owner(ROOT,self.fresh,obj,source.OWNER);f=fs[source.FUNCTION];words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']));witness=None
   for c in oracle.corpus():
    if c.alias:continue
    initial=oracle.fixture(c);want,calls=oracle.reference(initial,c);m=oracle.ChannelOracle(words,initial,c).run()
    if(oracle.public(m.memory),m.calls)!=(oracle.public(want),calls):witness=c;break
   assert witness is not None,name;negatives.append(dict(name=name,witness=vars(witness)))
  self.receipt['rebases']=dict(layouts=layouts,cases=count,alias_layouts=2,alias_cases=aliases,compiled_controls=len(negatives),original_and_C_objects_equal=True)
 def test_08_strict_full_image_and_inventory(self):
  values=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=values['conker/build/conker.us.elf'];truth=values['conker/conker.us.bin'][source.ROM:source.ROM+208];actual=(self.out/'first-linked.elf').read_bytes();source.check_image(before,actual,truth);at=source.elf_slot_offset(before,source.ENTRY,208);symbol=next(p for p,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8
  for offset in(20,at,at+100,at+204,source.elf_slot_offset(before,0x80082b20,4),symbol):
   bad=bytearray(actual);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  self.assertEqual(sum(a!=b for a,b in zip(before,actual)),150);self.assertEqual(values['conker/retail_word_patches.us.csv'],(self.out/'proposed-guards.csv').read_bytes());self.receipt['image']=dict(changed_bytes=150,code_bytes=149,extent_bytes=1,metadata_bytes=0,exclusions=0,corruptions=6,guards_unchanged=True)
