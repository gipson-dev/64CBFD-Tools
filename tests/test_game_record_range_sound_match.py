"""Record sound selection: direct words, ordered mutable inputs, caller and audio ABI."""
from dataclasses import replace
from pathlib import Path
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_record_range_sound_match as source
from tools.tests import game_record_range_sound_oracle as oracle
from tools.tests.game_record_range_sound_oracle import Case,fixture,reference,public,SoundOracle,RECORD,ALT,PACKET,STACK,put,read,sign,faults
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
ROOT=Path(__file__).resolve().parents[2]
VALUES=(0,1,0x7FFF,0x8000,0xFFFF,0x10000,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0xAABBCCDD)
LIMITS=(-32768,-1,0,1,2,127,255,32766,32767)

def controls():
 b=source.SELECTED;out=dict(signed_compare=b.replace('distance >= (u32)limit','(s32)distance >= limit'),unsigned_limit=b.replace('s32 limit = record->distanceLimit','s32 limit = (u16)record->distanceLimit'),strict_greater=b.replace('distance >= (u32)limit','distance > (u32)limit'),wrong_clamp=b.replace('distance = limit - 1','distance = limit - 2'),missing_clamp=b.replace('distance = limit - 1','distance = distance'),exclusive_span=b.replace('(u32)first + 1','(u32)first'),wide_span=b.replace('(u8)((u32)last - (u32)first + 1)','((u32)last - (u32)first + 1)'),wrong_x=b.replace('record->x, record->y','record->y, record->y'),byte_volume=b.replace('selected, volume','selected, (u8)volume'),late_limit=b.replace('distance, limit);','distance, record->distanceLimit);'),recapture_pointer=b.replace('    return func_10010F88','    record = &D_800D3098[index];\n    return func_10010F88'),early_x=b.replace('    s32 selected;','    s32 selected;\n    s16 cachedX = record->x;').replace('record->x, record->y','cachedX, record->y'),false_return=b.replace('    return func_10010F88','    func_10010F88').replace('distance, limit);','distance, limit);\n    return 0;'))
 assert all(v!=b for v in out.values());return out

