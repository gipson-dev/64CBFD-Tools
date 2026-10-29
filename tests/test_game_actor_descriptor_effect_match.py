"""Descriptor effect: canonical owner/wrapper ABI, caller, native and image checks."""
from pathlib import Path
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_actor_descriptor_effect_match as source
from tools.tests import game_actor_descriptor_effect_oracle as oracle
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
 controls={'geometry_gate':source.SELECTED.replace('if (func_150FF6E0(points, &origin, &direction, &velocity, &other, actor, descriptor))','if (func_150FF6E0(points, &origin, &direction, &velocity, &other, actor, descriptor) || 1)'), 'primary_vector':source.SELECTED.replace('func_151D3F14(&origin,','func_151D3F14(&direction,'),'swap_motion':source.SELECTED.replace('func_151D4408(&direction, &velocity,','func_151D4408(&velocity, &direction,'),'matrix_stride':source.SELECTED.replace('descriptor[2] * 64','descriptor[2] * 32'),'scale':source.SELECTED.replace('actor, 1.0f,','actor, 2.0f,'),'selector':source.SELECTED.replace('func_150FF474(&origin, points, selector, parameter);','func_150FF474(&origin, points, selector + 1, parameter);'),'parameter':source.SELECTED.replace('func_151D3F14(&origin, selector, parameter);','func_151D3F14(&origin, selector, 0);'),'skip_final':source.SELECTED.replace('func_150FF474(&origin, points, selector, parameter);','')}
 return controls

