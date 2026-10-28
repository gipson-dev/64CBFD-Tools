"""Type-0x5B point effect: direct C, dispatcher routes and strict whole image."""
from dataclasses import replace
from pathlib import Path
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_type91_point_effect_match as source
from tools.tests import game_type91_point_effect_oracle as oracle
from tools.tests.game_type91_point_effect_oracle import Case,fixture,reference,public,PointEffectOracle,SYMBOLS,POINTS,RECORD,INPUT,ALT,HEAD,PACKET,TABLE,STACK,put,read,faults
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
ROOT=Path(__file__).resolve().parents[2]

def controls():
 b=source.SELECTED
 out=dict(inverted_companions=b.replace('if (companions)','if (!companions)'),early_position=b.replace('    if (companions)', '    payload.position = *position;\n    if (companions)').replace('    payload.position = *position;\n    payload.accumulator','    payload.accumulator'),wrong_class=b.replace('0x5B','0x5A'),wrong_flag=b.replace('payload.flag = flag','payload.flag = group'),wrong_accumulator=b.replace('0.0f','1.0f'),short_copy=b.replace('memcpy(effect + 0x28, &payload, sizeof(payload))','memcpy(effect + 0x28, &payload, 16)'))
 assert all(v!=b for v in out.values());return out

def native_harness():
 t=source.HEADERS+source.DECLARATIONS+"typedef char ABI[(sizeof(void*)==4&&sizeof(vertex)==12&&sizeof(Type91PointPayload)==20&&__builtin_offsetof(Type91PointPayload,accumulator)==12&&__builtin_offsetof(Type91PointPayload,flag)==16)?1:-1];\nstatic struct {u32 left[4];vertex value;u32 right[4];}point,expectedPoint;\nstatic u8 record[80],expectedRecord[80];\nstatic vertex wantedPoint;\nstatic u32 seed,mode,fail,companionCalls,factoryCalls,copyCalls,error;\nstatic u8 wantedCompanions,wantedFlag,wantedGroup;\nstatic s16 wantedLifetime;\nstatic s32 wantedContext;\nstatic void bytes(void*d,const void*s,u32 n){u32 i;for(i=0;i<n;i++)((u8*)d)[i]=((const u8*)s)[i];}\nstatic u32 bits(f32 x){union{f32 f;u32 u;}v;v.f=x;return v.u;}\ns32 func_151DC6A0(vertex*p,s32 group,s32 context){\n if(p!=&point.value||group!=wantedGroup||context!=wantedContext||!wantedCompanions||companionCalls++!=0||factoryCalls||copyCalls)error=1;\n if(mode&1){point.value.x+=7.0f;point.value.y=-point.value.y;expectedPoint.value=point.value;}\n return(s32)0x87654321u;\n}\nvoid*func_15149130(s16 lifetime,s8 a,s8 type,s8 b,u8 c,u8 d,s32 extra,u8 group,s32 context){\n if(lifetime!=wantedLifetime||a!=-1||type!=0x5B||b!=-1||c!=1||d||extra!=20||group!=wantedGroup||context!=wantedContext||factoryCalls++!=0||copyCalls||companionCalls!=(wantedCompanions!=0))error=1;\n wantedPoint=point.value;\n if(mode&2){point.value.z+=17.0f;expectedPoint.value=point.value;}\n return fail?NULL:record;\n}\nvoid*memcpy(void*d,const void*s,size_t n){const Type91PointPayload*p=s;\n if(d!=record+40||n!=20||copyCalls++!=0||factoryCalls!=1||fail||bits(p->position.x)!=bits(wantedPoint.x)||bits(p->position.y)!=bits(wantedPoint.y)||bits(p->position.z)!=bits(wantedPoint.z)||bits(p->accumulator)!=0||p->flag!=wantedFlag)error=1;\n bytes(d,s,n);return d;\n}\n"
 for name,b in dict(selected=source.SELECTED,**controls()).items():t+=b.replace(source.FUNCTION,name)+"\n"
 return t+"typedef void(*Construct)(vertex*,s16,u8,u8,u8,s32);\nstatic const s16 lifetimes[]={-32768,-1,0,1,300,32767};\nstatic int check(Construct fn){u32 i,j,k;u8*p,*q;\n for(seed=0;seed<256;seed++)for(j=0;j<6;j++)for(k=0;k<2;k++)for(fail=0;fail<2;fail++)for(mode=0;mode<4;mode++){\n  p=(u8*)&point;q=(u8*)&expectedPoint;for(i=0;i<sizeof(point);i++)p[i]=q[i]=(u8)(seed+i*17);\n  for(i=0;i<80;i++)record[i]=expectedRecord[i]=(u8)(seed+i*13);\n  point.value.x=(f32)seed*0.25f;point.value.y=-(f32)seed*0.5f;point.value.z=(f32)seed*0.125f+1.0f;expectedPoint.value=point.value;\n  wantedCompanions=k?(u8)seed:0;wantedFlag=(u8)seed;wantedGroup=(u8)(seed*17+3);wantedLifetime=lifetimes[j];wantedContext=(s32)(0x87654321u+seed*29u);\n  companionCalls=factoryCalls=copyCalls=error=0;fn(&point.value,wantedLifetime,wantedCompanions,wantedFlag,wantedGroup,wantedContext);\n  if(error||factoryCalls!=1||companionCalls!=(wantedCompanions!=0)||copyCalls!=!fail)return 1;\n  if(!fail){bytes(expectedRecord+40,&wantedPoint,12);for(i=52;i<56;i++)expectedRecord[i]=0;expectedRecord[56]=wantedFlag;}\n  for(i=0;i<80;i++)if((fail||i<57||i>=60)&&record[i]!=expectedRecord[i])return 1;\n  p=(u8*)&point;q=(u8*)&expectedPoint;for(i=0;i<sizeof(point);i++)if(p[i]!=q[i])return 1;\n }return 0;\n}\nstatic int run(void){if(check(selected))return 10;\nif(!check(inverted_companions))return 20;\nif(!check(early_position))return 21;\nif(!check(wrong_class))return 22;\nif(!check(wrong_flag))return 23;\nif(!check(wrong_accumulator))return 24;\nif(!check(short_copy))return 25;\nreturn 0;}\n\nvoid _start(void) {\n    int result = run();\n    __asm__ volatile(\".byte 0xcd,0x80\" : : \"a\"(1), \"b\"(result) : \"memory\");\n    __builtin_unreachable();\n}\n"


