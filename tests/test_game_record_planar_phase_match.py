"""Planar phase offsets: sequenced guarded C, all original callers and strict whole image."""
from dataclasses import replace
from pathlib import Path
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_record_planar_phase_match as source
from tools.tests import game_record_planar_phase_oracle as oracle
from tools.tests.game_record_planar_phase_oracle import Case,fixture,reference,public,PhaseOracle,SYMBOLS,RECORD,AMP,PHASE,RATE,ALT,ALT_AMP,ALT_PHASE,ALT_RATE,TRIG_TABLE,STACK,put,read,faults
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
ROOT=Path(__file__).resolve().parents[2]

from tools.tests.test_game_row_destination_fill import START

def controls():
 b=source.SELECTED
 out=dict(wrong_x_amp=b.replace('amplitudes[0]','amplitudes[1]'),wrong_z_amp=b.replace('amplitudes[1]','amplitudes[0]'),missing_phase0=b.replace('    phases[0] += rates[0] * (u32)D_800BE9E4;',''),missing_phase1=b.replace('    phases[1] += rates[1] * (u32)D_800BE9E4;',''),wrong_rate=b.replace('rates[1]','rates[0]'),wrong_angle=b.replace('- 0x40','- 0x3F'),early_ticks=b.replace('    f32 sample;', '    f32 sample;\n    u32 ticks = (u32)D_800BE9E4;').replace('rates[0] * (u32)D_800BE9E4','rates[0] * ticks').replace('rates[1] * (u32)D_800BE9E4','rates[1] * ticks'))
 assert all(v!=b for v in out.values());return out

def native_harness():
 t=source.HEADERS+source.DECLARATIONS+"typedef char ABI[(sizeof(void*)==4&&sizeof(f32)==4&&sizeof(u8)==1)?1:-1];\ntypedef struct {u8 prefix[76];f32 x;u32 middle;f32 z;u8 suffix[168];} Record;\ntypedef char Layout[(__builtin_offsetof(Record,x)==76&&__builtin_offsetof(Record,z)==84&&sizeof(Record)==256)?1:-1];\nstatic Record record,expected;\nstatic f32 amplitudes[2],expectedAmp[2];\nstatic u8 phases[2],expectedPhase[2],rates[2],expectedRate[2],wantedAngles[2];\nstatic s32 expectedTicks;\ns32 D_800BE9E4;\nstatic u32 mode,seed,callCount,error;\nstatic void bytes(void*d,const void*s,u32 n){u32 i;for(i=0;i<n;i++)((u8*)d)[i]=((const u8*)s)[i];}\nstatic int same(const void*a,const void*b,u32 n){u32 i;for(i=0;i<n;i++)if(((const u8*)a)[i]!=((const u8*)b)[i])return 0;return 1;}\nstatic f32 value(u8 angle){return ((s32)angle-128)*0.03125f;}\nstatic void effect(u32 ordinal,f32*a,u8*p,u8*r,s32*t){\n if(ordinal==0&&(mode&1)){a[0]=-7.5f;p[1]=0x91;}\n if(ordinal==1&&(mode&4)){a[1]=11.5f;*t=(s32)0x87654321u;r[0]=0xA7;p[1]=0xF3;}\n}\nf32 func_151423D8(u8 angle){\n if(callCount>=2||angle!=wantedAngles[callCount])error=1;\n effect(callCount,amplitudes,phases,rates,&D_800BE9E4);callCount++;\n return value(angle);\n}\n"
 for name,b in dict(selected=source.SELECTED,**controls()).items():t+=b.replace(source.FUNCTION,name)+"\n"
 t+="typedef void(*Update)(u8*,f32*,u8*,u8*);\nstatic const u32 tickCases[]={0,1,7,0x7FFFFFFFu,0x80000000u,0xFFFFFFFFu};\nstatic int check(Update fn){u32 i,j,k;f32 v;\n for(seed=0;seed<256;seed++)for(j=0;j<6;j++)for(k=0;k<4;k++){\n  mode=(k&1)|((k&2)<<1);\n  for(i=0;i<sizeof(record);i++)((u8*)&record)[i]=(u8)(seed+i*13);\n  bytes(&expected,&record,sizeof(record));\n  amplitudes[0]=expectedAmp[0]=(f32)((s32)seed-127)*0.25f;\n  amplitudes[1]=expectedAmp[1]=(f32)((s32)seed-111)*-0.125f;\n  phases[0]=expectedPhase[0]=(u8)seed;phases[1]=expectedPhase[1]=(u8)(seed*17+3);\n  rates[0]=expectedRate[0]=(u8)(seed*7+1);rates[1]=expectedRate[1]=(u8)(seed*11+3);\n  D_800BE9E4=expectedTicks=(s32)tickCases[j];\n  wantedAngles[0]=(u8)(expectedPhase[0]-64);v=value(wantedAngles[0]);effect(0,expectedAmp,expectedPhase,expectedRate,&expectedTicks);expected.x=v*expectedAmp[0];\n  wantedAngles[1]=(u8)(expectedPhase[1]-64);v=value(wantedAngles[1]);effect(1,expectedAmp,expectedPhase,expectedRate,&expectedTicks);expected.z=v*expectedAmp[1];\n  expectedPhase[0]=(u8)(expectedPhase[0]+expectedRate[0]*(u32)expectedTicks);\n  expectedPhase[1]=(u8)(expectedPhase[1]+expectedRate[1]*(u32)expectedTicks);\n  callCount=error=0;fn((u8*)&record,amplitudes,phases,rates);\n  if(error||callCount!=2||!same(&record,&expected,sizeof(record))||!same(amplitudes,expectedAmp,sizeof(amplitudes))||!same(phases,expectedPhase,2)||!same(rates,expectedRate,2)||D_800BE9E4!=expectedTicks)return 1;\n }return 0;\n}\n"
 t+="static int run(void){if(check(selected))return 10;\n"
 for i,name in enumerate(controls()):t+="if(!check("+name+"))return "+str(i+20)+";\n"
 return t+"return 0;}\n"+START

class RecordPlanarPhaseTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>48I',cls.rom,source.ROM));local=cls.fresh/'qualified-padded.o';local.write_bytes((cls.out/'qualified-padded.o').read_bytes());data,functions=source.link_owner(ROOT,cls.fresh,local,source.OWNER);cls.words=list(struct.unpack_from('>48I',data,functions[source.FUNCTION]['value']))
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def compare(self,c=Case(),images=None,entry=source.ENTRY,symbols=SYMBOLS):
  initial=fixture(c,symbols);memory,calls=reference(initial,c,symbols);pair=[]
  for words in images or(self.truth,self.words):
   m=PhaseOracle(words,initial,c,symbols,entry).run();self.assertEqual((public(m.memory),m.calls),(public(memory),calls),c);pair.append(m)
  self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);return pair[0]
 def rebased(self,obj,entry,symbols,label):
  text,functions,bindings=parse_object(obj);assembly,unknown=emit_function(text,functions[source.FUNCTION],bindings,source.FUNCTION,symbols);self.assertFalse(unknown);p=self.fresh/label;p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
  subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
  subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,*['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
  return list(struct.unpack('>%dI'%(len(sections(p.with_suffix('.elf'))['.text'][1])//4),sections(p.with_suffix('.elf'))['.text'][1]))

 def test_01_owner_Make_census_and_source_ABI(self):
  self.assertEqual(self.words,self.truth);source.checked_payload(*source.payload(self.out/'selected.o'))
  for label in('before','after'):
   obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertEqual(source.check_owner_diagnostics(diag),0);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),31)
  self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),30);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'))
  proposed=(self.out/'proposed-owner.c').read_text();self.assertEqual(proposed,source.recovered_owner(self.values[source.SOURCE].decode()));self.assertEqual(proposed.count('#pragma GLOBAL_ASM'),2);self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),5)
  ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertFalse(any(w==source.ENTRY for w in ws));self.assertEqual([4*i for i,w in enumerate(ws)if w in(0x0C000000|(source.ENTRY>>2&0x3FFFFFF),0x08000000|(source.ENTRY>>2&0x3FFFFFF))],[0xDCBB8,0x107AFC,0x115CE8,0x2021D8])
  for name in('DC6B0','105FC0','113D60','200930'):
   for path in('conker/src/game/generated_'+name+'.c','conker/build/src/game/generated_'+name+'.c.o'):
    self.assertEqual((ROOT/path).read_bytes(),self.values[path])
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(words=48,frame=24,bindings=4,guards=2,neighbors=30,compact_functions=31,GLOBAL_ASM_routines=2,Make_commands=5,diagnostics=0,arguments=4,void_return=True,legacy_caller_return_declarations_ignored=True,current_callers_unchanged=True)
 def test_02_guest_phase_bytes_live_ticks_and_aliases(self):
  count=0;visits=set();aliases=0
  for angle,rates,ticks,mode,phase in itertools.product((0,63,64,127,128,191,192,255),((0,0),(1,255),(128,17)),(0,1,7,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(0,1,2,4,8,15),(0,8)):
   c=Case(angles=(angle,(angle*17+3)&255),rates=rates,ticks=ticks,mode=mode,phase=phase);m=self.compare(c);visits.update(m.visits);count+=1
  for byte in range(256):
   for field in('angle0','angle1','rate0','rate1'):
    c=Case(angles=(byte,201)if field=='angle0'else(17,byte)if field=='angle1'else(17,201),rates=(byte,241)if field=='rate0'else(3,byte)if field=='rate1'else(3,241));self.compare(c);count+=1
  for phases in(source.TICKS,source.TICKS+1,source.TICKS+2,source.TICKS+3,RECORD+76,RECORD+83,RATE-1,RATE,RATE+1):
   self.compare(Case(phases=phases,ticks=0x12345678));count+=1;aliases+=1
  for amp in(RECORD+76,RECORD+80,RECORD+84,source.TICKS):self.compare(Case(amp=amp));count+=1;aliases+=1
  for phase in(0,8):
   for offset in(-24,-16,0,8,24,32):
    self.compare(Case(phases=STACK+phase+offset,phase=phase));count+=1;aliases+=1
  self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+192,4)));self.receipt['guest']=dict(cases=count,visited_words=48,guest_aliases=aliases,all_phase_and_rate_bytes=True,wrapped_tick_products=True,late_pointer_and_tick_reads=True,complete_state_trace=True,second_phase_loaded_before_first_store=True,trig_provider_bounded=True,portable_alias_NaN_or_FCSR_claim=False)
 def helpers(self):
  connected={};elf=self.values['conker/build/conker.us.elf']
  for va,rom,words in((source.TRIG,0x16F888,27),(source.DAMP,0x15EE08,19)):
   body=list(struct.unpack_from('>%dI'%words,self.rom,rom));at=source.elf_slot_offset(elf,va,4*words);self.assertEqual(list(struct.unpack_from('>%dI'%words,elf,at)),body);connected.update({va+4*i:w for i,w in enumerate(body)})
  return connected
 def table(self,m):
  elf=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(elf,TRIG_TABLE,260);m.update({TRIG_TABLE+i:b for i,b in enumerate(elf[at:at+260])});return m
 def test_03_all_original_callers_and_retained_helpers(self):
  helpers=self.helpers();seen=set();cases=0
  for angle,phase in itertools.product(range(256),(0,8)):
   c=Case(angles=(angle,(angle*17+3)&255),phase=phase);initial=self.table(fixture(c));wanted=oracle.actual_reference(initial,c);pair=[PhaseOracle(w,initial,c,connected=helpers).run()for w in(self.truth,self.words)];self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(public(pair[0].memory),public(wanted));seen.update(pair[0].visits);cases+=1
  counts=[];visited=[]
  for parent,rom,words,owner in((0x150AF6E4,0xDCB94,21,'DC6B0'),(0x150DA628,0x107AD8,21,'105FC0'),(0x150E8824,0x115CD4,12,'113D60'),(0x151D4D04,0x2021B4,21,'200930')):
   original=list(struct.unpack_from('>%dI'%words,self.rom,rom));elf=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(elf,parent,words*4);self.assertEqual(list(struct.unpack_from('>%dI'%words,elf,at)),original);parent_seen=set();pcases=0
   for angle,ticks,phase in itertools.product((0,63,64,127,128,191,192,255),(0,1,3,7,0xFFFFFFFF,0x80000000),(0,8)):
    c=Case(record=RECORD,amp=RECORD+0xAC,phases=RECORD+0xA8,rate=RECORD+0xAA,angles=(angle,(angle*17+3)&255),ticks=ticks,phase=phase);initial=self.table(fixture(c));wanted=oracle.actual_reference(initial,c)
    if words==21:
     for _ in range(max(0,signed(ticks))):
      for i in range(3):put(wanted,RECORD+0x58+4*i,oracle.mul(read(wanted,RECORD+0x58+4*i),read(wanted,RECORD+0xB4)))
    pair=[PhaseOracle(original,initial,c,entry=parent,arguments=(RECORD,0xABCDEF91),connected=helpers|{source.ENTRY+4*i:v for i,v in enumerate(w)}).run()for w in(self.truth,self.words)];m=pair[0];self.assertEqual(complete(m),complete(pair[1]));self.assertEqual(public(m.memory),public(wanted));self.assertEqual(m.r[2],1);self.assertEqual(m.target_entries,[(RECORD,RECORD+0xAC,RECORD+0xA8,RECORD+0xAA)]);self.assertEqual(len(m.calls),4 if words==21 else 3)
    if words==21:self.assertEqual(m.calls[-1],(source.DAMP,(RECORD+0x58,read(initial,RECORD+0xB4))))
    parent_seen.update(m.visits);seen.update(m.visits);pcases+=1
   self.assertTrue(set(range(parent,parent+words*4,4))<=parent_seen);counts.append(pcases);visited.append(words)
  self.assertEqual(len(seen&set(helpers)),46);self.receipt['caller']=dict(helper_cases=cases,original_caller_cases=counts,original_caller_words=[21,21,12,21],visited_caller_words=visited,retained_helper_words=46,visited_helper_words=46,current_caller_bytes_equal_retail=True,actual_four_argument_call_and_ignored_return=True,actual_raw_float_damping_argument=True,retained_trig_table=True,all_original_returns_executed=True,hardware_or_gameplay_claim=False)
 def test_04_native32_four_argument_ABI_and_controls(self):
  unit=self.fresh/'native.c';unit.write_text(native_harness())
  for opt in('O0','O2','O3'):
   exe=self.fresh/('native-'+opt);p=subprocess.run([*native_command('-'+opt,True),'-mstackrealign',str(unit),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stderr);p=subprocess.run([str(exe)],capture_output=True,timeout=60);self.assertEqual(p.returncode,0,(opt,p.stderr))
  self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_each_profile=6144,effective_controls=len(controls()),trapping_UBSan=True,actual_four_argument_void_function_pointer=True,all_phase_rate_bytes=True,unsigned_product_wrap=True,complete_record_and_inputs_checked=True,trig_provider_bounded=True)
 def test_05_fired_access_prefixes(self):
  cuts=0
  for mode,phase in itertools.product((0,1,2,4,8,15),(0,8)):
   c=Case(mode=mode,phase=phase);initial=fixture(c);good=self.compare(c)
   for cut in range(good.root_accesses):
    pair=[]
    for w in(self.truth,self.words):
     m=PhaseOracle(w,initial,c);m.root_fault=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     self.assertEqual(m.root_accesses,cut);pair.append(m)
    self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));cuts+=1
  self.receipt['faults']=dict(fired_prefix_pairs=cuts,complete_state_trace_PC_delay=True,guest_instruction_boundaries_only=True)
 def test_06_real_padder_controls_and_GNU_relocations(self):
  raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'));bad=bytearray(raw);bad[124]^=1;wrong=dict(rs);wrong[108]=[('R_MIPS_HI16','wrong')]
  for b,bindings in((raw[:-4],rs),(bytes(bad),rs),(raw,wrong)):
   with self.assertRaises(ValueError):source.checked_payload(b,bindings)
  self.assertEqual(source.normalized_payload(raw,rs),source.payload(self.out/('original-'+source.FUNCTION+'.o')))
  self.assertEqual((self.out/'proposed-word-patches.csv').read_bytes(),source.guard_manifest(self.values['conker/retail_word_patches.us.csv']))
  for row in source.NEW_GUARDS:
   at=int(row['offset'],0);self.assertFalse(rs.get(at));original=int(row['expected'],0);changed=int(row['replacement'],0)
   self.assertEqual((original&~((31<<11)|(31<<16))),(changed&~((31<<11)|(31<<16))))
   self.assertEqual(((original>>11)&31,(original>>16)&31),((changed>>16)&31,(changed>>11)&31))
   # The production padder must reject changed expected words and new bindings.
   for variant in ('word','binding'):
    altered=[dict(v)for v in source.NEW_GUARDS];target=next(v for v in altered if v['offset']==row['offset'])
    target['expected' if variant=='word' else 'expected_relocations']='0x00000000'if variant=='word'else'R_MIPS_26:func_151423D8'
    import csv,io
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,list(altered[0]),lineterminator='\n');writer.writeheader();writer.writerows(altered);manifest=self.fresh/('bad-'+str(at)+'-'+variant+'.csv');manifest.write_text(stream.getvalue())
    with self.assertRaises(ValueError):source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=manifest,filename=source.OWNER)
  p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=self.out/'proposed-word-patches.csv',filename=source.OWNER));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes());count=0
  for j,entry in enumerate((source.ENTRY,0x17007FFC,0x2500FFFC)):
   symbols=SYMBOLS if j==0 else dict(func_151423D8=entry+0x10004,D_800BE9E4=0x800D8004 if j==1 else 0x80107FFC)
   images=[self.rebased(p,entry,symbols,'rebase-%d-%d'%(j,k))[:48]for k,p in enumerate((self.out/('original-'+source.FUNCTION+'.o'),self.out/'qualified-padded.o',self.out/'make-shadow/src/game/generated_15D730.c.o'))];self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
   for mode,phase in itertools.product((0,1,2,4,8,15),(0,8)):self.compare(Case(mode=mode,phase=phase),images[:2],entry,symbols);count+=1
  self.receipt['rebases']=dict(layouts=3,guest_cases=count,J26_and_HILO_relocations=True,original_compiler_and_actual_Make=True,raw_binding_controls=3,padder_guard_controls=4,guards=2)
 def test_07_actually_compiled_semantic_controls(self):
  for name in('wrong_x_amp','wrong_z_amp','wrong_angle','missing_phase0','early_ticks'):
   obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+controls()[name],'negative-'+name);self.assertFalse(diag);words=self.rebased(obj,source.ENTRY,SYMBOLS,'negative-link-'+name);c=Case(mode=4);initial=fixture(c);expected,calls=reference(initial,c);m=PhaseOracle(words,initial,c).run();self.assertNotEqual((public(m.memory),m.calls),(public(expected),calls),name)
  self.receipt['compiled_control']=dict(actually_compiled_IDO_negatives=5,semantic_value_failures=True)
 def test_08_strict_entire_image_extent_and_corruptions(self):
  v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=v['conker/conker.us.bin'][source.ROM:source.ROM+192];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,192);symbol=next(p for p,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8
  for offset in(20,at,at+180,at+192,source.elf_slot_offset(before,TRIG_TABLE,4),symbol):
   bad=bytearray(expected);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  count=sum(x!=y for x,y in zip(before,expected));self.assertEqual(count,149);self.receipt['image']=dict(changed_bytes=count,code_bytes=148,size_bytes=1,other6055_bodies_and6056_addresses_fixed=True,all_named_definitions_checked=True,protected_owners=720,protected_bytes=189088,exclusions=0,effective_corruptions=6,shared_headers_helpers_current_callers_unchanged=True,inherited_guards_unchanged=True,new_guards=2)
