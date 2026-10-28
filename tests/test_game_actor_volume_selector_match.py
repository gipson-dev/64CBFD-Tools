"""Actor/volume query: direct C, original dispatcher, aliases and strict image."""
from dataclasses import replace
from pathlib import Path
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_actor_volume_selector_match as source
from tools.tests import game_actor_volume_selector_oracle as oracle
from tools.tests.game_actor_volume_selector_oracle import Case,fixture,reference,public,ActorVolumeOracle,SYMBOLS,POINTS,RECORD,PACKET,PARENT,LOOKUP,JUMPTABLE,PARENT_TABLE,STACK,put,read,faults
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
ROOT=Path(__file__).resolve().parents[2]

def controls():
 b=source.SELECTED
 out=dict(no_mask=b.replace('selector &= 0xFFF;','selector &= 0xFFFF;'),reject_equality=b.replace('< (u32)selector','<= (u32)selector'),signed_count=b.replace('(u32)D_800D3094 < (u32)selector','D_800D3094 < selector'),wrong_flag=b.replace('& 3) == 3','& 3) == 2'),exact_flag=b.replace('(D_800D3098[selector].flags & 3) == 3','D_800D3098[selector].flags == 3'),wrong_actor=b.replace('[actorIndex]','[actorIndex ^ 1]'),wrong_axis=b.replace('.z_position','.y_position'),boolean_return=b.replace('return func_150A2E4C(','return !!func_150A2E4C('))
 assert all(v!=b for v in out.values());return out

def native_harness():
 t=source.HEADERS+source.DECLARATIONS+r'''
typedef char ABI[(sizeof(void*)==4&&sizeof(struct127)==812&&__builtin_offsetof(struct127,x_position)==20&&__builtin_offsetof(struct127,y_position)==24&&__builtin_offsetof(struct127,z_position)==28&&sizeof(GeneratedCDE80Record)==52&&__builtin_offsetof(GeneratedCDE80Record,flags)==21)?1:-1];
struct127 D_800CC2D0[26];
static struct127 savedActors[26];
static GeneratedCDE80Record records[4096],savedRecords[4096];
GeneratedCDE80Record *D_800D3098=records;
s32 D_800D3094;
static u32 calls,error,index,actor,result;
static u32 word(f32 x){union{u32 u;f32 f;}v;v.f=x;return v.u;}
__attribute__((noinline,noclone)) s32 func_150A2E4C(GeneratedCDE80Record*p,f32 x,f32 y,f32 z){
 if(p!=records+index||word(x)!=word(D_800CC2D0[actor].x_position)||word(y)!=word(D_800CC2D0[actor].y_position)||word(z)!=word(D_800CC2D0[actor].z_position))error=1;
 calls++;return(s32)result;
}
'''
 for n,b in dict(selected=source.SELECTED,**controls()).items():t+=b.replace('s32 '+source.FUNCTION,'static s32 '+n)+'\n'
 t+=r'''
typedef s32(*Query)(s32,s32);
static int one(Query fn,u32 selector,u32 count,u32 flag,u32 which){u32 i,wanted,actual;u8*p,*q;
 index=selector&4095u;actor=which;D_800D3094=(s32)count;records[index].flags=(u8)flag;savedRecords[index]=records[index];calls=error=0;
 result=0x87654321u+index*17u+which;wanted=count<index?1u:(flag&3)==3?result:0u;
 actual=(u32)fn((s32)which,(s32)selector);
 if(actual!=wanted||error||calls!=(count>=index&&(flag&3)==3)||D_800D3098!=records||(u32)D_800D3094!=count)return 1;
 p=(u8*)&records[index];q=(u8*)&savedRecords[index];for(i=0;i<52;i++)if(p[i]!=q[i])return 1;
 return 0;
}
static int check(Query fn){u32 i,a,f;u8*p,*q;
 p=(u8*)records;for(i=0;i<sizeof(records);i++)p[i]=(u8)(i*13+59);
 for(i=0;i<4096;i++)savedRecords[i]=records[i];
 p=(u8*)D_800CC2D0;for(i=0;i<sizeof(D_800CC2D0);i++)p[i]=(u8)(i*17+23);
 for(a=0;a<26;a++){D_800CC2D0[a].x_position=(f32)(a*7);D_800CC2D0[a].y_position=-(f32)(a*7+1);D_800CC2D0[a].z_position=(f32)(a*7+2);savedActors[a]=D_800CC2D0[a];}
 for(i=0;i<4096;i++)for(a=0;a<26;a++){
  if(one(fn,i,i,3,a)||one(fn,i,i?i-1:0,3,a)||one(fn,i,i+1,255,a)||one(fn,i,0xFFFFFFFFu,3,a)||one(fn,i,0x80000000u,3,a))return 1;
 }
 for(f=0;f<256;f++)for(a=0;a<26;a++)if(one(fn,1,1,f,a)||one(fn,0,0,f,a)||one(fn,0x1001,10,f,a))return 1;
 p=(u8*)records;q=(u8*)savedRecords;for(i=0;i<sizeof(records);i++)if(p[i]!=q[i])return 1;
 p=(u8*)D_800CC2D0;q=(u8*)savedActors;for(i=0;i<sizeof(D_800CC2D0);i++)if(p[i]!=q[i])return 1;
 return 0;
}
static int run(void){if(check(selected))return 10;
'''
 for i,n in enumerate(controls()):t+='if(!check('+n+'))return '+str(20+i)+';\n'
 return t+'return 0;}\n'+START

class ActorVolumeSelectorTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>48I',cls.rom,source.ROM));local=cls.fresh/'qualified-padded.o';local.write_bytes((cls.out/'qualified-padded.o').read_bytes());data,functions=source.link_owner(ROOT,cls.fresh,local,source.OWNER);cls.words=list(struct.unpack_from('>48I',data,functions[source.FUNCTION]['value']))
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def compare(self,c=Case(),images=None,entry=source.ENTRY,symbols=SYMBOLS):
  initial=fixture(c,symbols);memory,result,calls=reference(initial,c,symbols);pair=[]
  for words in images or(self.truth,self.words):
   m=ActorVolumeOracle(words,initial,c,symbols,entry).run();self.assertEqual((public(m.memory),m.r[2],m.calls),(public(memory),result,calls),c);pair.append(m)
  self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);return pair[0]
 def rebased(self,obj,entry,symbols,label):
  text,functions,bindings=parse_object(obj);assembly,unknown=emit_function(text,functions[source.FUNCTION],bindings,source.FUNCTION,symbols);self.assertFalse(unknown);p=self.fresh/label;p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
  subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
  subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,*['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
  return list(struct.unpack('>%dI'%(len(sections(p.with_suffix('.elf'))['.text'][1])//4),sections(p.with_suffix('.elf'))['.text'][1]))
 def test_01_owner_Make_census_and_source_ABI(self):
  self.assertEqual(self.words,self.truth);source.checked_payload(*source.payload(self.out/'selected.o'))
  for label in('before','after'):
   obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),28)
  self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),27);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'))
  proposed=(self.out/'proposed-owner.c').read_text();self.assertEqual(proposed,source.recovered_owner(self.values[source.SOURCE].decode()));self.assertEqual(proposed.count('#pragma GLOBAL_ASM'),2);self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),5)
  ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertFalse(any(w==source.ENTRY for w in ws));self.assertEqual([4*i for i,w in enumerate(ws)if w in(0x0C000000|(source.ENTRY>>2&0x3FFFFFF),0x08000000|(source.ENTRY>>2&0x3FFFFFF))],[0xCDC10])
  self.assertIn('s32 func_150A04D8() {\n    return 0;\n}',self.values['conker/src/game/generated_CD860.c'].decode())
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(words=48,frame=24,bindings=7,guards=0,neighbors=27,compact_functions=28,GLOBAL_ASM_routines=2,Make_commands=5,diagnostics=0,arguments=2,current_parent_unchanged_placeholder=True,inline_actor_table_stride=812,direct_site='0x150A0760')
 def test_02_guest_unsigned_bounds_float_bits_and_aliases(self):
  count=0;visits=set()
  for actor,selector,limit,flag,point in itertools.product((0,25,0xFFFFFFFF,0x7FFFFFFF,0x80000000),(0,1,4095,4097,0xFFFFFFFF),(0,1,4094,4095,0x80000000,0xFFFFFFFF),(0,2,3,128,255),POINTS[:2]):
   m=self.compare(Case(actor,selector,limit,flag,point,phase=(count&1)*8));visits.update(m.visits);count+=1
  for flag,point in itertools.product(range(256),POINTS):self.compare(Case(flag=flag,point=point));count+=1
  aliases=0
  for phase,home in itertools.product((0,8),(-24,-20,-16,-12,0,4,8,16,32)):
   self.compare(Case(selector=0,count=0,phase=phase,record=STACK+phase+home));count+=1;aliases+=1
  for offset in range(0,52,4):
   self.compare(Case(selector=0,count=0,record=source.TABLE-offset));count+=1;aliases+=1
  for offset in(0,4,8,12,16,20,24):
   self.compare(Case(selector=0,count=0,record=source.ACTORS+20-offset));count+=1;aliases+=1
  self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+192,4)));self.receipt['guest']=dict(cases=count,visited_words=48,all_flag_bytes=True,full_word_actor_and_selector=True,bit_exact_float_arguments=True,guest_aliases=aliases,complete_state_and_trace=True,opaque_helper=True,portable_C_out_of_bounds_claim=False)
 def test_03_original_dispatcher_return_and_retained_plane_helper(self):
  helper=list(struct.unpack_from('>38I',self.rom,0xD02FC));elf=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(elf,source.HELPER,152);self.assertEqual(list(struct.unpack_from('>38I',elf,at)),helper);connected=dict(zip(range(source.HELPER,source.ENTRY,4),helper));seen=set();helper_cases=0
  for actor,origin,point,scale in itertools.product((0,25),((0,0,0),(-32768,17,32767),(9,-123,5)),POINTS[:2],(-0.5,0.5)):
   c=Case(actor=actor,point=point);memory=fixture(c)
   for i,v in enumerate(origin):put(memory,RECORD+2*i,v&65535,2)
   for off,v in((0x24,1.0),(0x28,scale),(0x2C,-2.0),(0x30,3.0)):put(memory,RECORD+off,bits(v))
   x=floating(bits(floating(point[0])-origin[0]));y=floating(bits(floating(point[1])-origin[1]));z=floating(bits(y-origin[2]));product=floating(bits(floating(bits(z*3.0))+floating(bits(x*-2.0))));wanted=int(floating(bits(floating(bits(product*scale))-y))<=0.0)
   models=[ActorVolumeOracle(w,memory,c,connected=connected).run()for w in(self.truth,self.words)];self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(models[0].r[2],wanted);seen.update(models[0].visits);helper_cases+=1
  parent=list(struct.unpack_from('>317I',self.rom,0xCD988));at=source.elf_slot_offset(elf,JUMPTABLE,52);self.assertEqual(struct.unpack_from('>13I',elf,at),PARENT_TABLE);parent_cases=0;parent_visits=set()
  for actor,selector,limit,flag,phase in itertools.product((-1,0,25),(0,1,4097),(0,1,0xFFFFFFFF),(0,3,255),(0,8)):
   c=Case(actor,selector,limit,flag,phase=phase);memory=fixture(c);put(memory,PACKET+8,0xCABB2017)
   for i,v in enumerate(PARENT_TABLE):put(memory,JUMPTABLE+4*i,v)
   _,result,calls=reference(memory,c);models=[ActorVolumeOracle(parent,memory,c,entry=PARENT,arguments=(selector,13,PACKET),connected=dict(zip(range(source.ENTRY,source.ENTRY+192,4),w))).run()for w in(self.truth,self.words)]
   self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual((models[0].r[2],models[0].calls),(result,[(LOOKUP,(0xCABB0017,)),(source.ENTRY,(actor&0xFFFFFFFF,selector)),*calls]));parent_visits.update(models[0].visits);parent_cases+=1
  for n in('conker/src/game/generated_CD860.c','conker/build/src/game/generated_CD860.c.o'):self.assertEqual((ROOT/n).read_bytes(),self.values[n])
  self.receipt['caller']=dict(cases=parent_cases,helper_cases=helper_cases,original_caller_words=317,original_caller_visited_words=len(parent_visits&set(range(PARENT,PARENT+1268,4))),retained_helper_words=38,retained_helper_visited_words=len(seen&set(range(source.HELPER,source.ENTRY,4))),command=13,actor_reference_kind='0x2000',complete_return_join=True,lookup_provider_bounded=True,current_parent_still_placeholder=True,full_dispatcher_or_gameplay_claim=False,helper_finite_IEEE_cases=True)
 def test_04_native32_canonical_arrays_returns_and_controls(self):
  unit=self.fresh/'native.c';unit.write_text(native_harness())
  for opt in('O0','O2','O3'):
   exe=self.fresh/('native-'+opt);p=subprocess.run([*native_command('-'+opt,True),'-mstackrealign',str(unit),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stderr);p=subprocess.run([str(exe)],capture_output=True,timeout=60);self.assertEqual(p.returncode,0,(opt,p.stderr))
  self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_each_profile=4096*26*5+256*26*3,effective_controls=len(controls()),trapping_UBSan=True,canonical_26_actor_array=True,all4096_masked_indices=True,all_flag_bytes=True,whole_storage_fences=True,two_argument_function_pointer=True,opaque_helper=True,native_NaN_payload_claim=False)
 def test_05_fired_access_prefixes_and_skipped_reads(self):
  cuts=0
  for limit,flag,phase,record in itertools.product((0,1,0xFFFFFFFF),(0,3,255),(0,8),(None,STACK+16)):
   c=Case(count=limit,flag=flag,phase=phase,record=record);initial=fixture(c);good=self.compare(c)
   for cut in range(good.root_accesses):
    pair=[]
    for w in(self.truth,self.words):
     m=ActorVolumeOracle(w,initial,c);m.root_fault=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     self.assertEqual(m.root_accesses,cut);pair.append(m)
    self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));cuts+=1
  for limit,flag in((0,3),(1,0)):
   c=Case(count=limit,flag=flag);memory=fixture(c)
   for i in range(12):memory.pop(source.ACTORS+20+i,None)
   if limit==0:
    for i in range(4):memory.pop(source.TABLE+i,None)
    for i in range(52):memory.pop(RECORD+i,None)
   for w in(self.truth,self.words):self.assertEqual(ActorVolumeOracle(w,memory,c).run().r[2],1 if limit==0 else 0)
  self.receipt['faults']=dict(fired_prefix_pairs=cuts,complete_state_trace_PC_delay=True,bounds_skip_pointer_and_actor_reads=True,inactive_flag_skips_actor_reads=True)
 def test_06_real_padder_controls_and_GNU_relocations(self):
  raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'));bad=bytearray(raw);bad[124]^=1;wrong=dict(rs);wrong[108]=[('R_MIPS_LO16','wrong')]
  for b,bindings in((raw[:-4],rs),(bytes(bad),rs),(raw,wrong)):
   with self.assertRaises(ValueError):source.checked_payload(b,bindings)
  p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=ROOT/'conker/retail_word_patches.us.csv',filename=source.OWNER));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes());count=0
  for j,entry in enumerate((source.ENTRY,0x17007FFC,0x2500FFFC)):
   symbols=SYMBOLS if j==0 else dict(D_800D3094=0x81007FFC+j*0x10000,D_800D3098=0x82008004+j*0x10000,D_800CC2D0=0x8300FFFC+j*0x10000,func_150A2E4C=entry+0x10000)
   images=[self.rebased(p,entry,symbols,'rebase-%d-%d'%(j,k))[:48]for k,p in enumerate((self.out/('original-'+source.FUNCTION+'.o'),self.out/'selected.o',self.out/'make-shadow/src/game/generated_CDE80.c.o'))];self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
   for limit,flag,actor in itertools.product((0,1,0xFFFFFFFF),(0,3,255),(0,25)):
    self.compare(Case(actor=actor,count=limit,flag=flag),images[:2],entry,symbols);count+=1
  self.receipt['rebases']=dict(layouts=3,guest_cases=count,HI_LO_carries_and_J26=True,original_compiler_and_actual_Make=True,raw_binding_controls=3,guards=0)
 def test_07_actually_compiled_semantic_controls(self):
  for name,c in(('no_mask',Case(selector=4097,count=10)),('signed_count',Case(count=0xFFFFFFFF)),('reject_equality',Case()),('wrong_axis',Case())):
   obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+controls()[name],'negative-'+name);self.assertFalse(diag);words=self.rebased(obj,source.ENTRY,SYMBOLS,'negative-link-'+name);initial=fixture(c);_,result,calls=reference(initial,c);m=ActorVolumeOracle(words,initial,c).run();self.assertNotEqual((m.r[2],m.calls),(result,calls),name)
  self.receipt['compiled_control']=dict(actually_compiled_IDO_negatives=4,semantic_value_failures=True,mask_unsigned_count_equality_and_axis_controls=True)
 def test_08_strict_entire_image_extent_and_corruptions(self):
  v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=v['conker/conker.us.bin'][source.ROM:source.ROM+192];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,192);symbol=next(p for p,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8
  for offset in(20,at,at+180,at+192,source.elf_slot_offset(before,0x80082B20,4),symbol):
   bad=bytearray(expected);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  count=sum(x!=y for x,y in zip(before,expected));self.assertEqual(count,158);self.receipt['image']=dict(changed_bytes=count,code_bytes=157,size_bytes=1,other6055_bodies_and6056_addresses_fixed=True,all_named_definitions_checked=True,protected_owners=720,protected_bytes=189088,exclusions=0,effective_corruptions=6,shared_headers_helper_current_parent_and_guards_unchanged=True)