class Type91PointEffectTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>48I',cls.rom,source.ROM));local=cls.fresh/'qualified-padded.o';local.write_bytes((cls.out/'qualified-padded.o').read_bytes());data,functions=source.link_owner(ROOT,cls.fresh,local,source.OWNER);cls.words=list(struct.unpack_from('>48I',data,functions[source.FUNCTION]['value']))
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def compare(self,c=Case(),images=None,entry=source.ENTRY,symbols=SYMBOLS):
  initial=fixture(c);memory,calls,packets=reference(initial,c,symbols);pair=[]
  for words in images or(self.truth,self.words):
   m=PointEffectOracle(words,initial,c,symbols,entry).run();self.assertEqual((public(m.memory),m.calls,m.copy_packets),(public(memory),calls,packets),c)
   if c.allocated:self.assertEqual(bytes(m.memory[c.record+40+i]for i in range(20)),bytes(memory[c.record+40+i]for i in range(20)),c)
   pair.append(m)
  self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);return pair[0]
 def rebased(self,obj,entry,symbols,label):
  text,functions,bindings=parse_object(obj);assembly,unknown=emit_function(text,functions[source.FUNCTION],bindings,source.FUNCTION,symbols);self.assertFalse(unknown);p=self.fresh/label;p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
  subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
  subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,*['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
  return list(struct.unpack('>%dI'%(len(sections(p.with_suffix('.elf'))['.text'][1])//4),sections(p.with_suffix('.elf'))['.text'][1]))

 def test_01_owner_Make_census_and_source_ABI(self):
  self.assertEqual(self.words,self.truth);source.checked_payload(*source.payload(self.out/'selected.o'))
  for label in('before','after'):
   obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertEqual(source.check_owner_diagnostics(diag),0);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),3)
  self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),2);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'))
  proposed=(self.out/'proposed-owner.c').read_text();self.assertEqual(proposed,source.recovered_owner(self.values[source.SOURCE].decode()));self.assertEqual(proposed.count('#pragma GLOBAL_ASM'),0);self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3)
  ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertFalse(any(w==source.ENTRY for w in ws));self.assertEqual([4*i for i,w in enumerate(ws)if w in(0x0C000000|(source.ENTRY>>2&0x3FFFFFF),0x08000000|(source.ENTRY>>2&0x3FFFFFF))],[0x54704,0x5472C])
  self.assertIn('s32 func_151DC6A0() {\n    return 0;\n}',proposed);self.assertIn('s32 func_150265CC() {\n    return 0;\n}',self.values['conker/src/game/generated_50D80.c'].decode())
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(words=48,frame=72,bindings=3,guards=0,neighbors=2,compact_functions=3,Make_commands=3,diagnostics=0,arguments=6,void_return=True,current_companion_and_parent_placeholders_unchanged=True,payload_bytes=20,three_uninitialized_tail_bytes=True,direct_sites=['0x15027254','0x1502727C'])
 def test_02_guest_homes_payload_order_and_aliases(self):
  count=0;visits=set();aliases=0
  for lifetime,companions,allocated,mode,point,phase in itertools.product((0,0x7FFF,0x8000,0xFFFF,0x12348001),(0,1,0x100,0xABCDEF80),(False,True),(0,1,2,4,8,16,31),POINTS[:2],(0,8)):
   m=self.compare(Case(lifetime=lifetime,companions=companions,allocated=allocated,mode=mode,point=point,phase=phase));visits.update(m.visits);count+=1
  for byte in range(256):
   self.compare(Case(companions=byte,flag=0xAABB0000|byte,group=0x12340000|((byte*17+3)&255),context=0x87654321));count+=1
  for phase,offset in itertools.product((0,8),(-20,-16,-12,-8,0,4,24,32)):
   self.compare(Case(position=STACK+phase+offset,phase=phase));count+=1;aliases+=1
  for phase,offset in itertools.product((0,8),(-20,-16,-12,24,32)):
   self.compare(Case(record=STACK+phase+offset-40,phase=phase));count+=1;aliases+=1
  for offset in(-4,0,4):self.compare(Case(position=RECORD+40+offset));count+=1;aliases+=1
  self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+192,4)));self.receipt['guest']=dict(cases=count,visited_words=48,guest_aliases=aliases,all_companion_flag_group_bytes=True,signed_lifetime=True,complete_state_and_trace=True,ordered_point_copies_and_late_home_reads=True,all20payload_bytes_including_tail=True,helpers_bounded=True,portable_alias_padding_or_FCSR_claim=False)
 def helpers(self):
  connected={};elf=self.values['conker/build/conker.us.elf']
  for va,rom,words in((source.FACTORY,0x1765E0,49),(source.ALLOCATOR,0x194F18,28),(source.INITIALIZER,0x195EFC,20),(source.BZERO,0x226F0,40),(source.COPY,0x22EC0,11)):
   body=list(struct.unpack_from('>%dI'%words,self.rom,rom));at=source.elf_slot_offset(elf,va,words*4);self.assertEqual(list(struct.unpack_from('>%dI'%words,elf,at)),body);connected.update({va+4*i:w for i,w in enumerate(body)})
  return connected
 def helper_expected(self,initial,c,payload,lifetime,flag,group,context):
  m=dict(initial)
  if c.allocated:
   m[c.record]=35;m[c.record+1]=context&255;m[c.record+12]=group&255;m[c.record+13]=1;put(m,c.record+14,lifetime&65535,2)
   m[c.record+16]=255;m[c.record+17]=91;m[c.record+18]=255;m[c.record+19]=0
   put(m,c.record+4,0);put(m,c.record+8,c.oldhead);put(m,oracle.list_address(context),c.record)
   if c.oldhead:put(m,c.oldhead+4,c.record)
   for i in range(16):m[c.record+20+i]=0
   for i,b in enumerate(payload):m[c.record+40+i]=b
  return m
 def test_03_original_dispatcher_helpers_and_tables(self):
  helpers=self.helpers();seen=set();cases=0
  for allocated,oldhead,phase,context,companions in itertools.product((False,True),(0,HEAD),(0,8),(0,1,255),(0,1)):
   c=Case(allocated=allocated,oldhead=oldhead,phase=phase,context=context,companions=companions);initial=fixture(c);pair=[PointEffectOracle(w,initial,c,connected=helpers).run()for w in(self.truth,self.words)];m=pair[0];self.assertEqual(complete(m),complete(pair[1]));seen.update(m.visits)
   sp=STACK+phase;payload=bytearray(initial[sp-20+i]for i in range(20));struct.pack_into('>4I',payload,0,*c.point,0);payload[16]=c.flag
   self.assertEqual(public(m.memory),public(self.helper_expected(initial,c,payload,c.lifetime,c.flag,c.group,context)))
   self.assertIn((source.ALLOCATOR,(35,context,60,1,c.group,1)),m.calls);self.assertIn((source.HEAP,(60,1,1,0,1)),m.calls);self.assertEqual(m.copy_packets,[bytes(payload)]if allocated else []);cases+=1
  elf=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(elf,TABLE,20);table=elf[at:at+20];self.assertEqual(struct.unpack('>5I',table),(0x15027038,0x15027058,0x15027068,0x1502723C,0x15027264));at=source.elf_slot_offset(elf,0x8008A654,4);self.assertEqual(struct.unpack_from('>I',elf,at)[0],0x151DC97C)
  parent=list(struct.unpack_from('>3451I',self.rom,0x53A7C));parent_seen=set();parent_cases=0
  for route,allocated,skip,group,phase,parsed in itertools.product((3,4),(False,True),(False,True),(0,0x80,0x123456FF),(0,8),(0,0x7FFF,0xFFFF8000)):
   c=Case(allocated=allocated,phase=phase,group=group,parsed=parsed,companions=int(route==3),flag=int(route==3));initial=fixture(c);initial.update({TABLE+i:b for i,b in enumerate(table)});initial[PACKET]=5;put(initial,PACKET+2,27,2);initial[PACKET+4]=int(skip);put(initial,PACKET+6,route,2);args=(PACKET,7,0xAABBCCDD,1,0x76543210,0,0,INPUT,group);sp=STACK+phase-0x750
   pair=[PointEffectOracle(parent,initial,c,entry=source.PARENT,arguments=args,connected=helpers|{source.ENTRY+4*i:v for i,v in enumerate(w)}).run()for w in(self.truth,self.words)];m=pair[0];self.assertEqual(complete(m),complete(pair[1]));parent_seen.update(m.visits);seen.update(m.visits);self.assertEqual(m.r[2],1)
   self.assertEqual(m.calls[0],(source.PARSER,(PACKET,5,7,sp+0x6A4,1,27,0,0,0,0,0x76543210)))
   wanted=dict(initial)
   if skip:self.assertEqual(len(m.calls),1);self.assertFalse(m.target_entries)
   else:
    lifetime=oracle.half((parsed-1)&0xFFFFFFFF);self.assertEqual(m.target_entries,[(INPUT,lifetime&0xFFFFFFFF,int(route==3),int(route==3),group,0)])
    payload=bytearray(initial[sp-20+i]for i in range(20));struct.pack_into('>4I',payload,0,*c.point,0);payload[16]=int(route==3);wanted=self.helper_expected(initial,c,payload,lifetime,int(route==3),group,0);self.assertEqual(m.copy_packets,[bytes(payload)]if allocated else [])
   self.assertEqual(public(m.memory),public(wanted));parent_cases+=1
  for n in('conker/src/game/generated_50D80.c','conker/build/src/game/generated_50D80.c.o'):self.assertEqual((ROOT/n).read_bytes(),self.values[n])
  self.receipt['caller']=dict(connected_helper_cases=cases,original_dispatcher_cases=parent_cases,original_dispatcher_words=3451,visited_dispatcher_words=len(parent_seen&set(range(source.PARENT,source.PARENT+3451*4,4))),retained_helper_words=len(helpers),visited_helper_words=len(seen&set(helpers)),full_entry_to_return_for_command27_routes3_and4=True,packet_skip_return=True,retained_jump_and_callback_tables=True,real_factory_allocator_initializer_bzero_memcpy=True,parser_companion_heap_providers_bounded=True,current_parent_and_companion_placeholders_unchanged=True,whole_dispatcher_or_gameplay_claim=False)
 def test_04_native32_canonical_types_and_controls(self):
  unit=self.fresh/'native.c';unit.write_text(native_harness())
  for opt in('O0','O2','O3'):
   exe=self.fresh/('native-'+opt);p=subprocess.run([*native_command('-'+opt,True),'-mstackrealign',str(unit),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stderr);p=subprocess.run([str(exe)],capture_output=True,timeout=60);self.assertEqual(p.returncode,0,(opt,p.stderr))
  self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_each_profile=24576,effective_controls=len(controls()),trapping_UBSan=True,actual_six_argument_void_function_pointer=True,canonical_types=True,whole_point_record_fences=True,helpers_bounded=True,uninitialized_tail_excluded_from_native_value_claim=True)
 def test_05_fired_access_prefixes_and_failure_skip(self):
  cuts=0
  for allocated,companions,mode,phase in itertools.product((False,True),(0,1),(0,2,4,16,31),(0,8)):
   c=Case(allocated=allocated,companions=companions,mode=mode,phase=phase);initial=fixture(c);good=self.compare(c)
   for cut in range(good.root_accesses):
    pair=[]
    for w in(self.truth,self.words):
     m=PointEffectOracle(w,initial,c);m.root_fault=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     self.assertEqual(m.root_accesses,cut);pair.append(m)
    self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));cuts+=1
  c=Case(allocated=False);memory=fixture(c)
  for i in range(80):memory.pop(RECORD+i,None)
  for w in(self.truth,self.words):self.assertFalse(PointEffectOracle(w,memory,c).run().copy_packets)
  self.receipt['faults']=dict(fired_prefix_pairs=cuts,complete_state_trace_PC_delay=True,failed_allocation_skips_copy=True,guest_instruction_boundaries_only=True)
 def test_06_real_padder_controls_and_GNU_relocations(self):
  raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'));bad=bytearray(raw);bad[124]^=1;wrong=dict(rs);wrong[44]=[('R_MIPS_26','wrong')]
  for b,bindings in((raw[:-4],rs),(bytes(bad),rs),(raw,wrong)):
   with self.assertRaises(ValueError):source.checked_payload(b,bindings)
  p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=ROOT/'conker/retail_word_patches.us.csv',filename=source.OWNER));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes());count=0
  for j,entry in enumerate((source.ENTRY,0x17007FFC,0x2500FFFC)):
   symbols=SYMBOLS if j==0 else dict(func_151DC6A0=entry+0x10004,func_15149130=entry+0x28004,memcpy=entry+0x40004)
   images=[self.rebased(p,entry,symbols,'rebase-%d-%d'%(j,k))[:48]for k,p in enumerate((self.out/('original-'+source.FUNCTION+'.o'),self.out/'selected.o',self.out/'make-shadow/src/game/generated_209B50.c.o'))];self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
   for allocated,companions,mode in itertools.product((False,True),(0,1),(0,2,4,16,31)):self.compare(Case(allocated=allocated,companions=companions,mode=mode),images[:2],entry,symbols);count+=1
  self.receipt['rebases']=dict(layouts=3,guest_cases=count,J26_relocations=3,original_compiler_and_actual_Make=True,raw_binding_controls=3,guards=0)
 def test_07_actually_compiled_semantic_controls(self):
  for name in('wrong_class','wrong_flag','wrong_accumulator','short_copy'):
   obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+controls()[name],'negative-'+name);self.assertFalse(diag);words=self.rebased(obj,source.ENTRY,SYMBOLS,'negative-link-'+name);c=Case();initial=fixture(c);expected,calls,packets=reference(initial,c);m=PointEffectOracle(words,initial,c).run();self.assertNotEqual((public(m.memory),m.calls,m.copy_packets),(public(expected),calls,packets),name)
  self.receipt['compiled_control']=dict(actually_compiled_IDO_negatives=4,semantic_value_failures=True)
 def test_08_strict_entire_image_extent_and_corruptions(self):
  v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=v['conker/conker.us.bin'][source.ROM:source.ROM+192];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,192);symbol=next(p for p,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8
  for offset in(20,at,at+180,at+192,source.elf_slot_offset(before,TABLE,4),symbol):
   bad=bytearray(expected);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  count=sum(x!=y for x,y in zip(before,expected));self.assertEqual(count,146);self.receipt['image']=dict(changed_bytes=count,code_bytes=145,size_bytes=1,other6055_bodies_and6056_addresses_fixed=True,all_named_definitions_checked=True,protected_owners=720,protected_bytes=189088,exclusions=0,effective_corruptions=6,shared_headers_helpers_current_parent_and_guards_unchanged=True)
