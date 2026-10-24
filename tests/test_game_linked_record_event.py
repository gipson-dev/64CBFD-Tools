"""Canonical event ABI, live linked-record reads, guarded returns and strict image."""
from dataclasses import dataclass
from pathlib import Path
import csv,io,itertools,json,struct,subprocess,unittest
from tools.experiments import game_linked_record_event as source
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
OWNER,PACKET,NODES=0x30000,0x20000,0x40000
HELPER,PARENT,TABLE=0x150F892C,0x15149434,0x8008A8D8
CALLER_SOURCE='conker/src/game/done/game_1765E0.c'
CALLER_OBJECT='conker/build/src/game/done/game_1765E0.c.o'
VALUES=(0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0x12345678)

@dataclass(frozen=True)
class Case:
    command:int=66
    tag:int=255
    match:bool=True
    alias:int=0
    effects:bool=False
    pattern:int=0

def packet(c,phase=0):return STACK+phase+8 if c.alias==5 else PACKET

def fixture(c,phase=0):
    m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,512)}
    for base,n in((OWNER-64,0x200),(PACKET-64,0x200),(NODES-64,0x1400)):
        m.update({base+i:(i*13+0x5A)&255 for i in range(n)})
    p=packet(c,phase);put(m,p,VALUES[c.pattern%6]);m[p+4]=c.tag if c.match else c.tag^1
    put(m,OWNER+0x28,VALUES[c.pattern%6]);m[OWNER+0x2C]=c.tag;m[OWNER+0x13]=56
    if not c.match:put(m,OWNER+0x28,VALUES[c.pattern%6]^1)
    for i in range(8):put(m,OWNER+0x34+i*4,NODES+i*0x200)
    if c.alias==1:
        for i in range(8):put(m,OWNER+0x34+i*4,NODES)
    if c.alias==2:put(m,OWNER+0x34,OWNER+0x50+3-0x6E)
    if c.alias==3:put(m,OWNER+0x34,OWNER+0x38+3-0x6E)
    if c.alias==4:put(m,OWNER+0x34,OWNER+0x30-0x6E)
    return m

def mutation(m):
    put(m,OWNER+0x28,read(m,OWNER+0x28)^0xA55AA55A);m[OWNER+0x31]^=0x37

def reference(initial,c,phase=0,home=True):
    m=dict(initial);calls=[];p=packet(c,phase)
    if home:put(m,STACK+phase+8,c.command)
    command=c.command&255
    if command==66 and m[p+4]==m[OWNER+0x2C]:
        for i in range(7):put(m,read(m,OWNER+0x34+4*i)+0x6E,1,1)
        put(m,read(m,OWNER+0x50)+0x6E,0,1);m[OWNER+0x30]=7
    elif command==63 and read(m,p)==read(m,OWNER+0x28):
        calls=[(HELPER,(OWNER,))]
        if c.effects:mutation(m)
    return m,calls

def public(m,c,phase=0):
    p=packet(c,phase)
    return {a:v for a,v in m.items()if not STACK-2048<=a<STACK+512 or p<=a<p+8}

class EventOracle(RayOracle):
    def __init__(self,words,memory,c=Case(),phase=0,entry=source.ENTRY,connected=None,arguments=None,helper=HELPER):
        TimingOracle.__init__(self,words,memory,phase=phase,entry=entry,
            arguments=arguments or(OWNER,packet(c,phase),c.command),connected=connected)
        self.case,self.helper=c,helper
    def record_call(self,target):
        assert target in(source.ENTRY,self.helper)
        args=self.arguments(3 if target==source.ENTRY else 1)
        self.calls.append((target,args));self.events.append(('CALL',target,args))
    def hook(self,target):
        assert target==self.helper
        if self.case.effects:mutation(self.memory)
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo,self.condition=0x87654321,0x12345678,True
        self.r[2]=0x76543210

def controls():
    b=source.SELECTED[source.FUNCTION]
    return dict(command=b.replace('command == 0x42','command == 0x43'),
        helper_command=b.replace('command == 0x3F','command == 0x3E'),
        tag=b.replace('packetAddress)[4]','packetAddress)[5]'),
        tag_gate=b.replace('== group->tag','!= group->tag'),
        count=b.replace('i < 7','i < 6'),
        active=b.replace('[0x6E] = 1','[0x6E] = 0'),
        last=b.replace('records[7]','records[6]'),
        final=b.replace('records[7][0x6E] = 0','records[7][0x6E] = 1'),
        selected_index=b.replace('selected = 7','selected = 6'),
        reference=b.replace('*(s32 *)packetAddress ==','*(s32 *)packetAddress !='),
        owner=b.replace('func_150F892C(owner);','func_150F892C((struct260 *)((u8 *)owner + 4));'),
        early_last=b.replace('            for (i = 0;', '            u8 *last = group->records[7];\n            for (i = 0;').replace('group->records[7][0x6E] = 0','last[0x6E] = 0'))