def native_harness(values):
 text=source.HEADERS+source.DECLARATIONS+r'''
typedef char ABI[(sizeof(void*)==4&&sizeof(RecordSoundEntry)==52&&__builtin_offsetof(RecordSoundEntry,distanceLimit)==6)?1:-1];
static RecordSoundEntry records[8],expected[8],alternate[8];
RecordSoundEntry *D_800D3098;
static RecordSoundEntry *selectedRecord;
static u32 wantFirst,wantSpan,selectedValue,handle,mode,phase,error,expectedArgs[11];
u16 func_10010E78(u16,s32,u16,s16,u8,s32,s16,s16,s16,s16,s16);
s32 func_1000F568(s32 first,u32 span){
 if(phase++!=0||(u32)first!=wantFirst||span!=wantSpan)error=1;
 if(mode){selectedRecord->x=0x7001;selectedRecord->y=(s16)0x8002;selectedRecord->z=0x7FFE;selectedRecord->distanceLimit=7;D_800D3098=alternate+2;}
 return (s32)selectedValue;
}
u16 func_10010E78(u16 a,s32 b,u16 c,s16 d,u8 e,s32 f,s16 g,s16 h,s16 i,s16 j,s16 k){
 u32 actual[11],n;actual[0]=a;actual[1]=(u32)b;actual[2]=c;actual[3]=(u32)d;actual[4]=e;actual[5]=(u32)f;actual[6]=(u32)g;actual[7]=(u32)h;actual[8]=(u32)i;actual[9]=(u32)j;actual[10]=(u32)k;
 if(phase++!=1)error=1;for(n=0;n<11;n++)if(actual[n]!=expectedArgs[n])error=1;return(u16)handle;
}
'''
 owner=values['conker/src/init_EB00.c'].decode();lo,hi=source.function_span(owner,'func_10010F88');text+=owner[lo:hi]+'\n'
 for name,body in dict(selected=source.SELECTED,**controls()).items():text+=body.replace('u16 '+source.FUNCTION,'static u16 '+name)+'\n'
 text+=r'''
typedef u16(*Adapter)(s32,s32,u16,s32,u32);
static int check(Adapter fn){u32 n,pattern,i,first,last,volume,distance,bound,want,result;int index;s32 limit;u8*p=(u8*)records,*q=(u8*)expected;
 for(n=0;n<65536;n++)for(pattern=0;pattern<5;pattern++){
  for(i=0;i<sizeof(records);i++)p[i]=q[i]=(u8)(n+i*13);for(i=0;i<sizeof(alternate);i++)((u8*)alternate)[i]=(u8)(i*7+3);
  index=(int)(n&3)-1;D_800D3098=records+2;selectedRecord=D_800D3098+index;
  selectedRecord->x=(s16)(n*3);selectedRecord->y=(s16)(n*5+1);selectedRecord->z=(s16)(n*7+2);selectedRecord->distanceLimit=(s16)n;
  expected[index+2]=*selectedRecord;limit=(s16)n;bound=(u32)limit;
  distance=pattern==0?0:pattern==1?bound:pattern==2?bound-1:pattern==3?0xFFFFFFFFu:0x10000u;want=distance>=bound?bound-1:distance;
  first=0xA5000000u+n*17;last=first+(n&511)-1;volume=0xBEEF0000u+n;wantFirst=first;wantSpan=(last-first+1)&255;selectedValue=0x98760000u+n*7;handle=n*13;mode=pattern&1;phase=error=0;
  if(mode){expected[index+2].x=0x7001;expected[index+2].y=(s16)0x8002;expected[index+2].z=0x7FFE;expected[index+2].distanceLimit=7;}
  for(i=0;i<11;i++)expectedArgs[i]=0;expectedArgs[1]=selectedValue;expectedArgs[2]=(u16)volume;expectedArgs[6]=(u32)(s32)expected[index+2].x;expectedArgs[7]=(u32)(s32)expected[index+2].y;expectedArgs[8]=(u32)(s32)expected[index+2].z;expectedArgs[9]=(u32)(s32)(s16)want;expectedArgs[10]=(u32)limit;
  result=fn((s32)first,(s32)last,(u16)volume,index,distance);
  if(error||phase!=2||result!=(u16)handle||D_800D3098!=(mode?alternate+2:records+2))return 1;
  for(i=0;i<sizeof(records);i++)if(p[i]!=q[i])return 1;for(i=0;i<sizeof(alternate);i++)if(((u8*)alternate)[i]!=(u8)(i*7+3))return 1;
 }return 0;}
static int run(void){if(check(selected))return 10;
'''
 for i,name in enumerate(controls()):text+='if(!check('+name+'))return '+str(20+i)+';\n'
 return text+'return 0;}\n'+START

class RecordRangeSoundTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>48I',cls.rom,source.ROM));local=cls.fresh/'qualified-padded.o';local.write_bytes((cls.out/'qualified-padded.o').read_bytes());data,functions=source.link_owner(ROOT,cls.fresh,local,source.OWNER);cls.words=list(struct.unpack_from('>48I',data,functions[source.FUNCTION]['value']))
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def compare(self,c=Case(),images=None,entry=source.ENTRY,table=source.TABLE,random=source.RANDOM,sound=source.SOUND):
  initial=fixture(c,table);want,calls=reference(initial,c,table,random,sound);pair=[]
  for words in images or(self.truth,self.words):
   m=SoundOracle(words,initial,c,entry,table=table,random=random,sound=sound).run();self.assertEqual((public(m.memory),m.calls,m.r[2]),(public(want),calls,c.handle&65535),c);pair.append(m)
  self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);return pair[0]
 def link_object(self,obj,entry,table,random,sound,label):
  p=self.fresh/(label+'.ld');elf=p.with_suffix('.elf');p.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry);cmd=['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p),'-e',source.FUNCTION,'-o',str(elf),str(obj)];cmd+=['--defsym=%s=0x%X'%(n,v)for n,v in(('D_800D3098',table),('func_1000F568',random),('func_10010F88',sound))];subprocess.run(cmd,capture_output=True,check=True);raw=sections(elf)['.text'][1];return list(struct.unpack('>%dI'%(len(raw)//4),raw))
 def test_01_owner_Make_census_and_source_ABI(self):
  self.assertEqual(self.words,self.truth);source.checked_payload(*source.payload(self.out/'selected.o'))
  for label in('before','after'):
   obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),17)
  self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),16);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'))
  proposed=(self.out/'proposed-owner.c').read_text();self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()),proposed);self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3);self.assertNotIn('#pragma GLOBAL_ASM',proposed)
  ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertFalse(any(w==source.ENTRY for w in ws));self.assertEqual([i*4 for i,w in enumerate(ws)if w in(0x0C000000|(source.ENTRY>>2&0x3FFFFFF),0x08000000|(source.ENTRY>>2&0x3FFFFFF))],[0xCC5F0])
  self.assertIn('s32 func_1509EFF0() {\n    return 0;\n}',self.values[source.SOURCE].decode());self.assertIn('u16 func_10010F88(s32 arg0, u16 arg1, s16 arg2, u8 arg3, s32 arg4, s16 arg5, s16 arg6, s16 arg7, s16 arg8, s16 arg9)',self.values['conker/src/init_EB00.c'].decode())
  self.assertLess(source.SELECTED.index('selected = func_1000F568'),source.SELECTED.index('return func_10010F88'));self.assertIn('(u32)last - (u32)first + 1',source.SELECTED)
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(words=48,frame=56,bindings=4,guards=0,neighbors=16,compact_functions=17,GLOBAL_ASM_routines=0,Make_commands=3,diagnostics=0,arguments=5,canonical_u16_result=True,source_read_order_explicit=True,current_parent_unchanged_placeholder=True,direct_site='0x1509F140')
 def test_02_guest_unsigned_limits_live_fields_and_aliases(self):
  count=0;visits=set()
  for index,value,limit,mode,phase in itertools.product(range(5),VALUES,LIMITS,(0,1,2,4,7),(0,8)):
   args=list(Case().args);args[index]=value;m=self.compare(Case(tuple(args),limit,mode,phase=phase));visits.update(m.visits);count+=1
  for span,handle in itertools.product(range(256),(0,65535)):
   args=(0xFFFFFFFF,(0xFFFFFFFF+span-1)&0xFFFFFFFF,0xABCD0000|span,0,span);self.compare(Case(args,handle=handle));count+=1
  for alias,mode,phase in itertools.product(range(0,52,4),(0,7),(0,8)):self.compare(Case(alias=alias,mode=mode,phase=phase));count+=1
  for home,mode,phase in itertools.product((-40,-36,-32,-28,-24,0,4,8,16,32),(0,7),(0,8)):self.compare(Case(home=home,mode=mode,phase=phase));count+=1
  self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+192,4)));self.receipt['guest']=dict(cases=count,visited_words=48,all_five_argument_words=True,signed_limit_unsigned_comparison=True,all_byte_spans_including_zero_forwarding=True,thirteen_global_pointer_aliases=True,ten_stack_record_aliases=True,late_field_and_home_reads=True,complete_state_and_trace=True,selector_bounded_zero_span_is_not_real_selector_acceptance=True)
 def test_03_original_caller_return_and_retained_sound_wrapper(self):
  raw=self.rom[0x10F88:0x10FFC];self.assertEqual(len(raw),116);before=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(before,source.SOUND,116);self.assertEqual(before[at:at+116],raw);helper={source.SOUND+4*i:w for i,w in enumerate(struct.unpack('>29I',raw))};count=0;visited=set()
  for limit,mode,distance,phase in itertools.product(VALUES,(0,1),(0,0xFFFFFFFF),(0,8)):
   args=(*Case().args[:4],distance);c=Case(args,limit,mode,handle=limit&65535,phase=phase);initial=fixture(c);want,calls=reference(initial,c,chain=True);pair=[]
   for words in(self.truth,self.words):
    m=SoundOracle(words,initial,c,connected=helper).run();self.assertEqual((public(m.memory),m.calls,m.r[2]),(public(want),calls,c.handle));visited.update(m.visits);pair.append(m)
   self.assertEqual(complete(pair[0]),complete(pair[1]));count+=1
  self.assertTrue(set(helper)<=visited);caller={}
  for lo,hi in((0x1509F0B0,0x1509F0B8),(0x1509F128,0x1509F150),(0x1509F238,0x1509F248)):
   caller.update({lo+4*i:w for i,w in enumerate(struct.unpack_from('>%dI'%((hi-lo)//4),self.rom,lo-0x14FD2B50))})
  self.assertEqual(len(caller),16);cases=0
  for first,index,distance,mode,phase in itertools.product((0,0xFFFF,0x7FFFFFFF,0x80000000),(0,1,4095),(0,500,0xFFFFFFFF),(0,1),(0,8)):
   args=(first,(first+5)&4095,0xA5000000|(first&65535),index,distance);c=Case(args,mode=mode,handle=first&65535,phase=phase);initial=fixture(c);sp=STACK+phase;put(initial,sp+0x30,first);put(initial,PACKET+8,0xFEA00000|args[1]);put(initial,PACKET+16,args[2]);put(initial,PACKET+24,distance);want,calls=reference(initial,c);pair=[]
   for words in(self.truth,self.words):
    connected=dict(caller);connected.update({source.ENTRY+4*i:w for i,w in enumerate(words)});m=SoundOracle([caller[0x1509F0B0],caller[0x1509F0B4]],initial,c,entry=0x1509F0B0,connected=connected,arguments=(0,));m.r[1]=m.r[2]=0x4000;m.r[3]=0xA5004000|index;m.r[16]=PACKET;put(m.memory,sp+0x28,m.before[16]);put(m.memory,sp+0x2C,m.before[31]);m.before[29]=sp+48;m.run()
    self.assertEqual(m.target_entries,[args]);self.assertEqual(m.calls,[(source.ENTRY,args),*calls]);self.assertEqual(public(m.memory),public(want));self.assertEqual((m.r[2],m.r[29]),(c.handle,sp+48));pair.append(m)
   self.assertEqual(complete(pair[0]),complete(pair[1]));cases+=1
  self.receipt['caller']=dict(original_caller_words=16,original_windows=3,cases=cases,original_direct_sites=1,actual_argument_setup_and_final_return=True,retained_helper_words=29,helper_cases=count,all_helper_words_visited=True,current_parent_placeholder_preserved=True,random_selector_and_final_voice_provider_bounded=True,no_full_parent_or_gameplay_claim=True)
 def test_04_native32_mutation_order_and_effective_controls(self):
  for opt in('-O0','-O2','-O3'):
   p=self.fresh/('native-'+opt[1:]+'.c');p.write_text(native_harness(self.values));binary=p.with_suffix('');q=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);p.with_suffix('.diagnostics.txt').write_text(q.stdout+q.stderr);self.assertEqual(q.returncode,0,q.stdout+q.stderr);self.assertEqual(subprocess.run([str(binary)],timeout=60).returncode,0,opt)
  self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_each_profile=65536*5,effective_controls=len(controls()),trapping_UBSan=True,all_signed_halfword_limits_and_u16_results=True,actual_five_argument_function_pointer=True,actual_retained_sound_wrapper_C=True,whole_storage_fences=True,defined_unsigned_range_wrap=True,explicit_selector_before_live_coordinates=True,guest_stack_aliases_not_native_storage_claims=True)
 def test_05_fired_access_prefixes_and_late_read_boundary(self):
  cuts=0
  for limit,mode,home,phase in itertools.product((-1,0,500),(0,7),(None,-36),(0,8)):
   c=Case(limit=limit,mode=mode,home=home,phase=phase);initial=fixture(c);good=self.compare(c)
   for cut in range(good.root_accesses):
    pair=[]
    for words in(self.truth,self.words):
     m=SoundOracle(words,initial,c);m.root_fault=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     self.assertEqual(m.root_accesses,cut);pair.append(m)
    self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));cuts+=1
  for words in(self.truth,self.words):
   c=Case();m=SoundOracle(words,fixture(c),c);m.drop_table=True;m.run();self.assertEqual(m.r[2],c.handle)
  self.receipt['faults']=dict(fired_prefix_pairs=cuts,complete_state_trace_PC_delay=True,captured_pointer_and_limit_unmapped_after_selector=True)
 def test_06_real_padder_controls_and_GNU_relocations(self):
  raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'));bad=bytearray(raw);bad[124]^=1;wrong=dict(rs);wrong[28]=[('R_MIPS_LO16','wrong')]
  for b,bindings in((raw[:-4],rs),(bytes(bad),rs),(raw,wrong)):
   with self.assertRaises(ValueError):source.checked_payload(b,bindings)
  p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=ROOT/'conker/retail_word_patches.us.csv',filename=source.OWNER));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes());cases=0
  for j,(entry,table,random,sound)in enumerate(((source.ENTRY,source.TABLE,source.RANDOM,source.SOUND),(0x17007FFC,0x81018004,0x17012000,0x17012800),(0x2500FFFC,0x8200FFF0,0x25030004,0x25040004))):
   images=[self.link_object(p,entry,table,random,sound,'layout-%d-%d'%(j,k))[:48]for k,p in enumerate((self.out/('original-'+source.FUNCTION+'.o'),self.out/'selected.o'))];self.assertEqual(*images)
   for mode,home,distance in itertools.product((0,7),(None,4),(0,0xFFFFFFFF)):
    c=Case((*Case().args[:4],distance),mode=mode,home=home);self.compare(c,images,entry,table,random,sound);cases+=1
  self.receipt['rebases']=dict(layouts=3,guest_cases=cases,HI_LO_carry_and_two_J26_bindings=True,original_and_compiler_objects=True,raw_binding_controls=3,guards=0)
 def test_07_actually_compiled_semantic_controls(self):
  b=controls();cases=(('early_x',Case(mode=1)),('signed_compare',Case(limit=-1)),('strict_greater',Case((*Case().args[:4],500))),('late_limit',Case(mode=1)))
  for name,c in cases:
   body=b[name];obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+body,'negative-'+name);self.assertFalse(diag);words=self.link_object(obj,source.ENTRY,source.TABLE,source.RANDOM,source.SOUND,'negative-'+name);initial=fixture(c);want,calls=reference(initial,c);m=SoundOracle(words,initial,c).run();self.assertNotEqual(m.calls,calls,name)
  self.receipt['compiled_control']=dict(actually_compiled_IDO_negatives=4,captured_coordinates_unsigned_comparison_equality_and_cached_limit=True,semantic_value_failures=True)
 def test_08_strict_entire_image_extent_and_corruptions(self):
  v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=v['conker/conker.us.bin'][source.ROM:source.ROM+192];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,192);symbol=next(p for p,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8
  for offset in(20,at,at+180,at+192,source.elf_slot_offset(before,0x80082B20,4),symbol):
   bad=bytearray(expected);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  count=sum(x!=y for x,y in zip(before,expected));self.assertEqual(count,149);self.receipt['image']=dict(changed_bytes=count,code_bytes=148,size_bytes=1,other6055_bodies_and6056_addresses_fixed=True,all_named_definitions_checked=True,protected_owners=720,protected_bytes=189088,exclusions=0,effective_corruptions=6,shared_headers_helpers_current_parent_and_guards_unchanged=True)
