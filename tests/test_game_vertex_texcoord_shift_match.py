"""Vertex texture-coordinate shift: live fields, guard closure and strict linked image."""
from dataclasses import dataclass
from pathlib import Path
import csv,io,itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_vertex_texcoord_shift_match as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2]
RECORD,FIRST,SECOND=0x30000,0x50000,0x70000

def half(m,a):return(m[a]<<8)|m[a+1]
def sethalf(m,a,v):m[a]=(v>>8)&255;m[a+1]=v&255
def signed(v):return(v^32768)-32768

@dataclass(frozen=True)
class Case:
    packed:int=0x0003FFFB
    count:int=3
    buffer:int=0
    layout:int=0
    pattern:int=0
    phase:int=0

def fixture(c,selector=source.SELECTOR):
    m={STACK+c.phase+i:(i*17+0xA5)&255 for i in range(-64,64)}
    for base,size in((RECORD,0x480),(FIRST-32,0x300),(SECOND-32,0x300),(selector-64,256)):
        for i in range(size):m[base+i]=(i*13+c.pattern*37+(base>>16))&255
    p,q=FIRST,SECOND
    if c.layout==1:q=p
    elif c.layout==2:q=p+16
    elif c.layout==3:p=RECORD+0xE;q=FIRST
    elif c.layout==4:p=RECORD+0x34;q=FIRST
    elif c.layout==5:p=selector-8;q=FIRST
    elif c.layout==6:p=RECORD+0x18;q=SECOND
    elif c.layout==7:p=RECORD+0xC;q=FIRST
    elif c.layout==8:q=p+2
    put(m,RECORD+0x20,p);put(m,RECORD+0x24,q);put(m,RECORD+0x3C,c.packed);sethalf(m,RECORD+0x16,c.count);m[selector]=c.buffer
    if c.buffer>1:
        put(m,RECORD+0x20+4*c.buffer,SECOND);put(m,RECORD+0x20+4*(c.buffer^1),SECOND)
    if c.layout==3:put(m,RECORD+0x3C,0);sethalf(m,q+8,1);sethalf(m,q+10,2);sethalf(m,q+24,0);sethalf(m,q+26,0x1357)
    elif c.layout==4:put(m,RECORD+0x3C,0x00010002);sethalf(m,q+8,5);sethalf(m,q+10,7)
    elif c.layout==5:put(m,RECORD+0x3C,0);sethalf(m,q+8,0x100);sethalf(m,q+10,3)
    elif c.layout==6:put(m,RECORD+0x3C,0);sethalf(m,q+8,5);sethalf(m,q+10,7)
    elif c.layout==7:put(m,RECORD+0x3C,0);sethalf(m,q+8,3);sethalf(m,q+10,1)
    return m

def reference(initial,selector=source.SELECTOR,limit=64):
    m=dict(initial);packed=read(m,RECORD+0x3C);ds,dt=signed(packed>>16),signed(packed&65535);index=0
    while index<half(m,RECORD+0x16):
        assert index<limit,'Reference fixture must terminate in its declared domain'
        for at,delta in((8,ds),(10,dt)):
            b=m[selector];p=read(m,RECORD+0x20+4*(not b));value=signed(half(m,p+16*index+at));q=read(m,RECORD+0x20+4*b);sethalf(m,q+16*index+at,value+delta)
        index+=1
    return m,ds&0xFFFFFFFF,index

class TexcoordOracle(RayOracle):
    def __init__(self,words,memory,c=Case(),entry=source.ENTRY):
        TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=(RECORD,));self.hi=0x89ABCDEF;self.lo=0x76543210;self.condition=True
    def execute(self,word):
        op=word>>26
        if op not in(33,41):return super().execute(word)
        rs,rt,imm=word>>21&31,word>>16&31,word&65535;at=(self.r[rs]+(imm if imm<32768 else imm-65536))&0xFFFFFFFF
        self.dispatched_word=word;self.own_instruction=True
        try:
            if op==33:self.r[rt]=signed(self.get(at,2))&0xFFFFFFFF
            else:self.put(at,self.r[rt]&65535,2)
            self.r[0]=0
        finally:self.own_instruction=False
    def record_call(self,target):raise AssertionError(('Unexpected texture-coordinate call',hex(target)))
    def hook(self,target):raise AssertionError(target)

