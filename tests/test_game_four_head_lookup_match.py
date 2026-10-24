"""Four selected heads: priority, byte ABI, home aliases and literal scheduling."""
from dataclasses import dataclass
from pathlib import Path
import csv,io,itertools,json,struct,subprocess,unittest
from tools.experiments import game_four_head_lookup_match as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT=Path(__file__).resolve().parents[2]
TABLE,MAP,NODES,OWNER=0x800DCE50,0x800A9270,0x200000,0x60000
PARENT,PARENT_ROM,PARENT_SIZE=0x151AE0E4,0x1DB594,384

@dataclass(frozen=True)
class Case:
    keyword:int=0
    pattern:int=2
    alias:int=0
    phase:int=0

def argument(c):
    return {4:NODES+0x120,5:78,6:NODES+0x20}.get(c.alias,c.keyword)&0xFFFFFFFF

def stack(c,table=TABLE,mapping=MAP):
    return {3:NODES+16,4:NODES+8,5:mapping,6:table+47*4}.get(c.alias,STACK+c.phase)

def fixture(c,table=TABLE,mapping=MAP):
    m={STACK+i:(i*17+0xA5)&255 for i in range(-512,512)}
    m.update({table+i:0 for i in range(0x340)})
    m.update({NODES+i:(i*13+0x5A)&255 for i in range(0x500)})
    put(m,mapping,47);put(m,mapping+4,78)
    heads=[];lists=[]
    for slot in range(4):
        n=0 if c.pattern==0 else(c.pattern+slot)%5
        nodes=[NODES+slot*0x100+j*0x20 for j in range(n)];lists.append(nodes)
        head=nodes[0]if nodes else 0;heads.append(head)
        for j,node in enumerate(nodes):
            tag=(slot*37+j*29+c.pattern)&255 if c.pattern<4 else (j+c.pattern)%3 if c.pattern<8 else (0,127,128,255)[(slot+j+c.pattern)%4]
            put(m,node+8,nodes[j+1]if j+1<n else 0);m[node+16]=tag
    if c.alias==1:heads=[heads[0]]*4
    elif c.alias==2:
        tail=NODES+0x450;put(m,tail+8,0);m[tail+16]=255
        for nodes in lists:
            if nodes:put(m,nodes[-1]+8,tail)
    elif c.alias==4:m[NODES+0x120+16]=32
    elif c.alias==5:
        m[NODES+0x200+16]=78
    elif c.alias==6:m[NODES+0x20+16]=32
    for slot,head in enumerate(heads):put(m,table+(slot%2)*416+(47 if slot<2 else 78)*4,head)
    return m

def reference(initial,c,table=TABLE,mapping=MAP):
    m=dict(initial);put(m,stack(c,table,mapping),argument(c));key=argument(c)&255
    for outer in range(2):
        column=read(m,mapping+outer*4)
        for row in range(2):
            node=read(m,table+row*416+column*4);steps=0
            while node:
                tag=m[node+16];next_=read(m,node+8)
                if tag==key:return m,node
                node=next_;steps+=1
                assert steps<100,'Fixture cycle'
    return m,0

class LookupOracle(RayOracle):
    def __init__(self,words,memory,c=Case(),entry=source.ENTRY,connected=None,arguments=None,table=TABLE,mapping=MAP):
        TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,
            arguments=arguments or(argument(c),),connected=connected)
        self.r[29]=self.before[29]=stack(c,table,mapping)
        self.hi,self.lo,self.condition=0x89ABCDEF,0x76543210,True
    def record_call(self,target):
        assert target==source.ENTRY
        args=self.arguments(1);self.calls.append((target,args));self.events.append(('CALL',target,args))
    def hook(self,target):raise AssertionError(('Unexpected lookup helper',target))

class CallerBoundary(Exception):pass

class BoundaryCode(dict):
    def __init__(self,base,boundary,passes=0):
        super().__init__(base);self.base,self.boundary,self.passes=base,boundary,passes
    def __getitem__(self,pc):
        word=self.base[pc]
        if pc==self.boundary:
            if not self.passes:raise CallerBoundary
            self.passes-=1
        return word

