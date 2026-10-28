"""Actual recursive MIPS execution and independent finite-graph observations."""
from dataclasses import dataclass
from pathlib import Path
import copy,csv,io,os,subprocess,time
from tools.experiments import game_recursive_dependency_readiness_match as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
import itertools,json,struct,sys
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults

ENTRY,TABLE,BITMAP=0x1509CBD4,0x8008743C,0x800D2E4C
LISTS,BITS=0x200000,0x90000
@dataclass(frozen=True)
class Case:
    children:tuple=((),)
    mask:int=0
    root:int=0
    phase:int=0
    special:int=0

def fixture(c):
    entered=STACK+c.phase
    m={entered+i:(i*17+0xA5)&255 for i in range(-4096,256)}
    ids={c.root}|{i for i,_ in c.children}|{x for _,v in c.children for x in v}
    # A compact sparse table still tests exact wrapped guest indexing.
    for node in ids:
        at=(TABLE+node*20)&0xFFFFFFFF
        for off in range(20):m[(at+off)&0xFFFFFFFF]=0xA5
        put(m,at,((LISTS+node*32)&0xFFFFFFFF))
    for node,children in c.children:
        for i,value in enumerate((*children,65535)):put(m,(LISTS+node*32+i*2)&0xFFFFFFFF,value,2)
    for i in range(8192):m[BITS+i]=0
    for node in ids:
        if node>=0 and c.mask>>node&1:m[BITS+(node>>3)]|=1<<(node&7)
    put(m,BITMAP,BITS)
    if c.special:
        assert c.root==0 and c.children==((0,(5,)),(5,()))
        # At this SP the child saves the parent's S0 directly onto the
        # global bitmap-pointer word. Its value is the child id, five.
        assert entered-60==BITMAP
        m[5]=0;m[BITS]=32
    return m

def reference(c):
    graph=dict(c.children);calls=[]
    def visit(node):
        for child in graph[node]:
            calls.append((ENTRY,(child&0xFFFFFFFF,)))
            result=visit(child)
            if not(c.mask>>child&1)or not result:return 0
        return 1
    return visit(c.root),calls

class Oracle(RayOracle):
    def __init__(self,words,memory,c,entry=ENTRY,connected=None,arguments=None,fault=None):
        TimingOracle.__init__(self,words,memory,phase=c.phase if c.phase in(0,8)else 0,entry=entry,
            arguments=arguments or(c.root&0xFFFFFFFF,),connected=connected)
        self.r[29]=self.before[29]=STACK+c.phase
        self.trace=[];self.cut=fault;self.access_count=0
    def access(self):
        if self.own_instruction:
            if self.access_count==self.cut:raise faults.AccessBoundary
            self.access_count+=1
    def get(self,address,size):
        value=super().get(address,size)
        if self.own_instruction:self.trace.append(('R',address,size,value))
        return value
    def put(self,address,value,size):
        super().put(address,value,size)
        if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
    def record_call(self,target):
        assert target==ENTRY,hex(target)
        args=self.arguments(1);self.calls.append((target,args));self.events.append(('CALL',target,args))
    def hook(self,target):raise AssertionError(('Unowned recursive helper',hex(target)))

