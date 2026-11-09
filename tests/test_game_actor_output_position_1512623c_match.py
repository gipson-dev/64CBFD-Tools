"""Direct actor position query: whole owner/image, output aliases and real call windows."""
from dataclasses import replace
import csv,itertools,json,struct,subprocess,unittest
from pathlib import Path
from tools.experiments import game_actor_output_position_1512623c_match as match
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests import game_actor_output_position_1512623c_oracle as guest
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_projected_packet_draw import native_command
ROOT=match.ROOT

def corpus():
 for i,(matrix,category,alternate,height,mode,phase)in enumerate(itertools.product((0,guest.MATRIX),(0,26,27,28,0x100001B,0x8000001B),(0,1,16,256,0x80000000),(-32768,-1,0,1,32767),(0,3,4,12,27),(0,8))):
  yield guest.Case(matrix=matrix,category=category,alternate=alternate,height=height,mode=mode,phase=phase,flag=(0,1,0xFFFFFFFF)[i%3])
 for axis,word,mode in itertools.product(range(3),(0,0x80000000,1,0x7F7FFFFF,0x7F800000,0xFF800000,0x7FC12345),(0,3)):
  xyz=list(guest.Case().position);xyz[axis]=word;yield guest.Case(matrix=0,position=tuple(xyz),mode=mode)

def aliases():
 for phase in(0,8):
  home=guest.STACK+phase
  variants=[{},dict(outputs=(guest.OUTPUT,)*3),dict(outputs=(guest.ACTOR+0x18,guest.ACTOR+0x1C,guest.ACTOR+0x14)),dict(outputs=(guest.META+0x114,guest.OUTPUT+4,guest.OUTPUT+8)),dict(outputs=(guest.OUTPUT,guest.META+0x114,guest.OUTPUT+8)),dict(metadata=guest.ACTOR+0x18-0x114),dict(outputs=(home-24,guest.OUTPUT+4,guest.OUTPUT+8)),dict(outputs=(home-4,guest.OUTPUT+4,guest.OUTPUT+8))]
  for spec,matrix,category,alternate,mode in itertools.product(variants,(0,guest.MATRIX),(0,27),(0,16),(0,3,4,12,27)):
   yield guest.Case(**spec,matrix=matrix,category=category,alternate=alternate,mode=mode,phase=phase,height=-32768)

def controls():
 b=match.SELECTED
 override=b.replace('        } else if (category == 0x1B) {','        }\n        if (category == 0x1B) {').replace('        } else {\n            fallback = 1;','        } else if (!alternate) {\n            fallback = 1;')
 cached_y=b.replace('        *x = actor->x_position;','        f32 cachedY = actor->y_position;\n        *x = actor->x_position;').replace('*y = actor->y_position +','*y = cachedY +')
 cached_z=b.replace('        *x = actor->x_position;','        f32 cachedZ = actor->z_position;\n        *x = actor->x_position;').replace('*z = actor->z_position;','*z = cachedZ;')
 return dict(category_override=override,narrow_category=b.replace('category == 0x1B','(u8)category == 0x1B'),narrow_alternate=b.replace('alternate != 0','(u8)alternate != 0'),wrong_slot3=b.replace('matrixIndex = 3','matrixIndex = 2'),wrong_slot4=b.replace('matrixIndex = 4','matrixIndex = 3'),wrong_stride=b.replace('matrixIndex * 0x40','matrixIndex * 0x44'),wrong_height_sign=b.replace('(f32)metadata->height','(f32)(u16)metadata->height'),wrong_height_scale=b.replace('0.75f','0.5f'),cached_y=cached_y,cached_z=cached_z,wrong_point=b.replace('input[1] = 20.0f','input[1] = 21.0f'),skip_helper=b.replace('func_15143134(input, output, matrix);','(void)matrix; (void)input; output[0] = output[1] = output[2] = 0.0f;'))

