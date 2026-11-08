"""Type46 updater: source/ABI, owner/image, original dispatcher/helpers and native C."""
from dataclasses import replace
import csv,io,itertools,json,math,struct,subprocess,unittest
from pathlib import Path
from tools.experiments import game_type46_record_update_150c5568_match as match
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests import game_type46_record_update_150c5568_oracle as guest
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
ROOT=match.ROOT

def corpus():
 for i,(flags,selector,result,mode,phase)in enumerate(itertools.product((0,1,2,3,0x80000001,0xFFFFFFFF),(-1,0,1),(0,1,0xFFFFFFFF),(0,1,2,4,8,16,32,64,128,256,512,1024),(0,8))):
  yield guest.Case(flags=flags,selector=selector,callback_result=result,mode=mode,phase=phase,points=guest.POINTS[(i//2)%4],seed=i%255,gate=(0,1,255)[(i//2)%3])
 for selector,axis,point,phase in itertools.product((-128,-2,0,1,127),range(3),guest.POINTS,(0,8)):yield guest.Case(selector=selector,mode=1,seed=axis,points=point,phase=phase)

def controls():
 b=match.SELECTED
 return dict(wrong_active=b.replace('record->active & 1','record->active == 1'),wrong_sentinel=b.replace('selector != -1','selector != 0'),
  unsigned_selector=b.replace('(s8)record->payload.attributes[0]','(u8)record->payload.attributes[0]'),
  wrong_snapshot=b.replace('oldX = record->payload.first[0] - record->payload.second[0]','oldX = record->payload.second[0] - record->payload.first[0]'),
  all_axes_required=b.replace('delta[0] != oldX || delta[1] != oldY || delta[2] != oldZ','delta[0] != oldX && delta[1] != oldY && delta[2] != oldZ'),
  always_length=b.replace('delta[0] != oldX || delta[1] != oldY || delta[2] != oldZ','delta[0] != oldX || delta[1] != oldY || delta[2] != oldZ || 1'),
  wrong_status=b.replace('D_80088760[selector]((u8 *)record) == 0','D_80088760[selector]((u8 *)record) == 1'),
  missing_release=b.replace('            func_1516972C((struct102 *)record);',''),
  missing_cache=b.replace('record->distance = func_15143E64(delta);','func_15143E64(delta);'),
  wrong_cache=b.replace('record->distance = func_15143E64(delta);','*(f32 *)((u8 *)record + 0xC4) = func_15143E64(delta);'))

def linked(obj,entry,label,out,defs=None):
 defs=defs or guest.symbols();text,functions,bindings=parse_object(obj);f=functions[match.FUNCTION];assembly,unknown=emit_function(text,f,bindings,match.FUNCTION,defs);assert not unknown;p=out/label
 p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%(n,a)for n,a in defs.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack_from('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1]))

class Type46UpdateTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/'conker/conker.us.bin').read_bytes();cls.truth=list(struct.unpack_from('>79I',cls.rom,match.ROM));cls.raw=linked(cls.out/'qualified-owner.o',match.ENTRY,'raw-suite',cls.out);cls.fitted=linked(cls.prepared['qualified_object'],match.ENTRY,'fitted-suite',cls.out);cls.blob,cls.refs=match.function_blob(cls.out/'qualified-owner.o');assert cls.fitted==cls.truth
 def receipt(self,name,value):(self.out/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')
 def compare(self,c,images=None,entry=None,defs=None,initial=None):
  initial=guest.fixture(c,defs)if initial is None else initial;expected,calls,vectors,snaps=guest.reference(initial,c,defs);models=[]
  for words in images or(self.truth,self.raw,self.fitted):
   m=guest.Oracle(words,initial,c,entry=entry,s=defs).run();self.assertTrue((guest.public(m.memory),m.calls,m.vectors,m.snapshots)==(guest.public(expected),calls,vectors,snaps),(c,'public contract'));models.append(m)
  self.assertTrue(guest.full_state(models[0])==guest.full_state(models[-1]),(c,'literal state'));return models
 def test_01_owner_actual_Make_guard_and_whole_image_rejections(self):
  q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['raw_neighbors'],q['padded_neighbors']),(79,64,14,14,14));self.assertEqual((q['actual_Make']['commands'],q['actual_Make']['functions']),(3,15));self.assertEqual((q['strict_changed_bytes'],q['exclusions'],q['named_metadata_rows']),(280,0,2))
  proof=match.certificate(self.blob,self.refs);self.assertEqual(sorted(proof['permutation']),list(range(79)));self.assertEqual((proof['insertions'],proof['omissions']),(0,0))
  ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom[:len(self.rom)&~3]);self.assertEqual([i*4 for i,w in enumerate(ws)if match.ENTRY<=w<match.ENTRY+316],[0x230DA0]);self.assertFalse([w for w in ws if w>>26 in(2,3)and match.ENTRY<=(((w&0x3FFFFFF)<<2)|0x10000000)<match.ENTRY+316]);self.assertEqual(guest.descriptor_pointer(70),0x8008C2E0)
  for at in range(316):
   bad=bytearray(self.blob);bad[at]^=1
   with self.assertRaises(ValueError):match.normalize(bytes(bad),self.refs)
  for at in self.refs:
   refs=dict(self.refs);refs[at]=[(refs[at][0][0],'wrong')]
   with self.assertRaises(ValueError):match.normalize(self.blob,refs)
  rows=list(csv.DictReader(io.StringIO((self.out/'qualified-guards.csv').read_text())));indices=[i for i,r in enumerate(rows)if r['function']==match.FUNCTION];self.assertEqual(len(indices),14)
  for index in indices:
   altered=[dict(r)for r in rows];altered[index]['expected']='0x%08X'%(int(altered[index]['expected'],16)^1);p=self.out/('rejected-%d.csv'%index)
   with p.open('w',newline='')as stream:w=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(altered)
   with self.assertRaises(ValueError):emit_padded_assembly(self.out/'qualified-owner.o',ROOT/'conker/asm/F2820.s',filename=match.OWNER,word_patches_path=p)
  before,after=self.prepared['predecessor_elf'].read_bytes(),self.prepared['qualified_elf'].read_bytes()
  for at in(0x80,len(after)-1,match.elf_slot_offset(before,match.ENTRY,316),2787412,2787428,3069280,3069294):
   bad=bytearray(after);bad[at]^=1
   with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),self.rom[match.ROM:match.ROM+316])
 def test_02_guest_signed_selectors_live_deltas_and_all_words(self):
  count=0;visits=set()
  for c in corpus():visits.update(self.compare(c)[0].visits);count+=1
  self.assertEqual(visits,set(range(match.ENTRY,match.ENTRY+316,4)))
  # The inactive gate requires only the flags word and its private frame.
  c=guest.Case(flags=0);initial=guest.fixture(c)
  for i in range(0x18,0xC4):initial.pop(c.record+i,None)
  self.compare(c,initial=initial)
  self.receipt('guest-contract',dict(cases_per_body=count,visited_words=79,inactive_payload_unmapped=True,signed_selector_and_minus_one_skip=True,snapshot_live_float_equality=True,NaN_FCSR_hardware_equivalence_claimed=False))
 def test_03_aliases_and_literal_fault_prefixes(self):
  count=0
  for record,mode,gate,phase in itertools.product((guest.RECORD,guest.ALT),(4,8,16,32,128,512),(0,1,255),(0,8)):
   self.compare(guest.Case(record=record,mode=mode|1,gate=gate,phase=phase));count+=1
  cuts=delay=0
  for flags,selector,result,mode,phase in itertools.product((0,1),(-1,0,1),(0,1),(0,1,8),(0,8)):
   c=guest.Case(flags=flags,selector=selector,callback_result=result,mode=mode,phase=phase);initial=guest.fixture(c);m=guest.Oracle(self.truth,initial,c).run()
   for cut in range(m.all_accesses):
    pair=[guest.Oracle(code,initial,c)for code in(self.truth,self.fitted)]
    for model in pair:
     model.cut=cut
     with self.assertRaises(faults.AccessBoundary):model.run()
    self.assertTrue(guest.full_state(pair[0])==guest.full_state(pair[1]),(c,cut));self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));cuts+=1;delay+=pair[0].delay_of is not None
  self.receipt('aliases-faults',dict(alias_cases_per_body=count,fired_prefix_pairs=cuts,delay_slot_cuts=delay,complete_fitted_private_state=True,raw_private_fault_or_portable_C_alias_claimed=False))
 def test_04_original_dispatcher_cursor_and_two_record_walk(self):
  count=0;visits=set()
  for flags,selector,live,depth,next_record in itertools.product((0,1),(-1,0,1),(0,1),(0,1,3),(0,guest.ALT)):
   c=guest.ConnectedCase(flags=flags,selector=selector,live=live,depth=depth,next_record=next_record);pair=[]
   for code in(self.truth,self.raw,self.fitted):
    machine,initial=guest.caller_machine(self.rom,code,c);expected=dict(initial);calls=[];vectors=[];snaps=[];entries=[];p=c.record
    while p:
     entries.append(p);guest.put(expected,guest.CURSORS+4*depth,guest.read(expected,p+8));expected,cc,vv,ss=guest.connected_reference(expected,replace(c,record=p));calls.append((match.ENTRY,(p,)));calls.extend(cc);vectors.extend(vv);snaps.extend(ss);p=guest.read(expected,guest.CURSORS+4*depth);self.assertLessEqual(len(entries),2)
    expected[guest.COUNT]=(depth-1)&255
    with self.assertRaises(guest.WindowBoundary):machine.run()
    self.assertTrue((guest.public(machine.memory),machine.calls,machine.vectors,machine.snapshots,machine.target_entries)==(guest.public(expected),calls,vectors,snaps,entries),(c,'caller'));self.assertEqual(machine.r[16],0);visits.update(machine.visits);pair.append(machine)
   self.assertTrue(guest.full_state(pair[0])==guest.full_state(pair[-1]));count+=1
  self.assertTrue(set(range(guest.WINDOW,guest.END,4))<=visits);self.receipt('callers',dict(cases_per_body=count,original_words=14,one_and_two_record_walks=True,return_ignored=True,cursor_detach_and_depth=True,complete_parent_claimed=False))
 def test_05_original_callbacks_length_release_and_detach(self):
  seen=set();count=0;table=self.rom[0x22FF68:0x22FF68+101*0x34];null_type=next(i for i in range(2,101)if struct.unpack_from('>I',table,i*0x34+0x28)[0]==0)
  for selector,live,key,matrix,kind,depth in itertools.product((-1,0,1),(0,1),(0xA7,0xA6),(False,True),(0,1,70,null_type),(0,1,3)):
   c=guest.ConnectedCase(selector=selector,live=live,saved_identity=key,matrix=matrix,record_type=kind,depth=depth);initial=guest.connected_fixture(c,self.rom);expected,calls,vectors,snaps=guest.connected_reference(initial,c);pair=[]
   for code in(self.truth,self.raw,self.fitted):
    model=guest.ConnectedOracle(code,initial,c,self.rom).run();self.assertTrue((guest.public(model.memory),model.calls,model.vectors,model.snapshots)==(guest.public(expected),calls,vectors,snaps),(c,'helpers'));seen.update(model.visits);pair.append(model)
   self.assertTrue(guest.full_state(pair[0])==guest.full_state(pair[-1]));count+=1
  before=(self.out/'frozen'/match.ELF).read_bytes()
  helpers=[dict(entry=hex(e),literal_words=n,visited_words=len(set(range(e,e+4*n,4))&seen),before_ELF_equals_retail=before[match.elf_slot_offset(before,e,n*4):match.elf_slot_offset(before,e,n*4)+n*4]==self.rom[p:p+n*4])for e,p,n in guest.HELPERS]
  self.assertEqual([h['visited_words']for h in helpers],[18,37,12,28,20]);self.receipt('connections',dict(cases_per_body=count,helpers=helpers,authentic_callback_slots=2,descriptor_slot=70,null_destructor_type=null_type,transform_destructor_and_fallback_bounded=True,full_gameplay_claimed=False))
 def test_06_independent_GNU_links_and_signed_LO_carries(self):
  from tools.tests.test_game_view_list_setup import ViewListSetupTests
  ctx=type('Original',(),dict(root=ROOT,out=self.out));original=ViewListSetupTests.original.__func__(ctx,'original-type46-update',(ROOT/'conker/asm/F2820.s').read_text(),match.FUNCTION);count=links=0
  for i,entry in enumerate((match.ENTRY,0x18017FFC,0x2500FFFC)):
   defs=guest.symbols()if i==0 else dict(D_80088760=(0x80107FFC,0x80108004)[i-1],func_15143E64=(entry&0xF0000000)+0x5030004,func_1516972C=(entry&0xF0000000)+0x5048004)
   images=[linked(p,entry,'rebase-%d-%d'%(i,j),self.out,defs)for j,p in enumerate((original,self.out/'qualified-owner.o',self.prepared['qualified_object']))];links+=3;self.assertEqual(images[0],images[2])
   for selector,result,mode,phase in itertools.product((-1,0,1),(0,1),(0,1,4,8,32),(0,8)):
    self.compare(guest.Case(selector=selector,callback_result=result,mode=mode,phase=phase),images,entry,defs);count+=1
  self.receipt('rebases',dict(GNU_links=links,cases_per_body=count,independent_original_raw_fitted=True,HI_LO_carry_edges=True))
 def test_07_effective_compiled_semantic_controls(self):
  rows=controls();self.assertEqual(len(rows),10);evidence={};cases=[guest.Case(flags=flags,selector=selector,callback_result=result,mode=mode,seed=axis,points=points)for flags,selector,result,mode,axis,points in itertools.product((1,3),(-1,0,1),(0,1,0xFFFFFFFF),(0,1,2),(0,1,2),guest.POINTS[:3])]
  # Different private stack allocations alone are not semantic negatives.
  calls_public=lambda calls:[(target,('delta',)if target==guest.LENGTH else args)for target,args in calls]
  for name,body in rows.items():
   self.assertNotEqual(body,match.SELECTED);obj,diag=compile_owner(ROOT,self.out,match.ISOLATED_HEADER+body,'negative-'+name);self.assertFalse(diag);code=linked(obj,match.ENTRY,'negative-link-'+name,self.out)
   for c in cases:
    initial=guest.fixture(c);expected,calls,vectors,snaps=guest.reference(initial,c);model=guest.Oracle(code,initial,c).run()
    if(guest.public(model.memory),calls_public(model.calls),model.vectors,model.snapshots)!=(guest.public(expected),calls_public(calls),vectors,snaps):evidence[name]=dict(flags=c.flags,selector=c.selector,result=c.callback_result,mode=c.mode,axis=c.seed,private_pointer_addresses_ignored=True);break
   self.assertIn(name,evidence,name)
  self.receipt('compiled-controls',evidence)
 def test_08_native32_profiles_typed_callbacks_and_full_record(self):
  text,count=native_source();out=self.out/'native';out.mkdir(exist_ok=True)
  for opt in('-O0','-O2','-O3'):
   path=out/(opt[1:]+'.c');binary=path.with_suffix('.elf');path.write_text(text);p=subprocess.run([*native_command(opt),'-fno-builtin','-fno-strict-aliasing','-mstackrealign',str(path),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stdout+p.stderr);p=subprocess.run([str(binary)],capture_output=True,timeout=60);self.assertEqual(p.returncode,0,(opt,p.returncode,p.stdout,p.stderr))
  self.receipt('native-contract',dict(cases_per_profile=count,profiles=['O0','O2','O3'],controls=sorted(controls()),trap_UBSan=True,typed_callbacks_and_record_layout=True,whole_record_canaries=True,guest_private_aliases_excluded=True))

def native_source():
 rows=[]
 for i,(flags,selector,result,mode,points,axis)in enumerate(itertools.product((0,1,2,3,0xFFFFFFFF),(0,1,-1),(0,1,0xFFFFFFFF),(0,1,2,64,256,1024),guest.POINTS[:3],range(3))):
  c=guest.Case(flags=flags,selector=selector,callback_result=result,mode=mode,points=points,seed=(i//3)*3%252+axis,length_result=(0,0x80000000,0x41280000,0x3F800001)[i%4]);initial=guest.fixture(c);expected,calls,vectors,snaps=guest.reference(initial,c)
  inputs=[c.flags,c.selector&255,c.callback_result,c.length_result,c.mode,c.seed,*c.points]
  outputs=[];padding=[]
  for p in(guest.RECORD,guest.ALT):
   outputs.append([guest.read(expected,p+0x10),expected[p+0x30],*(guest.read(expected,p+off)for off in(0x18,0x1C,0x20,0x24,0x28,0x2C,0xC0))]);padding.append(expected[p+0x3C])
  kinds=[];slots=[];snapshots=[]
  for (target,args),snapshot in zip(calls,snaps):
   kind=1 if target==guest.LENGTH else 2 if target==guest.RELEASE else 0;kinds.append(kind);slots.append(0 if target==guest.CB0 else 1 if target==guest.CB1 else 0);snapshots.append(snapshot[1:])
  kinds +=[0]*(3-len(kinds));slots +=[0]*(3-len(slots));snapshots +=[(0,)*9]*(3-len(snapshots));vector=vectors[0]if vectors else(0,0,0)
  array=lambda values:'{'+','.join('0x%Xu'%(v&0xFFFFFFFF)for v in values)+'}'
  rows.append('{'+','.join((array(inputs),'{'+','.join(array(v)for v in outputs)+'}',array(padding),str(len(calls)),array(kinds),array(slots),'{'+','.join(array(v)for v in snapshots)+'}',array(vector)))+'}')
 text=match.ISOLATED_HEADER+match.SELECTED+'\n'
 for name,body in controls().items():text+=body.replace(match.FUNCTION,'negative_'+name)+'\n'
 text+='''
typedef struct {u32 in[12],expected[2][9],padding[2],calls,kinds[3],slots[3],snapshots[3][9],vector[3];} Row;
static const Row vectors[]={
'''+',\n'.join(rows)+'''\n};
typedef struct {Type46DistanceRecord record;u8 fence[56];} Ledger;
typedef char Layout[(sizeof(void*)==4&&sizeof(Type46DistanceRecord)==200&&sizeof(Ledger)==256&&__builtin_offsetof(Type46DistanceRecord,payload)==0x18&&__builtin_offsetof(Type46DistanceRecord,distance)==0xC0)?1:-1];
typedef void(*Fn)(u8*);typedef s32(*Callback)(u8*);
static Ledger actual[2],want[2];static const Row*v;static u32 order,error;
static void copy(void*d,const void*s,u32 n){u32 i;for(i=0;i<n;i++)((u8*)d)[i]=((const u8*)s)[i];}
static u32 word(const void*p){u32 b;copy(&b,p,4);return b;}
static void set(void*p,u32 b){copy(p,&b,4);}
static int same(const void*a,const void*b,u32 n){u32 i;for(i=0;i<n;i++)if(((const u8*)a)[i]!=((const u8*)b)[i])return 0;return 1;}
static void emit(u32 kind,u32 slot,u8*p,const f32*delta){u32 i,snapshot[9];Type46DistanceRecord*r=&actual[0].record;
 if(p!=(u8*)r)error=1;
 if(order>=v->calls){error=1;return;}
 if(kind!=v->kinds[order]||(kind==0&&slot!=v->slots[order]))error=1;
 snapshot[0]=word(&r->active);snapshot[1]=r->payload.attributes[0];
 for(i=0;i<3;i++){snapshot[2+i]=word(&r->payload.first[i]);snapshot[5+i]=word(&r->payload.second[i]);}snapshot[8]=word(&r->distance);
 for(i=0;i<9;i++)if(snapshot[i]!=v->snapshots[order][i])error=1;
 if(kind==1)for(i=0;i<3;i++)if(word(delta+i)!=v->vector[i])error=1;
 order++;
}
static s32 apply_callback(u8*p,u32 slot){u32 axis=v->in[5]%3;Type46DistanceRecord*r=(Type46DistanceRecord*)(void*)p;emit(0,slot,p,(const f32*)0);
 if(v->in[4]&1)r->payload.second[axis]+=1.0f;
 if(v->in[4]&2){r->payload.first[axis]+=1.0f;r->payload.second[axis]+=1.0f;}
 if(v->in[4]&1024)set(&r->active,word(&r->active)&~1u);
 return(s32)v->in[2];
}
__attribute__((noinline,noclone)) static s32 cb0(u8*p){return apply_callback(p,0);}
__attribute__((noinline,noclone)) static s32 cb1(u8*p){return apply_callback(p,1);}
__attribute__((noinline,noclone)) static s32 bad_slot(u8*p){return apply_callback(p,255);}
Callback D_80088760[256]={[0]=cb0,[1]=cb1,[2 ... 255]=bad_slot};
__attribute__((noinline,noclone)) f32 func_15143E64(f32*p){f32 result;emit(1,0,(u8*)&actual[0].record,p);
 if(v->in[4]&64)set(&actual[0].record.payload.first[2],0xC1980000);
 set(&result,v->in[3]);return result;
}
__attribute__((noinline,noclone)) void func_1516972C(struct102*p){u8*bytes=(u8*)(void*)p;emit(2,0,bytes,(const f32*)0);if(v->in[4]&256)bytes[0x3C]^=0x55;}
__attribute__((noinline,noclone)) static void invoke(Fn fn,u8*p){fn(p);}
static void initialize(Ledger*l){u32 i;Type46DistanceRecord*r=&l->record;
 for(i=0;i<sizeof(*l);i++)((u8*)l)[i]=(u8)(i*13+v->in[5]+0x59);
 r->header[0]=70;r->header[1]=0;for(i=4;i<12;i++)r->header[i]=0;
 set(&r->active,v->in[0]);r->payload.attributes[0]=(u8)v->in[1];r->payload.attributes[8]=0;set(&r->distance,0xC1200000);
 for(i=0;i<3;i++){set(&r->payload.first[i],v->in[6+i]);set(&r->payload.second[i],v->in[9+i]);}
}
static int check(Fn fn,const Row*row){u32 i,j;v=row;order=error=0;
 for(i=0;i<2;i++){initialize(&actual[i]);copy(&want[i],&actual[i],sizeof(Ledger));
  set(&want[i].record.active,v->expected[i][0]);want[i].record.payload.attributes[0]=(u8)v->expected[i][1];
  for(j=0;j<3;j++){set(&want[i].record.payload.first[j],v->expected[i][2+j]);set(&want[i].record.payload.second[j],v->expected[i][5+j]);}
  set(&want[i].record.distance,v->expected[i][8]);((u8*)&want[i])[0x3C]=(u8)v->padding[i];
 }
 invoke(fn,(u8*)&actual[0].record);
 return error||order!=v->calls||!same(actual,want,sizeof(actual));
}
'''
 text+='static Fn negatives[]={'+','.join('negative_'+n for n in controls())+'};\n'
 text+='''static s32 run(void){u32 i,j,found;
 for(i=0;i<sizeof(vectors)/sizeof(vectors[0]);i++)if(check(func_150C5568,&vectors[i]))return 1;
 for(j=0;j<sizeof(negatives)/sizeof(negatives[0]);j++){found=0;
  for(i=0;i<sizeof(vectors)/sizeof(vectors[0]);i++)if(check(negatives[j],&vectors[i])){found=1;break;}
  if(!found)return(s32)(10+j);
 }
 return 0;
}
'''+START
 return text,len(rows)

if __name__=='__main__':unittest.main()
