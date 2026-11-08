"""Timed scale callback: owner/image audit, sound ABI, live reloads and status."""
from dataclasses import replace
import csv,io,itertools,json,math,struct,subprocess,unittest
from pathlib import Path
from tools.experiments import game_timed_scale_callback_151b5e94_match as match
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests import game_timed_scale_callback_151b5e94_oracle as guest
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
ROOT=match.ROOT

def corpus():
 angles=(0,0x80000000,1,0x80000001,0xBF800000,0xC1A00000,0x3F800000,0x41490FDA,0x41490FDB,0x41490FDC,0x41EF3332,0x41EF3333,0x41EF3334,0x42000000,0x7FC12345,0x7F800000,0xFF800000)
 for i,(angle,tick,base,mode,phase)in enumerate(itertools.product(angles,(0,0x80000000,0x3F800000,0x40800000),(0x40000000,0xC0300000,0x3F800001),(0,1,2,4,8,16,32,64,5,12,68),(0,8))):
  yield guest.Case(angle=angle,tick=tick,base=base,mode=mode,phase=phase,sample=(0x3F400000,0x3F800001,0xBF000001,0)[i%4],result=(0,1,0xFFFFFFFF,0x80)[i%4],seed=i&255,sound_phase=(0x41000000,0x41A00000)[i&1])

def controls():
 b=match.SELECTED
 return dict(wrong_step=b.replace('D_800AA434 * D_800BE9A4','D_800AA434 + D_800BE9A4'),
  inclusive_sound=b.replace('> D_800AA438','>= D_800AA438'),
  wrong_reset=b.replace('= 0.0f;','= 1.0f;'),
  inclusive_pulse=b.replace('< D_800AA43C','<= D_800AA43C'),
  wrong_gain=b.replace('D_800AA440 * state[1]','1.0f * state[1]'),
  missing_output=b.replace('*(f32 *)(owner + 0x18) = ',''),
  early_base=b.replace('    f32 result;','    f32 result;\n    f32 savedBase;').replace('        result = sinf(state[0]);','        savedBase = state[1];\n        result = sinf(state[0]);').replace('(result * (D_800AA440 * state[1])) + state[1]','(result * (D_800AA440 * savedBase)) + savedBase'),
  early_phase=b.replace('    f32 result;','    f32 result;\n    f32 savedPhase = state[0];').replace('if (state[0] < D_800AA43C)','if (savedPhase < D_800AA43C)').replace('sinf(state[0])','sinf(savedPhase)'),
  constant_result=b.replace('return func_15133894(owner);','func_15133894(owner);\n    return 1;'),
  wrong_sound=b.replace('func_10010F88(0x502','func_10010F88(0x503'),
  missing_sound=b.replace('        func_10010F88(0x502, 24000, 0, 0, -1,\n                      (s32)*(f32 *)(owner + 0x38),\n                      (s32)*(f32 *)(owner + 0x3C),\n                      (s32)*(f32 *)(owner + 0x40), 100, 500);',''),
  wrong_coordinate=b.replace('(s32)*(f32 *)(owner + 0x38)','(s32)*(f32 *)(owner + 0x3C)'))