def controls():
    b=source.SELECTED
    result=dict(wrong_high_shift=b.replace('packedOffset >> 16','packedOffset >> 15'),
        wrong_low=b.replace('packedOffset & 0xFFFF','packedOffset >> 16'),
        wrong_second_source=b.replace('record->buffers[!D_800BE9C0] + offset + 10','record->buffers[!D_800BE9C0] + offset + 8'),
        wrong_destination=b.replace('record->buffers[D_800BE9C0]','record->buffers[!D_800BE9C0]'),
        subtract_s=b.replace('+ offsetS;','- offsetS;'),subtract_t=b.replace('+ offsetT;','- offsetT;'),
        wrong_stride=b.replace('offset += 16','offset += 8'),
        byte_store=b.replace('*(s16 *)(record->buffers[D_800BE9C0]','*(s8 *)(record->buffers[D_800BE9C0]'))
    assert all(x!=b for x in result.values());return result

def native_harness():
    text=source.HEADERS+source.DECLARATIONS+'''
u8 D_800BE9C0;
#define SLOTS 0x10004
static Vtx actual[2*SLOTS+16],expected[2*SLOTS+16];
static TexcoordShiftRecord record;
typedef void(*Handler)(TexcoordShiftRecord*);
typedef char ABI[(sizeof(void*)==4&&sizeof(s32)==4&&sizeof(Vtx)==16&&
 __builtin_offsetof(Vtx,v.tc)==8&&__builtin_offsetof(TexcoordShiftRecord,vertexCount)==0x16&&
 __builtin_offsetof(TexcoordShiftRecord,buffers)==0x20&&__builtin_offsetof(TexcoordShiftRecord,packedOffset)==0x3C&&
 sizeof(TexcoordShiftRecord)==0x40)?1:-1];
'''
    for label,body in dict(selected=source.SELECTED,**controls()).items():text+=body.replace(source.FUNCTION,label)+'\n'
    text+='''static int one(Handler fn,u32 count,u32 packed,u32 buffer,u32 alias,u32 indirect){
 u32 i,j;u32 n=count+4;u8*p=(u8*)&record;u8 *a=(u8*)(actual+4),*b=(u8*)(actual+SLOTS+8),*x=(u8*)(expected+4),*y=(u8*)(expected+SLOTS+8);
 s32 ds=(s16)(packed>>16),dt=(s16)packed;s16 *src,*dst;
 for(i=0;i<sizeof(record);i++)p[i]=(i*13+packed)&255;
 for(i=0;i<n*16+32;i++){a[(s32)i-16]=x[(s32)i-16]=(i*17+packed)&255;b[(s32)i-16]=y[(s32)i-16]=(i*19+(packed>>16)+3)&255;}
 if(alias==1){b=a;y=x;}else if(alias==2){b=a+16;y=x+16;}
 record.vertexCount=count;record.packedOffset=(s32)packed;record.buffers[0]=a;record.buffers[1]=b;D_800BE9C0=buffer;
 for(i=0;i<count;i++){
  src=(s16*)((buffer?x:y)+16*i+8);dst=(s16*)((buffer?y:x)+16*i+8);*dst=(s16)(*src+ds);
  src=(s16*)((buffer?x:y)+16*i+10);dst=(s16*)((buffer?y:x)+16*i+10);*dst=(s16)(*src+dt);
 }
 if(indirect){Handler volatile dispatch=fn;dispatch(&record);}else fn(&record);
 if(record.vertexCount!=count||(u32)record.packedOffset!=packed||record.buffers[0]!=a||record.buffers[1]!=b||D_800BE9C0!=buffer)return 1;
 for(j=0;j<2;j++){u8*u=(u8*)(actual+(j?SLOTS+8:4));u8*v=(u8*)(expected+(j?SLOTS+8:4));for(i=0;i<n*16+32;i++)if(u[(s32)i-16]!=v[(s32)i-16])return 1;}
 return 0;
}
static const u32 packs[]={0,0x7FFF8000u,0x80007FFFu,0xFFFFFFFFu,0x0003FFFBu};
static int variant(Handler fn,u32 full){u32 c,p,b,a,d;const u32 counts[]={0,1,2,3,7,16,0x7FFF,0x8000,0xFFFF};
 for(c=0;c<(full?9u:4u);c++)for(p=0;p<5;p++)for(b=0;b<2;b++)for(a=0;a<(full?3u:1u);a++)for(d=0;d<2;d++)
  if(one(fn,counts[c],packs[p],b,a,d))return 23;return 0;
}
int run(void){if(variant(selected,1))return 1;
'''
    for i,label in enumerate(controls()):text+='if(variant(%s,0)!=23)return %d;\n'%(label,11+i)
    return text+'return 0;}\n'+START,9*5*2*3*2

