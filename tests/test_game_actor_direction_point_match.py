"""Actor direction point: direct C, both original callers and strict image."""
from dataclasses import replace
from pathlib import Path
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_actor_direction_point_match as source
from tools.tests import game_actor_direction_point_oracle as oracle
from tools.tests.game_actor_direction_point_oracle import Case,fixture,reference,public,DirectionOracle,SYMBOLS,POINTS,ACTOR,ALT,POINT,OUT,ALT_OUT,OWNER,LINK,CHANGED,RESULT,DATA,BYTES,TRIG_TABLE,FRACTIONS,FRACTION,RAY,FACTORY,COPY,STACK,put,read,faults
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
 out=dict(wrong_yaw=b.replace('func_15143794(yaw, pitch','func_15143794(pitch, pitch'),wrong_pitch=b.replace('func_15143794(yaw, pitch','func_15143794(yaw, yaw'),wrong_scale=b.replace('actor->unkF0','actor->unkEC'),wrong_x=b.replace('point->x += origin.unk0','point->x += origin.unk4'),wrong_z=b.replace('point->z += origin.unk8','point->z += origin.unk4'),missing_origin=b.replace('*originOut = origin;',''),wrong_radius=b.replace('yaw, pitch, radius, point','yaw, pitch, otherScale, point'))
 assert all(v!=b for v in out.values());return out

def native_harness():
 t=source.HEADERS+source.DECLARATIONS+"typedef char ABI[(sizeof(void*)==4&&sizeof(struct127)==812&&__builtin_offsetof(struct127,unkF0)==240&&sizeof(vertex)==12&&sizeof(struct17)==12)?1:-1];\nstatic struct127 actor,actorExpected;\nstatic struct{u32 left[4];vertex point;u32 right[4];}out,expected;\nstatic struct{u32 left[4];struct17 origin;u32 right[4];}returned,returnedExpected;\nstatic struct17 wantedOrigin;\nstatic vertex direction;\nstatic s16 wantedYaw,wantedPitch;\nstatic f32 wantedRadius;\nstatic u32 seed,mode,phase,error;\nstatic void copy(void*d,const void*s,u32 n){u32 i;for(i=0;i<n;i++)((u8*)d)[i]=((const u8*)s)[i];}\nstatic int same(const void*a,const void*b,u32 n){u32 i;for(i=0;i<n;i++)if(((const u8*)a)[i]!=((const u8*)b)[i])return 0;return 1;}\nvoid func_1515C244(struct127*p,struct17*origin,f32*radius,f32*other){\n if(phase++!=0||p!=&actor||origin==(struct17*)&out.point||radius==other)error=1;\n *origin=wantedOrigin;*radius=wantedRadius;*other=-99.5f;\n if(mode&1)actor.unkF0=actorExpected.unkF0=-0.75f;\n}\nvoid func_15143794(s16 yaw,s16 pitch,f32 radius,vertex*p){\n if(phase++!=1||yaw!=wantedYaw||pitch!=wantedPitch||radius!=wantedRadius||p!=&out.point)error=1;\n *p=direction;\n if(mode&2)actor.unkF0=actorExpected.unkF0=1.25f;\n}\n"
 for n,b in dict(selected=source.SELECTED,**controls()).items():t+=b.replace(source.FUNCTION,n)+"\n"
 return t+"typedef void(*Query)(struct127*,s16,s16,vertex*,struct17*);\nstatic const s16 angles[]={-32768,-257,-256,-1,0,1,255,256,257,32767};\nstatic const f32 scales[]={-2.0f,-0.0f,0.0f,0.5f,1.0f,2.25f};\nstatic int check(Query fn){u32 a,b,s,optional,i;u8*p;f32 scaled;\n for(seed=0;seed<16;seed++)for(a=0;a<10;a++)for(b=0;b<10;b++)for(s=0;s<6;s++)for(mode=0;mode<4;mode++)for(optional=0;optional<2;optional++){\n  p=(u8*)&actor;for(i=0;i<sizeof(actor);i++)p[i]=(u8)(seed+i*13);\n  p=(u8*)&out;for(i=0;i<sizeof(out);i++)p[i]=(u8)(seed+i*17);\n  p=(u8*)&returned;for(i=0;i<sizeof(returned);i++)p[i]=(u8)(seed+i*19);\n  actor.unkF0=scales[s];actor.unkEC=9.5f;copy(&actorExpected,&actor,sizeof(actor));copy(&expected,&out,sizeof(out));copy(&returnedExpected,&returned,sizeof(returned));\n  wantedYaw=angles[a];wantedPitch=angles[b];wantedRadius=(f32)seed+0.5f;\n  wantedOrigin.unk0=(f32)seed*0.25f-8.0f;wantedOrigin.unk4=(f32)seed*0.5f+3.0f;wantedOrigin.unk8=-(f32)seed-7.0f;\n  direction.x=(f32)angles[a]*0.5f+1.5f;direction.y=(f32)angles[b]*0.25f+2.0f;direction.z=(f32)seed*0.125f+0.75f;\n  phase=error=0;fn(&actor,wantedYaw,wantedPitch,&out.point,optional?&returned.origin:NULL);\n  if(error||phase!=2)return 1;\n  scaled=direction.y*actorExpected.unkF0;\n  expected.point.x=direction.x+wantedOrigin.unk0;expected.point.y=scaled+wantedOrigin.unk4;expected.point.z=direction.z+wantedOrigin.unk8;\n  if(optional)returnedExpected.origin=wantedOrigin;\n  if(!same(&actor,&actorExpected,sizeof(actor))||!same(&out,&expected,sizeof(out))||!same(&returned,&returnedExpected,sizeof(returned)))return 1;\n }return 0;\n}\nstatic int run(void){if(check(selected))return 10;\nif(!check(wrong_yaw))return 20;\nif(!check(wrong_pitch))return 21;\nif(!check(wrong_scale))return 22;\nif(!check(wrong_x))return 23;\nif(!check(wrong_z))return 24;\nif(!check(missing_origin))return 25;\nif(!check(wrong_radius))return 26;\nreturn 0;}\n\nvoid _start(void) {\n    int result = run();\n    __asm__ volatile(\".byte 0xcd,0x80\" : : \"a\"(1), \"b\"(result) : \"memory\");\n    __builtin_unreachable();\n}\n"

