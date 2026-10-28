"""Actor point effects: direct C, literal ABI, original caller and whole-image preservation."""
from dataclasses import replace
from pathlib import Path
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_actor_point_effects_match as source
from tools.tests import game_actor_point_effects_oracle as oracle
from tools.tests.game_actor_point_effects_oracle import Case,fixture,reference,public,EffectsOracle,SYMBOLS,ACTOR,STACK,put,read,faults,SELECT,QUERY,BASE,SURFACE,FIRST,SECOND,PARENT,SETUP,FINAL,TRANSFORM,CHECK
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
ROOT=Path(__file__).resolve().parents[2]
def native_harness():
 body=source.SELECTED
 controls={
  'wrong_sentinel':body.replace('type != 99','type != 98'),
  'wide_availability':body.replace('u8 available;','s32 available;'),
  'skip_base':body.replace('        func_15138120(actor, type, 1);',''),
  'skip_point_effect':body.replace('            func_151382E0(&position, type, &surface, group, context);',''),
  'wrong_group':body.replace('&surface, group, context','&surface, (u8)(group ^ 1), context'),
  'wrong_context':body.replace('&surface, group, context','&surface, group, 0'),
  'force_points':body.replace('if (available)','if (available || 1)'),
 }
 assert all(text!=body for text in controls.values())
 unit=source.HEADERS+r'''
 typedef char ABI[(sizeof(void*)==4&&sizeof(s32)==4&&sizeof(vertex)==12&&sizeof(ActorEffectSurface)==36&&__builtin_offsetof(ActorEffectSurface,metadata)==24&&__builtin_offsetof(ActorEffectSurface,value)==32)?1:-1];
 static struct102 actor;
 static u8 expectedActor[sizeof(actor)],expectedPoint[12],expectedSurface[36];
 static vertex *point;
 static ActorEffectSurface *surface;
 static u32 seed,mode,callCount,error,kind,queryResult,wantedCount,wantedCalls[6],wantedGroup;
 static s32 wantedContext;
 static int same(const void*a,const void*b,u32 n){u32 i;for(i=0;i<n;i++)if(((const u8*)a)[i]!=((const u8*)b)[i])return 0;return 1;}
 static void fill(void*p,u32 n,u32 salt){u32 i;for(i=0;i<n;i++)((u8*)p)[i]=(u8)(seed+i*13+salt);}
 static void change(void*p,u32 n,u32 salt){u32 i;for(i=0;i<n;i++)((u8*)p)[i]^=(u8)(salt+i*7);}
 static void event(u32 id){if(callCount>=wantedCount||wantedCalls[callCount]!=id)error=1;callCount++;}
 s32 __attribute__((noinline)) func_15134070(struct102*a){event(0);if(a!=&actor)error=1;return(s32)kind;}
 s32 __attribute__((noinline)) func_151380B4(struct102*a,s32 type,vertex*p){event(1);if(a!=&actor||(u32)type!=kind)error=1;point=p;fill(p,12,21);return(s32)queryResult;}
 s32 __attribute__((noinline)) func_15138120(struct102*a,s32 type,u8 base){event(2);if(a!=&actor||(u32)type!=kind||base!=1)error=1;if(mode&1){if(point)change(point,12,0x17);((u8*)a)[4]^=0x83;}return 0x7777;}
 void __attribute__((noinline)) func_1504715C(ActorEffectSurface*d,struct102*a){event(3);if(a!=&actor)error=1;surface=d;fill(d,36,79);if(mode&2){if(point)change(point,12,0x39);d->state^=0xA1;}}
 s32 __attribute__((noinline)) func_151382E0(vertex*p,s32 type,ActorEffectSurface*d,u8 group,s32 context){event(4);if(p!=point||d!=surface||(u32)type!=kind||group!=wantedGroup||context!=wantedContext||!same(p,expectedPoint,12)||!same(d,expectedSurface,36))error=1;if(mode&4){change(p,12,0x47);change(d,36,0xB3);}return 0x8888;}
 s32 __attribute__((noinline)) func_15138424(struct102*a,vertex*p,s32 type,ActorEffectSurface*d,u8 group,s32 context){event(5);if(mode&4){change(expectedPoint,12,0x47);change(expectedSurface,36,0xB3);}if(a!=&actor||p!=point||d!=surface||(u32)type!=kind||group!=wantedGroup||context!=wantedContext||!same(p,expectedPoint,12)||!same(d,expectedSurface,36))error=1;return 0x9999;}
 '''
 for name,text in dict(selected=body,**controls).items():unit+=text.replace('func_15138BC0',name)+'\n'
 unit+=r'''
 typedef void(*Update)(struct102*,u8,s32);
 static const u32 kinds[]={0,19,98,99,100,0xFFFFFFFFu};
 static const u32 queries[]={0,1,255,256,257,0xFFFFFF00u,0xFFFFFFFFu,0x80000000u};
 static int check(Update fn){u32 k,j;
  for(seed=0;seed<256;seed++)for(k=0;k<6;k++)for(j=0;j<8;j++)for(mode=0;mode<8;mode++){
   kind=kinds[k];queryResult=queries[j];wantedGroup=(seed*17+mode)&255;wantedContext=(s32)(0x81234567u+seed*127+j*11);
   fill(&actor,sizeof(actor),31);fill(expectedActor,sizeof(actor),31);fill(expectedPoint,12,21);fill(expectedSurface,36,79);
   wantedCalls[0]=0;wantedCalls[1]=1;wantedCalls[2]=2;wantedCalls[3]=3;wantedCalls[4]=4;wantedCalls[5]=5;
   wantedCount=kind==99?1:((queryResult&255)?6:3);
   if(kind!=99&&(mode&1)){change(expectedPoint,12,0x17);expectedActor[4]^=0x83;}
   if(kind!=99&&(queryResult&255)&&(mode&2)){change(expectedPoint,12,0x39);expectedSurface[29]^=0xA1;}
   point=0;surface=0;callCount=error=0;fn(&actor,(u8)wantedGroup,wantedContext);
   if(error||callCount!=wantedCount||!same(&actor,expectedActor,sizeof(actor)))return 1;
  }return 0;
 }
 static int run(void){if(check(selected))return 10;
 '''
 for i,name in enumerate(controls):unit+='if(!check('+name+'))return '+str(20+i)+';\n'
 unit+='return 0;}\n'+START
 return unit

class ActorPointEffectsTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>48I',cls.rom,source.ROM));local=cls.fresh/'qualified-padded.o';local.write_bytes((cls.out/'qualified-padded.o').read_bytes());data,functions=source.link_owner(ROOT,cls.fresh,local,source.OWNER);cls.words=list(struct.unpack_from('>48I',data,functions[source.FUNCTION]['value']))
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def compare(self,c=Case(),images=None,entry=source.ENTRY,symbols=SYMBOLS):
  initial=fixture(c,symbols);memory,calls,observations=reference(initial,c,symbols);pair=[]
  for words in images or(self.truth,self.words):
   m=EffectsOracle(words,initial,c,symbols,entry).run();self.assertEqual((public(m.memory),m.calls,m.observations),(public(memory),calls,observations),c);pair.append(m)
  self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);return pair[0]
 def rebased(self,obj,entry,symbols,label):
  text,functions,bindings=parse_object(obj);assembly,unknown=emit_function(text,functions[source.FUNCTION],bindings,source.FUNCTION,symbols);self.assertFalse(unknown);p=self.fresh/label;p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
  subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
  subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,*['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
  return list(struct.unpack('>%dI'%(len(sections(p.with_suffix('.elf'))['.text'][1])//4),sections(p.with_suffix('.elf'))['.text'][1]))


 def test_01_owner_Make_census_and_source_ABI(self):
  self.assertEqual(self.words,self.truth);source.checked_payload(*source.payload(self.out/'selected.o'))
  for label in('before','after'):
   obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertEqual(source.check_owner_diagnostics(diag),2);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),65 if label=='before'else 64)
  a,b=self.out/'before-owner.o',self.out/'after-owner.o';self.assertEqual(set(parse_object(a)[1])-{source.FUNCTION},set(parse_object(b)[1]))
  for n in parse_object(b)[1]:self.assertEqual(source.function_payload(a,n),source.function_payload(b,n))
  self.assertEqual(source.same_functions(self.out/'before-padded.o',self.out/'qualified-padded.o',(source.FUNCTION,)),64);self.assertEqual(source.normalized_pools(a),source.normalized_pools(b))
  self.assertEqual((self.out/'proposed-owner.c').read_text(),source.recovered_owner(self.values[source.SOURCE].decode()));self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),6)
  ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertFalse(any(w==source.ENTRY for w in ws));self.assertEqual([4*i for i,w in enumerate(ws)if w in(0x0C000000|(source.ENTRY>>2&0x3FFFFFF),0x08000000|(source.ENTRY>>2&0x3FFFFFF))],[0x1C1F3C])
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(words=48,frame=96,bindings=6,guards=0,neighbors=64,before_functions=65,after_functions=64,isolated_functions=1,Make_commands=6,inherited_warning712=2,new_diagnostics=0,arguments=3,void_return=True,current_callers_unchanged=True)
 def test_02_guest_calls_low_byte_and_home_reload(self):
  count=0;visits=set()
  for kind,query,mode,phase in itertools.product((0,19,98,99,100,0xFFFFFFFF),(0,1,255,256,257,0xFFFFFF00,0xFFFFFFFF,0x80000000),(0,1,2,4,8,16,31),(0,8)):
   c=Case(kind=kind,query=query,mode=mode,phase=phase);m=self.compare(c);visits.update(m.visits);count+=1
  for byte in range(256):
   self.compare(Case(group=0xAB123400|byte,context=(0x81234567+byte*123)&0xFFFFFFFF,seed=byte));count+=1
  self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+192,4)));self.receipt['guest']=dict(cases=count,visited_words=48,all_group_bytes=True,all_branches=True,low_byte_query_result=True,escaped_point_surface_mutations=True,guest_group_context_home_reload=True,guest_gate_byte_alias=True,complete_state_and_trace=True)
 def test_03_original_caller_query_selector_and_surface(self):
  elf=self.values['conker/build/conker.us.elf'];caller=list(struct.unpack_from('>19I',self.rom,0x1C1F18));at=source.elf_slot_offset(elf,PARENT,76);self.assertEqual(elf[at:at+76],self.rom[0x1C1F18:0x1C1F64]);seen=set();count=0
  for kind,query,mode,phase in itertools.product((0,19,99,100),(0,1,256,257),(0,1,2,4,7),(0,8)):
   c=Case(kind=kind,query=query,group=255,context=1,mode=mode,phase=phase);initial=fixture(c);wanted,calls,obs=reference(initial,c,sp=STACK+phase-24)
   pair=[EffectsOracle(caller,initial,c,entry=PARENT,arguments=(0xA7123456,ACTOR,0x3333),connected={source.ENTRY+4*i:v for i,v in enumerate(w)}).run()for w in(self.truth,self.words)]
   m=pair[0];self.assertEqual(complete(m),complete(pair[1]));self.assertEqual(public(m.memory),public(wanted));self.assertEqual(m.target_entries,[(ACTOR,255,1)]);self.assertEqual(m.calls,[(SETUP,(ACTOR,)),(source.ENTRY,(ACTOR,255,1)),*calls,(FINAL,(0,0xA7123456,ACTOR))]);self.assertEqual(m.observations,obs);seen.update(m.visits);count+=1
  self.assertTrue(set(range(PARENT,PARENT+76,4))<=seen)
  # These original helpers establish the contracts; only the query is currently byte-exact C.
  original={SELECT:list(struct.unpack_from('>63I',self.rom,0x161520)),QUERY:list(struct.unpack_from('>27I',self.rom,0x165564)),SURFACE:list(struct.unpack_from('>89I',self.rom,0x7460C))}
  for entry,offset,length,exact in((SELECT,0x161520,252,False),(QUERY,0x165564,108,True),(SURFACE,0x7460C,356,False)):
   at=source.elf_slot_offset(elf,entry,length);self.assertEqual(elf[at:at+length]==self.rom[offset:offset+length],exact)
  wanted_types={0:0,1:0,2:0,3:0,4:0,16:13,17:1,20:1,22:4,52:11,56:13,59:1,71:10,88:3,90:2,91:3,95:2,112:17,116:2,117:2,122:2,128:3,135:14,136:4,144:4,145:13,150:7,152:12,154:19,156:5,157:6,159:9,160:8,171:18,176:14,177:15,178:17,180:16};selector_seen=set();query_seen=set();surface_seen=set()
  for byte in range(256):
   initial=fixture();initial[ACTOR+4]=byte
   for a,n in((0x800A4350,129),(0x800A4554,23)):
    at=source.elf_slot_offset(elf,a,n*4)
    for j,b in enumerate(elf[at:at+n*4]):initial[a+j]=b
   m=EffectsOracle(original[SELECT],initial,entry=SELECT,arguments=(ACTOR,)).run();self.assertEqual(m.r[2],wanted_types.get(byte,99));self.assertEqual(public(m.memory),public(initial));selector_seen.update(m.visits)
  query_cases=0
  for kind,ptr,low,phase in itertools.product((0,1,19,99),(0,0x240000),(0,1,14,15,31,255),(0,8)):
   c=Case(kind=kind,phase=phase);initial=fixture(c);put(initial,ACTOR+0x1D4,ptr);initial[ACTOR+0x74]=low;point=ACTOR+0x280;expected=dict(initial);success=bool(ptr and(low&15)!=15)
   if success:oracle.fill(expected,point,12,c.seed,21)
   m=EffectsOracle(original[QUERY],initial,c,entry=QUERY,arguments=(ACTOR,kind,point)).run();self.assertEqual(m.r[2],int(success));self.assertEqual(public(m.memory),public(expected));self.assertEqual(m.calls,[(TRANSFORM,(0x800A3FD8+kind*16,point,ptr+0x300,kind))]if success else[]);query_seen.update(m.visits);query_cases+=1
  surface_cases=0
  for flag,index,answer,phase in itertools.product((0,0x200000),(0,1,7),(0,1,0xFFFFFFFF),(0,8)):
   c=Case(query=answer,phase=phase);initial=fixture(c);d=ACTOR+0x280;put(initial,ACTOR+0xF8,flag);put(initial,ACTOR+0x180,bits(19.75));put(initial,ACTOR+0x14,bits(-12.5));put(initial,ACTOR+0x1C,bits(34.5));put(initial,ACTOR+0x1A0,index,2);put(initial,0x800DBEF4,0x350000);expected=dict(initial);put(expected,d,bits(19.75))
   if flag:
    for j,v in enumerate((988,19,1034,-1012,19,34,988,19,-966)):put(expected,d+4+2*j,v&65535,2)
   else:
    for j in range(18):expected[d+4+j]=initial[ACTOR+0x18C+j]
   put(expected,d+24,read(initial,ACTOR+0x184));expected[d+28]=6|int(not index or bool(answer));expected[d+29]=2 if index else 1;put(expected,d+32,0x350000+(index-1)*160 if index else 0)
   m=EffectsOracle(original[SURFACE],initial,c,entry=SURFACE,arguments=(d,ACTOR)).run();self.assertEqual(public(m.memory),public(expected));self.assertEqual(m.calls,[(CHECK,(index-1,))]if index else[]);surface_seen.update(m.visits);surface_cases+=1
  self.receipt['caller']=dict(original_caller_cases=count,caller_words=19,visited_caller_words=19,current_caller_byte_exact=True,selector_cases=256,selector_words=63,selector_visited=len(selector_seen),query_cases=query_cases,query_words=27,query_visited=len(query_seen),surface_cases=surface_cases,surface_words=89,surface_visited=len(surface_seen),query_current_byte_exact=True,selector_surface_original_only=True,base_and_point_effect_providers_bounded=True,hardware_or_gameplay_claim=False)
 def test_04_native32_three_argument_ABI_and_controls(self):
  unit=self.fresh/'native.c';unit.write_text(native_harness())
  for opt in('O0','O2','O3'):
   exe=self.fresh/('native-'+opt);p=subprocess.run([*native_command('-'+opt,True),'-mstackrealign',str(unit),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stderr);p=subprocess.run([str(exe)],capture_output=True,timeout=60);self.assertEqual(p.returncode,0,(opt,p.stderr))
  self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_each_profile=98304,effective_controls=7,trapping_UBSan=True,actual_three_argument_void_function_pointer=True,all_group_bytes=True,mutable_escaped_point_surface=True,portable_home_alias_claim=False)
 def test_05_fired_access_prefixes(self):
  cuts=0
  for kind,query,mode,phase in itertools.product((19,99),(0,1,256),(0,8,16,31),(0,8)):
   c=Case(kind=kind,query=query,mode=mode,phase=phase);initial=fixture(c);good=self.compare(c)
   for cut in range(good.root_accesses):
    pair=[]
    for w in(self.truth,self.words):
     m=EffectsOracle(w,initial,c);m.root_fault=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     self.assertEqual(m.root_accesses,cut);pair.append(m)
    self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));cuts+=1
  self.receipt['faults']=dict(fired_prefix_pairs=cuts,complete_state_trace_PC_delay=True,guest_instruction_boundaries_only=True)
 def test_06_real_padder_controls_and_GNU_relocations(self):
  raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'));bad=bytearray(raw);bad[124]^=1;wrong=dict(rs);wrong[100]=[('R_MIPS_26','wrong')]
  for b,bindings in((raw[:-4],rs),(bytes(bad),rs),(raw,wrong)):
   with self.assertRaises(ValueError):source.checked_payload(b,bindings)
  self.assertEqual((raw,rs),source.payload(self.out/('original-'+source.FUNCTION+'.o')))
  asm=self.fresh/'padded.s';asm.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/'conker/retail_layout.us.txt',source.OWNER,word_patches_path=ROOT/'conker/retail_word_patches.us.csv',function_objects={source.FUNCTION:self.out/'selected.o'}));obj=asm.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(asm)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes())
  with self.assertRaises(ValueError):source.emit_padded_assembly(self.out/'after-owner.o',ROOT/'conker/retail_layout.us.txt',source.OWNER,function_objects={source.FUNCTION:self.out/'after-owner.o'})
  count=0
  for j,entry in enumerate((source.ENTRY,0x17007FFC,0x2500FFFC)):
   symbols=SYMBOLS if j==0 else{n:entry+0x10004+i*0x1000 for i,n in enumerate(SYMBOLS)}
   images=[self.rebased(p,entry,symbols,'rebase-%d-%d'%(j,k))[:48]for k,p in enumerate((self.out/('original-'+source.FUNCTION+'.o'),self.out/'qualified-padded.o',self.out/'make-shadow/src/game_161520.c.o'))];self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
   for mode,phase in itertools.product((0,1,2,4,8,16,31),(0,8)):self.compare(Case(mode=mode,phase=phase),images[:2],entry,symbols);count+=1
  self.receipt['rebases']=dict(layouts=3,guest_cases=count,six_J26_bindings=True,original_compiler_actual_Make=True,raw_binding_controls=3,missing_override_control=1,guards=0)
 def test_07_actually_compiled_semantic_controls(self):
  cases={'sentinel':(source.SELECTED.replace('type != 99','type != 98'),Case(kind=99)),'wide':(source.SELECTED.replace('u8 available;','s32 available;'),Case(query=256)),'base':(source.SELECTED.replace('        func_15138120(actor, type, 1);',''),Case()),'group':(source.SELECTED.replace('&surface, group, context','&surface, (u8)(group ^ 1), context'),Case()),'context':(source.SELECTED.replace('&surface, group, context','&surface, group, 0'),Case())}
  for name,(body,c)in cases.items():
   obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+body,'negative-'+name);self.assertFalse(diag);words=self.rebased(obj,source.ENTRY,SYMBOLS,'negative-link-'+name);initial=fixture(c);expected,calls,obs=reference(initial,c);m=EffectsOracle(words,initial,c).run();self.assertNotEqual((public(m.memory),m.calls,m.observations),(public(expected),calls,obs),name)
  self.receipt['compiled_control']=dict(actually_compiled_IDO_negatives=5,semantic_failures=True)
 def test_08_strict_entire_image_extent_and_corruptions(self):
  v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=v['conker/conker.us.bin'][source.ROM:source.ROM+192];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,192);symbol=next(p for p,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8
  for offset in(20,at,at+180,at+192,source.elf_slot_offset(before,0x800A4350,4),symbol):
   bad=bytearray(expected);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  count=sum(x!=y for x,y in zip(before,expected));self.assertEqual(count,155);self.receipt['image']=dict(changed_bytes=count,code_bytes=154,size_bytes=1,all_named_definitions_checked=True,protected_owners=720,protected_bytes=189088,exclusions=0,effective_corruptions=6,shared_headers_helpers_current_callers_unchanged=True,all_guard_bytes_unchanged=True)
