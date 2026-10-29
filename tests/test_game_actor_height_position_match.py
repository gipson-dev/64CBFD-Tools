"""Direct actor height position: aliases, float words, original routes and image."""
from pathlib import Path
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_actor_height_position_match as source
from tools.tests import game_actor_height_position_oracle as oracle
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests.test_game_effect_position_payload import complete
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2]
C=oracle.Case

def controls():
 controls={'wrong_x':source.SELECTED.replace('position[0] = *(f32 *)(actor + 0x14);','position[0] = *(f32 *)(actor + 0x18);'),'reverse_height':source.SELECTED.replace('D_8009FE60 < *(f32 *)(actor + 0x180)','D_8009FE60 > *(f32 *)(actor + 0x180)'),'fallback_y':source.SELECTED.replace('position[1] = *(f32 *)(actor + 0x18);','position[1] = *(f32 *)(actor + 0x1C);'),'skip_z':source.SELECTED.replace('position[2] = *(f32 *)(actor + 0x1C);',''),'upper_margin':source.SELECTED.replace('position[1] + 100.0f','position[1] + 99.0f'),'lower_margin':source.SELECTED.replace('position[1] - 100.0f','position[1] - 99.0f'),'skip_initializer':source.SELECTED.replace('func_1504715C(result, (HeightActor71820 *)actor);',''),'query_selector':source.SELECTED.replace('func_15046C80(start, 0,','func_15046C80(start, 1,'),'return_one':source.SELECTED.replace('return func_15046C80(start, 0, position[1] - 100.0f, result);','func_15046C80(start, 0, position[1] - 100.0f, result);\n    return 1;')}
 return controls