class VertexTexcoordShiftTests(unittest.TestCase):
    receipt={}
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
        cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>46I',rom,source.ROM))
        data,fs=source.link_owner(ROOT,cls.fresh,cls.out/'qualified-padded.o',source.OWNER);cls.words=list(struct.unpack_from('>46I',data,fs[source.FUNCTION]['value']))
        data,fs=source.link_owner(ROOT,cls.fresh,cls.out/'selected.o',source.OWNER);cls.raw=list(struct.unpack_from('>46I',data,fs[source.FUNCTION]['value']))
    @classmethod
    def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
    def compare(self,c=Case(),initial=None,images=None,entry=source.ENTRY,selector=source.SELECTOR,raw=True):
        initial=fixture(c,selector)if initial is None else initial;expected,value,iters=reference(initial,selector);pair=[]
        for words in images or(self.truth,self.words):
            m=TexcoordOracle(words,initial,c,entry).run();self.assertEqual(m.memory,expected,c);self.assertEqual(m.r[2],value,c);self.assertFalse(m.calls);pair.append(m)
        self.assertEqual(complete(pair[0]),complete(pair[1]))
        if raw:
            m=TexcoordOracle(self.raw,initial,c).run();self.assertEqual(m.memory,expected,c);self.assertEqual(m.r[2],value);self.assertFalse(m.calls)
        return pair[0],iters
    def test_01_owner_actual_Make_and_reference_census(self):
        self.assertEqual(self.words,self.truth);self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()).encode(),(self.out/'proposed-owner.c').read_bytes())
        for label in('before','after'):
            obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),84)
        self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),83);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'))
        self.assertEqual(source.same_functions(self.out/'after-owner.o',self.out/'make-shadow/src/game/generated_142560.c.o.compact'),84);self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),5)
        rom=self.values['conker/conker.us.bin'];targets={source.ENTRY,0x0C000000|(source.ENTRY>>2&0x3FFFFFF),0x08000000|(source.ENTRY>>2&0x3FFFFFF)};hits=[]
        for i in range(0,len(rom)-3,4):
            if struct.unpack_from('>I',rom,i)[0]in targets:hits.append(i)
        self.assertFalse(hits)
        if self.installed:source.audit(ROOT,self.out)
        self.receipt['owner']=dict(words=46,frame=0,guards=40,bindings=2,neighbors=83,compact_functions=84,Make_commands=5,retained_GLOBAL_ASM=self.values[source.SOURCE].count(b'#pragma GLOBAL_ASM'),diagnostics_empty=True,aligned_pointer_JAL_J_census_empty=True,one_record_argument=True,unidentified_dynamic_callers_not_claimed=True,incidental_V0_observed_separately_from_void_C_API=True)
    def test_02_raw_and_normalized_boundaries_and_buffer_bytes(self):
        count=0;visits=set()
        for packed,n,b,phase in itertools.product((0,0x7FFF8000,0x80007FFF,0xFFFFFFFF,0x0003FFFB),(0,1,2,3,7),(0,1),(0,8)):
            m,_=self.compare(Case(packed,n,b,phase=phase));visits.update(m.visits);count+=1
        for b in range(256):self.compare(Case(buffer=b,count=2,pattern=b));count+=1
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+184,4)))
        self.receipt['guest']=dict(cases=count,all_46_words_visited=True,all_256_buffer_bytes=True,empty_and_loop_boundaries=True,signed_halfword_offsets_and_wrapping_stores=True,raw_C_public_memory_and_V0_equal=True,normalized_complete_private_state_equal=True,full_byte_pointer_slots_guest_only=True)
    def test_03_live_count_selector_pointer_and_packed_aliases(self):
        count=0
        for layout,packed,phase in itertools.product(range(1,9),(0,0x0003FFFB,0x7FFF8000),(0,8)):
            c=Case(packed,count=3,layout=layout,phase=phase);_,iters=self.compare(c)
            if layout in(3,7):self.assertEqual(iters,1)
            count+=1
        self.receipt['aliases']=dict(cases=count,layouts=9,live_count_after_either_store=True,selector_reload_between_coordinates=True,pointer_reload_after_halfword_store=True,packed_offsets_captured_before_writes=True,overlapping_vertex_buffers=True,record_and_global_overlap_guest_only=True)
    def test_04_native32_actual_C_and_effective_controls(self):
        text,count=native_harness()
        for opt in('-O0','-O2','-O3'):
            p=self.fresh/('native-'+opt[1:]+'.c');p.write_text(text);binary=p.with_suffix('');q=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);p.with_suffix('.diagnostics.txt').write_text(q.stdout+q.stderr);self.assertEqual(q.returncode,0,q.stdout+q.stderr)
            self.assertEqual(subprocess.run([str(binary)],timeout=45).returncode,0,opt)
        self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_per_profile=count,counts_through_65535=True,actual_layout_and_SDK_vertex_offsets=True,typed_void_indirect_calls=True,overlapping_valid_vertex_arrays=True,effective_controls=len(controls()),trapping_UBSan=True,arbitrary_buffer_bytes_and_record_aliases_not_claimed_portable=True)
    def test_05_faults_sparse_empty_and_large_unsigned_count_prefix(self):
        count=0
        for c in(Case(count=0),Case(count=1),Case(count=2,layout=5),Case(count=3,layout=3),Case(count=2,layout=6)):
            initial=fixture(c);m,_=self.compare(c)
            for cut in range(m.root_accesses):
                pair=[]
                for words in(self.truth,self.words):
                    x=TexcoordOracle(words,initial,c);x.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):x.run()
                    self.assertEqual(x.root_accesses,cut);pair.append(x)
                self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));count+=1
        c=Case(count=0);m=fixture(c);keep=set(range(RECORD+0x16,RECORD+0x18))|set(range(RECORD+0x3C,RECORD+0x40));sparse={a:v for a,v in m.items()if a in keep};self.compare(c,sparse)
        for n in(0x7FFF,0x8000,0xFFFF):
            c=Case(count=n);initial=fixture(c);pair=[]
            for words in(self.truth,self.words):
                x=TexcoordOracle(words,initial,c);x.root_fault=12
                with self.assertRaises(faults.AccessBoundary):x.run()
                pair.append(x)
            self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertNotEqual(half(pair[0].memory,FIRST+8),half(initial,FIRST+8))
        self.receipt['faults']=dict(fired_prefix_pairs=count,sparse_empty_needs_only_packed_word_and_count=True,unsigned_large_counts_have_fired_first_iteration_prefixes=3,full_large_counts_native32=True,guest_only_fault_order=True)
    def test_06_effective_compiled_live_reload_negatives(self):
        b=source.SELECTED
        cases={
          'cached_selector':(b.replace('        offset = 0;','        u8 cached = D_800BE9C0;\n        offset = 0;').replace('buffers[D_800BE9C0]','buffers[cached]').replace('buffers[!D_800BE9C0]','buffers[!cached]'),Case(count=2,layout=5)),
          'cached_count':(b.replace('    s32 offset;','    s32 offset;\n    u16 cached = record->vertexCount;').replace('if (record->vertexCount > 0)','if (cached > 0)').replace('index < record->vertexCount','index < cached'),Case(count=2,layout=3)),
          'cached_destination':(b.replace('        offset = 0;','        u8 *cached = record->buffers[D_800BE9C0];\n        offset = 0;').replace('record->buffers[D_800BE9C0]','cached').replace('u8 *cached = cached;','u8 *cached = record->buffers[D_800BE9C0];'),Case(count=2,layout=6)),
          'xor_source':(b.replace('!D_800BE9C0','(D_800BE9C0 ^ 1)'),Case(count=2,buffer=2))}
        for label,(body,c)in cases.items():
            self.assertNotEqual(body,b);obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+body,'negative-'+label);self.assertFalse(diag);data,fs=source.link_owner(ROOT,self.fresh,obj,source.OWNER);info=fs[source.FUNCTION];words=list(struct.unpack_from('>%dI'%(info['size']//4),data,info['value']));initial=fixture(c);expected,_,_=reference(initial);actual=TexcoordOracle(words,initial,c).run();self.assertNotEqual(actual.memory,expected,label)
        self.receipt['compiled_negatives']=dict(effective=len(cases),cached_selector_count_destination_and_xor_source=True,actual_emitted_guest_code=True)
    def test_07_guard_closure_padder_and_GNU_rebases(self):
        raw,bindings=source.checked_payload(*source.payload(self.out/'selected.o'));fitted,updated=source.normalized(raw,bindings);self.assertEqual((fitted,updated),source.function_payload(self.out/('original-'+source.FUNCTION+'.o'),source.FUNCTION));self.assertEqual(set(updated),{36,40})
        for at in range(46):
            bad=bytearray(raw);bad[4*at]^=1
            with self.assertRaises(ValueError):source.normalized(bytes(bad),bindings)
        with self.assertRaises(ValueError):source.normalized(raw,bindings|{44:[('R_MIPS_LO16','wrong')]})
        old=self.values['conker/retail_word_patches.us.csv'];guards=source.guard_bytes(old,raw,bindings);self.assertEqual(guards,(self.out/'qualified-guards.csv').read_bytes());self.assertTrue(guards.startswith(old));self.assertEqual(len(guards[len(old):].splitlines()),40)
        rows=list(csv.DictReader(io.StringIO(guards.decode())));schema=list(rows[0]);selected_rows=[i for i,row in enumerate(rows)if row['filename']==source.OWNER and row['function']==source.FUNCTION];self.assertEqual(len(selected_rows),40)
        for n in selected_rows:
            changed=[dict(row)for row in rows];changed[n]['expected']='0x%08X'%(int(changed[n]['expected'],16)^1);p=self.fresh/'bad-guards.csv'
            with p.open('w',newline='')as stream:
                writer=csv.DictWriter(stream,fieldnames=schema);writer.writeheader();writer.writerows(changed)
            with self.assertRaises(ValueError):emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=p,filename=source.OWNER)
        p=self.fresh/'padded.s';p.write_text(emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=self.out/'qualified-guards.csv',filename=source.OWNER));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes())
        asm,missing=emit_function(fitted,dict(value=0,size=184),updated,source.FUNCTION,dict(D_800BE9C0=source.SELECTOR));self.assertFalse(missing);p=self.fresh/'independent.s';p.write_text(asm);obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-mabi=32','-o',str(obj),str(p)],capture_output=True,check=True);count=0
        for i,(entry,selector)in enumerate(((source.ENTRY,source.SELECTOR),(0x15316058,0x81207FFC),(0x15516058,0x81208000))):
            images=[]
            for j,object_ in enumerate((self.out/('original-'+source.FUNCTION+'.o'),obj)):
                p=self.fresh/('rebase-%d-%d.ld'%(i,j));elf=p.with_suffix('.elf');p.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p),'-e',source.FUNCTION,'--defsym=D_800BE9C0=0x%X'%selector,'-o',str(elf),str(object_)],capture_output=True,check=True);images.append(list(struct.unpack_from('>46I',sections(elf)['.text'][1])))
            self.assertEqual(*images)
            for c in(Case(count=0),Case(),Case(buffer=1),Case(count=2,layout=5)):
                self.compare(c,images=images,entry=entry,selector=selector,raw=False);count+=1
        self.receipt['guards']=dict(rows=40,all_46_raw_word_corruptions_rejected=True,all_40_actual_padder_guard_corruptions_rejected=True,wrong_binding_rejected=True,old_guard_bytes_preserved=True,independent_cursor_zero_LO16_swap=True,loop_register_cycles_closed=True,GNU_links=6,rebase_layouts=3,rebased_guest_cases=count,HI16_LO16_signed_low_carry=True)
    def test_08_strict_image_frozen_inputs_and_corruptions(self):
        values=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=values['conker/build/conker.us.elf'];truth=values['conker/conker.us.bin'][source.ROM:source.ROM+184];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,184);symbol=next(pos for pos,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8
        for offset in(20,at,at+184,source.elf_slot_offset(before,0x80082B20,4),symbol):
            bad=bytearray(expected);bad[offset]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        for bad in(expected[:-1],expected+bytes([0])):
            with self.assertRaises(ValueError):source.check_image(before,bad,truth)
        for b,t in((before[:-1],truth),(before,truth[:-1]),(before,bytes([truth[0]^1])+truth[1:])):
            with self.assertRaises(ValueError):source.check_image(b,expected,t)
        q=json.loads((self.out/'preparation.json').read_text());self.assertEqual((q['changed_bytes'],q['code_bytes'],q['metadata_bytes'],q['exclusions']),(139,138,1,0));self.receipt['strict']=dict(changed_bytes=139,code_bytes=138,metadata_bytes=1,exclusions=0,corruptions=7,wrong_inputs=3,focused_inputs=len(values))
if __name__=='__main__':unittest.main()