def controls():
    b=source.SELECTED[source.FUNCTION]
    row_major=b.replace('        column = D_800A9270[outer];\n','').replace(
        '            node = ((LookupRow1D92F0 *)D_800DCE50)[row].cells[column];',
        '            column = D_800A9270[row];\n            node = ((LookupRow1D92F0 *)D_800DCE50)[outer].cells[column];')
    return dict(one_column=b.replace('outer < 2','outer < 1'),one_row=b.replace('row < 2','row < 1'),
        reversed_columns=b.replace('D_800A9270[outer]','D_800A9270[1 - outer]'),
        row_major=row_major,neighbor_column=b.replace('cells[column]','cells[column + 1]'),
        wrong_key_byte=b.replace('node->key','node->reserved0C[3]'),
        signed_key=b.replace('key == node->key','(s8)key == node->key'),
        wrong_equality=b.replace('key == node->key','key != node->key'),
        truncate=b.replace('next = node->next','next = NULL'),
        return_next=b.replace('return node;','return next;'),
        mask_key=b.replace('    outer = 0;','    key &= 127;\n    outer = 0;'))

class FourHeadLookupTests(unittest.TestCase):
    receipt={}
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out)
        cls.rom=cls.values['conker/conker.us.bin'];cls.old=cls.values['conker/build/conker.us.elf']
        cls.truth=list(struct.unpack_from('>44I',cls.rom,source.ROM))
        data,fs=source.link_owner(ROOT,cls.out,cls.out/'qualified-padded.o',source.OWNER)
        cls.words=list(struct.unpack_from('>44I',data,fs[source.FUNCTION]['value']))
        data,fs=source.link_owner(ROOT,cls.out,cls.out/'after-owner.o',source.OWNER)
        cls.raw=list(struct.unpack_from('>43I',data,fs[source.FUNCTION]['value']))
        cls.parent=list(struct.unpack_from('>96I',cls.rom,PARENT_ROM))
    def compare(self,c=Case(),images=None,entry=source.ENTRY,table=TABLE,mapping=MAP):
        initial=fixture(c,table,mapping);expected,value=reference(initial,c,table,mapping);models=[]
        for words in images or(self.truth,self.words):
            m=LookupOracle(words,initial,c,entry=entry,table=table,mapping=mapping)
            saved=tuple(m.r[16:24])+tuple(m.r[28:32]);m.run()
            self.assertEqual(m.memory,expected,c);self.assertEqual(m.r[2],value,c);self.assertFalse(m.calls)
            self.assertEqual(tuple(m.r[16:24])+tuple(m.r[28:32]),saved)
            self.assertEqual((m.hi,m.lo,m.condition),(0x89ABCDEF,0x76543210,True));models.append(m)
        self.assertEqual(complete(models[0]),complete(models[1]))
        return models[0]
    def test_01_full_owner_actual_Make_and_original_bindings(self):
        q=json.loads((self.out/'qualification.json').read_text());mk=json.loads((self.out/'make-shadow.json').read_text())[0]
        self.assertEqual((q['total_words'],q['new_guards'],q['inserted_schedule_words']),(44,37,1))
        self.assertEqual(self.words,self.truth)
        self.assertEqual(source.normalized(*source.payload(self.out/'after-owner.o',source.FUNCTION)),
            source.payload(source.original(ROOT,self.out,source.FUNCTION),source.FUNCTION))
        before=source.parse_object(self.out/'before-owner.o')[1]
        self.assertEqual(q['preserved_neighbors'],len(before)-1)
        self.assertEqual((mk['actual_Make_commands'],mk['compact_functions_equal']),(5,len(before)))
        self.assertTrue(mk['complete_padded_object_equal'])
        self.assertEqual(self.values[source.SOURCE].decode().count('#pragma GLOBAL_ASM'),6)
        self.assertEqual(struct.unpack_from('>2I',self.rom,0x24DD30),(47,78))
        direct=[];literal=[]
        for at in range(0,len(self.rom)-3,4):
            word=struct.unpack_from('>I',self.rom,at)[0]
            if word==source.ENTRY:literal.append(at)
            if word>>26==3 and(word&0x3FFFFFF)==((source.ENTRY>>2)&0x3FFFFFF):direct.append(at)
        self.assertEqual(direct,[0x1DB5A8]);self.assertEqual(literal,[])
        self.receipt['owner']=dict(raw_words=43,fitted_words=44,guards=37,moved_existing_return_delay_words=1,
            neighbors=len(before)-1,handwritten_neighbors=6,Make_commands=5,bindings=4,prepared_reference_aligned_words=len(self.rom)//4,
            original_caller_direct_sites=direct,literal_pointer_sites=literal)
    def test_02_guest_keys_priority_shared_lists_and_home_aliases(self):
        count=0;visits=set()
        for key,pattern,(upper,phase)in itertools.product(range(256),range(12),((0,0),(0xA5A50000,8))):
            c=Case(upper|key,pattern,0,phase);m=self.compare(c);visits.update(m.visits)
            expected,value=reference(fixture(c),c);raw=LookupOracle(self.raw,fixture(c),c).run()
            self.assertEqual(raw.memory,expected);self.assertEqual(raw.r[2],value);count+=1
        alias_cases=0
        for alias,pattern,key in itertools.product(range(1,7),(2,6,8,11),(0,1,32,78,127,128,165,255)):
            c=Case(0xA5000000|key,pattern,alias);self.compare(c)
            expected,value=reference(fixture(c),c);raw=LookupOracle(self.raw,fixture(c),c).run()
            self.assertEqual(raw.memory,expected);self.assertEqual(raw.r[2],value);count+=1;alias_cases+=1
        reachable=set(range(source.ENTRY,source.ENTRY+176,4))-{source.ENTRY+31*4}
        self.assertTrue(reachable<=visits);self.assertNotIn(source.ENTRY+31*4,visits)
        self.receipt['guest']=dict(cases=count,all_key_bytes=True,byte_corner_hits=True,upper_homes=True,aliases=6,alias_cases=alias_cases,
            raw_C_public_semantics_checked=True,fitted_full_private_state_equal=True,reachable_words_visited=43,
            unreachable_retail_word=31,column_before_row_priority=True)
    def test_03_fixed_raw_binding_and_real_padder_controls(self):
        raw,bindings=source.payload(self.out/'after-owner.o',source.FUNCTION)
        self.assertEqual(source.digest(raw),source.RAW_SHA)
        for i in range(43):
            bad=bytearray(raw);bad[i*4+3]^=1
            with self.assertRaises(ValueError):source.normalized(bytes(bad),bindings)
        rejected=0
        for at in bindings:
            bad={k:list(v)for k,v in bindings.items()};del bad[at]
            with self.assertRaises(ValueError):source.normalized(raw,bad)
            rejected+=1
            bad={k:list(v)for k,v in bindings.items()};bad[at]=[(bad[at][0][0],'D_80000000')]
            with self.assertRaises(ValueError):source.normalized(raw,bad)
            rejected+=1
        for bad in(raw[:-4],raw+b'\0'*4):
            with self.assertRaises(ValueError):source.normalized(bad,bindings)
        old=self.values['conker/retail_word_patches.us.csv'];after=source.guard_bytes(old,raw,bindings)
        self.assertTrue(after.startswith(old));fields=list(csv.DictReader(io.StringIO(old.decode())).fieldnames)
        rows=list(csv.DictReader(io.StringIO(after[len(old):].decode()),fieldnames=fields))
        self.assertEqual(len(rows),37);self.assertEqual(sum(bool(x['insert_after'])for x in rows),1)
        self.assertEqual((rows[-1]['offset'],rows[-1]['insert_after']),('0x0A8','0x00000000'))
        self.assertEqual(sum(x['expected_relocations']!='-'for x in rows),4)
        self.assertEqual(sum(x['replacement_relocations']!='-'for x in rows),4)
        for column,value in(('expected','0x00000000'),('expected_relocations','R_MIPS_26:func_151AE590')):
            badrows=[dict(row)for row in rows];badrows[0][column]=value
            stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');writer.writerows(badrows)
            p=self.out/('bad-padder-'+column+'.csv');p.write_bytes(old+stream.getvalue().encode())
            with self.assertRaises(ValueError):source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=p,filename=source.OWNER)
        bad=bytearray(old);bad[-5]^=1
        with self.assertRaises(ValueError):source.guard_bytes(bytes(bad),raw,bindings)
        self.receipt['guards']=dict(raw_word_controls=43,binding_controls=rejected,extent_controls=2,padder_controls=2,prefix_control=1,
            old_prefix_identical=True,existing_return_delay_moved_not_padding_filler=True)
    def test_04_actual_original_caller_windows(self):
        cases=0;visits=set()
        gates=((1,1,0),(0x8000,1,0),(0xFFFF,1,0),(0,0,0),(0,1,1),(0,1,0))
        for key,(half,enabled,busy)in itertools.product(range(256),gates):
            c=Case(key,8);initial=fixture(c);head=read(initial,TABLE+47*4);initial[head+16]=key
            put(initial,head+0x52,half,2);initial.update({OWNER+i:0 for i in range(0x400)})
            initial[OWNER+0x1CA]=enabled;initial[OWNER+0x104]=busy
            models=[];boundary=half==0 and enabled!=0 and busy==0
            for words in(self.truth,self.words):
                connected={source.ENTRY+i*4:w for i,w in enumerate(words)}
                m=LookupOracle(self.parent,initial,c,entry=PARENT,connected=connected,arguments=(OWNER,0xA5A50000|key))
                if boundary:
                    m.code=BoundaryCode(m.code,0x151AE134)
                    with self.assertRaises(CallerBoundary):m.run()
                    self.assertEqual(m.r[5],head);self.assertEqual(m.r[16],OWNER)
                else:m.run()
                self.assertEqual(m.calls,[(source.ENTRY,(key,))]);self.assertEqual(m.r[2],head)
                self.assertEqual(read(m.memory,STACK-0x38),key)
                self.assertEqual(read(m.memory,STACK+4),0xA5A50000|key)
                visits.update(m.visits);models.append(m)
            self.assertEqual(complete(models[0]),complete(models[1]));cases+=1
        for key in range(256):
            c=Case(key,0);initial=fixture(c);models=[]
            for words in(self.truth,self.words):
                m=LookupOracle(self.parent,initial,c,entry=PARENT,
                    connected={source.ENTRY+i*4:w for i,w in enumerate(words)},arguments=(OWNER,0xABCD0000|key))
                m.code=BoundaryCode(m.code,0x151AE108,passes=1)
                with self.assertRaises(CallerBoundary):m.run()
                self.assertEqual((m.r[2],m.r[5]),(0,0));self.assertEqual(m.calls,[(source.ENTRY,(key,))])
                self.assertIn(0x151AE10C,m.visits);models.append(m)
            self.assertEqual(complete(models[0]),complete(models[1]));cases+=1
        self.receipt['caller']=dict(cases=cases,original_words=96,return_gates=5,all_key_bytes=True,
            NULL_spin_one_iteration=True,continuation_boundary='151AE134',signed_halfword_values=[1,0x8000,0xFFFF],
            original_call_window_only=True,current_C_caller_still_stub=True,remaining_math_helper_path_not_qualified=True)
    def test_05_native32_semantic_C_and_effective_controls(self):
        body=source.SELECTED[source.FUNCTION];variants=dict(selected=body,**controls())
        for name,b in variants.items():
            if name!='selected':self.assertNotEqual(b,body,name)
        text=source.HEADERS+source.DECLARATIONS+'''
u8 D_800DCE50[0x340] __attribute__((aligned(4)));
s32 D_800A9270[2]={47,78};
static LookupNode1D92F0 nodes[4][4],tail;
static u8 beforeTable[0x340],beforeNodes[sizeof(nodes)],beforeTail[sizeof(tail)];
typedef char ABI[(sizeof(void*)==4&&sizeof(LookupRow1D92F0)==416&&
 __builtin_offsetof(LookupNode1D92F0,next)==8&&__builtin_offsetof(LookupNode1D92F0,key)==16)?1:-1];
static u32 word(const void*p){u32 v,i;for(i=0;i<4;i++)((u8*)&v)[i]=((const u8*)p)[i];return v;}
static void copy(u8*d,const u8*s,u32 n){u32 i;for(i=0;i<n;i++)d[i]=s[i];}
static int equal(const u8*a,const u8*b,u32 n){u32 i;for(i=0;i<n;i++)if(a[i]!=b[i])return 0;return 1;}
static void setup(u32 pattern,u32 alias){
 u32 i,j,n;LookupNode1D92F0*heads[4];
 for(i=0;i<0x340;i++)D_800DCE50[i]=0;
 for(i=0;i<sizeof(nodes);i++)((u8*)nodes)[i]=(u8)(i*13+0x5A);
 for(i=0;i<sizeof(tail);i++)((u8*)&tail)[i]=(u8)(i*17+0xA5);
 tail.next=0;tail.key=255;
 for(i=0;i<4;i++){
  n=pattern?(pattern+i)%5:0;heads[i]=n?nodes[i]:0;
  for(j=0;j<n;j++){
   nodes[i][j].next=j+1<n?nodes[i]+j+1:alias==2?&tail:0;
   nodes[i][j].key=(u8)(pattern<4?i*37+j*29+pattern:pattern<8?(j+pattern)%3:
    ((u32[]){0,127,128,255})[(i+j+pattern)%4]);
  }
 }
 if(alias==1)for(i=0;i<4;i++)heads[i]=heads[0];
 for(i=0;i<4;i++)*(LookupNode1D92F0**)(void*)(D_800DCE50+(i%2)*416+(i<2?47:78)*4)=heads[i];
 copy(beforeTable,D_800DCE50,sizeof(beforeTable));copy(beforeNodes,(u8*)nodes,sizeof(nodes));copy(beforeTail,(u8*)&tail,sizeof(tail));
}
static LookupNode1D92F0*model(u8 key){
 u32 col,row,p,next;
 for(col=0;col<2;col++)for(row=0;row<2;row++){
  p=word(D_800DCE50+row*416+(u32)D_800A9270[col]*4);
  while(p){next=word((u8*)p+8);if(*((u8*)p+16)==key)return(LookupNode1D92F0*)p;p=next;}
 }
 return 0;
}
'''
        for name,b in variants.items():text+=b.replace(source.FUNCTION,name)+'\n'
        text+='''
typedef LookupNode1D92F0*(*Lookup)(u8);
static int variant(Lookup fn){
 u32 key,pattern,alias;LookupNode1D92F0*wanted,*actual;
 for(pattern=0;pattern<12;pattern++)for(alias=0;alias<3;alias++)for(key=0;key<256;key++){
  setup(pattern,alias);wanted=model((u8)key);actual=fn((u8)key);
  if(actual!=wanted||!equal(beforeTable,D_800DCE50,sizeof(beforeTable))||
   !equal(beforeNodes,(u8*)nodes,sizeof(nodes))||!equal(beforeTail,(u8*)&tail,sizeof(tail))||
   D_800A9270[0]!=47||D_800A9270[1]!=78)return 23;
 }
 return 0;
}
int run(void){
'''
        for i,name in enumerate(variants):text+='if(variant(%s)!=%d)return %d;\n'%(name,0 if name=='selected'else 23,11+i)
        text+='return 0;}\n'+START
        for opt in('-O0','-O2','-O3'):
            p=self.out/('native-'+opt[1:]+'.c');p.write_text(text);binary=p.with_suffix('')
            result=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual(subprocess.run([str(binary)],timeout=60).returncode,0,opt)
        self.receipt['native']=dict(profiles=['O0','O2','O3'],cases_per_profile=9216,effective_controls=len(variants)-1,
            actual_semantic_C=True,canonical_pointer_byte_ABI=True,trap_UBSan=True,readonly_table_and_nodes=True,stack_home_aliases_guest_only=True)
    def test_06_fault_prefixes_and_next_load_on_success(self):
        count=0
        for c in(Case(),Case(0xA5000000|255,11),Case(127,0),Case(0,2,1),Case(255,6,2),Case(0,8,3),Case(0,2,4),Case(0,2,5),Case(0,2,6)):
            m=self.compare(c);initial=fixture(c)
            for fault in range(m.root_accesses):
                models=[]
                for words in(self.truth,self.words):
                    x=LookupOracle(words,initial,c);x.root_fault=fault
                    with self.assertRaises(faults.AccessBoundary):x.run()
                    self.assertEqual(x.root_accesses,fault);models.append(x)
                self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        c=Case(37,2);initial=fixture(c);head=read(initial,TABLE+47*4);initial[head+16]=37
        put(initial,head+8,0xDEADBEEF);models=[]
        for words in(self.truth,self.words):
            x=LookupOracle(words,initial,c).run();self.assertEqual(x.r[2],head);self.assertEqual(x.r[6],0xDEADBEEF);models.append(x)
        self.assertEqual(complete(models[0]),complete(models[1]))
        bad=list(self.words);bad[26]=0
        x=LookupOracle(bad,initial,c).run();self.assertEqual(x.r[2],head);self.assertNotEqual(complete(x),complete(models[0]))
        c=Case(38,2);models=[]
        for words in(self.truth,self.words):
            x=LookupOracle(words,initial,c)
            with self.assertRaisesRegex(AssertionError,'unmapped read'):x.run()
            models.append(x)
        self.assertEqual(complete(models[0]),complete(models[1]))
        self.receipt['faults']=dict(pairs=count,hit_still_loads_next=True,skipped_next_load_negative_effective=True,
            miss_invalid_next_fault=True,emitted_guest_order_only=True)
    def test_07_independent_GNU_rebases_and_priority_negative(self):
        fitted,bindings=source.normalized(*source.payload(self.out/'after-owner.o',source.FUNCTION))
        objects=[source.original(ROOT,self.out,source.FUNCTION)]
        asm,missing=emit_function(fitted,dict(value=0,size=176),bindings,source.FUNCTION,{'D_800DCE50':TABLE,'D_800A9270':MAP})
        self.assertFalse(missing);p=self.out/'independent-fitted.s';p.write_text(asm);obj=p.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-mabi=32','-o',str(obj),str(p)],capture_output=True,check=True);objects.append(obj)
        links=0
        for i,(entry,table,mapping)in enumerate(((source.ENTRY,TABLE,MAP),(source.ENTRY+0x200000,0x80107FF0,0x80127FF8),(source.ENTRY+0x500000,0x80218010,0x80238000))):
            images=[]
            for j,obj in enumerate(objects):
                p=self.out/('link-%d-%d.ld'%(i,j));elf=p.with_suffix('.elf')
                p.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p),'-e',source.FUNCTION,
                    '--defsym=D_800DCE50=0x%X'%table,'--defsym=D_800A9270=0x%X'%mapping,'-o',str(elf),str(obj)],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>44I',sections(elf)['.text'][1])));links+=1
            self.assertEqual(*images)
            for key in(0,1,127,128,255):self.compare(Case(key,8),images=images,entry=entry,table=table,mapping=mapping)
        b=controls()['row_major'];obj,diag=source.compile_owner(ROOT,self.out,source.HEADERS+source.DECLARATIONS+b,'negative-row-major')
        self.assertFalse(diag);data,fs=source.link_owner(ROOT,self.out,obj,source.OWNER);info=fs[source.FUNCTION]
        words=list(struct.unpack_from('>%dI'%(info['size']//4),data,info['value']))
        c=Case(1,6);expected,value=reference(fixture(c),c)
        x=LookupOracle(words,fixture(c),c).run();self.assertEqual(x.memory,expected);self.assertNotEqual(x.r[2],value)
        self.receipt['links']=dict(independent_GNU_links=links,layouts=3,four_HI_LO_bindings=True,carry_boundaries=True,
            actual_MIPS_row_major_negative_effective=True)
    def test_08_strict_image_and_frozen_inputs(self):
        pred=source.predicted_image(self.old,source.truths(self.values));source.check_image(self.old,(self.out/'first-linked.elf').read_bytes(),source.truths(self.values))
        report=json.loads((self.out/'first-link.json').read_text())
        self.assertEqual(sum(a!=b for a,b in zip(self.old,pred)),report['changed_bytes'])
        self.assertEqual(report['closed_symbol_cycles'],1)
        cycle={name:(offset,location)for offset,name,_,location in source.symbol_rows(self.old)if name=='D_80095BCC'}
        for at in(0,len(pred)-1,source.elf_slot_offset(pred,source.ENTRY,176),source.elf_slot_offset(pred,PARENT,12),
                cycle['D_80095BCC'][0]+4,cycle['D_80095BCC'][1]):
            bad=bytearray(pred);bad[at]^=1
            with self.assertRaises(ValueError):source.check_image(self.old,bytes(bad),source.truths(self.values))
        installed=(ROOT/source.SOURCE).read_bytes()!=self.values[source.SOURCE]
        source.check_inputs(ROOT,self.out,installed)
        self.receipt['strict']=dict(changed_bytes=report['changed_bytes'],code_bytes=report['code_bytes_changed'],
            metadata_bytes=report['metadata_bytes_changed'],closed_symbol_cycles=1,exclusions=0,corruptions=6,focused_inputs=36)

if __name__=='__main__':unittest.main()
