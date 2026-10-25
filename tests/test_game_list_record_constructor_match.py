"""List constructor ABI, partial stores, caller gates and strict image checks."""
from dataclasses import dataclass
from pathlib import Path
import itertools,json,struct,subprocess,unittest

from tools.experiments import game_list_record_constructor_match as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

ROOT=Path(__file__).resolve().parents[2]
HEAD,ALLOC,NEW,ALT=0x800DDD64,0x10003C40,0x60000,0x70000
CORE=0x10003C6C
NODES=tuple(0x20000+0x100*i for i in range(4))


@dataclass(frozen=True)
class Case:
    count:int=0
    first:int=0
    second:int=255
    result_mode:int=1
    mutation:int=0


def destination(c,phase=0):
    return(0,NEW,HEAD,NODES[0],NODES[c.count-1]if c.count else NEW,
        STACK+phase-0x24,STACK+phase-0x20)[c.result_mode]


def fixture(c,phase=0):
    memory={STACK+i:(17*i+0xA5)&255 for i in range(-2048,512)}
    for base in(*NODES,HEAD,NEW,ALT):memory.update({base+i:(13*i+0x5A)&255 for i in range(-16,0x80)})
    put(memory,HEAD,NODES[0]if c.count else 0)
    for i in range(c.count):put(memory,NODES[i]+0x24,NODES[i+1]if i+1<c.count else 0)
    return memory


def allocator_effect(memory,c,sp,incoming):
    if c.mutation&1:put(memory,HEAD,ALT)
    if c.mutation&2 and c.count:put(memory,NODES[c.count-1]+0x24,ALT)
    if c.mutation&4:
        put(memory,incoming,0xDEADBEEF);put(memory,incoming+4,0x12345680)
    for i in range(4):put(memory,sp+4*i,0xB7000000+i)


def reference(initial,c,phase=0):
    memory=dict(initial);sp=STACK+phase
    put(memory,sp,c.first);put(memory,sp+4,c.second)
    node=read(memory,HEAD);link=HEAD
    if node:
        while read(memory,node+0x24):node=read(memory,node+0x24)
        link=node+0x24
    allocator_effect(memory,c,sp-32,sp);node=destination(c,phase)
    if node:
        put(memory,link,node);put(memory,node+0x24,0);put(memory,node+0x28,0,2)
        memory[node+0x2E]=0;put(memory,node+0x10,0);put(memory,node+0xC,0)
        memory[node+0x2F]=read(memory,sp)&255;memory[node+0x30]=read(memory,sp+4)&255
    return memory,node


def public(memory):
    return{a:b for a,b in memory.items()if not STACK-2048<=a<STACK+512}


class ConstructorOracle(RayOracle):
    def __init__(self,words,memory,c=Case(),phase=0,entry=source.ENTRY,connected=None,arguments=None,child_sp=None):
        TimingOracle.__init__(self,words,memory,phase=phase,entry=entry,
            arguments=arguments or(c.first,c.second),connected=connected)
        self.case,self.child_sp=c,STACK+phase if child_sp is None else child_sp
        self.hi,self.lo,self.condition=0x89ABCDEF,0x76543210,True
    def access(self):
        if self.own_instruction:
            if self.root_accesses==self.root_fault:raise faults.AccessBoundary
            self.root_accesses+=1
    def put(self,address,value,size):
        if self.recording and self.own_instruction:
            self.access()
            assert all(address+i in self.memory for i in range(size)),('unmapped write',address,size)
            own=self.own_instruction;self.own_instruction=False
            try:return super().put(address,value,size)
            finally:self.own_instruction=own
        return super().put(address,value,size)
    def record_call(self,target):
        if target==source.ENTRY:
            args=self.arguments(2);assert args==(0,255),args
            self.calls.append((target,args));self.events.append(('CALL',target,args));return
        assert target==ALLOC,hex(target)
        args=self.arguments(4);assert args==(0x34,1,0,1),args
        self.calls.append((target,args));self.events.append(('CALL',target,args))
    def hook(self,target):
        assert target in(ALLOC,CORE)
        allocator_effect(self.memory,self.case,self.r[29],self.child_sp)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo=0x87654321,0x12345678;self.r[2]=destination(self.case,self.child_sp-STACK)