def native_harness():
 controls_map=controls()
 src=source.HEADERS+source.DECLARATIONS+r'''
 typedef char Pointer32[sizeof(void*)==4?1:-1];
 f32 D_8009FE60;
 static u8 *actor,*out,*result;static u8 expected[0x600];
 static u32 pattern,queryEnabled,layout,resultLayout,mode,returned,ncalls,error,cases;
 static u32 expectedRay[3],expectedLower;
 static const u32 values[]={0,0x80000000u,0x3f800000u,0xbf800000u,0x42c80000u,0xc2c80000u,0x7f800000u,0xff800000u,0x7fc12345u,1,0x7f7fffffu,0xff7fffffu};
 static const s32 returns[]={0,1,-1,(-2147483647-1)};
 static f32 fp(u32 v){union{u32 w;f32 f;}x;x.w=v;return x.f;}
 static u32 bits(f32 v){union{u32 w;f32 f;}x;x.f=v;return x.w;}
 static void putword(u8*p,u32 v){u8*q=(u8*)&v;u32 i;for(i=0;i<4;i++)p[i]=q[i];}
 static u32 word(const u8*p){u32 v;u8*q=(u8*)&v;u32 i;for(i=0;i<4;i++)q[i]=p[i];return v;}
 __attribute__((noinline,noclone)) void func_1504715C(HeightResult71820*d,HeightActor71820*a){
  u32 i;if((u8*)d!=result||(u8*)a!=actor||ncalls++!=0)error=1;
  for(i=0;i<36;i++)((u8*)d)[i]=(u8)(i*7+mode);putword((u8*)d,0x43960000u);
  if(mode&1)*(f32*)(out+4)=fp(0x442f0000u);}
 __attribute__((noinline,noclone)) s32 func_15046C80(f32*p,u16 selector,f32 lower,HeightResult71820*d){
  u32 i;if(selector!=0||(u8*)d!=result||bits(lower)!=expectedLower||ncalls++!=1)error=1;
  for(i=0;i<3;i++)if(word((u8*)p+4*i)!=expectedRay[i])error=1;
  ((u8*)d)[28]=0xd7;if(mode&2)*(f32*)out=fp(0xc3480000u);
  return returns[returned];}
 '''+source.SELECTED
 for name,body in controls_map.items():src+=body.replace(source.FUNCTION,'negative_'+name)
 src+=r'''
 typedef s32(*Update)(f32*,u8*,HeightResult71820*,u8);static Update volatile good=func_150BA930;
 static int one(Update fn,u32 fourth){u32 i,p,d;f32 height;u32 resultWord;
  for(i=0;i<0x600;i++)actor[i]=(u8)(i*13+pattern);
  *(f32*)(actor+0x14)=fp(values[pattern%12]);*(f32*)(actor+0x18)=fp(values[(pattern+3)%12]);
  *(f32*)(actor+0x1c)=fp(values[(pattern+6)%12]);*(f32*)(actor+0x180)=fp(values[(pattern+9)%12]);
  out=layout==0?actor+0x380:layout==1?actor+0x14:layout==2?actor+0x18:layout==3?actor+0x180:layout==4?actor+0x17c:actor+0x1c;
  result=!queryEnabled?0:resultLayout==0?actor+0x400:resultLayout==1?out:resultLayout==2?actor+0x14:actor+0x17c;
  D_8009FE60=fp(values[(pattern+4)%12]);for(i=0;i<0x600;i++)expected[i]=actor[i];p=(u32)(out-actor);d=result?(u32)(result-actor):0;
  putword(expected+p,word(expected+0x14));height=fp(word(expected+0x180));
  putword(expected+p+4,D_8009FE60<height?bits(height):word(expected+0x18));putword(expected+p+8,word(expected+0x1c));
  if(queryEnabled){
   expectedRay[0]=word(expected+p);expectedRay[1]=bits(fp(word(expected+p+4))+100.0f);expectedRay[2]=word(expected+p+8);
   for(i=0;i<36;i++)expected[d+i]=(u8)(i*7+mode);putword(expected+d,0x43960000u);
   if(mode&1)putword(expected+p+4,0x442f0000u);
   expectedLower=bits(fp(word(expected+p+4))-100.0f);expected[d+28]=0xd7;if(mode&2)putword(expected+p,0xc3480000u);
  }
  ncalls=error=0;resultWord=(u32)fn((f32*)out,actor,(HeightResult71820*)result,(u8)fourth);cases++;
  if(resultWord!=(queryEnabled?(u32)returns[returned]:1u)||error||ncalls!=(queryEnabled?2u:0u))return 1;
  for(i=0;i<0x600;i++)if(actor[i]!=expected[i])return 2;
  return 0;}
 static int corpus(Update fn,u32 negative){int code;
  for(pattern=0;pattern<12;pattern++)for(queryEnabled=0;queryEnabled<2;queryEnabled++)for(layout=0;layout<6;layout++)for(resultLayout=0;resultLayout<4;resultLayout++)for(mode=0;mode<4;mode++)for(returned=0;returned<4;returned++){
   code=one(fn,pattern*17+mode);if(code)return negative?1:code;}
  return 0;}
 static int run(void){u32 address,requested,i;Update bad[]={'''+','.join('negative_'+n for n in controls_map)+r'''};
  __asm__ volatile("int $0x80":"=a"(address):"a"(45),"b"(0):"memory");requested=(address+15u)&~15u;
  __asm__ volatile("int $0x80":"=a"(address):"a"(45),"b"(requested+0x600):"memory");if(address<requested+0x600)return 90;actor=(u8*)requested;
  if(corpus(good,0))return 91;if(cases!=9216)return 92;
  for(i=0;i<sizeof(bad)/sizeof(bad[0]);i++)if(!corpus(bad[i],1))return 93;
  return 0;}
 '''+START
 return src

class ActorHeightPositionTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>52I',cls.rom,source.ROM));data,fs=source.link_owner(ROOT,cls.fresh,cls.out/'selected.o',source.OWNER);cls.words=list(struct.unpack_from('>52I',data,fs[source.FUNCTION]['value']));assert cls.words==cls.truth
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def compare(self,c=C()):
  initial=oracle.fixture(c);wanted,calls,packets,result=oracle.reference(initial,c);pair=[]
  for code in(self.truth,self.words):
   m=oracle.HeightOracle(code,initial,c).run();self.assertEqual((oracle.public(m.memory),m.calls,m.packets,m.r[2]),(oracle.public(wanted),calls,packets,result),c);pair.append(m)
  self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);return pair[0]
 def test_01_owner_actual_Make_and_four_argument_ABI(self):
  self.assertEqual(self.truth[0],0x27bdffd0)
  for label in('before','after'):
   obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),6)
  self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),5);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'));self.assertEqual(source.same_functions(self.out/'after-owner.o',self.out/'make-shadow/src/game/generated_E7970.c.o.compact'),6);self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3)
  self.assertEqual(source.checked_payload(*source.payload(self.out/'selected.o')),source.payload(self.out/('original-'+source.FUNCTION+'.o')));self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()),(self.out/'proposed-owner.c').read_text())
  words=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertEqual([4*i for i,w in enumerate(words)if w==0x0c000000|(source.ENTRY>>2&0x3ffffff)],[0xe7ef4]);self.assertFalse(any(w==source.ENTRY for w in words))
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(words=52,slot_words=52,alignment_words=0,frame=48,bindings=4,guards=0,neighbors=5,compact_functions=6,Make_commands=3,arguments=4,fourth_unused=True,return_type='s32',no_diagnostics=True)
 def test_02_guest_float_words_and_live_aliases(self):
  count=0;visited=set()
  for c in oracle.corpus():m=self.compare(c);visited.update(m.visits);count+=1
  missing=set(range(source.ENTRY,source.ENTRY+208,4))-visited;self.assertEqual(missing,{0x150ba978});self.receipt['guest']=dict(cases=count,body_words=52,reachable_words=51,unreachable_duplicate_load='0x150BA978',full_state_and_access_trace=True,position_layouts=6,result_layouts=4,NaN_and_infinity_values=True,portable_C_fault_or_FCSR_claimed=False)
 def test_03_original_caller_and_height_helpers(self):
  rom=self.rom;elf=self.values['conker/build/conker.us.elf'];truth=self.truth;compiled=self.words;put,read,bits=oracle.put,oracle.read,oracle.bits
  PARENT,END,SKIP=0x150BAA14,0x150BAA64,0x150BABD0
  parent=list(struct.unpack_from('>20I',rom,0xe7ec4))
  count=0;visited=set()
  for enabled,pattern,mode,fourth,returned,phase in itertools.product((False,True),(0,3,9),range(4),(0,255),(0,1,0xffffffff),(0,8)):
   sp=oracle.STACK+phase;c=C(pattern=pattern,mode=mode,fourth=0xab000000|fourth,returned=returned,phase=phase,position_override=sp-12,result_override=sp-48,child_home=sp-120);initial=oracle.fixture(c);put(initial,oracle.ACTOR+0x1d4,0x12340000 if enabled else 0)
   if enabled:wanted,calls,packets,value=oracle.reference(initial,c)
   else:wanted,calls,packets,value=initial,[],[],None
   pair=[]
   for body in(truth,compiled):
    m=oracle.Caller(body,initial,c,parent)
    try:m.run()
    except oracle.WindowBoundary:pass
    else:raise AssertionError('Caller did not reach scoped boundary')
    args=(sp-12,oracle.ACTOR,sp-48,fourth);expectedCalls=[(source.ENTRY,args)]+calls if enabled else []
    assert(oracle.public(m.memory),m.calls,m.packets)==(oracle.public(wanted),expectedCalls,packets),(enabled,c)
    assert m.children==([args]if enabled else [])
    if enabled:assert m.memory[sp-53]==value&255
    visited.update(m.visits);pair.append(m)
   assert complete(pair[0])==complete(pair[1]);count+=1
  assert set(range(PARENT,PARENT+80,4))<=visited
  CHECK,CLASSIFY,FALLBACK,ENTITIES=0x15145C90,0x15047004,0x1504697C,0x800DBEF4
  descriptions=[(source.INITIALIZE,0x7460c,89),(source.QUERY,0x74130,32)];connected={};currentExact=[]
  for entry,pos,n in descriptions:
   body=list(struct.unpack_from('>%dI'%n,rom,pos));connected.update(zip(range(entry,entry+4*n,4),body));at=source.elf_slot_offset(elf,entry,n*4);currentExact.append(elf[at:at+n*4]==rom[pos:pos+n*4])
  hcount=0;seen={entry:set()for entry,_,_ in descriptions}
  for flag,index,answer,status,returned,mutation,phase in itertools.product((0,0x200000),(0,1,7),(0,1,0xffffffff),(0,1,2),(0,1,0xffffffff),(False,True),(0,8)):
   c=C(returned=returned,phase=phase);initial=oracle.fixture(c);put(initial,oracle.ACTOR+0x14,bits(-12.5));put(initial,oracle.ACTOR+0x18,bits(88.0));put(initial,oracle.ACTOR+0x1c,bits(34.5));put(initial,oracle.ACTOR+0x180,bits(19.75));put(initial,source.THRESHOLD,bits(-1000.0));put(initial,oracle.ACTOR+0xf8,flag);put(initial,oracle.ACTOR+0x184,0x12345678);put(initial,oracle.ACTOR+0x1a0,index,2);put(initial,ENTITIES,0x38000)
   wanted,calls,packets,value=oracle.expected(initial,c,flag,index,answer,status,mutation);pair=[]
   for body in(truth,compiled):
    m=oracle.Helpers(body,initial,c,index,answer,status,mutation,connected).run();assert(oracle.public(m.memory),m.calls,m.packets,m.r[2])==(oracle.public(wanted),calls,packets,value),(flag,index,answer,status,returned,mutation,phase)
    for entry,_,n in descriptions:seen[entry].update(set(range(entry,entry+4*n,4))&m.visits)
    pair.append(m)
   assert complete(pair[0])==complete(pair[1]);hcount+=1
  self.receipt['integration']=dict(caller_words=20,caller_cases=count,fourth_unused=True,return_low_byte_consumed=True,full_parent_claimed=False,helper_literal_words=121,helper_cases=hcount,helper_coverage=[len(seen[e])for e,_,_ in descriptions],helper_current_ELF_exact=currentExact,original_helpers_executed=True,entity_check_and_lower_queries_bounded=True,query_status_domain=[0,1,2])
 def test_04_padder_raw_guards_and_GNU_rebases(self):
  raw,bindings=source.checked_payload(*source.payload(self.out/'selected.o'));bad=bytearray(raw);bad[60]^=1;rejections=0
  for data,rel in ((raw[:-4],bindings),(bytes(bad),bindings),(raw,bindings|{140:[('R_MIPS_26','wrong')]})):
   try:source.checked_payload(data,rel)
   except ValueError:pass
   else:raise AssertionError('Raw corruption accepted')
   rejections+=1
  names=('func_1504715C','func_15046C80','D_8009FE60')
  def linked(obj,entry,targets,label):
   p=self.fresh/label;text,fs,relocations=parse_object(obj);assembly,unresolved=emit_function(text,fs[source.FUNCTION],relocations,source.FUNCTION,dict(zip(names,targets)));assert not unresolved;p.with_suffix('.s').write_text(assembly);isolated=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-o',str(isolated),str(p.with_suffix('.s'))],capture_output=True,check=True);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
   subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,*['--defsym=%s=0x%X'%(n,v)for n,v in zip(names,targets)],'-o',str(p.with_suffix('.elf')),str(isolated)],capture_output=True,check=True);return list(struct.unpack_from('>52I',sections(p.with_suffix('.elf'))['.text'][1]))
  count=0
  for j,(entry,targets)in enumerate(((source.ENTRY,(source.INITIALIZE,source.QUERY,source.THRESHOLD)),(0x17007ffc,(0x1704715c,0x17046c80,0x800dfff8)),(0x2500fffc,(0x2504715c,0x25046c80,0x800e7ffc)))):
   initialize,query,threshold=targets;images=[linked(self.out/name,entry,targets,'layout-%d-%d'%(j,k))for k,name in enumerate(('original-'+source.FUNCTION+'.o','selected.o','qualified-padded.o'))];assert images[0]==images[1]==images[2]
   for c in(C(query=False),C(),C(pattern=3,mode=3),C(position_layout=1,result_layout=1),C(position_layout=3,result_layout=3),C(phase=8,returned=0xffffffff)):
    initial=oracle.fixture(c,threshold);want,calls,packets,result=oracle.reference(initial,c,threshold,initialize,query);pair=[]
    for code in images:
     m=oracle.HeightOracle(code,initial,c,entry,threshold,initialize,query).run();assert(oracle.public(m.memory),m.calls,m.packets,m.r[2])==(oracle.public(want),calls,packets,result);pair.append(m)
    assert complete(pair[0])==complete(pair[1])==complete(pair[2]);count+=1
  self.receipt['rebases']=dict(layouts=3,cases=count,raw_corruptions_rejected=rejections,original_compiler_padded_equal=True,guards=0)
 def test_05_fired_access_prefixes_and_saved_pointer_lifetime(self):
  cuts=delays=0
  for c in(C(query=False),C(),C(pattern=3),C(pattern=9,mode=3),C(position_layout=1,result_layout=1),C(position_layout=3,result_layout=3),C(phase=8)):
   good=self.compare(c)
   for cut in range(good.root_accesses):
    pair=[]
    for code in(self.truth,self.words):
     m=oracle.HeightOracle(code,oracle.fixture(c),c);m.root_fault=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     self.assertEqual(m.root_accesses,cut);pair.append(m)
    self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));cuts+=1;delays+=pair[0].delay_of is not None
  self.receipt['faults']=dict(prefix_pairs=cuts,delay_slot_cuts=delays,full_state_trace_PC_delay=True,portable_C_fault_or_FCSR_claimed=False)
 def test_06_native32_aliases_and_effective_controls(self):
  unit=self.fresh/'native.c';unit.write_text(native_harness())
  for opt in('O0','O2','O3'):
   exe=self.fresh/('native-'+opt);p=subprocess.run(native_command('-'+opt)+['-mstackrealign',str(unit),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertEqual(subprocess.run([str(exe)],timeout=60).returncode,0,opt)
  self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_each_profile=9216,effective_controls=len(controls()),trapping_UBSan=True,fresh_untyped_backing=True,position_layouts=6,result_layouts=4,NaN_and_infinity_values=True)
 def test_07_independently_compiled_semantic_controls(self):
  mutations=[]
  for name,body in controls().items():
   obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+body,'negative-'+name);assert not diag
   data,fs=source.link_owner(ROOT,self.fresh,obj,source.OWNER);f=fs[source.FUNCTION];code=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']));witness=None
   for c in oracle.corpus():
    initial=oracle.fixture(c);wanted,calls,packets,result=oracle.reference(initial,c);m=oracle.HeightOracle(code,initial,c).run()
    if(oracle.public(m.memory),m.calls,m.packets,m.r[2])!=(oracle.public(wanted),calls,packets,result):witness=c;break
   assert witness is not None,name;mutations.append(dict(name=name,witness=vars(witness)))
  self.receipt['compiled_controls']=dict(count=len(mutations),observable_memory_calls_packets_return_mismatches=True)
 def test_08_entire_image_and_unchanged_manifests(self):
  values=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=values['conker/build/conker.us.elf'];actual=(self.out/'first-linked.elf').read_bytes();truth=values['conker/conker.us.bin'][source.ROM:source.ROM+208];source.check_image(before,actual,truth);at=source.elf_slot_offset(before,source.ENTRY,208);symbol=next(p for p,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8
  for offset in(20,at,at+100,at+208,source.elf_slot_offset(before,0x80082b20,4),symbol):
   bad=bytearray(actual);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  self.assertEqual(sum(a!=b for a,b in zip(before,actual)),152);self.assertEqual((self.out/'proposed-guards.csv').read_bytes(),values['conker/retail_word_patches.us.csv']);self.receipt['image']=dict(changed_bytes=152,code_bytes=151,extent_bytes=1,metadata_bytes=0,exclusions=0,corruptions=6,new_guard_rows=0,all_guard_bytes_unchanged=True)