def native_harness():
 controls_map=controls()
 src=source.HEADERS+source.DECLARATIONS+r'''
 typedef char Pointer32[sizeof(void*)==4?1:-1];
 static u8 *actor;static u8 descriptor[128],matrices[16384],alternate[16384];
 static u32 selector,parameter,mode,found,geometry,pattern,indexByte,ncalls,error;
 static struct17 *outputs[5];
 static const u32 values[]={0,0x80000000u,0x3f800000u,0xbf800000u,0x7f800000u,0x7fc12345u,1,0x7f7fffffu};
 static void putword(u8*p,u32 v){u8*q=(u8*)&v;u32 i;for(i=0;i<4;i++)p[i]=q[i];}
 static u32 word(const void*p){u32 v;u8*q=(u8*)&v;const u8*b=(const u8*)p;u32 i;for(i=0;i<4;i++)q[i]=b[i];return v;}
 static void checkvector(struct17*p,u32 group,u32 n,u32 afterPrimary,u32 afterSecondary){u32 i,want;
  for(i=0;i<n;i++){want=values[(i+group+pattern)%8];
   if(group==1&&i==0&&afterPrimary&&(mode&4))want=0xc1200000u;
   if(group==1&&i==1&&afterSecondary&&(mode&8))want=0x41200000u;
   if(group==0&&i==17&&afterSecondary&&(mode&8))want=0x44340000u;
   if(word((u8*)p+4*i)!=want)error=1;}}
 __attribute__((noinline,noclone)) s32 func_1503195C(u8*p,s32 key,u32 ordinal){
  if(p!=actor||key!=0x82||ordinal!=0||ncalls++!=0)error=1;if(mode&1)*(u8**)(actor+0x1d4)=alternate;
  return found?(s32)descriptor:0;}
 __ACTUAL_WRAPPER__
 __attribute__((noinline,noclone)) s32 func_150FF6E0(struct17*p0,struct17*p1,struct17*p2,struct17*p3,struct17*p4,u8*p,u8*d){
  u32 i,j,n;struct17 *a[]={p0,p1,p2,p3,p4};
  if(p!=actor||d!=descriptor||ncalls++!=1)error=1;
  for(j=0;j<5;j++){outputs[j]=a[j];n=j==0?18:3;for(i=0;i<n;i++)putword((u8*)a[j]+4*i,values[(i+j+pattern)%8]);}
  if(mode&2)descriptor[2]=(u8)(indexByte+1);return geometry;}
 __attribute__((noinline,noclone)) void func_151D3F14(struct17*p,u8 s,s32 param){
  if(p!=outputs[1]||s!=selector||(u32)param!=parameter||ncalls++!=2)error=1;
  checkvector(p,1,3,0,0);
  if(mode&4){putword((u8*)p,0xc1200000u);descriptor[2]=(u8)(indexByte+2);*(u8**)(actor+0x1d4)=alternate;}}
 __attribute__((noinline,noclone)) void func_151D4408(struct17*p,struct17*q,void*matrix,u8*a,f32 scale,u8 s,s32 param){
  u32 idx=(mode&4)?(u8)(indexByte+2):(mode&2)?(u8)(indexByte+1):indexByte;
  u8*base=(mode&(1|4))?alternate:matrices;
  if(p!=outputs[2]||q!=outputs[3]||matrix!=base+idx*64||a!=actor||scale!=1.0f||s!=selector||(u32)param!=parameter||ncalls++!=3)error=1;
  checkvector(p,2,3,0,0);checkvector(q,3,3,0,0);
  if(mode&8){putword((u8*)outputs[1]+4,0x41200000u);putword((u8*)outputs[0]+68,0x44340000u);}}
 __attribute__((noinline,noclone)) void func_150FF474(struct17*p,struct17*q,u8 s,s32 param){
  if(p!=outputs[1]||q!=outputs[0]||s!=selector||(u32)param!=parameter||ncalls++!=4)error=1;
  checkvector(p,1,3,1,1);checkvector(q,0,18,1,1);}
 '''+source.SELECTED
 for name,body in controls_map.items():src+=body.replace(source.FUNCTION,'negative_'+name)
 src+=r'''
 typedef void(*Update)(u8*,u8,s32);static Update volatile good=func_150F9950;
 static const u32 parameters[]={0,1,0x80000000u,0xffffffffu};
 static int corpus(Update fn,u32 negative){u32 k,i,j,expectedCalls,expectedIndex;u8*expectedBase;
  for(selector=0;selector<256;selector++)for(found=0;found<2;found++)for(geometry=0;geometry<2;geometry++)for(mode=0;mode<16;mode++)for(k=0;k<4;k++){
   parameter=parameters[k];pattern=selector%8;indexByte=selector;
   for(i=0;i<0x340;i++)actor[i]=(u8)(i*13+selector);
   for(i=0;i<128;i++)descriptor[i]=(u8)(i*7);descriptor[2]=(u8)indexByte;
   *(u8**)(actor+0x1d4)=matrices;error=ncalls=0;
   for(j=0;j<5;j++)outputs[j]=0;
   fn(actor,(u8)selector,(s32)parameter);
   expectedCalls=!found?1:!geometry?2:5;
   expectedIndex=!found?indexByte:found&&geometry&&(mode&4)?(u8)(indexByte+2):(mode&2)?(u8)(indexByte+1):indexByte;
   expectedBase=(mode&1)||(found&&geometry&&(mode&4))?alternate:matrices;
   if(error||ncalls!=expectedCalls||descriptor[2]!=expectedIndex||*(u8**)(actor+0x1d4)!=expectedBase)return negative?1:10;
   for(i=0;i<0x340;i++)if(!(i>=0x1d4&&i<0x1d8)&&actor[i]!=(u8)(i*13+selector))return negative?1:11;
  }
  return 0;}
 static int run(void){u32 address,requested,i;Update bad[]={'''+','.join('negative_'+n for n in controls_map)+r'''};
  __asm__ volatile("int $0x80":"=a"(address):"a"(45),"b"(0):"memory");requested=(address+15u)&~15u;
  __asm__ volatile("int $0x80":"=a"(address):"a"(45),"b"(requested+0x400):"memory");if(address<requested+0x400)return 90;actor=(u8*)requested;
  if(corpus(good,0))return 91;
  for(i=0;i<sizeof(bad)/sizeof(bad[0]);i++)if(!corpus(bad[i],1))return 92;
  return 0;}
 '''+START
 return src.replace('__ACTUAL_WRAPPER__',source.WRAPPER_SELECTED)

class ActorDescriptorEffectTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>49I',cls.rom,source.ROM));cls.images=[]
  for name in('original-'+source.FUNCTION+'.o','selected.o','qualified-padded.o'):
   data,fs=source.link_owner(ROOT,cls.fresh,cls.out/name,source.OWNER);cls.images.append(list(struct.unpack_from('>49I',data,fs[source.FUNCTION]['value'])))
  assert cls.images[0]==cls.images[2]==cls.truth
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def compare(self,c=C(),images=None,entry=source.ENTRY,targets=None):
  initial=oracle.fixture(c);wanted,calls,packets=oracle.reference(initial,c,targets);ms=[]
  for words in self.images if images is None else images:
   m=oracle.DescriptorOracle(words,initial,c,entry,targets).run();self.assertEqual((oracle.public(m.memory),m.calls,m.packets),(oracle.public(wanted),calls,packets),c);ms.append(m)
  normalized=ms[2]if len(ms)==3 else ms[1];self.assertEqual(complete(ms[0]),complete(normalized));self.assertEqual(ms[0].trace,normalized.trace);return ms[0]
 def test_01_owner_wrapper_ABI_and_actual_Make(self):
  self.assertEqual(self.truth[0],0x27bdff58)
  for label in('before','after'):
   obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),17)
   obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/('wrapper-'+label+'.c')).read_text(),'fresh-wrapper-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/('wrapper-'+label+'.o')),16)
  self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),16);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'));self.assertEqual(source.same_functions(self.out/'after-owner.o',self.out/'make-shadow/src/game/generated_124920.c.o.compact'),17);self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),5)
  self.assertEqual(source.same_functions(self.out/'wrapper-before.o',self.out/'wrapper-after.o'),16);self.assertEqual(source.normalized_pools(self.out/'wrapper-before.o'),source.normalized_pools(self.out/'wrapper-after.o'));self.assertEqual((self.out/'wrapper-after-padded.o').read_bytes(),self.values[source.WRAPPER_OBJECT]);self.assertEqual((self.out/'wrapper-before-padded.o').read_bytes(),self.values[source.WRAPPER_OBJECT]);self.assertEqual(source.recovered_wrapper(self.values[source.WRAPPER_SOURCE].decode()),(self.out/'proposed-wrapper-owner.c').read_text())
  self.assertEqual(source.normalized_payload(*source.payload(self.out/'selected.o')),source.payload(self.out/('original-'+source.FUNCTION+'.o')));self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()),(self.out/'proposed-owner.c').read_text())
  words=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertEqual([4*i for i,w in enumerate(words)if w==0x0c000000|(source.ENTRY>>2&0x3ffffff)],[0x55dd4]);self.assertFalse(any(w==source.ENTRY for w in words))
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(words=49,slot_words=52,alignment_words=3,frame=168,bindings=5,guards=5,neighbors=16,compact_functions=17,Make_commands=5,arguments=3,void_return=True,wrapper_words=9,wrapper_compact_functions=16,wrapper_complete_object_unchanged=True,no_diagnostics=True)
 def test_02_guest_geometry_packets_and_provider_mutations(self):
  count=0;visited=set()
  for c in oracle.corpus():m=self.compare(c);visited.update(m.visits);count+=1
  self.assertEqual(visited,set(range(source.ENTRY,source.ENTRY+196,4)));self.receipt['guest']=dict(cases=count,all49body_words_reachable=True,raw_public_memory_calls_packets_equal=True,normalized_full_state_access_equal=True,five_effect_providers_bounded=True)
 def test_03_original_caller_window_and_lookup_chain(self):
  elf=self.values['conker/build/conker.us.elf'];rom=self.rom;body=self.images[0];padded=self.images[2];put=oracle.put
  ENTRY,CASE,END,TABLE=0x15028810,0x15028920,0x15029BA4,0x80096CEC
  off=source.elf_slot_offset(elf,TABLE,37*4);table=elf[off:off+148];slots=[i for i,w in enumerate(struct.unpack('>37I',table))if w==CASE];assert len(slots)==1;actorId=slots[0]+0x74
  prefix=list(struct.unpack_from('>15I',rom,0x55cc0));case=list(struct.unpack_from('>5I',rom,0x55dd0))
  count=0;visited=set()
  for null,found,geometry,selector,mode,phase in itertools.product((False,True),(False,True),(False,True),(0,37,255),range(16),(0,8)):
   c=C(found,geometry,selector,1,255,mode,phase,pattern=selector%8);initial=oracle.fixture(c);sp=oracle.STACK+phase
   initial.update({sp+i:(i*7)&255 for i in range(1024,2048)});put(initial,sp+0x764,0 if null else oracle.ACTOR);initial[sp+0x773]=selector;initial[oracle.ACTOR+4]=actorId
   initial.update({TABLE+i:b for i,b in enumerate(table)});wanted,calls,packets=oracle.reference(initial,c)if not null else(initial,[],[]);pair=[]
   for words in(body,padded):
    m=oracle.Caller(words,initial,c,prefix,case)
    try:m.run()
    except oracle.WindowBoundary:pass
    else:raise AssertionError('Original window did not reach continuation')
    wantedCalls=[(source.ENTRY,(oracle.ACTOR,selector,1))]+calls if not null else[]
    assert(oracle.public(m.memory),m.calls,m.packets,m.r[2])==(oracle.public(wanted),wantedCalls,packets,1),(null,c)
    assert m.children==([(oracle.ACTOR,selector,1)]if not null else[]);visited.update(m.visits);pair.append(m)
   assert complete(pair[0])==complete(pair[1]);count+=1
  assert set(range(ENTRY,ENTRY+60,4))|set(range(CASE,CASE+20,4))<=visited
  PROVIDER,HEAD,OTHER=0x1503195C,0x800C3EE0,0x32000
  descriptions=[(source.LOOKUP,0x12C738,9),(PROVIDER,0x5EE0C,28)];connected={}
  for entry,pos,n in descriptions:
   code=list(struct.unpack_from('>%dI'%n,rom,pos));at=source.elf_slot_offset(elf,entry,n*4);assert elf[at:at+n*4]==rom[pos:pos+n*4];connected.update(zip(range(entry,entry+n*4,4),code))
  hcount=0;seen={entry:set()for entry,_,_ in descriptions}
  for route,geometry,index,mode,phase in itertools.product(range(5),(False,True),(0,255),(0,2,4,8,14),(0,8)):
   found=route==4;c=C(found,geometry,37,0x80000000,index,mode,phase);initial=oracle.fixture(c);initial[oracle.ACTOR+0x3b]=0 if route==0 else 7
   initial.update({OTHER+i:0xa5 for i in range(128)});put(initial,HEAD,0 if route==1 else OTHER);initial[OTHER]=9 if route in(2,4)else 7;initial[OTHER+6]=0x81 if route==3 else 0x82;put(initial,OTHER+0x54,oracle.DESCRIPTOR if route==4 else 0)
   initial[oracle.DESCRIPTOR]=7;initial[oracle.DESCRIPTOR+6]=0x82;put(initial,oracle.DESCRIPTOR+0x54,0)
   wanted,calls,packets=oracle.reference(initial,c);calls=[calls[0],(PROVIDER,(oracle.ACTOR,0x82,0))]+calls[1:];pair=[]
   for words in(body,padded):
    m=oracle.Lookup(words,initial,c,connected).run();assert(oracle.public(m.memory),m.calls,m.packets)==(oracle.public(wanted),calls,packets),(route,c,m.calls,calls)
    for entry,_,n in descriptions:seen[entry].update(set(range(entry,entry+n*4,4))&m.visits)
    pair.append(m)
   assert complete(pair[0])==complete(pair[1]);hcount+=1
  self.receipt['integration']=dict(caller_window_words=20,caller_cases=count,actor_type=actorId,table_slot=slots[0],full_parent_claimed=False,result_ignored_and_replaced_by1=True,wrapper_provider_literal_words=37,wrapper_provider_cases=hcount,wrapper_provider_coverage=[len(seen[e])for e,_,_ in descriptions],other_providers_bounded=True)
 def test_04_five_real_padder_guards(self):
  base=(self.out/'after-owner.o').read_bytes();_,fs,_=parse_object(self.out/'after-owner.o');start=fs[source.FUNCTION]['value'];shoff=struct.unpack_from('>I',base,32)[0];shsize,shcount,shnames=struct.unpack_from('>HHH',base,46);headers=[struct.unpack_from('>10I',base,shoff+i*shsize)for i in range(shcount)];strings=base[headers[shnames][4]:headers[shnames][4]+headers[shnames][5]];sec={strings[h[0]:].split(b'\0',1)[0].decode():h for h in headers};text_at=sec['.text'][4];rel=sec['.rel.text'];rejections=0
  for row in source.NEW_GUARDS:
   offset=int(row['offset'],0);bad=bytearray(base);bad[text_at+start+offset]^=1;p=self.fresh/('bad-word-%X.o'%offset);p.write_bytes(bad)
   try:source.emit_padded_assembly(p,ROOT/source.ASM,word_patches_path=self.out/'proposed-guards.csv',filename=source.OWNER)
   except ValueError:pass
   else:raise AssertionError('Stale word accepted')
   rejections+=1;bad=bytearray(base);hits=[]
   for at in range(rel[4],rel[4]+rel[5],8):
    if struct.unpack_from('>I',base,at)[0]==start+20:hits.append(at)
   assert len(hits)==1;struct.pack_into('>I',bad,hits[0],start+offset);p=self.fresh/('bad-relocation-%X.o'%offset);p.write_bytes(bad)
   try:source.emit_padded_assembly(p,ROOT/source.ASM,word_patches_path=self.out/'proposed-guards.csv',filename=source.OWNER)
   except ValueError:pass
   else:raise AssertionError('Stale relocation accepted')
   rejections+=1
  self.receipt['guards']=dict(rows=5,stale_word_relocation_rejections=rejections,inserted_words=0,omitted_words=0,closed_register_cycle=True)
 def test_05_fired_access_prefixes_and_delay_slots(self):
  cuts=delays=0
  for c in(C(found=False),C(geometry=False),C(),C(mode=15,index=255),C(selector=0xab0000ff,parameter=0xffffffff),C(phase=8,mode=4)):
   good=self.compare(c)
   for cut in range(good.root_accesses):
    pair=[]
    for words in(self.images[0],self.images[2]):
     m=oracle.DescriptorOracle(words,oracle.fixture(c),c);m.root_fault=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     self.assertEqual(m.root_accesses,cut);pair.append(m)
    self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));cuts+=1;delays+=pair[0].delay_of is not None
  self.receipt['faults']=dict(prefix_pairs=cuts,delay_slot_cuts=delays,full_state_trace_PC_delay=True,raw_fault_schedule_not_equated=True,portable_C_fault_claimed=False)
 def test_06_native32_actual_wrapper_and_effective_controls(self):
  unit=self.fresh/'native.c';unit.write_text(native_harness())
  for opt in('O0','O2','O3'):
   exe=self.fresh/('native-'+opt);p=subprocess.run(native_command('-'+opt)+['-mstackrealign',str(unit),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertEqual(subprocess.run([str(exe)],timeout=60).returncode,0,opt)
  self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_each_profile=65536,effective_controls=len(controls()),trapping_UBSan=True,untyped_aligned_actor=True,typed_vectors=True,actual_corrected_wrapper_C=True,canonical_provider_arguments=True)
 def test_07_GNU_rebases_and_IDO_negative_controls(self):
  names=('func_150FF288','func_150FF6E0','func_151D3F14','func_151D4408','func_150FF474')
  def linked(obj,entry,targets,label):
   p=self.fresh/label;text,fs,relocations=parse_object(obj);assembly,unresolved=emit_function(text,fs[source.FUNCTION],relocations,source.FUNCTION,dict(zip(names,targets)));assert not unresolved;p.with_suffix('.s').write_text(assembly);obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-o',str(obj),str(p.with_suffix('.s'))],capture_output=True,check=True);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,*['--defsym=%s=0x%X'%(name,value)for name,value in zip(names,targets)],'-o',str(p.with_suffix('.elf')),str(obj)],capture_output=True,check=True);return list(struct.unpack_from('>49I',sections(p.with_suffix('.elf'))['.text'][1]))
  count=0
  for j,(entry,delta)in enumerate(((source.ENTRY,0),(0x17007ffc,0x02000000),(0x2500fffc,0x10000000))):
   targets=tuple(x+delta for x in(source.LOOKUP,source.GEOMETRY,source.PRIMARY,source.SECONDARY,source.FINAL));images=[linked(self.out/name,entry,targets,'layout-%d-%d'%(j,k))for k,name in enumerate(('original-'+source.FUNCTION+'.o','qualified-padded.o','selected.o'))];assert images[0]==images[1]
   for c in(C(found=False),C(geometry=False),C(),C(mode=15,index=255),C(selector=0xab0000ff,parameter=0xffffffff),C(phase=8,mode=4)):
    initial=oracle.fixture(c);want,calls,packets=oracle.reference(initial,c,targets);ms=[]
    for body in images:
     m=oracle.DescriptorOracle(body,initial,c,entry,targets).run();assert(oracle.public(m.memory),m.calls,m.packets)==(oracle.public(want),calls,packets);ms.append(m)
    assert complete(ms[0])==complete(ms[1])and ms[0].trace==ms[1].trace;count+=1
  rows=[]
  for name,body in controls().items():
   obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+body,'negative-'+name);assert not diag
   data,fs=source.link_owner(ROOT,self.fresh,obj,source.OWNER);f=fs[source.FUNCTION];words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']));witness=None
   for c in oracle.corpus():
    initial=oracle.fixture(c);want,calls,packets=oracle.reference(initial,c);m=oracle.DescriptorOracle(words,initial,c).run()
    if(oracle.public(m.memory),m.calls,m.packets)!=(oracle.public(want),calls,packets):witness=c;break
   assert witness is not None,name;rows.append(dict(name=name,witness=vars(witness)))
  self.receipt['rebases']=dict(layouts=3,cases=count,compiled_controls=len(rows),raw_public_packets_equal=True,original_and_padded_full_equal=True)
 def test_08_entire_image_guard_history_and_dual_source(self):
  values=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=values['conker/build/conker.us.elf'];actual=(self.out/'first-linked.elf').read_bytes();truth=values['conker/conker.us.bin'][source.ROM:source.ROM+208];source.check_image(before,actual,truth);at=source.elf_slot_offset(before,source.ENTRY,208);symbol=next(p for p,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8
  for offset in(20,at,at+100,at+196,source.elf_slot_offset(before,0x80082b20,4),symbol):
   bad=bytearray(actual);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  self.assertEqual(sum(a!=b for a,b in zip(before,actual)),154);self.assertTrue((self.out/'proposed-guards.csv').read_bytes().startswith(values['conker/retail_word_patches.us.csv']));self.assertEqual(values[source.WRAPPER_OBJECT],(self.out/'wrapper-after-padded.o').read_bytes());self.receipt['image']=dict(changed_bytes=154,code_bytes=153,extent_bytes=1,metadata_bytes=0,exclusions=0,corruptions=6,new_guard_rows=5,inherited_guard_prefix_unchanged=True,wrapper_complete_object_identical=True)