class ActorDirectionPointTests(unittest.TestCase):
 receipt={}
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>48I',cls.rom,source.ROM));local=cls.fresh/'qualified-padded.o';local.write_bytes((cls.out/'qualified-padded.o').read_bytes());data,functions=source.link_owner(ROOT,cls.fresh,local,source.OWNER);cls.words=list(struct.unpack_from('>48I',data,functions[source.FUNCTION]['value']))
 @classmethod
 def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
 def compare(self,c=Case(),images=None,entry=source.ENTRY,symbols=SYMBOLS):
  initial=fixture(c);memory,calls,out=reference(initial,c,symbols);pair=[]
  for words in images or(self.truth,self.words):
   m=DirectionOracle(words,initial,c,symbols,entry).run();self.assertEqual((public(m.memory),m.calls),(public(memory),calls),c);self.assertEqual(oracle.vector(m.memory,c.point),oracle.vector(memory,c.point),c)
   if out:self.assertEqual(oracle.vector(m.memory,out),oracle.vector(memory,out),c)
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
   obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertEqual(source.check_owner_diagnostics(diag),2);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),37)
  self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),36);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'))
  proposed=(self.out/'proposed-owner.c').read_text();self.assertEqual(proposed,source.recovered_owner(self.values[source.SOURCE].decode()));self.assertEqual(proposed.count('#pragma GLOBAL_ASM'),8);self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),5)
  ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertFalse(any(w==source.ENTRY for w in ws));self.assertEqual([4*i for i,w in enumerate(ws)if w in(0x0C000000|(source.ENTRY>>2&0x3FFFFFF),0x08000000|(source.ENTRY>>2&0x3FFFFFF))],[0x134C88,0x134E50])
  for va in source.PARENTS:self.assertIn('s32 func_%X() {\n    return 0;\n}'%va,self.values[source.SOURCE].decode())
  if self.installed:source.audit(ROOT,self.out)
  self.receipt['owner']=dict(words=48,frame=56,bindings=2,guards=0,neighbors=36,compact_functions=37,GLOBAL_ASM_routines=8,Make_commands=5,inherited_warning712_count=2,selected_diagnostics=0,arguments=5,void_return=True,current_parents_unchanged_placeholders=True,actor_bytes=812,vector_bytes=12,late_actor_scale_offset=240,direct_sites=['0x151077D8','0x151079A0'])
 def test_02_guest_signed_angles_read_order_and_aliases(self):
  count=0;visits=set()
  for yaw,pitch,optional,mode,point,phase in itertools.product((0,1,0x7FFF,0x8000,0xFFFF,0xABCD8001),(0,0x7FFF,0x8000,0xFFFF),(False,True),(0,1,2,4,8,16,32,63),POINTS,(0,8)):
   m=self.compare(Case(yaw=yaw,pitch=pitch,optional=optional,mode=mode,direction=point,phase=phase));visits.update(m.visits);count+=1
  aliases=0
  for phase,offset in itertools.product((0,8),(-20,-16,-12,-8,-4,24,40)):
   if offset not in(-8,-4):self.compare(Case(point=STACK+phase+offset,phase=phase));count+=1;aliases+=1
   self.compare(Case(output=STACK+phase+offset,phase=phase));count+=1;aliases+=1
  for point,out in itertools.product((ACTOR+0xEC,ACTOR+0xF0,POINT),(POINT-4,POINT,POINT+4,ACTOR+0xF0)):
   self.compare(Case(point=point,output=out));count+=1;aliases+=1
  self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+192,4)));self.receipt['guest']=dict(cases=count,visited_words=48,signed_halfword_angles=True,optional_output=True,guest_aliases=aliases,late_scale_read_and_provider_home_redirects=True,complete_state_and_trace=True,bounded_origin_direction_providers=True,portable_alias_NaN_payload_or_FCSR_claim=False)
 def helpers(self):
  connected={};elf=self.values['conker/build/conker.us.elf']
  for va,rom,words in((source.ORIGIN,0x1896F4,41),(source.DIRECTION,0x170C44,40),(source.TRIG,0x16F888,27),(FRACTION,0x134F90,38),(COPY,0x22EC0,11)):
   body=list(struct.unpack_from('>%dI'%words,self.rom,rom));at=source.elf_slot_offset(elf,va,words*4);self.assertEqual(list(struct.unpack_from('>%dI'%words,elf,at)),body);connected.update({va+4*i:w for i,w in enumerate(body)})
  return connected
 def tables(self,m):
  elf=self.values['conker/build/conker.us.elf']
  for va,size in((TRIG_TABLE,260),(FRACTIONS,8)):
   at=source.elf_slot_offset(elf,va,size);m.update({va+i:v for i,v in enumerate(elf[at:at+size])})
  return m
 def fractions(self,m,start,end):
  return tuple(tuple(oracle.add(start[i],oracle.mul(oracle.sub(end[i],start[i]),read(m,FRACTIONS+4*j)))for i in range(3))for j in range(2))
 def test_03_original_callers_helpers_and_retained_tables(self):
  helpers=self.helpers();seen=set();cases=0
  for yaw,actor_id,radius,height,optional in itertools.product(range(0,256,17),(0,0xBA,0xBB,0xFF),(-32768,7),(0,32767),(False,True)):
   c=Case(yaw=yaw,pitch=(yaw*7+64)&65535,actor_id=actor_id,actor_radius=radius,height=height,optional=optional);initial=self.tables(fixture(c));expected,point,origin=oracle.actual_reference(initial,c);pair=[DirectionOracle(w,initial,c,connected=helpers).run()for w in(self.truth,self.words)];self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(public(pair[0].memory),public(expected));seen.update(pair[0].visits);cases+=1
  caller_counts=[];caller_visited=[]
  parent=list(struct.unpack_from('>121I',self.rom,0x134BB0));parent_seen=set();parent_cases=0
  for active,hit,allocated,lifetime,alignment,phase in itertools.product((False,True),(False,True),(False,True),(-1,17),range(4),(0,8)):
   c=Case(yaw=0xFFFF,pitch=0x8080,ray_hit=hit,allocated=allocated,phase=phase);initial=self.tables(fixture(c));put(initial,ACTOR+0x1D4,int(active));initial[ACTOR+0x3B]=0xA7;sp=STACK+phase-0x120
   args=(ACTOR,c.yaw,c.pitch,lifetime&0xFFFFFFFF,0x98765432,oracle.bits(2.5),oracle.bits(-3.25),0x8765FFFE,0x12348000,BYTES+alignment,0xABCDEF91,0xCAFE1234)
   pair=[DirectionOracle(parent,initial,c,entry=source.PARENTS[0],arguments=args,connected=dict(helpers,**{})|{source.ENTRY+4*i:v for i,v in enumerate(w)}).run()for w in(self.truth,self.words)];m=pair[0];self.assertEqual(complete(m),complete(pair[1]));parent_seen.update(m.visits);seen.update(m.visits);self.assertEqual(m.r[2],RESULT if active and hit and allocated else 0)
   if not active:self.assertFalse(m.calls)
   else:
    self.assertEqual(m.target_entries,[(ACTOR,0xFFFFFFFF,0xFFFF8080,sp+0xC4,sp+0x50)]);expected,point,origin=oracle.actual_reference(initial,c);delta=tuple(oracle.sub(point[i],origin[i])for i in range(3));self.assertEqual(m.ray_packets,[(ACTOR,*point,*delta,sp+0x5C,0,0,1,1,0xFFFFFFFF,0,0)])
    if hit:
     end=(oracle.bits(9.5),oracle.bits(-7),oracle.bits(2));first,second=self.fractions(initial,point,end);packet=m.factory_packets[0];self.assertEqual(struct.unpack_from('>H',packet)[0],300 if lifetime==-1 else 17);self.assertEqual(packet[2],0 if lifetime==-1 else 1);self.assertEqual(struct.unpack_from('>12I',packet,4),(*point,*first,*second,*end));self.assertEqual(packet[0x34],0);self.assertEqual(struct.unpack_from('>3I2H',packet,0x38),(args[4],args[5],args[6],0xFFFE,0x8000));self.assertEqual(packet[0x48:0x4C],bytes(initial[BYTES+alignment+i]for i in range(4)));self.assertEqual(packet[0x4C],2);self.assertIn((FACTORY,(sp+0xC0,12,0x91,args[11])),m.calls)
     if allocated:
      extension=bytearray(initial[sp+0x114+i]for i in range(12));struct.pack_into('>I',extension,0,ACTOR);extension[4]=0xA7;struct.pack_into('>2H',extension,6,0xFFFF,0x8080);self.assertEqual(m.copy_packets,[bytes(extension)]);self.assertEqual(bytes(m.memory[DATA+i]for i in range(12)),bytes(extension))
    else:self.assertFalse(m.factory_packets)
   wanted=dict(initial)
   if active and hit:
    put(wanted,RESULT+0x60,DATA)
    if allocated:
     for i,v in enumerate(extension):wanted[DATA+i]=v
   self.assertEqual(public(m.memory),public(wanted));parent_cases+=1
  self.assertEqual(set(range(source.PARENTS[0],source.PARENTS[0]+484,4))-parent_seen,{0x15107744,0x15107870})
  caller_counts.append(parent_cases);caller_visited.append(len(parent_seen&set(range(source.PARENTS[0],source.PARENTS[0]+484,4))))
  parent=list(struct.unpack_from('>63I',self.rom,0x134DD4));parent_seen=set();parent_cases=0
  for route,axis,phase,actor_id in itertools.product(('inactive','stale','same','changed'),range(3),(0,8),(0,0xFF)):
   c=Case(yaw=0x8123,pitch=0xFE45,phase=phase,actor_id=actor_id,point=OWNER+20,optional=False);initial=self.tables(fixture(c));put(initial,OWNER+0x60,LINK);put(initial,LINK,ACTOR);put(initial,ACTOR,0 if route=='inactive'else 1);initial[LINK+4]=0xA6 if route=='stale'else 0xA7;initial[ACTOR+0x3B]=0xA7;put(initial,LINK+6,c.yaw,2);put(initial,LINK+8,c.pitch,2);initial[CHANGED]=0xA5;expected,point,origin=oracle.actual_reference(initial,c)
   for i,v in enumerate(point):put(initial,OWNER+20+4*i,oracle.add(v,oracle.bits(1.0))if route=='changed'and i==axis else v)
   end=(oracle.bits(50),oracle.bits(-60),oracle.bits(70))
   for i,v in enumerate(end):put(initial,OWNER+0x38+4*i,v)
   pair=[DirectionOracle(parent,initial,c,entry=source.PARENTS[1],arguments=(OWNER,CHANGED),connected=helpers|{source.ENTRY+4*i:v for i,v in enumerate(w)}).run()for w in(self.truth,self.words)];m=pair[0];self.assertEqual(complete(m),complete(pair[1]));parent_seen.update(m.visits);seen.update(m.visits);valid=route in('same','changed');self.assertEqual((m.r[2],m.memory[CHANGED]),(int(valid),1 if route=='changed'else 0 if valid else 0xA5));wanted=dict(initial)
   if valid:
    self.assertEqual(m.target_entries,[(ACTOR,oracle.sign(c.yaw)&0xFFFFFFFF,oracle.sign(c.pitch)&0xFFFFFFFF,OWNER+20,0)])
    for i,v in enumerate(point):put(wanted,OWNER+20+4*i,v)
    if route=='changed':
     first,second=self.fractions(initial,point,end)
     for dst,values in((OWNER+0x20,first),(OWNER+0x2C,second)):
      for i,v in enumerate(values):put(wanted,dst+4*i,v)
    wanted[CHANGED]=int(route=='changed')
   else:self.assertFalse(m.calls)
   self.assertEqual(public(m.memory),public(wanted));parent_cases+=1
  caller_counts.append(parent_cases);caller_visited.append(len(parent_seen&set(range(source.PARENTS[1],source.PARENTS[1]+252,4))))
  self.assertEqual(set(range(source.PARENTS[1],source.PARENTS[1]+252,4))-parent_seen,{0x15107970});self.assertEqual(set(helpers)-seen,{0x1515C258})
  self.receipt['caller']=dict(unreachable_duplicate_delay_words=['0x15107744','0x15107870','0x15107970'],unreachable_origin_branch_delay='0x1515C258',connected_helper_cases=cases,original_caller_cases=caller_counts,original_caller_words=[121,63],original_caller_visited_words=caller_visited,retained_helper_words=157,retained_helper_visited_words=len(seen&set(helpers)),real_origin_direction_trig_fraction_memcpy=True,retained_trig_and_fraction_constants=True,unaligned_copy_offsets=[0,1,2,3],all_return_routes=True,ray_and_factory_providers_bounded=True,current_parent_placeholders_unchanged=True,hardware_gameplay_or_FCSR_claim=False)
 def test_04_native32_canonical_types_and_controls(self):
  unit=self.fresh/'native.c';unit.write_text(native_harness())
  for opt in('O0','O2','O3'):
   exe=self.fresh/('native-'+opt);p=subprocess.run([*native_command('-'+opt,True),'-mstackrealign',str(unit),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stderr);p=subprocess.run([str(exe)],capture_output=True,timeout=60);self.assertEqual(p.returncode,0,(opt,p.stderr))
  self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_each_profile=76800,effective_controls=len(controls()),trapping_UBSan=True,actual_five_argument_void_function_pointer=True,canonical_types=True,whole_actor_point_origin_fences=True,late_scale_provider_mutations=True,helpers_bounded=True)
 def test_05_fired_access_prefixes_and_optional_output(self):
  cuts=0
  for optional,mode,phase in itertools.product((False,True),(0,2,4,16,32,63),(0,8)):
   c=Case(optional=optional,mode=mode,phase=phase);initial=fixture(c);good=self.compare(c)
   for cut in range(good.root_accesses):
    pair=[]
    for w in(self.truth,self.words):
     m=DirectionOracle(w,initial,c);m.root_fault=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
     self.assertEqual(m.root_accesses,cut);pair.append(m)
    self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));cuts+=1
  c=Case(optional=False);memory=fixture(c)
  for i in range(12):memory.pop(OUT+i,None)
  for w in(self.truth,self.words):DirectionOracle(w,memory,c).run()
  self.receipt['faults']=dict(fired_prefix_pairs=cuts,complete_state_trace_PC_delay=True,null_optional_skips_output=True,guest_instruction_boundaries_only=True)
 def test_06_real_padder_controls_and_GNU_relocations(self):
  raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'));bad=bytearray(raw);bad[124]^=1;wrong=dict(rs);wrong[40]=[('R_MIPS_26','wrong')]
  for b,bindings in((raw[:-4],rs),(bytes(bad),rs),(raw,wrong)):
   with self.assertRaises(ValueError):source.checked_payload(b,bindings)
  p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=ROOT/'conker/retail_word_patches.us.csv',filename=source.OWNER,rodata_symbol=source.RODATA_SYMBOL));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes());count=0
  for j,entry in enumerate((source.ENTRY,0x17007FFC,0x2500FFFC)):
   symbols=SYMBOLS if j==0 else dict(func_1515C244=entry+0x10004,func_15143794=entry+0x28004)
   images=[self.rebased(p,entry,symbols,'rebase-%d-%d'%(j,k))[:48]for k,p in enumerate((self.out/('original-'+source.FUNCTION+'.o'),self.out/'selected.o',self.out/'make-shadow/src/game/generated_133190.c.o'))];self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
   for optional,mode,phase in itertools.product((False,True),(0,2,4,16,32,63),(0,8)):self.compare(Case(optional=optional,mode=mode,phase=phase),images[:2],entry,symbols);count+=1
  self.receipt['rebases']=dict(layouts=3,guest_cases=count,J26_relocations=True,original_compiler_and_actual_Make=True,raw_binding_controls=3,guards=0,owner_rodata_binding_preserved=True)
 def test_07_actually_compiled_semantic_controls(self):
  for name in('wrong_yaw','wrong_scale','missing_origin','wrong_radius'):
   obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+controls()[name],'negative-'+name);self.assertFalse(diag);words=self.rebased(obj,source.ENTRY,SYMBOLS,'negative-link-'+name);c=Case(direction=POINTS[1]);initial=fixture(c);expected,calls,out=reference(initial,c);m=DirectionOracle(words,initial,c).run();self.assertNotEqual((public(m.memory),m.calls),(public(expected),calls),name)
  self.receipt['compiled_control']=dict(actually_compiled_IDO_negatives=4,semantic_value_failures=True,angle_scale_optional_and_radius_controls=True)
 def test_08_strict_entire_image_extent_and_corruptions(self):
  v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=v['conker/conker.us.bin'][source.ROM:source.ROM+192];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,192);symbol=next(p for p,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8
  for offset in(20,at,at+180,at+192,source.elf_slot_offset(before,TRIG_TABLE,4),symbol):
   bad=bytearray(expected);bad[offset]^=1
   with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
  count=sum(x!=y for x,y in zip(before,expected));self.assertEqual(count,144);self.receipt['image']=dict(changed_bytes=count,code_bytes=143,size_bytes=1,other6055_bodies_and6056_addresses_fixed=True,all_named_definitions_checked=True,protected_owners=720,protected_bytes=189088,exclusions=0,effective_corruptions=6,shared_headers_helpers_current_parents_and_guards_unchanged=True)
