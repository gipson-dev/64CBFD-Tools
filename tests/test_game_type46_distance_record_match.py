"""Type46 distance record: guarded C, actual caller/helpers and strict complete image."""
from dataclasses import replace
from pathlib import Path
import csv,io,itertools,json,math,os,struct,subprocess,unittest
from tools.experiments import game_type46_distance_record_match as source
from tools.tests import game_type46_distance_record_oracle as oracle
from tools.tests.game_type46_distance_record_oracle import Case,fixture,reference,public,DistanceOracle,SYMBOLS,POINTS,RECORD,ALT,INPUT,ACTOR,HEAD,LIST,STACK,put,read,faults
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
ROOT=Path(__file__).resolve().parents[2]
def controls():
 b=source.SELECTED
 out=dict(wrong_size=b.replace('extraBytes + 0xC8u','extraBytes + 0xC4u'),short_copy=b.replace('payload, 0x24','payload, 0x20'),reversed_x=b.replace('record->payload.first[0] - record->payload.second[0]','record->payload.second[0] - record->payload.first[0]'),missing_state=b.replace('    record->state = 0;',''))
 assert all(v!=b for v in out.values());return out

def native_harness():
 t=source.HEADERS+source.DECLARATIONS+"typedef char ABI[(sizeof(void*)==4&&sizeof(Type46DistancePayload)==36&&sizeof(Type46DistanceRecord)==200&&__builtin_offsetof(Type46DistanceRecord,payload)==24&&__builtin_offsetof(Type46DistanceRecord,distance)==192)?1:-1];\nstatic Type46DistanceRecord actual,expected;\nstatic Type46DistancePayload input;\nstatic u32 extra,fail,mutateInput,mutateLength,seed,phase,error;\nstatic f32 wantedDelta[3],lengthValue;\nstatic void bytes(void*d,const void*s,u32 n){u32 i;for(i=0;i<n;i++)((u8*)d)[i]=((const u8*)s)[i];}\nvoid *func_15167A68(s32 a,s32 b,s32 c,s32 d,u8 e,u8 f){\n if(phase++!=0||a!=70||b!=0||(u32)c!=extra+200u||d!=1||e!=255||f!=1)error=1;\n if(mutateInput){input.first[0]+=9.0f;input.attributes[11]=(u8)(seed^255);}\n return fail?NULL:&actual;\n}\nvoid *memcpy(void*d,const void*s,size_t n){\n if(phase++!=1||d!=&actual.payload||s!=&input||n!=36)error=1;\n bytes(d,s,n);bytes(&expected.payload,&input,36);\n wantedDelta[0]=input.first[0]-input.second[0];wantedDelta[1]=input.first[1]-input.second[1];wantedDelta[2]=input.first[2]-input.second[2];return d;\n}\nf32 func_15143E64(f32*p){u32 i;\n if(phase++!=2||actual.active!=expected.active||actual.state!=expected.state)error=1;\n for(i=0;i<3;i++)if(p[i]!=wantedDelta[i])error=1;\n if(mutateLength){actual.payload.attributes[0]=expected.payload.attributes[0]=0xA7;actual.payload.first[2]=expected.payload.first[2]=3.5f;}\n return lengthValue;\n}\n/* Create a type-0x46 record and cache the distance between its first two points. */\n"
 for name,b in dict(selected=source.SELECTED,**controls()).items():t+=b.replace(source.FUNCTION,name)+'\n'
 return t+"typedef Type46DistanceRecord*(*Create)(const Type46DistancePayload*,u32);\nstatic const u32 sizes[]={0,1,0x7FFFFFFFu,0x80000000u,0xFFFFFF37u,0xFFFFFF38u,0xFFFFFF39u,0xFFFFFFFFu};\nstatic int check(Create fn){u32 i,n;Type46DistanceRecord*result;\n for(seed=0;seed<256;seed++)for(n=0;n<8;n++)for(fail=0;fail<2;fail++)for(mutateInput=0;mutateInput<2;mutateInput++)for(mutateLength=0;mutateLength<2;mutateLength++){\n  for(i=0;i<sizeof(actual);i++)((u8*)&actual)[i]=((u8*)&expected)[i]=(u8)(i*17+seed);\n  for(i=0;i<3;i++){input.first[i]=(f32)((s32)seed-128)*0.25f+(f32)i;input.second[i]=(f32)(seed&63)*0.5f-(f32)i;}\n  for(i=0;i<12;i++)input.attributes[i]=(u8)(seed+i*13);extra=sizes[n];lengthValue=(f32)seed+0.5f;phase=error=0;\n  result=fn(&input,extra);\n  if(error||phase!=(fail?1:3)||result!=(fail?NULL:&actual))return 1;\n  if(!fail){expected.distance=lengthValue;expected.active=1;expected.state=0;}\n  for(i=0;i<sizeof(actual);i++)if(((u8*)&actual)[i]!=((u8*)&expected)[i])return 1;\n }return 0;\n}\nstatic int run(void){if(check(selected))return 10;\nif(!check(wrong_size))return 20;\nif(!check(short_copy))return 21;\nif(!check(reversed_x))return 22;\nif(!check(missing_state))return 23;\nreturn 0;}\n\nvoid _start(void) {\n    int result = run();\n    __asm__ volatile(\".byte 0xcd,0x80\" : : \"a\"(1), \"b\"(result) : \"memory\");\n    __builtin_unreachable();\n}\n"