def controls():
    body=source.SELECTED
    return{
        'late_publish':body.replace('    *link = node;\n','').replace('    return (struct162 *)node;','    *link = node;\n    return (struct162 *)node;'),
        'opaque_clear':body.replace('    node->next = NULL;','    node->opaque0[0] = 0;\n    node->next = NULL;'),
        'wrong_first':body.replace('node->first2F = first;','node->first2F = second;'),
        'missing_next':body.replace('    node->next = NULL;\n',''),
        'wrong_size':body.replace('allocate_memory(0x34, 1, 0, 1)','allocate_memory(0x38, 1, 0, 1)')}


def native_harness(values):
    header=source.HEADERS+source.DECLARATIONS.replace('extern ListRecord1AB530 *D_800DDD64;','ListRecord1AB530 *D_800DDD64;')
    text=header+r'''
typedef char ABI[(sizeof(void*)==4&&sizeof(s32)==4&&sizeof(ListRecord1AB530)==0x34&&
 __builtin_offsetof(ListRecord1AB530,next)==0x24&&__builtin_offsetof(ListRecord1AB530,state28)==0x28&&
 __builtin_offsetof(ListRecord1AB530,flags2E)==0x2E&&__builtin_offsetof(ListRecord1AB530,first2F)==0x2F&&
 __builtin_offsetof(ListRecord1AB530,second30)==0x30)?1:-1];
typedef struct162 *(*Constructor)(s32,s32);
static u8 *arena,*expected;
static u32 mutations,length,resultOffset,error,calls;
static const u32 nodes[]={0x200,0x300,0x400,0x500};
__attribute__((noinline,noclone)) s32 func_10003C6C(s32 size,s32 a,s32 b,s32 inserted,s32 c){
 if(size!=0x34||a!=1||b||inserted||c!=1||calls++){error=1;return 0;}
 if(mutations&1)D_800DDD64=(ListRecord1AB530*)(void*)(arena+0x800);
 if((mutations&2)&&length)*(ListRecord1AB530**)(void*)(arena+nodes[length-1]+0x24)=
  (ListRecord1AB530*)(void*)(arena+0x800);
 return resultOffset?(s32)(u32)(arena+resultOffset):0;
}
'''
    allocator=values['conker/src/init_3C40.c'].decode();lo,hi=source.function_span(allocator,'allocate_memory')
    text+=allocator[lo:hi]+'\n'
    for name,body in dict(selected=source.SELECTED,**controls()).items():text+=body.replace(source.FUNCTION,name)+'\n'
    text+=r'''
static int one(Constructor fn,u32 n,u32 first,u32 second,u32 mode,u32 mutation){
 u32 i,dest,head,expectedHead;struct162 *actual;
 for(i=0;i<0x1000;i++)arena[i]=(u8)(i*13+0x5A);
 for(i=0;i<n;i++)*(ListRecord1AB530**)(void*)(arena+nodes[i]+0x24)=
  i+1<n?(ListRecord1AB530*)(void*)(arena+nodes[i+1]):0;
 for(i=0;i<0x1000;i++)expected[i]=arena[i];
 dest=(u32[]){0,0x700,0x200,n?nodes[n-1]:0x700}[mode];head=n?(u32)(arena+nodes[0]):0;
 expectedHead=mutation&1?(u32)(arena+0x800):head;
 if((mutation&2)&&n)*(u32*)(void*)(expected+nodes[n-1]+0x24)=(u32)(arena+0x800);
 if(dest){
  if(n)*(u32*)(void*)(expected+nodes[n-1]+0x24)=(u32)(arena+dest);else expectedHead=(u32)(arena+dest);
  *(u32*)(void*)(expected+dest+0x24)=0;*(u16*)(void*)(expected+dest+0x28)=0;
  expected[dest+0x2E]=0;*(u32*)(void*)(expected+dest+0x10)=0;*(u32*)(void*)(expected+dest+0xC)=0;
  expected[dest+0x2F]=(u8)first;expected[dest+0x30]=(u8)second;
 }
 D_800DDD64=(ListRecord1AB530*)(void*)head;length=n;mutations=mutation;resultOffset=dest;error=calls=0;
 actual=fn((s32)first,(s32)second);
 if(error||calls!=1||(u32)actual!=(dest?(u32)(arena+dest):0)||(u32)D_800DDD64!=expectedHead)return 23;
 for(i=0;i<0x1000;i++)if(arena[i]!=expected[i])return 23;
 return 0;
}
static const u32 values[]={0,0x7F,0x80,0xFF,0x100,0x12345678,0x80000000,0xFFFFFFFF};
static int variant(Constructor fn){u32 n,a,b,mode,mutation;
 for(n=0;n<=4;n++)for(a=0;a<8;a++)for(b=0;b<8;b++)for(mode=0;mode<4;mode++)for(mutation=0;mutation<4;mutation++)
  if(one(fn,n,values[a],values[b],mode,mutation))return 23;
 return 0;
}
static void *allocate(u32 n){u32 p,end;
 __asm__ volatile("int $0x80":"=a"(p):"a"(45),"b"(0):"memory");end=p+n;
 __asm__ volatile("int $0x80":"=a"(end):"a"(45),"b"(end):"memory");return end>=p+n?(void*)p:0;
}
static int run(void){
 arena=allocate(0x2000);if(!arena)return 97;expected=arena+0x1000;
 if(variant(selected))return 10;
'''
    for i,name in enumerate(controls()):text+=' if(variant(%s)!=23)return %d;\n'%(name,20+i)
    return text+' return 0;\n}\n'+START


class ListRecordConstructorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);cls.receipt={}
        cls.truth=list(struct.unpack('>45I',cls.values['conker/conker.us.bin'][source.ROM:source.ROM+180]))
        raw,bindings=source.checked_payload(*source.payload(cls.out/'after-owner.o',source.FUNCTION))
        linked,functions=source.link_owner(ROOT,cls.out,cls.out/'qualified-padded.o',source.OWNER)
        cls.words=list(struct.unpack_from('>45I',linked,functions[source.FUNCTION]['value']))
        cls.parent=list(struct.unpack_from('>32I',cls.values['conker/conker.us.bin'],source.PARENT_ROM))
        linked,fs=source.link_owner(ROOT,cls.out,cls.out/'typed-caller.o','game_36600')
        cls.typed_parent=list(struct.unpack_from('>32I',linked,fs[source.CALLER]['value']))
        cls.addClassCleanup(lambda:(cls.out/'focused-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n'))

    def compare(self,c=Case(),phase=0,images=None):
        initial=fixture(c,phase);expected,result=reference(initial,c,phase);pair=[]
        for words in(images or(self.truth,self.words)):
            m=ConstructorOracle(words,initial,c,phase).run()
            self.assertEqual(public(m.memory),public(expected));self.assertEqual(m.r[2],result)
            if result:
                for offset,size in((0x24,4),(0x28,2),(0x2E,1),(0x10,4),(0xC,4),(0x2F,1),(0x30,1)):
                    self.assertEqual(bytes(m.memory[result+offset+i]for i in range(size)),
                        bytes(expected[result+offset+i]for i in range(size)))
            self.assertEqual(m.calls,[(ALLOC,(0x34,1,0,1))]);pair.append(m)
        self.assertEqual(complete(pair[0]),complete(pair[1]));return pair[0]

    def test_01_direct_owner_Make_and_typed_caller(self):
        self.assertEqual(self.words,self.truth);self.assertEqual(self.parent,self.typed_parent)
        rom=self.values['conker/conker.us.bin'];jal=0x0C000000|((source.ENTRY>>2)&0x03FFFFFF)
        calls=[];pointers=[]
        for i,(word,)in enumerate(struct.iter_unpack('>I',rom[:len(rom)//4*4])):
            if word==jal:calls.append(i*4)
            if word==source.ENTRY:pointers.append(i*4)
        self.assertEqual(calls,[0x36658]);self.assertEqual(pointers,[])
        q=json.loads((self.out/'qualification.json').read_text());self.assertEqual((q['new_guards'],q['preserved_global_asm'],q['preserved_neighbors']),(0,1,7))
        self.assertTrue(json.loads((self.out/'make-shadow.json').read_text())['complete_padded_object_equal'])
        self.receipt['shape']=dict(q,encoded_JAL_sites=calls,literal_pointer_sites=pointers,
            allocator_C_ABI='s32(s32,s32,s32,s32)',pointer_cast_preserves_32_bit_address=True)

    def test_02_guest_aliases_late_homes_partial_stores_and_faults(self):
        count=0;seen=set()
        for n,(a,b),mode,mutation,phase in itertools.product((0,1,2,4),
            ((0,255),(0xFFFFFFFF,0x12345680),(0x80000000,0x7FFFFFFF),(0x1234567F,0x89ABCDEF)),range(7),range(8),(0,8)):
            m=self.compare(Case(n,a,b,mode,mutation),phase);seen.update(m.visits);count+=1
        self.assertEqual(seen,set(range(source.ENTRY,source.ENTRY+180,4)))
        prefixes=0
        for c in(Case(),Case(1),Case(4),Case(2,result_mode=0),Case(1,result_mode=4),Case(result_mode=2),Case(result_mode=5,mutation=4),Case(result_mode=6)):
            initial=fixture(c);m=self.compare(c)
            for fault in range(m.root_accesses):
                pair=[]
                for words in(self.truth,self.words):
                    x=ConstructorOracle(words,initial,c);x.root_fault=fault
                    with self.assertRaises(faults.AccessBoundary):x.run()
                    self.assertEqual(x.root_accesses,fault);pair.append(x)
                self.assertEqual(complete(pair[0]),complete(pair[1]));prefixes+=1
        compiled=[]
        for name in('late_publish','opaque_clear'):
            obj,diag=source.compile_owner(ROOT,self.out,source.HEADERS+source.DECLARATIONS+controls()[name],'negative-'+name)
            self.assertFalse(diag);data,fs=source.link_owner(ROOT,self.out,obj,source.OWNER);info=fs[source.FUNCTION]
            bad=list(struct.unpack_from('>%dI'%(info['size']//4),data,info['value']))
            c=Case(1,result_mode=4 if name=='late_publish'else 1);initial=fixture(c);expected,_=reference(initial,c)
            actual=ConstructorOracle(bad,initial,c).run();self.assertNotEqual(public(actual.memory),public(expected));compiled.append(name)
        self.receipt['guest']=dict(cases=count,reachable_words=45,fault_prefix_pairs=prefixes,compiled_controls=compiled,
            head_and_existing_node_aliases=True,incoming_home_aliases=True,late_home_provider_mutations=True,
            allocator='bounded arguments/return/head-tail/home mutation/clobber contract, not actual allocator',guest_fault_order_only=True)

    def test_03_actual_caller_gates_connected_and_NULL_behavior(self):
        count=0
        for gate,enabled,index,phase in itertools.product((0,1,255),(0,1,0x80000000),(0,1,255),(0,8)):
            c=Case();initial=fixture(c,phase);put(initial,0x800B0DF0,ALT);put(initial,ALT+0x10,index,1)
            initial[0x800DCDD0]=gate;initial[0x800DDD61]=0xA5;initial[0x800DD2D0]=0x5A
            put(initial,0x8008CFFC+index*4,enabled);pair=[]
            for parent,child in((self.parent,self.truth),(self.typed_parent,self.words)):
                connected={source.ENTRY+i*4:w for i,w in enumerate(child)}
                x=ConstructorOracle(parent,initial,c,phase,source.PARENT,connected=connected,arguments=(0xDEADBEEF,),child_sp=STACK+phase-24).run()
                self.assertEqual(read(x.memory,HEAD),NEW if gate and enabled else 0)
                self.assertEqual((x.memory[0x800DDD61],x.memory[0x800DD2D0]),(0,0))
                self.assertEqual(x.memory[NEW+0x2E],3 if gate and enabled else initial[NEW+0x2E])
                self.assertEqual(x.calls,[(source.ENTRY,(0,255)),(ALLOC,(0x34,1,0,1))]if gate and enabled else[])
                pair.append(x)
            self.assertEqual(complete(pair[0]),complete(pair[1]));count+=1
        for parent,child in((self.parent,self.truth),(self.typed_parent,self.words)):
            c=Case(result_mode=0);initial=fixture(c);put(initial,0x800B0DF0,ALT);put(initial,ALT+0x10,0,1)
            initial[0x800DCDD0]=1;initial[0x800DDD61]=1;initial[0x800DD2D0]=1;put(initial,0x8008CFFC,1)
            connected={source.ENTRY+i*4:w for i,w in enumerate(child)}
            x=ConstructorOracle(parent,initial,c,entry=source.PARENT,connected=connected,child_sp=STACK-24)
            with self.assertRaisesRegex(AssertionError,'unmapped write'):x.run()
            self.assertEqual(x.r[2],0);self.assertEqual(x.current_pc,source.PARENT+0x64)
        self.receipt['caller']=dict(connected_cases=count,original_and_typed_retained_32_words=True,caller_frame=24,
            nested_frame=32,arguments=[0,255],NULL_result_unconditionally_dereferenced=True,not_a_new_caller_match=True)

    def test_03b_actual_allocator_wrapper_and_fifth_argument_home(self):
        rom=self.values['conker/conker.us.bin'];original=rom[0x3C40:0x3C6C]
        elf=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(elf,ALLOC,44)
        self.assertEqual(elf[at:at+44],original);wrapper=list(struct.unpack('>11I',original))
        class Wrapped(ConstructorOracle):
            def record_call(self,target):
                if target!=CORE:return super().record_call(target)
                args=self.arguments(5);assert args==(0x34,1,0,0,1),args
                self.calls.append((target,args));self.events.append(('CALL',target,args))
        count=0
        for n,mode,mutation,phase in itertools.product((0,1,4),(0,1,2,4),range(8),(0,8)):
            c=Case(n,0x12345680,0xFFFFFFFF,mode,mutation);initial=fixture(c,phase);expected,result=reference(initial,c,phase);pair=[]
            for child in(self.truth,self.words):
                connected={ALLOC+i*4:w for i,w in enumerate(wrapper)}
                x=Wrapped(child,initial,c,phase,connected=connected).run()
                self.assertEqual(public(x.memory),public(expected));self.assertEqual(x.r[2],result)
                self.assertEqual(x.calls,[(ALLOC,(0x34,1,0,1)),(CORE,(0x34,1,0,0,1))]);pair.append(x)
            self.assertEqual(complete(pair[0]),complete(pair[1]));count+=1
        self.receipt['allocator_wrapper']=dict(connected_cases=count,original_and_retained_words=11,frame=32,
            fifth_outgoing_argument=1,inserted_fourth_argument=0,core_allocator_bounded=True)

    def test_04_native32_heap_partial_init_and_effective_controls(self):
        profiles=[];folder=self.out/'native';folder.mkdir(exist_ok=True)
        for opt in('-O0','-O2','-O3'):
            p=folder/('constructor-'+opt[1:]+'.c');p.write_text(native_harness(self.values));binary=p.with_suffix('')
            result=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            result=subprocess.run([str(binary)],cwd=ROOT,capture_output=True,text=True,timeout=120)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            profiles.append(dict(profile=opt,binary_SHA256=source.digest(binary.read_bytes()),exit=0))
        self.receipt['native']=dict(profiles=profiles,cases_per_profile=5120,trap_UBSan=True,heap_backed_typeless=True,
            effective_controls=list(controls()),layout_bytes=52,proper_constructor_function_pointer=True,
            actual_allocator_wrapper_C=True,core_allocator_bounded=True,
            global_head_and_guest_stack_aliases_not_portable_native_claims=True)

    def test_05_raw_controls_rebased_bindings_and_strict_image(self):
        raw,bindings=source.payload(self.out/'after-owner.o',source.FUNCTION)
        for i in range(45):
            bad=bytearray(raw);bad[4*i+3]^=1
            with self.assertRaises(ValueError):source.checked_payload(bytes(bad),bindings)
        with self.assertRaises(ValueError):source.checked_payload(raw[:-4],bindings)
        with self.assertRaises(ValueError):source.checked_payload(raw,{})
        links=0
        for i,(entry,head,allocator)in enumerate(((source.ENTRY,HEAD,ALLOC),(source.ENTRY+0x200000,HEAD+0x5000,ALLOC+0x30000),(source.ENTRY+0x400000,HEAD-0x7000,ALLOC+0x50000))):
            images=[]
            for j,obj in enumerate((source.original(ROOT,self.out),self.out/'selected.o')):
                ld=self.out/('rebase-%d-%d.ld'%(i,j));elf=ld.with_suffix('.elf');ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',source.FUNCTION,
                    '--defsym=D_800DDD64=0x%X'%head,'--defsym=allocate_memory=0x%X'%allocator,'-o',str(elf),str(obj)],capture_output=True,check=True)
                images.append(sections(elf)['.text'][1][:180]);links+=1
            self.assertEqual(*images)
        before=self.values['conker/build/conker.us.elf'];truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+180]
        pred=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth)
        symbol=next(at for at,n,_,_ in source.symbol_rows(before)if n==source.FUNCTION)
        for at in(0,len(pred)-1,source.elf_slot_offset(pred,source.ENTRY,180),source.elf_slot_offset(pred,source.ENTRY+176,4),symbol+8,source.elf_slot_offset(pred,source.PARENT,128)):
            bad=bytearray(pred);bad[at]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        source.check_inputs(ROOT,self.out,(ROOT/source.SOURCE).read_bytes()!=self.values[source.SOURCE])
        self.receipt['image']=dict(raw_word_corruptions=45,extent_controls=1,binding_controls=1,GNU_links=links,
            layouts=3,HI_LO_and_call_rebased=True,strict_image_corruptions=6,exclusions=0,
            prediction=json.loads((self.out/'first-link.json').read_text()))


if __name__=='__main__':unittest.main()