def linked(obj,entry,label,out,defs=None):
 defs=defs or guest.symbols();text,functions,bindings=parse_object(obj);f=functions[match.FUNCTION];assembly,unknown=emit_function(text,f,bindings,match.FUNCTION,defs);assert not unknown;p=out/label
 p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%(n,a)for n,a in defs.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack_from('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1]))

class ActorOutputPositionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/'conker/conker.us.bin').read_bytes();cls.truth=list(struct.unpack_from('>79I',cls.rom,match.ROM));cls.raw=linked(cls.out/'qualified-owner.o',match.ENTRY,'raw-suite',cls.out);cls.fitted=linked(cls.prepared['qualified_object'],match.ENTRY,'fitted-suite',cls.out);cls.blob,cls.refs=match.function_blob(cls.out/'qualified-owner.o');assert cls.truth==cls.raw==cls.fitted
 def receipt(self,name,value):(self.out/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')
 def compare(self,c,images=None,entry=match.ENTRY,defs=None,initial=None):
  initial=guest.fixture(c)if initial is None else initial;expected,calls,obs,flag=guest.reference(initial,c,helper=(defs or guest.symbols())['func_15143134']);models=[]
  for words in images or(self.truth,self.raw,self.fitted):
   m=guest.Oracle(words,initial,c,entry,syms=defs).run();self.assertTrue((guest.public(m.memory),m.calls,m.point_observations)==(guest.public(expected),calls,obs),(c,'public contract'));self.assertEqual(m.r[2],flag);models.append(m)
  self.assertTrue(all(guest.complete(m)==guest.complete(models[0])for m in models),(c,'complete private state'));return models
 def test_01_owner_actual_Make_direct_body_and_strict_image(self):
  q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['raw_neighbors'],q['padded_neighbors'],q['diagnostics']),(79,72,0,44,44,5));self.assertEqual((q['actual_Make']['commands'],q['actual_Make']['functions'],q['actual_Make']['diagnostics']),(5,45,5));self.assertEqual((q['strict_changed_bytes'],q['exclusions'],q['named_metadata_rows']),(230,0,0));self.assertTrue(q['direct_C']);self.assertEqual(match.normalize(self.blob,self.refs),(self.blob,self.refs));self.assertEqual(match.guard_rows(self.blob,self.refs),[])
  self.assertEqual((self.out/'qualified-guards.csv').read_bytes(),(self.out/'frozen'/match.GUARDS).read_bytes())
  self.assertEqual((ROOT/'conker/asm/nonmatchings/game_14FF90/func_151279A0.s').read_bytes(),(self.out/'frozen/conker/asm/nonmatchings/game_14FF90/func_151279A0.s').read_bytes())
  before_obj=parse_object(self.out/'predecessor-owner.o')[1];after_obj=parse_object(self.out/'qualified-owner.o')[1];overflow=[]
  for r in csv.DictReader((ROOT/'conker/retail_layout.us.txt').open()):
   if r['filename']!=match.OWNER:continue
   name=r['function'];slot=int(r['end'],16)-int(r['address'],16)
   if before_obj[name]['size']>slot:overflow.append(dict(function=name,retail_bytes=slot,compiled_bytes=before_obj[name]['size']));self.assertEqual(before_obj[name]['size'],after_obj[name]['size'])
  self.assertTrue(overflow);self.assertNotIn(match.FUNCTION,[r['function']for r in overflow])
  self.receipt('owner-audit',dict(inherited_diagnostics=5,new_diagnostics=0,preserved_GLOBAL_ASM=1,oversized_neighbors=overflow,independent_padder='isolated target',whole_owner_no_exclusions=True))
  for at in range(316):
   bad=bytearray(self.blob);bad[at]^=1
   with self.assertRaises(ValueError):match.normalize(bytes(bad),self.refs)
  refs={172:[('R_MIPS_26','wrong')]}
  with self.assertRaises(ValueError):match.normalize(self.blob,refs)
  before,after=self.prepared['predecessor_elf'].read_bytes(),self.prepared['qualified_elf'].read_bytes()
  for at in(0x80,len(after)-1,match.elf_slot_offset(before,match.ENTRY,316)):
   bad=bytearray(after);bad[at]^=1
   with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),self.rom[match.ROM:match.ROM+316])
 def test_02_guest_priority_height_and_all_words(self):
  count=0;seen=set()
  for c in corpus():seen.update(self.compare(c)[0].visits);count+=1
  self.assertEqual(seen,set(range(match.ENTRY,match.ENTRY+316,4)))
  c=guest.Case(category=27,alternate=16);initial=guest.fixture(c)
  for i in range(0x114,0x116):initial.pop(c.metadata+i,None)
  for i in range(0x14,0x20):initial.pop(c.actor+i,None)
  self.compare(c,initial=initial)
  self.receipt('guest-contract',dict(cases_per_body=count,visited_words=79,alternate_precedes_category27=True,full_word_category_and_alternate=True,signed_height=True,transform_unused_payload_unmapped=True,hardware_NaN_FCSR_claimed=False))
 def test_03_output_aliases_and_literal_fault_prefixes(self):
  count=0
  for c in aliases():self.compare(c);count+=1
  cuts=delay=0
  for matrix,category,alternate,mode,phase in itertools.product((0,guest.MATRIX),(0,27),(0,16),(0,3,12,27),(0,8)):
   c=guest.Case(matrix=matrix,category=category,alternate=alternate,mode=mode,phase=phase,height=-32768);initial=guest.fixture(c);model=guest.Oracle(self.truth,initial,c).run()
   for cut in range(model.all_accesses):
    pair=[guest.Oracle(w,initial,c)for w in(self.truth,self.raw,self.fitted)]
    for m in pair:
     m.cut=cut
     with self.assertRaises(faults.AccessBoundary):m.run()
    self.assertTrue(all(guest.complete(m)==guest.complete(pair[0])and(m.current_pc,m.delay_of)==(pair[0].current_pc,pair[0].delay_of)for m in pair));cuts+=1;delay+=pair[0].delay_of is not None
  self.receipt('aliases-faults',dict(alias_cases_per_body=count,fired_prefix_triples=cuts,delay_slot_cuts=delay,complete_private_state=True,portable_private_alias_or_fault_claimed=False))
 def test_04_original_seven_argument_call_windows_and_return_use(self):
  count=0;seen=[set(),set()]
  for index,matrix,category,alternate,height,phase in itertools.product((0,1),(0,guest.MATRIX),(0,27,0x100001B),(0,16,0xFFFFFFFF),(-32768,32767),(0,8)):
   c=guest.Case(matrix=matrix,category=category,alternate=alternate,height=height,phase=phase);pair=[]
   for words in(self.truth,self.raw,self.fitted):
    m,initial,child=guest.caller_machine(words,c,self.rom,index,actual_point=True);expected,calls,obs,flag=guest.reference(initial,child,actual_point=True)
    with self.assertRaises(guest.WindowBoundary):m.run()
    selected=[r for r in m.calls if r[0]in(match.ENTRY,guest.POINT)];self.assertTrue((guest.public(m.memory),selected,m.point_observations,m.target_entries)==(guest.public(expected),[(match.ENTRY,guest.arguments(child)),*calls],obs,[guest.arguments(child)]),c);pair.append(m);seen[index].update(m.visits)
   self.assertTrue(all(guest.complete(m)==guest.complete(pair[0])for m in pair));count+=1
  for i,(start,_,n,_)in enumerate(guest.WINDOWS):self.assertTrue(set(range(start,start+4*n,4))<=seen[i])
  audits=[guest.return_use_audit(self.rom,start)for start in(0x1512669C,0x15126BF4)]
  for at in(0x15126BF4,0x15126C24):
   bad=bytearray(self.rom);struct.pack_into('>I',bad,at-0x15000000+0x2D4B0,0x00406021)
   with self.assertRaises(ValueError):guest.return_use_audit(bytes(bad),0x15126BF4)
  self.receipt('callers',dict(cases_per_body=count,windows=[dict(entry=hex(s),words=n,end=hex(e))for s,_,n,e in guest.WINDOWS],arguments=7,void_return_use_audits=audits,full_parent_claimed=False))
 def test_05_actual_point_helper_and_bounded_matrix_leaves(self):
  count=0;seen=set()
  for category,alternate,fixed,height,phase in itertools.product((0,27,0x100001B),(0,16,0xFFFFFFFF),(0,1,255),(-32768,0,32767),(0,8)):
   c=guest.Case(category=category,alternate=alternate,fixed_matrix=fixed,height=height,phase=phase);initial=guest.fixture(c);expected,calls,obs,flag=guest.reference(initial,c,actual_point=True);pair=[]
   for words in(self.truth,self.raw,self.fitted):
    m=guest.connected_machine(words,initial,c,self.rom).run();selected=[r for r in m.calls if r[0]==guest.POINT];self.assertTrue((guest.public(m.memory),selected,m.point_observations)==(guest.public(expected),calls,obs),c)
    leaves=[r[0]for r in m.calls if r[0]in(guest.CONVERT,guest.TRANSFORM,guest.TRANSLATE)];self.assertEqual(leaves,([guest.CONVERT]if fixed else[])+[guest.TRANSFORM]if calls else[]);pair.append(m);seen.update(m.visits)
   self.assertTrue(all(guest.complete(m)==guest.complete(pair[0])for m in pair));count+=1
  before=self.prepared['predecessor_elf'].read_bytes();at=match.elf_slot_offset(before,guest.POINT,392);self.assertEqual(before[at:at+392],self.rom[0x1705E4:0x1705E4+392])
  self.receipt('connections',dict(cases_per_body=count,helper_words=98,visited_helper_words=len(set(range(guest.POINT,guest.POINT+392,4))&seen),before_ELF_equals_retail=True,float_and_fixed_formats=True,existing_leaf_providers_bounded=True,full_gameplay_claimed=False))
 def test_06_independent_GNU_links_and_jump_regions(self):
  from tools.tests.test_game_view_list_setup import ViewListSetupTests
  ctx=type('Original',(),dict(root=ROOT,out=self.out));original=ViewListSetupTests.original.__func__(ctx,'original-actor-output',(ROOT/'conker/asm/nonmatchings/game_14FF90/func_1512623C.s').read_text(),match.FUNCTION);count=links=0
  for i,entry in enumerate((match.ENTRY,0x18017FFC,0x2500FFFC)):
   defs=guest.symbols()if i==0 else dict(func_15143134=(entry&0xF0000000)+0x5048004)
   images=[linked(p,entry,'rebase-%d-%d'%(i,j),self.out,defs)for j,p in enumerate((original,self.out/'qualified-owner.o',self.prepared['qualified_object']))];links+=3;self.assertTrue(images[0]==images[1]==images[2])
   for matrix,category,alternate,mode,phase in itertools.product((0,guest.MATRIX),(0,27),(0,16),(0,3,12),(0,8)):self.compare(guest.Case(matrix=matrix,category=category,alternate=alternate,mode=mode,phase=phase),images,entry,defs);count+=1
  self.receipt('rebases',dict(GNU_links=links,cases_per_body=count,independent_original_raw_padded=True,jump_region_bindings=True))
 def test_07_effective_compiled_semantic_controls(self):
  rows=controls();self.assertEqual(len(rows),12);cases=[c for c in itertools.chain(corpus(),aliases())if c.mode in(0,3)and all(not guest.STACK-2048<=p<guest.STACK+2304 for p in c.outputs)];evidence={}
  call_view=lambda calls:[(t,('input','output',a[2])if t==guest.POINT else a)for t,a in calls]
  obs_view=lambda obs:[(a[2],point,xyz,height)for a,point,xyz,height in obs]
  for name,body in rows.items():
   self.assertNotEqual(body,match.SELECTED);obj,diag=compile_owner(ROOT,self.out,match.ISOLATED_HEADER+body,'negative-'+name);self.assertFalse(diag);words=linked(obj,match.ENTRY,'negative-link-'+name,self.out)
   for c in cases:
    initial=guest.fixture(c);expected,calls,obs,flag=guest.reference(initial,c);m=guest.Oracle(words,initial,c).run()
    if(guest.public(m.memory),call_view(m.calls),obs_view(m.point_observations))!=(guest.public(expected),call_view(calls),obs_view(obs)):evidence[name]=dict(matrix=hex(c.matrix),category=c.category,alternate=c.alternate,height=c.height,outputs=[hex(p)for p in c.outputs],mode=c.mode,private_pointer_addresses_ignored=True);break
   self.assertIn(name,evidence,name)
  self.receipt('compiled-controls',evidence)
 def test_08_native32_profiles_typed_outputs_and_canaries(self):
  text,count=native_source();out=self.out/'native';out.mkdir(exist_ok=True)
  for opt in('-O0','-O2','-O3'):
   p=out/(opt[1:]+'.c');binary=p.with_suffix('.elf');p.write_text(text);r=subprocess.run([*native_command(opt),'-fno-builtin','-fno-strict-aliasing','-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stdout+r.stderr);r=subprocess.run([str(binary)],capture_output=True,timeout=60);self.assertEqual(r.returncode,0,(opt,r.returncode,r.stdout,r.stderr))
  self.receipt('native-contract',dict(cases_per_profile=count,profiles=['O0','O2','O3'],effective_controls=sorted(controls()),trap_UBSan=True,typed_seven_argument_ABI=True,full_actor_metadata_output_canaries=True,private_and_metadata_aliases_excluded=True))

def native_source():
 rows={'selected':match.SELECTED,**controls()}
 bodies='\n'.join(b.replace(match.FUNCTION,n).replace('void '+n+'(', '__attribute__((noinline,noclone)) void '+n+'(')for n,b in rows.items())
 checks='\n'.join('if(variant(%s)!=%d)return %d;'%(n,0 if n=='selected'else 23,40+i)for i,n in enumerate(rows))
 return match.ISOLATED_HEADER+'''
typedef char PointerWidth[sizeof(void*)==4&&sizeof(s32)==4?1:-1];
typedef char ActorX[__builtin_offsetof(struct127,x_position)==0x14?1:-1];
typedef char ActorY[__builtin_offsetof(struct127,y_position)==0x18?1:-1];
typedef char ActorZ[__builtin_offsetof(struct127,z_position)==0x1C?1:-1];
typedef char MatrixOffset[__builtin_offsetof(struct127,unk1D4)==0x1D4?1:-1];
typedef char HeightOffset[__builtin_offsetof(ActorPositionMetadata14FF90,height)==0x114?1:-1];
typedef void(*Callback)(struct127*,ActorPositionMetadata14FF90*,s32,f32*,f32*,f32*,s32);
typedef struct{u8 before[32];struct127 actor;u8 after[32];} ActorArena;
typedef struct{u8 before[16];ActorPositionMetadata14FF90 metadata;u8 after[16];} MetadataArena;
typedef struct{f32 words[4];u8 after[16];} OutputArena;
static ActorArena a;static MetadataArena b;static OutputArena o;
static u8 ea[sizeof(a)],eb[sizeof(b)],eo[sizeof(o)];
static f32 matrices[5][4][4],otherMatrices[5][4][4];
static u32 calls,bad,mode,slot;
static void bytes(void*d,const void*s,u32 n){u8*dst=d;const u8*src=s;u32 i;for(i=0;i<n;i++)dst[i]=src[i];}
static u8 *mapped(void*p){u32 v=(u32)p;
 if(v-(u32)&a<sizeof(a))return ea+(v-(u32)&a);
 if(v-(u32)&b<sizeof(b))return eb+(v-(u32)&b);
 if(v-(u32)&o<sizeof(o))return eo+(v-(u32)&o);
 return 0;}
static f32 eget(f32*p){f32 v;bytes(&v,mapped(p),4);return v;}
static void eset(f32*p,f32 v){bytes(mapped(p),&v,4);}
__attribute__((noinline,noclone)) void func_15143134(f32*point,f32*out,u8*matrix){
 f32 y=slot==3?20.0f:116.0f,z=slot==3?0.0f:130.0f;calls++;
 if(matrix!=(u8*)matrices+slot*64||point[0]!=0.0f||point[1]!=y||point[2]!=z)bad=1;
 out[0]=3.25f+point[1]*0.5f;out[1]=-4.5f+point[2]*0.25f;out[2]=5.75f;
 if(mode&1){a.actor.x_position=5.5f;a.actor.y_position=-7.25f;a.actor.z_position=0.5f;b.metadata.height=-19;}
 if(mode&2)a.actor.unk1D4=(struct255*)otherMatrices;
}
''' + bodies + '''
static int one(Callback fn,u32 matrix,u32 category,u32 alternate,s32 height,u32 layout,u32 plan,u32 pattern){
 u32 i,want=matrix&&(alternate||category==27);f32 *x=&o.words[0],*y=&o.words[1],*z=&o.words[2];
 static const f32 positions[3][3]={{1.25f,-2.5f,0.125f},{-0.0f,1.0000001f,-1000.0f},{1.0e30f,1.0e-30f,-7.25f}};
 for(i=0;i<sizeof(a);i++)((u8*)&a)[i]=(u8)(i*13+37);
 for(i=0;i<sizeof(b);i++)((u8*)&b)[i]=(u8)(i*17+53);
 for(i=0;i<sizeof(o);i++)((u8*)&o)[i]=(u8)(i*19+71);
 a.actor.x_position=positions[pattern][0];a.actor.y_position=positions[pattern][1];a.actor.z_position=positions[pattern][2];
 a.actor.unk1D4=matrix?(struct255*)matrices:0;b.metadata.height=(s16)height;
 if(layout==1)y=z=x;
 if(layout==2){x=&a.actor.y_position;y=&a.actor.z_position;z=&a.actor.x_position;}
 if(layout==3)x=y=z=&a.actor.x_position;
 if(layout==4)y=&a.actor.z_position;
 if(layout==5)x=&a.actor.y_position;
 bytes(ea,&a,sizeof(a));bytes(eb,&b,sizeof(b));bytes(eo,&o,sizeof(o));calls=bad=0;mode=plan;slot=alternate?3:4;
 if(want){
  f32 py=slot==3?20.0f:116.0f,pz=slot==3?0.0f:130.0f;
  if(mode&1){s16 h=-19;eset(&a.actor.x_position,5.5f);eset(&a.actor.y_position,-7.25f);eset(&a.actor.z_position,0.5f);bytes(mapped(&b.metadata.height),&h,2);}
  if(mode&2){struct255*p=(struct255*)otherMatrices;bytes(mapped(&a.actor.unk1D4),&p,4);}
  eset(x,3.25f+py*0.5f);eset(y,-4.5f+pz*0.25f);eset(z,5.75f);
 }else{
  f32 scaled;eset(x,eget(&a.actor.x_position));scaled=(f32)(s16)height*0.75f;
  eset(y,eget(&a.actor.y_position)+scaled);eset(z,eget(&a.actor.z_position));
 }
 fn(&a.actor,&b.metadata,(s32)category,x,y,z,(s32)alternate);
 if(calls!=want||bad)return 23;
 for(i=0;i<sizeof(a);i++)if(((u8*)&a)[i]!=ea[i])return 23;
 for(i=0;i<sizeof(b);i++)if(((u8*)&b)[i]!=eb[i])return 23;
 for(i=0;i<sizeof(o);i++)if(((u8*)&o)[i]!=eo[i])return 23;
 return 0;
}
static int variant(Callback fn){u32 m,c,t,h,l,p,n,count=0;
 static const u32 categories[6]={0,26,27,28,0x100001B,0x8000001B};
 static const u32 alternates[6]={0,1,16,256,0x80000000,0xFFFFFFFF};
 static const s32 heights[5]={-32768,-1,0,1,32767};
 for(m=0;m<2;m++)for(c=0;c<6;c++)for(t=0;t<6;t++)for(h=0;h<5;h++)for(l=0;l<6;l++)for(p=0;p<4;p++)for(n=0;n<3;n++){
  if(one(fn,m,categories[c],alternates[t],heights[h],l,p,n))return 23;count++;
 }
 return count==25920?0:24;
}
static int run(void){CHECKS return 0;}
__attribute__((force_align_arg_pointer)) void _start(void){int code=run();__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
'''.replace('CHECKS',checks),25920