class Type46DistanceRecordTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>48I',cls.rom,source.ROM));local=cls.fresh/'qualified-padded.o';local.write_bytes((cls.out/'qualified-padded.o').read_bytes());data,functions=source.link_owner(ROOT,cls.fresh,local,source.OWNER);cls.words=list(struct.unpack_from('>48I',data,functions[source.FUNCTION]['value']))
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def compare(self,c=Case(),images=None,entry=source.ENTRY,symbols=SYMBOLS):
  initial=fixture(c);memory,result,calls,deltas=reference(initial,c,symbols);pair=[]
  for words in images or(self.truth,self.words):
   m=DistanceOracle(words,initial,c,symbols,entry).run();self.assertEqual((public(m.memory),m.r[2],m.calls,m.deltas),(public(memory),result,calls,deltas),c);pair.append(m)
  self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);return pair[0]
 def rebased(self,obj,entry,symbols,label):
  text,functions,bindings=parse_object(obj);assembly,unknown=emit_function(text,functions[source.FUNCTION],bindings,source.FUNCTION,symbols);self.assertFalse(unknown);p=self.fresh/label;p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
  subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
  subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,*['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
  return list(struct.unpack('>%dI'%(len(sections(p.with_suffix('.elf'))['.text'][1])//4),sections(p.with_suffix('.elf'))['.text'][1]))
 def test_01_owner_Make_census_and_source_ABI(self):
  self.assertEqual(self.words,self.truth);self.assertEqual(source.normalized_payload(*source.payload(self.out/'selected.o')),source.payload(self.out/('original-'+source.FUNCTION+'.o')))
  for label in('before','after'):
   obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),15)
  self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),14);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'))
  proposed=(self.out/'proposed-owner.c').read_text();self.assertEqual(proposed,source.recovered_owner(self.values[source.SOURCE].decode()));self.assertEqual(proposed.count('#pragma GLOBAL_ASM'),0);self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3)
  ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertFalse(any(w==source.ENTRY for w in ws));self.assertEqual([4*i for i,w in enumerate(ws)if w in(0x0C000000|(source.ENTRY>>2&0x3FFFFFF),0x08000000|(source.ENTRY>>2&0x3FFFFFF))],[0x17AAB4]);self.assertIn('s32 func_1514D564() {\n    return 0;\n}',self.values[source.CALLER_SOURCE].decode())
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(words=48,compiler_words=47,frame=48,bindings=3,guards=8,inserted_return_move=1,neighbors=14,compact_functions=15,Make_commands=3,diagnostics=0,arguments=2,payload_bytes=36,opaque_attributes=12,record_bytes=200,current_parent_unchanged_placeholder=True,direct_site='0x1514D604')
 def test_02_guest_raw_and_normalized_order_aliases(self):
  raw=self.rebased(self.out/'selected.o',source.ENTRY,SYMBOLS,'raw-semantic')[:47];count=0;visits=set()
  def one(c):
   nonlocal count
   good=self.compare(c);m=DistanceOracle(raw,fixture(c),c).run();self.assertEqual((m.memory,m.r[2],m.calls,m.deltas),(good.memory,good.r[2],good.calls,good.deltas));visits.update(good.visits);count+=1
  for extra,allocated,mode,point,phase in itertools.product((0,1,0x7FFFFFFF,0x80000000,0xFFFFFF37,0xFFFFFF38,0xFFFFFF39,0xFFFFFFFF),(False,True),(0,1,2,4,8,16,32,63),POINTS,(0,8)):one(Case(extra,allocated,mode,point,phase=phase))
  aliases=0
  for offset,phase in itertools.product((0,20,24,28,36,48),(0,8)):one(Case(payload=RECORD+offset,phase=phase));aliases+=1
  for address,phase in itertools.product((STACK+64,STACK-80),(0,8)):one(Case(payload=address+phase,phase=phase));aliases+=1
  for address in(STACK+128,STACK-320):one(Case(record=address));aliases+=1
  self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+192,4)));self.receipt['guest']=dict(cases=count,visited_words=48,guest_aliases=aliases,unsigned_size_wrap=True,provider_home_and_saved_pointer_mutations=True,raw_C_memory_return_and_calls_equal=True,normalized_complete_state_and_trace=True,opaque_helpers=True,portable_overlap_or_NaN_FCSR_claim=False)
 def helpers(self):
  connected={};elf=self.values['conker/build/conker.us.elf']
  for va,rom,words in((source.FACTORY,0x194F18,28),(source.INITIALIZER,0x195EFC,20),(source.COPY,0x22EC0,11),(source.LENGTH,0x171314,12)):
   body=list(struct.unpack_from('>%dI'%words,self.rom,rom));at=source.elf_slot_offset(elf,va,words*4);self.assertEqual(list(struct.unpack_from('>%dI'%words,elf,at)),body);connected.update({va+i*4:w for i,w in enumerate(body)})
  return connected
 def test_03_retained_helpers_and_complete_original_caller(self):
  helpers=self.helpers();seen=set();cases=0;raw=self.rebased(self.out/'selected.o',source.ENTRY,SYMBOLS,'raw-connected')[:47]
  for allocated,oldhead,phase,point in itertools.product((False,True),(0,HEAD),(0,8),POINTS[:3]):
   c=Case(allocated=allocated,oldhead=oldhead,phase=phase,point=point);initial=fixture(c);models=[DistanceOracle(w,initial,c,connected=helpers).run()for w in(self.truth,self.words,raw)]
   self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual((models[0].memory,models[0].r[2],models[0].calls,models[0].deltas),(models[2].memory,models[2].r[2],models[2].calls,models[2].deltas));m=models[0];seen.update(m.visits)
   self.assertEqual(m.r[2],RECORD if allocated else 0);self.assertEqual(m.calls[:2],[(source.FACTORY,(70,0,220,1,255,1)),(source.HEAP,(220,1,1,0,1))])
   expected=dict(initial)
   if allocated:
    expected[RECORD]=70;expected[RECORD+1]=0;expected[RECORD+12]=255;put(expected,RECORD+4,0);put(expected,RECORD+8,oldhead);put(expected,LIST,RECORD)
    if oldhead:put(expected,oldhead+4,RECORD)
    oracle.copy_bytes(expected,RECORD+24,c.payload,36);delta=[bits(floating(point[i])-floating(point[i+3]))for i in range(3)];squares=[bits(floating(d)*floating(d))for d in delta];length=bits(math.sqrt(floating(bits(floating(bits(floating(squares[0])+floating(squares[1])))+floating(squares[2])))))
    put(expected,RECORD+192,length);put(expected,RECORD+16,1);put(expected,RECORD+20,0);self.assertEqual(m.calls[2:],[(source.INITIALIZER,(RECORD,70)),(source.COPY,(RECORD+24,c.payload,36)),(source.LENGTH,(STACK+phase-16,))]);self.assertEqual(m.deltas,[tuple(delta)])
   self.assertEqual(public(m.memory),public(expected));cases+=1
  helper_visits=len(set(helpers)&seen);self.assertEqual(helper_visits,71)
  parent=list(struct.unpack_from('>58I',self.rom,0x17AA14));elf=self.values['conker/build/conker.us.elf'];constant_at=source.elf_slot_offset(elf,0x800A5DE4,16);constants=elf[constant_at:constant_at+16];parent_seen=set();parent_cases=0
  for allocated,oldhead,phase,point in itertools.product((False,True),(0,HEAD),(0,8),POINTS[:3]):
   c=Case(allocated=allocated,oldhead=oldhead,phase=phase,point=point);initial=fixture(c);initial.update({0x800A5DE4+i:b for i,b in enumerate(constants)});models=[]
   for w in(self.truth,self.words,raw):
    connected=dict(helpers);connected.update({source.ENTRY+4*i:v for i,v in enumerate(w)});models.append(DistanceOracle(parent,initial,c,entry=source.PARENT,connected=connected,arguments=(ACTOR,)).run())
   m=models[0];self.assertEqual(complete(m),complete(models[1]));self.assertEqual((public(m.memory),m.r[2],m.calls,m.deltas),(public(models[2].memory),models[2].r[2],models[2].calls,models[2].deltas));parent_seen.update(m.visits);sp=STACK+phase-88;self.assertEqual(m.target_entries,[(sp+52,20)])
   self.assertEqual(m.calls[:3],[(source.ENTRY,(sp+52,20)),(source.FACTORY,(70,0,220,1,255,1)),(source.HEAP,(220,1,1,0,1))])
   if allocated:
    self.assertEqual(m.calls[-2:],[(source.COPY,(RECORD+200,sp+28,20)),(source.FINAL,(RECORD,ACTOR,21))]);self.assertEqual(m.r[2],0xC0DEC0DE)
    payload=bytearray(initial[sp+52+i]for i in range(36));payload[:12]=constants[:12];payload[12:24]=b''.join(struct.pack('>I',v)for v in point[:3]);payload[24]=1;payload[28:32]=constants[12:];payload[32]=1
    extension=bytearray(initial[sp+28+i]for i in range(20));struct.pack_into('>I',extension,0,ACTOR);extension[4]=0xA7;extension[5]=6;struct.pack_into('>3I',extension,8,0,0xC3340000,0x429A0000)
    self.assertEqual(m.copy_packets,[bytes(payload),bytes(extension)]);self.assertEqual(bytes(m.memory[RECORD+24+i]for i in range(36)),bytes(payload));self.assertEqual(bytes(m.memory[RECORD+200+i]for i in range(20)),bytes(extension))
   else:self.assertEqual(m.r[2],0);self.assertEqual(len(m.calls),3)
   parent_cases+=1
  self.assertEqual(len(parent_seen&set(range(source.PARENT,source.PARENT+232,4))),58)
  for n in(source.CALLER_SOURCE,source.CALLER_OBJECT):self.assertEqual((ROOT/n).read_bytes(),self.values[n])
  self.receipt['caller']=dict(cases=parent_cases,original_caller_words=58,original_caller_visited_words=58,connected_helper_cases=cases,retained_helper_words=71,retained_helper_visited_words=71,real_factory_initializer_memcpy_and_sqrt=True,original_constant_and_padding_bytes=True,raw_C_connected=True,heap_and_final_event_providers_bounded=True,current_parent_still_placeholder=True,gameplay_or_hardware_FCSR_claim=False)
 def test_04_native32_typed_payload_and_effective_controls(self):
  unit=self.fresh/'native.c';unit.write_text(native_harness())
  for opt in('O0','O2','O3'):
   exe=self.fresh/('native-'+opt);p=subprocess.run([*native_command('-'+opt,True),'-mstackrealign','-fno-builtin',str(unit),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stderr);p=subprocess.run([str(exe)],capture_output=True,timeout=60);self.assertEqual(p.returncode,0,(opt,p.stderr))
  self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_each_profile=16384,effective_controls=4,trapping_UBSan=True,typed_36byte_payload_200byte_record=True,whole_record_fences=True,opaque_helpers=True)
 def test_05_fired_faults_and_failure_skip(self):
  cuts=0
  for allocated,mode,phase in itertools.product((False,True),(0,2,4,8,16,32,63),(0,8)):
   c=Case(allocated=allocated,mode=mode,phase=phase);initial=fixture(c);good=self.compare(c)
   for cut in range(good.root_accesses):
    pair=[]
    for w in(self.truth,self.words):
     m=DistanceOracle(w,initial,c);m.root_fault=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     self.assertEqual(m.root_accesses,cut);pair.append(m)
    self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));cuts+=1
  c=Case(allocated=False);initial=fixture(c)
  for p in(RECORD,INPUT):
   for i in range(256):initial.pop(p+i,None)
  for w in(self.truth,self.words):self.assertEqual(DistanceOracle(w,initial,c).run().r[2],0)
  self.receipt['faults']=dict(fired_prefix_pairs=cuts,normalized_complete_state_trace_PC_delay=True,failure_skips_payload_and_record_reads=True,portable_C_fault_claim=False)
 def test_06_actual_guard_rejections_extent_and_GNU_rebases(self):
  raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'));bad=bytearray(raw);bad[124]^=1;wrong=dict(rs);wrong[48]=[('R_MIPS_26','wrong')]
  for b,bindings in((raw[:-4],rs),(bytes(bad),rs),(raw,wrong)):
   with self.assertRaises(ValueError):source.normalized_payload(b,bindings)
  manifest=(self.out/'proposed-word-patches.csv').read_bytes();self.assertEqual(manifest,source.guard_manifest(self.values['conker/retail_word_patches.us.csv']));reader=csv.DictReader(io.StringIO(manifest.decode()));fields=reader.fieldnames;rows=list(reader);indices=[i for i,row in enumerate(rows)if row['function']==source.FUNCTION];self.assertEqual(len(indices),8);rejections=0
  for i,field in itertools.product(indices,('expected','expected_relocations')):
   changed=[dict(row)for row in rows];changed[i][field]='0xFFFFFFFF'if field=='expected'else'R_MIPS_26:wrong';path=self.fresh/'bad-guards.csv'
   with path.open('w',newline='')as stream:writer=csv.DictWriter(stream,fields);writer.writeheader();writer.writerows(changed)
   with self.assertRaisesRegex(ValueError,'stale word patch|stale relocations'):source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=path,filename=source.OWNER)
   rejections+=1
  p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=self.out/'proposed-word-patches.csv',filename=source.OWNER));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes());self.assertEqual(source.payload(obj),source.payload(self.out/('original-'+source.FUNCTION+'.o')));self.assertEqual(parse_object(obj)[1][source.FUNCTION]['size'],192);count=0
  for j,entry in enumerate((source.ENTRY,0x17007FFC,0x2500FFFC)):
   symbols=SYMBOLS if j==0 else dict(func_15167A68=entry+0x10000,memcpy=entry+0x20000,func_15143E64=entry+0x30000)
   images=[self.rebased(p,entry,symbols,'rebase-%d-%d'%(j,k))[:48]for k,p in enumerate((self.out/('original-'+source.FUNCTION+'.o'),obj,self.out/'make-shadow/src/game/generated_F2820.c.o'))];self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2]);raw_image=self.rebased(self.out/'selected.o',entry,symbols,'rebase-raw-%d'%j)[:47]
   for allocated,mode in itertools.product((False,True),(0,1,2,4,8,16,32,63)):
    c=Case(allocated=allocated,mode=mode);m=self.compare(c,images[:2],entry,symbols);q=DistanceOracle(raw_image,fixture(c),c,symbols,entry).run();self.assertEqual((q.memory,q.r[2],q.calls,q.deltas),(m.memory,m.r[2],m.calls,m.deltas));count+=1
  self.receipt['rebases']=dict(layouts=3,guest_cases=count,J26_bindings_preserved=True,original_compiler_and_actual_Make=True,raw_binding_controls=3,guards=8,actual_padder_stale_rejections=rejections,inserted_return_move_and_192byte_extent=True)
 def test_07_actually_compiled_semantic_controls(self):
  for name,b in controls().items():
   obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+b,'negative-'+name);self.assertFalse(diag);words=self.rebased(obj,source.ENTRY,SYMBOLS,'negative-link-'+name);c=Case();initial=fixture(c);memory,result,calls,deltas=reference(initial,c);m=DistanceOracle(words,initial,c).run();self.assertNotEqual((public(m.memory),m.r[2],m.calls,m.deltas),(public(memory),result,calls,deltas),name)
  self.receipt['compiled_control']=dict(actually_compiled_IDO_negatives=4,semantic_value_failures=True)
 def test_08_strict_entire_image_extent_and_corruptions(self):
  v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=v['conker/conker.us.bin'][source.ROM:source.ROM+192];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,192);symbol=next(p for p,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8
  for offset in(20,at,at+172,at+192,source.elf_slot_offset(before,0x80082B20,4),symbol):
   bad=bytearray(expected);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  count=sum(x!=y for x,y in zip(before,expected));self.assertEqual(count,145);self.receipt['image']=dict(changed_bytes=count,code_bytes=144,size_bytes=1,other6055_bodies_and6056_addresses_fixed=True,all_named_definitions_checked=True,protected_owners=720,protected_bytes=189088,exclusions=0,effective_corruptions=6,shared_headers_helpers_current_parent_unchanged=True,inherited_guard_bytes_preserved=True)