class LinkedRecordEventTests(unittest.TestCase):
    receipt={}
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out)
        cls.rom=cls.values['conker/conker.us.bin'];cls.old=cls.values['conker/build/conker.us.elf']
        cls.truth=list(struct.unpack_from('>44I',cls.rom,source.ROM))
        data,fs=source.link_owner(ROOT,cls.out,cls.out/'qualified-padded.o',source.OWNER)
        cls.words=list(struct.unpack_from('>44I',data,fs[source.FUNCTION]['value']))
        data,fs=source.link_owner(ROOT,cls.out,cls.out/'after-owner.o',source.OWNER)
        cls.raw=list(struct.unpack_from('>42I',data,fs[source.FUNCTION]['value']))
        cls.parent=list(struct.unpack_from('>23I',cls.rom,PARENT-0x15000000+0x2D4B0))
    def compare(self,c=Case(),phase=0,images=None,entry=source.ENTRY,helper=HELPER):
        initial=fixture(c,phase);expected,calls=reference(initial,c,phase);models=[]
        for words in images or(self.truth,self.words):
            m=EventOracle(words,initial,c,phase,entry=entry,helper=helper).run()
            self.assertEqual(public(m.memory,c,phase),public(expected,c,phase),c)
            self.assertEqual(m.calls,[(helper,args)for _,args in calls],c);models.append(m)
        self.assertEqual(complete(models[0]),complete(models[1]))
        return models[0]
    def test_01_owner_make_raw_fit_and_retained_dispatcher(self):
        q=json.loads((self.out/'qualification.json').read_text())
        self.assertEqual((q['total_words'],q['new_guards'],q['inserted_return_loads'],q['preserved_neighbors']),(44,9,2,16))
        self.assertEqual(self.words,self.truth)
        self.assertEqual(source.normalized(*source.payload(self.out/'after-owner.o',source.FUNCTION)),
            source.payload(source.original(ROOT,self.out,source.FUNCTION),source.FUNCTION))
        mk=json.loads((self.out/'make-shadow.json').read_text())[0]
        self.assertEqual((mk['actual_Make_commands'],mk['compact_functions_equal']),(5,17))
        self.assertTrue(mk['complete_padded_object_equal'])
        at=source.elf_slot_offset(self.old,PARENT,92);self.assertEqual(self.old[at:at+92],struct.pack('>23I',*self.parent))
        at=source.elf_slot_offset(self.old,TABLE+56*4,4)
        self.assertEqual(self.old[at:at+4],self.rom[0x22F478:0x22F47C])
        self.assertEqual(read(dict(enumerate(self.rom[0x22F478:0x22F47C])),0),source.ENTRY)
        self.assertEqual((ROOT/CALLER_OBJECT).read_bytes(),self.values[CALLER_OBJECT])
        self.receipt['owner']=dict(raw_words=42,fitted_words=44,guards=9,derived_return_copies=2,neighbors=16,Make_commands=5,caller_words=23)
    def test_02_guest_commands_tags_live_reads_and_private_aliases(self):
        count=0;visits=set()
        for byte,upper,match,phase in itertools.product(range(256),(0,0xA5A50000),(False,True),(0,8)):
            c=Case(command=upper|byte,tag=255-byte,match=match,pattern=byte%6,effects=bool(byte&1))
            m=self.compare(c,phase);visits.update(m.visits);count+=1
            initial=fixture(c,phase);expected,calls=reference(initial,c,phase)
            raw=EventOracle(self.raw,initial,c,phase).run()
            self.assertEqual(public(raw.memory,c,phase),public(expected,c,phase));self.assertEqual(raw.calls,calls)
        for tag,alias,command,phase in itertools.product((0,1,127,255),range(6),(66,63,0),(0,8)):
            self.compare(Case(command=command,tag=tag,alias=alias,effects=True),phase);count+=1
        for tag,match,phase in itertools.product(range(256),(False,True),(0,8)):
            self.compare(Case(tag=tag,match=match),phase);count+=1
        for pattern,match,effects in itertools.product(range(6),(False,True),(False,True)):
            self.compare(Case(command=63,pattern=pattern,match=match,effects=effects));count+=1
        self.assertTrue(set(range(source.ENTRY,source.ENTRY+176,4))<=visits)
        self.receipt['guest']=dict(cases=count,all_command_tag_bytes=True,upper_homes=True,aliases=6,
            raw_C_public_semantics_checked=True,fitted_full_private_state_equal=True,all_44_words_visited=True)
    def test_03_complete_raw_and_real_padder_controls(self):
        raw,bindings=source.payload(self.out/'after-owner.o',source.FUNCTION)
        for index in range(42):
            bad=bytearray(raw);bad[index*4]^=1
            with self.assertRaises(ValueError):source.normalized(bytes(bad),bindings)
        for bad in ({},{148:[('R_MIPS_26','func_150F892C')]}):
            with self.assertRaises(ValueError):source.normalized(raw,bad)
        with self.assertRaises(ValueError):source.normalized(raw[:-4],bindings)
        before=self.values['conker/retail_word_patches.us.csv'];after=source.guard_bytes(before,raw,bindings)
        self.assertTrue(after.startswith(before));rows=list(csv.DictReader(io.StringIO(after[len(before):].decode()),fieldnames=list(csv.DictReader(io.StringIO(before.decode())).fieldnames)))
        self.assertEqual(len(rows),9);self.assertEqual(sum(bool(r['insert_after'])for r in rows),2)
        for column,value in(('expected','0x00000000'),('expected_relocations','R_MIPS_26:func_150F892C')):
            badrows=[dict(r)for r in rows];badrows[0][column]=value
            stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n');writer.writerows(badrows)
            path=self.out/('bad-padder-'+column+'.csv');path.write_bytes(before+stream.getvalue().encode())
            with self.assertRaises(ValueError):source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=path,filename=source.OWNER)
        wrong=bytearray(before);wrong[-5]^=1
        with self.assertRaises(ValueError):source.guard_bytes(bytes(wrong),raw,bindings)
        self.receipt['guards']=dict(raw_word_controls=42,binding_or_extent_controls=3,padder_controls=2,prefix_control=1,
            old_prefix_identical=True,inserted_words_derived_from_existing_return=True)
    def test_04_full_original_dispatcher(self):
        count=0;visits=set()
        connected={source.ENTRY+4*i:w for i,w in enumerate(self.words)}
        for index,command,present,zero in itertools.product(range(256),(0xA5A50042,0x8765003F),(False,True),(False,True)):
            c=Case(command=command,tag=index,effects=True);initial=fixture(c);initial[OWNER+0x13]=index
            for i in range(74):put(initial,TABLE+4*i,0)
            put(initial,TABLE+56*4,source.ENTRY if present else 0);put(initial,TABLE,source.ENTRY if zero else 0)
            selected=index if index<74 else 0;invoked=(selected==56 and present)or(selected==0 and zero)
            expected,calls=reference(initial,Case(command=command&255,tag=index,effects=True),-24)if invoked else(dict(initial),[])
            # Parent and child homes are private; only the callback effects are public here.
            models=[]
            for words in(self.truth,self.words):
                code={source.ENTRY+4*i:w for i,w in enumerate(words)}
                m=EventOracle(self.parent,initial,c,entry=PARENT,connected=code).run()
                self.assertEqual(public(m.memory,c),public(expected,c))
                self.assertEqual([row for row in m.calls if row[0]==HELPER],calls)
                self.assertEqual(any(t==source.ENTRY for t,_ in m.calls),invoked)
                visits.update(m.visits);models.append(m)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.assertTrue(set(range(PARENT,PARENT+92,4))<=visits)
        self.receipt['caller']=dict(cases=count,all_23_words_visited=True,all_header_bytes=True,slot=56,actual_table_word=True,
            null_and_index_zero_routes=True,other_handlers_not_qualified=True)
    def test_05_native32_actual_C_dispatcher_and_callback(self):
        parent=self.values[CALLER_SOURCE].decode();lo,hi=source.function_span(parent,'func_15149434')
        body=source.SELECTED[source.FUNCTION];variants=dict(selected=body,**{k:v for k,v in controls().items()if k!='early_last'})
        for label,b in variants.items():
            if label!='selected':self.assertNotEqual(b,body,label)
        text=source.HEADERS+source.DECLARATIONS+'''
static u8 *arena,*expected,*currentOwner;static u32 error,calls,mutate;
void(*D_8008A8D8[74])(struct260*,s32,u8);
static u32 word(const void*p){u32 v,i;for(i=0;i<4;i++)((u8*)&v)[i]=((const u8*)p)[i];return v;}
static void setword(void*p,u32 v){u32 i;for(i=0;i<4;i++)((u8*)p)[i]=((u8*)&v)[i];}
s32 func_150F892C(struct260*owner){calls++;if((u8*)owner!=currentOwner){error=1;return 0;}
 if(mutate){setword(currentOwner+0x28,word(currentOwner+0x28)^0xA55AA55Au);currentOwner[0x31]^=0x37;}return (s32)0x87654321;}
'''
        for name,b in variants.items():text+=b.replace(source.FUNCTION,name)+'\n'
        text+=parent[lo:hi]+'''
typedef void(*Handler)(struct260*,s32,u8);
static int one(Handler fn,u32 command,u32 match,u32 layout,u32 effect,u32 wrapper){
 u32 i,expectedCalls=0,offset=0x100,p=layout==2?offset+0x28:0x200;u8*owner=arena+offset,*packet=arena+p;
 for(i=0;i<0x3000;i++)arena[i]=(u8)(i*13+0x5A);
 setword(packet,0x80000000u+command);packet[4]=(u8)(match?255-command:(255-command)^1);
 setword(owner+0x28,0x80000000u+command+(match?0:1));owner[0x2C]=(u8)(255-command);owner[0x13]=56;
 for(i=0;i<8;i++)*(u8**)(void*)(owner+0x34+i*4)=arena+0x400+i*0x200;
 if(layout==1)for(i=0;i<8;i++)*(u8**)(void*)(owner+0x34+i*4)=arena+0x400;
 for(i=0;i<0x3000;i++)expected[i]=arena[i];
 if((u8)command==66&&expected[p+4]==expected[offset+0x2C]){
  for(i=0;i<7;i++)expected[(u32)((u8*)word(expected+offset+0x34+i*4)-arena)+0x6E]=1;
  expected[(u32)((u8*)word(expected+offset+0x50)-arena)+0x6E]=0;expected[offset+0x30]=7;
 }else if((u8)command==63&&word(expected+p)==word(expected+offset+0x28)){
  expectedCalls=1;if(effect){setword(expected+offset+0x28,word(expected+offset+0x28)^0xA55AA55Au);expected[offset+0x31]^=0x37;}
 }
 calls=error=0;mutate=effect;currentOwner=owner;
 if(wrapper){for(i=0;i<74;i++)D_8008A8D8[i]=0;D_8008A8D8[56]=fn;func_15149434((struct260*)owner,(s32)packet,(u8)command);}
 else fn((struct260*)owner,(s32)packet,(u8)command);
 if(error||calls!=expectedCalls)return 23;
 for(i=0;i<0x3000;i++)if(arena[i]!=expected[i])return 23;return 0;
}
static int variant(Handler fn){u32 f,c,m,l,e;for(f=0;f<2;f++)for(c=0;c<256;c++)for(m=0;m<2;m++)for(l=0;l<3;l++)for(e=0;e<2;e++)
 if(one(fn,c,m,l,e,f))return 23;return 0;}
static void*allocate(u32 n){u32 p,end;__asm__ volatile("int $0x80":"=a"(p):"a"(45),"b"(0):"memory");end=p+n;
 __asm__ volatile("int $0x80":"=a"(end):"a"(45),"b"(end):"memory");return end>=p+n?(void*)p:0;}
int run(void){arena=allocate(0x6000);if(!arena||sizeof(void*)!=4)return 97;expected=arena+0x3000;
'''
        for i,name in enumerate(variants):
            text+='if(variant(%s)!=%d)return %d;\n'%(name,0 if name=='selected'else 23,11+i)
        text+='selected((struct260*)0,0,0);selected((struct260*)0,0,255);return 0;}\n'+START
        for opt in('-O0','-O2','-O3'):
            path=self.out/('native-'+opt[1:]+'.c');path.write_text(text);binary=path.with_suffix('')
            result=subprocess.run(native_command(opt)+['-mstackrealign',str(path),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual(subprocess.run([str(binary)],timeout=60).returncode,0,opt)
        self.receipt['native']=dict(profiles=['O0','O2','O3'],cases_per_profile=6144,controls=len(variants)-1,
            actual_C_dispatcher=True,canonical_function_pointer_types=True,trap_UBSan=True,private_homes_guest_only=True)
    def test_06_fault_prefixes_and_unsupported_NULL_inputs(self):
        count=0
        for c in(Case(),Case(match=False),Case(command=63,effects=True),Case(command=63,match=False),Case(alias=2),Case(alias=5)):
            m=self.compare(c);initial=fixture(c)
            for fault in range(m.root_accesses):
                models=[]
                for words in(self.truth,self.words):
                    x=EventOracle(words,initial,c);x.root_fault=fault
                    with self.assertRaises(faults.AccessBoundary):x.run()
                    self.assertEqual(x.root_accesses,fault);models.append(x)
                self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        for command in(0,1,62,64,65,67,255):
            for words in(self.truth,self.words):
                x=EventOracle(words,fixture(Case(command=command)),Case(command=command),arguments=(0,0,command)).run()
                self.assertFalse(x.calls)
        for command in(63,66):
            models=[]
            for words in(self.truth,self.words):
                x=EventOracle(words,fixture(Case(command=command)),Case(command=command),arguments=(0,0,command))
                with self.assertRaisesRegex(AssertionError,'unmapped read'):x.run()
                models.append(x)
            self.assertEqual(complete(models[0]),complete(models[1]))
        self.receipt['faults']=dict(pairs=count,unsupported_NULL_cases=7,selected_NULL_fault_cases=2,emitted_guest_order_only=True)
    def test_07_independent_links_and_early_pointer_negative(self):
        raw,rs=source.payload(self.out/'after-owner.o',source.FUNCTION)
        fitted,moved=source.normalized(raw,rs);objects=[source.original(ROOT,self.out,source.FUNCTION)]
        asm,missing=emit_function(fitted,dict(value=0,size=176),moved,source.FUNCTION,{'func_150F892C':HELPER})
        self.assertFalse(missing);path=self.out/'independent-fitted.s';path.write_text(asm);obj=path.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-mabi=32','-o',str(obj),str(path)],capture_output=True,check=True);objects.append(obj)
        links=0
        for i,(entry,helper)in enumerate(((source.ENTRY,HELPER),(source.ENTRY+0x200000,HELPER+0x400000),(source.ENTRY+0x500000,0x1FFF892C))):
            images=[]
            for j,obj in enumerate(objects):
                ld=self.out/('link-%d-%d.ld'%(i,j));elf=ld.with_suffix('.elf')
                ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',source.FUNCTION,'--defsym=func_150F892C=0x%X'%helper,'-o',str(elf),str(obj)],capture_output=True,check=True)
                data=sections(elf)['.text'][1];images.append(list(struct.unpack_from('>44I',data)));links+=1
            self.assertEqual(*images)
            for command in(0,63,66):self.compare(Case(command=command,effects=True),images=images,entry=entry,helper=helper)
        b=controls()['early_last'];obj,diag=source.compile_owner(ROOT,self.out,source.HEADERS+source.DECLARATIONS+b,'negative-early-last')
        self.assertFalse(diag);data,fs=source.link_owner(ROOT,self.out,obj,source.OWNER);at=fs[source.FUNCTION]['value']
        words=list(struct.unpack_from('>%dI'%(fs[source.FUNCTION]['size']//4),data,at))
        c=Case(alias=2);initial=fixture(c);expected,_=reference(initial,c)
        bad=EventOracle(words,initial,c).run();self.assertNotEqual(public(bad.memory,c),public(expected,c))
        self.receipt['links']=dict(independent_GNU_links=links,layouts=3,helper_relocation=True,early_eighth_pointer_negative_effective=True)
    def test_08_strict_image_and_frozen_inputs(self):
        pred=source.predicted_image(self.old,source.truths(self.values))
        source.check_image(self.old,(self.out/'first-linked.elf').read_bytes(),source.truths(self.values))
        self.assertEqual(sum(a!=b for a,b in zip(self.old,pred)),132)
        for at in(0,len(pred)-1,source.elf_slot_offset(pred,source.ENTRY,176),source.elf_slot_offset(pred,PARENT,92)):
            bad=bytearray(pred);bad[at]^=1
            with self.assertRaises(ValueError):source.check_image(self.old,bytes(bad),source.truths(self.values))
        installed=(ROOT/source.SOURCE).read_bytes()!=self.values[source.SOURCE]
        source.check_inputs(ROOT,self.out,installed)
        self.receipt['strict']=dict(changed_bytes=132,code_bytes=131,size_bytes=1,exclusions=0,corruptions=4,focused_inputs=29)

if __name__=='__main__':unittest.main()