def linked(raw,bindings,entry=ENTRY,table=TABLE,bitmap=BITMAP):
    words=list(struct.unpack('>%dI'%(len(raw)//4),raw));symbols={'func_1509CBD4':entry,'D_8008743C':table,'D_800D2E4C':bitmap}
    for at,records in bindings.items():
        assert len(records)==1;kind,name=records[0];value=symbols[name];word=words[at//4]
        if kind=='R_MIPS_HI16':value=(value+0x8000)>>16&65535;mask=65535
        elif kind=='R_MIPS_LO16':value&=65535;mask=65535
        else:assert kind=='R_MIPS_26';value=value>>2&0x3FFFFFF;mask=0x3FFFFFF
        assert not word&mask;words[at//4]=(word&~mask)|value
    return words

def corpus():
    for phase in(0,8):
        for mask in range(512):
            # Tree, shared DAG, repeated children and depth-eight chain.
            for graph in(
                ((0,(1,2,3)),(1,(4,5)),(2,(6,7)),(3,(8,)),(4,()),(5,()),(6,()),(7,()),(8,())),
                ((0,(1,2,1)),(1,(3,4)),(2,(4,3)),(3,()),(4,())),
                tuple((i,(i+1,))for i in range(8))+((8,()),)):
                yield Case(graph,mask,phase=phase)
    for node in(0,1,7,8,255,256,32767,32768,65534):
        for byte in range(256):
            # Use 65535 as a valid root table index; it is not in the list.
            mask=(1<<node)if byte&(1<<(node&7))else 0
            yield Case(((65535,(node,)),(node,())),mask,65535)
    for root in(-1,-0x80000000,0x7FFFFFFF):yield Case(((root,()),),0,root)


def prepared_words(root):
    prepared=root/source.BUILD
    raw,rel=source.checked_payload(*source.payload(prepared/"selected.o"))
    normalized,nrel=source.normalized_payload(raw,rel)
    rom=(root/"conker/conker.us.bin").read_bytes()
    retail=list(struct.unpack_from(">48I",rom,source.ROM))
    guarded=linked(normalized,nrel);plain=linked(raw,rel)
    assert retail==guarded
    return retail,guarded,plain

def recursive_checks(root,output):
    OUT=root/source.BUILD
    raw,rel=source.payload(OUT/'selected.o');normalized,nrel=source.normalized_payload(raw,rel)
    rom=(root/'conker/conker.us.bin').read_bytes();retail=list(struct.unpack_from('>48I',rom,0xCA084))
    guarded=linked(normalized,nrel);plain=linked(raw,rel);assert guarded==retail
    cases=0;visits=set();depth=0;all_cases=list(corpus())
    special=Case(((0,(5,)),(5,())),1<<5,phase=BITMAP+60-STACK,special=1)
    for c in all_cases+[special]:
        initial=fixture(c)
        try:models=[Oracle(w,initial,c).run()for w in(retail,guarded,plain)]
        except Exception as exc:raise AssertionError(('Recursive fixture failed',c,'STACK',hex(STACK),repr(exc)))from exc
        literal,matched,cmodel=models
        for model in models:
            assert(model.memory,model.calls,model.r[2],model.trace)==(literal.memory,literal.calls,literal.r[2],literal.trace),c
        assert(literal.r,literal.events,literal.current_pc,literal.delay_of)==(matched.r,matched.events,matched.current_pc,matched.delay_of),c
        if not c.special:
            expected,calls=reference(c);assert(literal.r[2],literal.calls)==(expected,calls),c
        else:
            assert literal.r[2]==0 and read(literal.memory,BITMAP)==5
            assert any(t[:3]==('R',BITMAP,4)and t[3]==5 for t in literal.trace)
        visits.update(literal.visits);depth=max(depth,(STACK+c.phase-min(x[1]for x in literal.trace if x[0]=='W'))//40);cases+=1
    missing=set(range(ENTRY,ENTRY+192,4))-visits
    # The second lhu at +144 is unreachable: the preceding unconditional
    # branch and its zero-result delay slot bypass it on every path.
    assert missing=={ENTRY+144},missing
    q=dict(cases=cases,visited_body_words=47,unreachable_word_offset=144,all48_literal_words_checked=True,actual_recursion=True,raw_C_memory_result_calls_and_access_trace_equal=True,independent_finite_graph_reference=True,child_stack_overwrites_live_bitmap_pointer=True)
    (output/"guest.json").write_text(json.dumps(q,indent=2)+"\n")
    return q


def fault_checks(root,output):
    retail,guarded,plain=prepared_words(root)
    all_cases=list(corpus())
    special=Case(((0,(5,)),(5,())),1<<5,phase=BITMAP+60-STACK,special=1)
    fault_pairs=0
    for c in(all_cases[0],all_cases[511],all_cases[1535],all_cases[-1],special):
        baseline=Oracle(retail,fixture(c),c).run()
        for cut in range(baseline.access_count):
            pair=[Oracle(w,fixture(c),c,fault=cut)for w in(retail,guarded)]
            for model in pair:
                try:model.run()
                except faults.AccessBoundary:pass
                else:raise AssertionError(('Fault did not fire',cut))
            a,b=pair;assert(a.memory,a.r,a.trace,a.calls,a.current_pc,a.delay_of)==(b.memory,b.r,b.trace,b.calls,b.current_pc,b.delay_of)
            fault_pairs+=1
    # Cycles retain the original unbounded recursion; compare fired prefixes
    # instead of inserting a depth limit or treating them as a false result.
    c=Case(((0,(0,)),),1)
    for cut in(10,50,100,200):
        pair=[Oracle(w,fixture(c),c,fault=cut)for w in(retail,guarded)]
        for model in pair:
            try:model.run()
            except faults.AccessBoundary:pass
            else:raise AssertionError('Cycle prefix did not reach its cut')
        a,b=pair;assert(a.memory,a.r,a.trace,a.calls,a.current_pc,a.delay_of)==(b.memory,b.r,b.trace,b.calls,b.current_pc,b.delay_of);fault_pairs+=1
    q=dict(fired_prefix_pairs=fault_pairs,full_private_register_memory_PC_delay_trace_equal=True,cycles_retain_unbounded_prefix=True)
    (output/"faults.json").write_text(json.dumps(q,indent=2)+"\n")
    return q


def native_checks(root,output):
    r=root;o=output
    body=source.SELECTED;F=source.FUNCTION
    variants=dict(selected=body,
        wrong_stride=body.replace('index * 20','index * 16'),
        wrong_byte=body.replace('child >> 3','child >> 4'),
        wrong_bit=body.replace('child & 7','(child + 1) & 7'),
        ignore_result=body.replace('result == 0','result < 0'),
        skip_recursion=body.replace('result = '+F+'(child);','result = 1;'),
        wrong_empty=body.replace('return 1;','return 0;'),
        wrong_failure=body.replace('return 0;','return 1;'))
    assert len(set(variants.values()))==len(variants)
    t='#include <ultra64.h>\n'+r'''
    typedef char NativeABI[(sizeof(void*)==4&&sizeof(s32)==4&&sizeof(u16)==2)?1:-1];
    s32 D_8008743C[65536*5];
    static struct {u32 pre[4];u16 data[65536][4];u32 post[4];} lists;
    static struct {u32 pre[4];u8 data[8192];u32 post[4];} bitmap;
    static u16 empty[4];u8 *D_800D2E4C;
    static u32 completed;
    '''
    for name,text in variants.items():
        text=text.replace(F,'candidate_'+name).replace('s32 candidate_'+name+'(',
            '__attribute__((noinline)) s32 candidate_'+name+'(')
        t+=text+'\n'
    t+=r'''
    typedef s32(*Candidate)(s32);
    static s32 fences(void){u32 i;for(i=0;i<4;i++)if(lists.pre[i]!=(0xCAFE0000u+i)||lists.post[i]!=(0xBAFE0000u+i)||bitmap.pre[i]!=(0xDAFE0000u+i)||bitmap.post[i]!=(0xEAFE0000u+i))return 1;return 0;}
    static void init(void){
     u32 i,j;completed=0;D_800D2E4C=bitmap.data;
     for(i=0;i<4;i++){empty[i]=65535;lists.pre[i]=0xCAFE0000u+i;lists.post[i]=0xBAFE0000u+i;bitmap.pre[i]=0xDAFE0000u+i;bitmap.post[i]=0xEAFE0000u+i;}
     for(i=0;i<65536;i++){for(j=0;j<4;j++)lists.data[i][j]=65535;D_8008743C[i*5]=(s32)&lists.data[i][0];for(j=1;j<5;j++)D_8008743C[i*5+j]=(s32)empty;}
     for(i=0;i<8192;i++)bitmap.data[i]=0;
    }
    static s32 one(Candidate fn,u32 child,u32 byte){
     s32 wanted,got;u32 at=child>>3;
     lists.data[65535][0]=(u16)child;bitmap.data[at]=(u8)byte;wanted=(byte>>(child&7))&1;got=fn(65535);completed++;
     if(got!=wanted||D_800D2E4C!=bitmap.data||lists.data[65535][0]!=child||lists.data[65535][1]!=65535||lists.data[child][0]!=65535||bitmap.data[at]!=byte||fences())return 1;
     bitmap.data[at]=0;return 0;
    }
    static s32 family(Candidate fn){
     static const u32 ids[]={0,1,7,8,255,256,32768,65534};u32 child,b,pattern,mask,i,j;
     init();
     for(child=0;child<65535;child++)for(pattern=0;pattern<4;pattern++){
      b=pattern==0?0:pattern==1?255:pattern==2?(1u<<(child&7)):(255u^(1u<<(child&7)));
      if(one(fn,child,b))return 1;
     }
     for(i=0;i<8;i++)for(b=0;b<256;b++)if(one(fn,ids[i],b))return 2;
     lists.data[65535][0]=65535;
     for(i=0;i<12;i++)lists.data[i][0]=(u16)(i+1);
     for(mask=0;mask<4096;mask++){
      bitmap.data[0]=(u8)(mask<<1);bitmap.data[1]=(u8)(mask>>7);
      if(fn(0)!=(s32)(mask==4095)||D_800D2E4C!=bitmap.data||bitmap.data[0]!=(u8)(mask<<1)||bitmap.data[1]!=(u8)(mask>>7)||fences())return 3;
      completed++;
     }
     for(i=0;i<12;i++)lists.data[i][0]=65535;
     for(i=0;i<8192;i++)bitmap.data[i]=0;
     if(completed!=268284||fences())return 4;
     for(i=0;i<65536;i++){
      if(D_8008743C[i*5]!=(s32)&lists.data[i][0])return 5;
      for(j=1;j<5;j++)if(D_8008743C[i*5+j]!=(s32)empty)return 6;
      for(j=0;j<4;j++)if(lists.data[i][j]!=65535)return 7;
     }
     return 0;
    }
    static int run(void){
     Candidate controls[]={candidate_wrong_stride,candidate_wrong_byte,candidate_wrong_bit,candidate_ignore_result,candidate_skip_recursion,candidate_wrong_empty,candidate_wrong_failure};u32 i;
     if(family(candidate_selected))return 10;
     for(i=0;i<7;i++)if(family(controls[i])==0)return (int)(100+i);
     return 0;
    }
    '''+START.replace('void _start(void)', '__attribute__((force_align_arg_pointer)) void _start(void)')
    p=o/'native-semantics.c';p.write_text(t);receipts=[];start=time.monotonic()
    for opt in('O0','O2','O3'):
        exe=o/('native-semantics-'+opt);cmd=native_command('-'+opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)]
        q=subprocess.run(cmd,cwd=r,capture_output=True,text=True);(o/('native-'+opt+'-compile.log')).write_text(q.stdout+q.stderr);assert q.returncode==0,(q.returncode,q.stdout,q.stderr)
        q=subprocess.run([str(exe)],capture_output=True,text=True,timeout=45);assert q.returncode==0,(opt,q.returncode,q.stdout,q.stderr)
        receipts.append(dict(profile=opt,positive_cases=268284,effective_controls=7,exit=q.returncode));print(receipts[-1],flush=True)
    q=dict(private_only=True,matching_credit=0,profiles=receipts,all65535_non_sentinel_child_values=True,all256_bitmap_bytes_at8_boundary_nodes=True,
        twelve_edge_chain_all4096_masks=True,independent_closed_expected_results=True,trapping_UBSan=True,freestanding_startup_stack_explicitly_aligned=True,
        noinline_recursive_C=True,complete_final_descriptor_list_inputs_and_buffer_fences=True,
        strict_aliasing_disabled_for_original_flat32bit_pointer_storage=True,guest_wrapped_indices_and_stack_aliases_separate=True,
        seconds=round(time.monotonic()-start,3))
    (o/'native-semantics.json').write_text(json.dumps(q,indent=2)+'\n');print(q,flush=True)

    return q


def caller_checks(root,output):
    r=root;o=root/source.BUILD;model=sys.modules[__name__]
    from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
    PARENT=0x1509B4A0;FIRST,SECOND,APPLY,FINISH=0x1509C120,0x15096970,0x1509B5AC,0x1509C3A0
    COUNT,IDS,FLAG=0x800D2F3C,0x800D2F40,0x8003C8E0
    PRIMARY,OTHER,ARGUMENT=0x30000,0x31000,0x87654321
    read,put=model.read,model.put
    def effect(memory,effects):
        if effects&1:memory[model.BITS]^=255
        if effects&2:put(memory,IDS,OTHER)
        if effects&4:put(memory,COUNT,1,1)
    def fixture(c,count):
        m=model.fixture(c);put(m,COUNT,count,1);put(m,IDS,PRIMARY);put(m,FLAG,0xDEADBEEF)
        for base,values in((PRIMARY,(0,1,2)),(OTHER,(2,1,0))):
            for i,value in enumerate(values):put(m,base+i*2,value,2)
        return m
    def reference(initial,effects):
        m=dict(initial);calls=[(FIRST,()),(SECOND,())];put(m,FLAG,0x05000000)
        def visit(node):
            pointer=read(m,(model.TABLE+node*20)&0xFFFFFFFF)
            while True:
                child=read(m,pointer,2)
                if child==65535:return 1
                calls.append((model.ENTRY,(child,)));result=visit(child)
                child=read(m,pointer,2)
                if not(m[(read(m,model.BITMAP)+(child>>3))&0xFFFFFFFF]&(1<<(child&7)))or not result:return 0
                pointer+=2
        index=0
        while index<read(m,COUNT,1):
            node=read(m,read(m,IDS)+2*index,2);calls.append((model.ENTRY,(node,)))
            if visit(node):
                node=read(m,read(m,IDS)+2*index,2);calls.append((APPLY,(node,ARGUMENT)));effect(m,effects)
            index+=1
        calls.append((FINISH,()));put(m,FLAG,0);return m,calls
    class CallerOracle(model.Oracle):
        def __init__(self,words,memory,c,connected,effects):
            super().__init__(words,memory,c,entry=PARENT,connected=connected,arguments=(0x12345678,ARGUMENT));self.effects=effects
        def record_call(self,target):
            sizes={FIRST:0,SECOND:0,FINISH:0,APPLY:2,model.ENTRY:1};assert target in sizes,hex(target)
            args=self.arguments(sizes[target]);self.calls.append((target,args));self.events.append(('CALL',target,args))
        def hook(self,target):
            assert target in(FIRST,SECOND,FINISH,APPLY)
            if target==APPLY:effect(self.memory,self.effects)
            for i in range(4):put(self.memory,self.r[29]+i*4,0xB5000000+i)
            for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
            self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
    def external(memory,c):
        entered=model.STACK+c.phase
        return{a:b for a,b in memory.items()if not entered-4096<=a<entered+256}

    raw,rel=source.payload(o/'selected.o');normalized,nrel=source.normalized_payload(raw,rel)
    rom=(r/'conker/conker.us.bin').read_bytes();parent=list(struct.unpack_from('>52I',rom,0xC8950));retail=list(struct.unpack_from('>48I',rom,0xCA084));guarded=model.linked(normalized,nrel);plain=model.linked(raw,rel)
    graph=((0,(1,2)),(1,(3,)),(2,(4,)),(3,()),(4,()))
    cases=0;parent_visits=set();target_visits=set()
    for mask,count,effects,phase in itertools.product(range(16),(0,1,3),(0,1,2,4,3,7),(0,8)):
        c=model.Case(graph,mask<<1,phase=phase);m=fixture(c,count);wanted,calls=reference(m,effects)
        models=[CallerOracle(parent,m,c,{model.ENTRY+4*i:w for i,w in enumerate(body)},effects).run()for body in(retail,guarded,plain)]
        a,b,raw_c=models
        for machine in models:
            assert(external(machine.memory,c),machine.calls)==(external(wanted,c),calls),(mask,count,effects,phase)
            assert read(machine.memory,FLAG)==0
        assert(a.memory,a.r,a.trace,a.events)==(b.memory,b.r,b.trace,b.events)
        assert(a.memory,a.trace,a.calls)==(raw_c.memory,raw_c.trace,raw_c.calls)
        parent_visits.update(a.visits&set(range(PARENT,PARENT+208,4)));target_visits.update(a.visits&set(range(model.ENTRY,model.ENTRY+192,4)));cases+=1
    assert parent_visits==set(range(PARENT,PARENT+208,4)),set(range(PARENT,PARENT+208,4))-parent_visits
    current=(r/'conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(current,PARENT,208)
    q=dict(private_only=True,matching_credit=0,connected_cases=cases,complete_original_caller_words=52,all52_caller_words_visited=True,
        caller_frame=48,actual_target_and_recursive_calls_executed=True,signed32_boolean_return_consumed_before_apply=True,
        saved_second_argument_forwarded=True,live_halfword_list_pointer_and_byte_count=True,bounded_apply_bitmap_pointer_count_effects=True,
        current_caller_equals_original_208bytes=current[at:at+208]==rom[0xC8950:0xC8A20],
        other_helpers_bounded_opaque_not_new_C_or_full_pipeline_credit=True,raw_C_full_memory_calls_access_trace_equal=True,
        normalized_full_register_memory_private_trace_equal=True)
    (output/'caller-integration.json').write_text(json.dumps(q,indent=2)+'\n');print(q,flush=True)

    return q


def opening_checks(root,output):
    r=root;o=output;prepared=root/source.BUILD;m=sys.modules[__name__];start=time.monotonic()
    raw,bindings=source.payload(prepared/'selected.o');normalized,nrel=source.normalized_payload(raw,bindings)
    literal=m.linked(normalized,nrel);plain=m.linked(raw,bindings)
    class Join(Exception):pass
    class JoinCode(m.faults.TrackedCode):
        def __getitem__(self,pc):
            if pc in(m.ENTRY+76,m.ENTRY+164):raise Join(pc)
            return super().__getitem__(pc)
    initial={m.STACK+i:(i*17+0xA5)&255 for i in range(-48,16)}
    m.put(initial,m.TABLE,m.LISTS);c=m.Case(((0,()),),0)
    for first in range(65536):
        m.put(initial,m.LISTS,first,2);pair=[m.Oracle(w,initial,c)for w in(literal,plain)];joins=[]
        for machine in pair:
            machine.code=JoinCode(machine.code,machine)
            try:machine.run()
            except Join as exc:joins.append(exc.args[0])
            else:raise AssertionError('Opening join was not reached')
        a,b=pair;expected=m.ENTRY+(164 if first==65535 else 76)
        assert joins==[expected,expected]and a.r[16]==b.r[16]==first
        assert a.r[2]==b.r[2]==(1 if first==65535 else m.LISTS)
        assert(a.memory,a.trace)==(b.memory,b.trace)
        assert all(a.r[reg]==b.r[reg]for reg in(*range(16,24),28,29,30,31))
    print('OPENING_JOINS',65536,flush=True)

    q=dict(actual_join_pairs=65536,all_first_halfwords=True,empty_and_nonempty_common_joins_equal=True,memory_access_S0_V0_and_saved_registers_equal=True)
    (output/"opening.json").write_text(json.dumps(q,indent=2)+"\n")
    return q


def rebase_control_checks(root,output):
    r=root;o=output;prepared=root/source.BUILD;m=sys.modules[__name__];start=time.monotonic()
    raw,bindings=source.payload(prepared/'selected.o');normalized,nrel=source.normalized_payload(raw,bindings)
    literal=m.linked(normalized,nrel);plain=m.linked(raw,bindings)
    assembly=(prepared/'before-conker_asm_C9EC0.s').read_text();begin=assembly.index('glabel '+source.FUNCTION);end=assembly.index('endlabel '+source.FUNCTION,begin)+len('endlabel '+source.FUNCTION)
    target=o/'isolated-target.s';target.write_text(assembly[begin:end]+'\n')
    reader=csv.DictReader(io.StringIO((prepared/'proposed-word-patches.csv').read_text()));fields=reader.fieldnames;rows=[row for row in reader if row['function']==source.FUNCTION];assert rows==source.NEW_GUARDS;isolated_guards=o/'isolated-target-guards.csv'
    with isolated_guards.open('w',newline='')as stream:
     writer=csv.DictWriter(stream,fields);writer.writeheader();writer.writerows(rows)
    path=o/'isolated-normalized.s';path.write_text(emit_padded_assembly(prepared/'selected.o',target,word_patches_path=isolated_guards,filename=source.OWNER))
    obj=path.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(r/'conker/include'),'-o',str(obj),str(path)],check=True,capture_output=True)
    def link(obj,label,entry,table,bitmap):
        script=o/(label+'.ld');elf=script.with_suffix('.elf');script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        cmd=['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,'--defsym=D_8008743C=0x%X'%table,'--defsym=D_800D2E4C=0x%X'%bitmap,'-o',str(elf),str(obj)]
        subprocess.run(cmd,check=True,capture_output=True);data=sections(elf)['.text'][1];assert len(data)==192;return list(struct.unpack('>48I',data))
    class Rebased(m.Oracle):
        def __init__(self,words,memory,c,entry):super().__init__(words,memory,c,entry=entry);self.rebased_entry=entry
        def record_call(self,target):
            assert target==self.rebased_entry,hex(target);args=self.arguments(1);self.calls.append((m.ENTRY,args));self.events.append(('CALL',target,args))
    def remap(memory,c,table,bitmap):
        data=dict(memory);ids={c.root}|{i for i,_ in c.children}|{v for _,children in c.children for v in children}
        for node in ids:
            old=(m.TABLE+node*20)&0xFFFFFFFF;new=(table+node*20)&0xFFFFFFFF
            for i in range(20):data[(new+i)&0xFFFFFFFF]=data.pop((old+i)&0xFFFFFFFF)
        for i in range(4):data[bitmap+i]=data.pop(m.BITMAP+i)
        return data
    rebased_cases=0
    for index,(entry,table,bitmap)in enumerate(((0x15200000,0x81207FFC,0x81208008),(0x15210004,0x81308000,0x8130FFFC),(0x1522FFF0,0x8140FFFC,0x81410004))):
        words=[link(obj,'gnu-%d-%s'%(index,label),entry,table,bitmap)for label,obj in(('original',prepared/'original-func_1509CBD4.o'),('normalized',obj),('raw',prepared/'selected.o'))]
        assert words[0]==words[1]
        for mask,phase in((0,0),(31,0),(31,8),(15,8),(2,0),(30,8)):
            c=m.Case(((0,(1,2,1)),(1,(3,)),(2,(4,)),(3,()),(4,())),mask,phase=phase);memory=remap(m.fixture(c),c,table,bitmap)
            models=[Rebased(w,memory,c,entry).run()for w in words];a,b,raw_c=models
            for machine in models:assert(machine.memory,machine.calls,machine.r[2],machine.trace)==(a.memory,a.calls,a.r[2],a.trace)
            assert(a.r,a.events,a.current_pc,a.delay_of)==(b.r,b.events,b.current_pc,b.delay_of);assert(a.r[2],a.calls)==m.reference(c);rebased_cases+=1
    print('GNU_REBASE_CASES',rebased_cases,flush=True)

    controls={'skip_recursion':source.SELECTED.replace('result = func_1509CBD4(child);','result = 1;'),
              'wrong_result':source.SELECTED.replace('return 1;','return 2;')}
    compiled=[]
    for name,body in controls.items():
        obj,diagnostics=source.compile_owner(r,o,source.HEADERS+source.DECLARATIONS+body,'control-'+name);assert not diagnostics
        payload,rel=source.payload(obj);wrong=m.linked(payload,rel)
        c=m.Case(((0,(1,)),(1,())),2);memory=m.fixture(c);truth=m.Oracle(literal,memory,c).run();candidate=m.Oracle(wrong,memory,c).run()
        assert(candidate.r[2],candidate.calls)!=(truth.r[2],truth.calls);compiled.append(name)

    rejections=0
    def rejected(fn):
        nonlocal rejections
        try:fn()
        except(ValueError,AssertionError):rejections+=1
        else:raise AssertionError('Ineffective rejection control')
    rejected(lambda:source.checked_payload(raw[:-4],bindings))
    corrupt=bytearray(raw);corrupt[0]^=1;rejected(lambda:source.checked_payload(bytes(corrupt),bindings))
    wrong=copy.deepcopy(bindings);wrong[76]=[('R_MIPS_26','func_1509CCF4')];rejected(lambda:source.checked_payload(raw,wrong))
    guards=source.NEW_GUARDS;source.NEW_GUARDS=copy.deepcopy(guards);source.NEW_GUARDS[0]['expected']='0x00000000';rejected(lambda:source.normalized_payload(raw,bindings));source.NEW_GUARDS=guards
    before=(prepared/'before-conker_build_conker.us.elf').read_bytes();actual=(prepared/'first-linked.elf').read_bytes();rom=(r/'conker/conker.us.bin').read_bytes();truth=rom[0xCA084:0xCA144];source.check_image(before,actual,truth)
    for at in(0,20,len(actual)-1,source.elf_slot_offset(actual,m.ENTRY,192),source.elf_slot_offset(actual,m.ENTRY,192)+191):
        damaged=bytearray(actual);damaged[at]^=1;rejected(lambda damaged=bytes(damaged):source.check_image(before,damaged,truth))
    rejected(lambda:source.guard_manifest((prepared/'before-conker_retail_word_patches.us.csv').read_bytes()+b'\n'))
    q=dict(private_only=True,matching_credit=0,derived_guard_count=12,
        actual_generated_isolated_padder_equal=True,isolated_manifest_exact_target_rows=True,complete_owner_manifest_already_qualified=True,GNU_layouts=3,rebased_recursive_cases=rebased_cases,signed_low_half_carries=True,
        actual_IDO_effective_controls=compiled,rejection_controls=rejections,strict_image_bytes=146,strict_image_exclusions=0,
        seconds=round(time.monotonic()-start,3))
    (o/'boundary-qualification.json').write_text(json.dumps(q,indent=2)+'\n');print(q,flush=True)

    return q