def linked(obj,entry,label,out,defs=None):
 defs=defs or guest.symbols();text,functions,bindings=parse_object(obj);f=functions[match.FUNCTION]
 assembly,unknown=emit_function(text,f,bindings,match.FUNCTION,defs);assert not unknown;p=out/label
 p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%(n,a)for n,a in defs.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack_from('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1]))

class TimedScaleTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/'conker/conker.us.bin').read_bytes();cls.truth=list(struct.unpack_from('>78I',cls.rom,match.ROM))
  cls.raw=linked(cls.out/'qualified-owner.o',match.ENTRY,'raw-suite',cls.out);cls.fitted=linked(cls.prepared['qualified_object'],match.ENTRY,'fitted-suite',cls.out)
  cls.raw_blob,cls.refs=match.function_blob(cls.out/'qualified-owner.o');assert cls.fitted==cls.truth
 def receipt(self,name,value):(self.out/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')
 def compare(self,c,images=None,entry=None,defs=None,initial=None):
  initial=guest.fixture(c,defs)if initial is None else initial;expected,calls,result,snapshots=guest.reference(initial,c,defs)
  models=[]
  for code in images or(self.truth,self.raw,self.fitted):
   m=guest.Oracle(code,initial,c,entry=entry,s=defs).run();self.assertEqual((guest.public(m.memory),m.calls,m.r[2],m.snapshots),(guest.public(expected),calls,result,snapshots),c);models.append(m)
  self.assertEqual(guest.full_state(models[0]),guest.full_state(models[-1]));return models
 def test_01_owner_actual_Make_image_and_fail_closed_guards(self):
  q=self.prepared['report'];self.assertEqual((q['words'],q['raw_words'],q['frame'],q['guards'],q['raw_neighbors'],q['padded_neighbors']),(78,77,72,7,2,2))
  self.assertEqual((q['actual_Make']['commands'],q['actual_Make']['functions']),(3,3));self.assertEqual((q['strict_changed_bytes'],q['exclusions'],q['named_metadata_rows']),(294,0,9))
  for entry,pos,n in guest.HELPERS:
   before=(self.out/'frozen'/match.ELF).read_bytes();at=match.elf_slot_offset(before,entry,n*4);self.assertEqual(before[at:at+n*4],self.rom[pos:pos+n*4])
  aligned=struct.unpack('>%dI'%(len(self.rom)//4),self.rom[:len(self.rom)&~3]);self.assertEqual([i*4 for i,w in enumerate(aligned)if match.ENTRY<=w<match.ENTRY+312],[0x22E384])
  self.assertFalse([w for w in aligned if w>>26 in(2,3)and match.ENTRY<=(((w&0x3FFFFFF)<<2)|0x10000000)<match.ENTRY+312])
  for at in range(308):
   bad=bytearray(self.raw_blob);bad[at]^=1
   with self.assertRaises(ValueError):match.normalize(bytes(bad),self.refs)
  for at in self.refs:
   refs=dict(self.refs);refs[at]=[(refs[at][0][0],'wrong')]
   with self.assertRaises(ValueError):match.normalize(self.raw_blob,refs)
  rows=list(csv.DictReader(io.StringIO((self.out/'qualified-guards.csv').read_text())));indices=[i for i,r in enumerate(rows)if r['function']==match.FUNCTION];self.assertEqual(len(indices),7)
  for index in indices:
   changed=[dict(r)for r in rows];changed[index]['expected']='0x%08X'%(int(changed[index]['expected'],16)^1);p=self.out/('rejected-%d.csv'%index)
   with p.open('w',newline='')as stream:w=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(changed)
   with self.assertRaises(ValueError):emit_padded_assembly(self.out/'qualified-owner.o',ROOT/'conker/asm/1E30A0.s',filename=match.OWNER,word_patches_path=p)
  before,after=self.prepared['predecessor_elf'].read_bytes(),self.prepared['qualified_elf'].read_bytes()
  for at in (0x80,len(after)-1,match.elf_slot_offset(before,match.ENTRY,312),2870372,2874660,3006660,3137178,3140765,3249615):
   bad=bytearray(after);bad[at]^=1
   with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),self.rom[match.ROM:match.ROM+312])
 def test_02_guest_thresholds_post_sound_and_sine_reloads(self):
  count=0;visits=set()
  for c in corpus():visits.update(self.compare(c)[0].visits);count+=1
  reachable=set(range(match.ENTRY,match.ENTRY+312,4))-{match.ENTRY+0x110}
  self.assertEqual(visits,reachable)
  self.receipt('guest-contract',dict(cases_per_body=count,reachable_words=77,unreachable_redundant_load=hex(match.ENTRY+0x110),literal_words=78,post_sound_phase_and_limit_reload=True,post_sine_base_gain_and_private_pointer_reload=True,NaN_payload_or_FCSR_hardware_equivalence_claimed=False))
 def test_03_aliases_saved_pointer_and_fault_prefixes(self):
  count=0
  for owner,angle,mode,phase in itertools.product((guest.OWNER,guest.symbols()['D_800BE9A4']-0x170,guest.symbols()['D_800AA440']-0x174,guest.symbols()['D_800AA434']-0x170),(0,0x42000000,0xBF800000),(0,1,2,4,8,32,64),(0,8)):
   self.compare(guest.Case(owner=owner,angle=angle,mode=mode,phase=phase));count+=1
  cuts=delay=0
  for angle,mode,phase in itertools.product((0,0x41490FDB,0x42000000),(0,1,2,4),(0,8)):
   c=guest.Case(angle=angle,tick=0,mode=mode,phase=phase);initial=guest.fixture(c);full=guest.Oracle(self.truth,initial,c).run()
   for cut in range(full.all_accesses):
    pair=[guest.Oracle(code,initial,c)for code in(self.truth,self.fitted)]
    for m in pair:
     m.cut=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
    self.assertEqual(guest.full_state(pair[0]),guest.full_state(pair[1]));self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));cuts+=1;delay+=pair[0].delay_of is not None
  self.receipt('aliases-faults',dict(alias_cases_per_body=count,prefix_pairs=cuts,delay_slot_cuts=delay,complete_fitted_private_state=True,portable_C_fault_or_raw_private_state_claimed=False))
 def test_04_actual_caller_and_forwarded_status(self):
  count=0;visits=set()
  for angle,mode,phase,selector,gate,result in itertools.product((0,0x41490FDB,0x42000000),(0,1,4),(0,8),(0,5),(0,5),(0,1,0xFFFFFFFF,0x80)):
   c=guest.Case(angle=angle,tick=0,mode=mode,phase=phase,result=result);pair=[]
   for body in(self.truth,self.raw,self.fitted):
    m,initial=guest.caller_machine(self.rom,body,c,selector,gate)
    with self.assertRaises(guest.WindowBoundary):m.run()
    expected,calls,value,snaps=guest.reference(initial,c)if selector else(initial,[],0,[])
    if selector:calls=[(match.ENTRY,(c.owner,))]+calls
    self.assertEqual((guest.public(m.memory),m.calls,m.snapshots,m.r[5]),(guest.public(expected),calls,snaps,1 if selector and result==0 else gate));pair.append(m);visits.update(m.visits)
   self.assertEqual(guest.full_state(pair[0]),guest.full_state(pair[-1]));count+=1
  self.assertTrue(set(range(guest.WINDOW,guest.END,4))<=visits);self.receipt('callers',dict(cases_per_body=count,original_words=13,selector=5,zero_sets_gate=True,nonzero_restores_gate=True,complete_parent_claimed=False))
 def test_05_connected_retail_math_move_status_and_sound_adapter(self):
  count=0;visits=set();results=set()
  for i,(velocity,flags,selector,geometry,attachment,event,phase)in enumerate(itertools.product((0xC0000000,0x40000000),(0,1),(0,1),(0,1),(-1,0x40,0x60),(0,7,0x80),(0,8))):
   c=guest.ConnectedCase(angle=(0,1,0x3F000000,0x3F800000,0x41490FDB,0x42000000,0xC1A00000,0xE0AD78EC,0x7FC12345)[i%9],tick=0 if i%4==0 else 0x3F800000,velocity=velocity,flags=flags,selector=selector,geometry=geometry,attachment=attachment,event_result=event,phase=phase)
   initial=guest.connected_fixture(c);expected,calls,result,snaps,packets=guest.connected_reference(initial,c);pair=[]
   for body in(self.truth,self.raw,self.fitted):
    m=guest.ConnectedOracle(body,initial,c,self.rom).run();self.assertEqual((guest.public(m.memory),m.calls,m.r[2],m.snapshots,m.geometry_packets),(guest.public(expected),calls,result,snaps,packets),c);pair.append(m);visits.update(m.visits)
   self.assertEqual(guest.full_state(pair[0]),guest.full_state(pair[-1]));results.add(result);count+=1
  covered=[dict(entry=hex(e),words=n,visited=len(set(range(e,e+4*n,4))&visits))for e,p,n in guest.HELPERS]
  self.assertEqual([v['visited']for v in covered][1:],[80,53,29]);self.receipt('connections',dict(cases_per_body=count,helpers=covered,return_values=sorted(results),bounded_sound_inner_geometry_event=True,full_gameplay_claimed=False))
 def test_06_three_GNU_links_and_relocation_carry_edges(self):
  from tools.tests.test_game_view_list_setup import ViewListSetupTests
  context=type('Original',(),dict(root=ROOT,out=self.out));original=ViewListSetupTests.original.__func__(context,'original-timed-scale',(ROOT/'conker/asm/1E30A0.s').read_text(),match.FUNCTION);count=links=0
  for j,entry in enumerate((match.ENTRY,0x18017FFC,0x2500FFFC)):
   defs=guest.symbols()
   if j:
    defs={name:((entry&0xF0000000)+0x3030004+4*i if name in('sinf','func_10010F88','func_15133894')else 0x80107FFC+0x10000*i+4*j)for i,name in enumerate(defs)}
   objects=(original,self.out/'qualified-owner.o',self.prepared['qualified_object']);images=[linked(p,entry,'rebase-%d-%d'%(j,k),self.out,defs)for k,p in enumerate(objects)];links+=3;self.assertEqual(images[0],images[2])
   for angle,phase,mode in itertools.product((0,0x41490FDB,0x42000000),(0,8),(0,1,4,64)):
    self.compare(guest.Case(angle=angle,tick=0,mode=mode,phase=phase),images,entry,defs);count+=1
  self.receipt('rebases',dict(GNU_links=links,cases_per_body=count,independent_original_raw_padded=True,HI_LO_carry_edges=True))
 def test_07_effective_compiled_semantic_and_status_controls(self):
  rows=controls();self.assertEqual(len(rows),12);evidence={};cases=[guest.Case(angle=angle,tick=0,mode=mode,result=0,sample=0x3F800001)for angle,mode in itertools.product((0,0x41490FDB,0x41EF3333,0x42000000),(0,1,4,64))]
  for name,body in rows.items():
   self.assertNotEqual(body,match.SELECTED);obj,diag=compile_owner(ROOT,self.out,match.ISOLATED_HEADER+body,'negative-'+name);self.assertFalse(diag);code=linked(obj,match.ENTRY,'negative-link-'+name,self.out)
   for c in cases:
    initial=guest.fixture(c);expected,calls,result,snaps=guest.reference(initial,c);m=guest.Oracle(code,initial,c).run()
    if(guest.public(m.memory),m.calls,m.r[2],m.snapshots)!=(guest.public(expected),calls,result,snaps):evidence[name]=dict(angle=hex(c.angle),mode=c.mode);break
   self.assertIn(name,evidence,name)
   if name=='constant_result':
    c=guest.Case(angle=0,tick=0,result=0);m,_=guest.caller_machine(self.rom,code,c,5,0)
    with self.assertRaises(guest.WindowBoundary):m.run()
    self.assertEqual(m.r[5],0)
  self.receipt('compiled-controls',evidence)
 def test_08_native32_profiles_typed_sound_and_canaries(self):
  text,count=native_source();output=self.out/'native';output.mkdir(exist_ok=True)
  for opt in('-O0','-O2','-O3'):
   path=output/(opt[1:]+'.c');binary=path.with_suffix('.elf');path.write_text(text)
   p=subprocess.run([*native_command(opt),'-fno-builtin','-fno-strict-aliasing','-mstackrealign',str(path),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stdout+p.stderr)
   p=subprocess.run([str(binary)],capture_output=True,timeout=60);self.assertEqual(p.returncode,0,(opt,p.returncode,p.stdout,p.stderr))
  self.receipt('native-contract',dict(profiles=['O0','O2','O3'],cases_per_profile=count,controls=sorted(controls()),trap_UBSan=True,typed_sound_narrowing=True,full_owner_canaries=True,guest_private_pointer_and_global_aliases_excluded=True))

def native_source():
 rows=[]
 for c in corpus():
  if c.phase or c.mode&34 or not math.isfinite(guest.floating(c.angle)):continue
  i=len(rows);c=replace(c,result=(0,1,0xFFFFFFFF,0x80)[i%4],sample=(0,0x3F400000,0x3F800001,0xBF000001)[i%4],coordinates=((0x3FA00000,0xC0300000,0x46FFFF80),(0xC70000C0,0,0x46FFFF80),(0x471C40C0,0xC71C40C0,0xBF800000))[i%3])
  initial=guest.fixture(c);expected,calls,result,snaps=guest.reference(initial,c)
  inputs=[c.angle,c.tick,c.base,c.sample,c.result,c.mode,c.sound_phase,*c.coordinates,c.seed]
  outputs=[guest.read(expected,c.owner+off)for off in(0x170,0x174,0x18,0x1C,0x38,0x3C,0x40)]+[guest.read(expected,guest.symbols()[name])for name in('D_800AA434','D_800AA438','D_800AA43C','D_800AA440','D_800BE9A4')]
  kinds=[];arguments=[];snapshots=[]
  for (target,args),snapshot in zip(calls,snaps):
   kind={guest.SOUND:0,guest.SINE:1,guest.FINISH:2}[target];kinds.append(kind)
   args=list(args)
   if kind==0:args[5:]=[guest.u32(guest.half(v))for v in args[5:]]
   if kind==2:args=[0]
   arguments.append(args+[0]*(10-len(args)));snapshots.append(snapshot)
  kinds +=[0]*(3-len(kinds));arguments +=[[0]*10]*(3-len(arguments));snapshots +=[(0,)*4]*(3-len(snapshots))
  array=lambda values:'{'+','.join('0x%Xu'%(v&0xFFFFFFFF)for v in values)+'}'
  rows.append('{'+','.join((array(inputs),array(outputs),str(len(calls)),array(kinds),'{'+','.join(array(v)for v in arguments)+'}','{'+','.join(array(v)for v in snapshots)+'}'))+'}')
 text=match.ISOLATED_HEADER+match.SELECTED+'\n'
 for name,body in controls().items():text+=body.replace(match.FUNCTION,'negative_'+name)+'\n'
 text+='''
typedef struct {u32 in[11],expected[12],calls,kind[3],args[3][10],snapshots[3][4];} Row;
static const Row vectors[]={
'''+',\n'.join(rows)+'''\n};
typedef struct {u8 prefix[0x18];f32 x,y;u8 gap20[0x18];f32 xyz[3];u8 gap44[0x12C];f32 phase,base;u8 tail178[0x88];} Owner;
typedef char Layout[(sizeof(void*)==4&&sizeof(Owner)==0x200&&__builtin_offsetof(Owner,phase)==0x170&&__builtin_offsetof(Owner,xyz)==0x38)?1:-1];
typedef s32(*Fn)(u8*);
static Owner owner,want;static const Row*v;static u32 order,error;
f32 D_800AA434,D_800AA438,D_800AA43C,D_800AA440,D_800BE9A4;
static void copy(void*d,const void*s,u32 n){u32 i;for(i=0;i<n;i++)((u8*)d)[i]=((const u8*)s)[i];}
static u32 word(const void*p){u32 b;copy(&b,p,4);return b;}
static void set(void*p,u32 b){copy(p,&b,4);}
static int same(const void*a,const void*b,u32 n){u32 i;for(i=0;i<n;i++)if(((const u8*)a)[i]!=((const u8*)b)[i])return 0;return 1;}
static void emit(u32 kind,const u32*args,u32 count){u32 i;u32 snap[4];
 if(order>=v->calls){error=1;return;}
 if(kind!=v->kind[order])error=1;
 for(i=0;i<count;i++)if(args[i]!=v->args[order][i])error=1;
 snap[0]=word(&owner.phase);snap[1]=word(&owner.base);snap[2]=word(&owner.x);snap[3]=word(&owner.y);
 for(i=0;i<4;i++)if(snap[i]!=v->snapshots[order][i])error=1;order++;
}
__attribute__((noinline,noclone)) u16 func_10010F88(s32 a,u16 b,s16 c,u8 d,s32 e,s16 f,s16 g,s16 h,s16 i,s16 j){
 u32 args[10]={(u32)a,b,(u32)c,d,(u32)e,(u32)f,(u32)g,(u32)h,(u32)i,(u32)j};emit(0,args,10);
 if(v->in[5]&4){set(&owner.phase,v->in[6]);set(&owner.base,0x40400000);}
 if(v->in[5]&16)set(&owner.xyz[1],0xC2DE0000);
 if(v->in[5]&64)set(&D_800AA43C,0x3F000000);
 return 0xA55A;
}
__attribute__((noinline,noclone)) f32 sinf(f32 angle){f32 value;u32 arg=word(&angle);emit(1,&arg,1);
 if(v->in[5]&1){set(&owner.base,0xC0300000);set(&D_800AA440,0x3E000001);}
 set(&value,v->in[3]);return value;
}
__attribute__((noinline,noclone)) s32 func_15133894(u8*p){u32 arg=0;if(p!=(u8*)&owner)error=1;emit(2,&arg,1);
 if(v->in[5]&8){set(&owner.phase,0xC0A00000);set(&D_800BE9A4,0x3F000000);}
 return(s32)v->in[4];
}
__attribute__((noinline,noclone)) static s32 invoke(Fn fn,u8*p){return fn(p);}
static u32 initial_word(u32 off){u32 i,b=0;for(i=0;i<4;i++)b=(b<<8)|(u8)((off+i)*13+v->in[10]+0xA5);return b;}
static int check(Fn fn,const Row*row){u32 i;u32 offsets[7]={0x170,0x174,0x18,0x1C,0x38,0x3C,0x40};s32 answer;
 v=row;order=error=0;
 for(i=0;i<sizeof(owner);i++)((u8*)&owner)[i]=(u8)(i*13+v->in[10]+0xA5);
 set(&owner.phase,v->in[0]);set(&owner.base,v->in[2]);set(&owner.x,initial_word(0x18));set(&owner.y,initial_word(0x1C));for(i=0;i<3;i++)set(&owner.xyz[i],v->in[7+i]);
 set(&D_800AA434,0x3F80418A);set(&D_800AA438,0x41EF3333);set(&D_800AA43C,0x41490FDB);set(&D_800AA440,0x3D4CCCCD);set(&D_800BE9A4,v->in[1]);
 copy(&want,&owner,sizeof(owner));for(i=0;i<7;i++)set((u8*)&want+offsets[i],v->expected[i]);
 answer=invoke(fn,(u8*)&owner);
 if(error||order!=v->calls||(u32)answer!=v->in[4]||!same(&owner,&want,sizeof(owner)))return 1;
 if(word(&D_800AA434)!=v->expected[7]||word(&D_800AA438)!=v->expected[8]||word(&D_800AA43C)!=v->expected[9]||word(&D_800AA440)!=v->expected[10]||word(&D_800BE9A4)!=v->expected[11])return 1;
 return 0;
}
'''
 text+='static Fn negatives[]={'+','.join('negative_'+n for n in controls())+'};\n'
 text+='''static s32 run(void){u32 i,j,found;
 for(i=0;i<sizeof(vectors)/sizeof(vectors[0]);i++)if(check(func_151B5E94,&vectors[i]))return 1;
 for(j=0;j<sizeof(negatives)/sizeof(negatives[0]);j++){found=0;
  for(i=0;i<sizeof(vectors)/sizeof(vectors[0]);i++)if(check(negatives[j],&vectors[i])){found=1;break;}
  if(!found)return(s32)(10+j);
 }
 return 0;
}
'''+START
 return text,len(rows)

if __name__=='__main__':unittest.main()
