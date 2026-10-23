"""Signed recursive node search: typed native, guest, callers and image gates."""
from pathlib import Path
import csv,io,itertools,json,struct,subprocess,unittest
from tools.experiments import game_recursive_node_search as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT=Path(__file__).resolve().parents[2]
ENTRY,TABLE=source.ENTRY,source.TABLE
OWNER,RECORD,NEXT=0x20000,0x24000,0x26000
VALUES=(-32768,-1,0,1,2,3,4,5,6,256,257,32767)

def native_harness(body, context):
    right='    if (func_1514D4B8(D_8008ABE8[index][3], wanted)) return 1;'
    left='    if (func_1514D4B8(D_8008ABE8[index][2], wanted)) return 1;'
    controls=dict(selected=body,
     sentinel_true=body.replace('if (index == -1) return 0;','if (index == -1) return 1;'),
     equality_false=body.replace('if (index == wanted) return 1;','if (index == wanted) return 0;'),
     skip_zero=body.replace('if (index == -1) return 0;','if (index == -1) return 0;\n    if (index == 0) return 0;'),
     drop_right=body.replace(right,''),drop_left=body.replace(left,''),
     right_as_left=body.replace('[index][3]','[index][2]'),left_as_right=body.replace('[index][2]','[index][3]'),
     wrong_wanted=body.replace(', wanted))',', 0))'),
     low_byte_match=body.replace('index == wanted','(u8)index == (u8)wanted'),
     one_ahead=body.replace('index == wanted','index + 1 == wanted'),
     sentinel_order=body.replace('    if (index == -1) return 0;\n    if (index == wanted) return 1;',
         '    if (index == wanted) return 1;\n    if (index == -1) return 0;'),
     non_boolean=body.replace('return 1;','return 2;'))
    assert len(controls)==13 and len(set(controls.values()))==13
    bodies='\n'.join(text.replace('func_1514D4B8',label)for label,text in controls.items())
    retail=',\n'.join('{'+','.join(map(str,row['cells']))+'}'for row in context['nodes'])
    checks='\n'.join('if(variant(%s)!=%d)return %d;'%(label,0 if label=='selected'else 23,40+i)for i,label in enumerate(controls))
    actual_pairs=context['terminating_native_pairs'];cases=2110792+len(actual_pairs)
    valid=',\n'.join('{%d,%d}'%(q['index'],q['wanted'])for q in actual_pairs)
    source='''#include <ultra64.h>
    typedef struct {u32 left[4];s16 nodes[30][4];u32 right[4];} Arena;
    typedef s32(*Probe)(s16,s16);
    static Arena arena;
    s16 *D_8008ABE8[30];
    static u8 before_arena[sizeof(Arena)],before_table[sizeof(D_8008ABE8)];
    static const s16 retail[28][4]={RETAIL};
    static const s16 wanted_cases[]={-32768,-1,0,1,2,3,4,5,6,256,257,32767};
    static const s16 actual_pairs[][2]={VALID};
    ''' .replace('RETAIL',retail).replace('VALID',valid)+bodies+'''
    static void snapshot(void){u32 j;for(j=0;j<sizeof(Arena);j++)before_arena[j]=((u8*)&arena)[j];
     for(j=0;j<sizeof(D_8008ABE8);j++)before_table[j]=((u8*)D_8008ABE8)[j];}
    static void setup(u32 plan,u32 actual){u32 i,j,choice;
     for(j=0;j<sizeof(Arena);j++)((u8*)&arena)[j]=(u8)(j*13+37);
     for(i=0;i<30;i++){
      D_8008ABE8[i]=actual&&i>=28?0:arena.nodes[i];
      for(j=0;j<4;j++)arena.nodes[i][j]=actual?(i<28?retail[i][j]:0):(j<2?(s16)(0x5A00+i):-1);
      if(!actual&&i<4)for(j=2;j<4;j++){
       choice=plan%3;plan/=3;arena.nodes[i][j]=choice==0?-1:choice==1?(s16)(i+1):4;
      }
     }
     snapshot();}
    static s32 reference(s16 index,s16 wanted){s16 stack[64];u32 top=1,steps=0;stack[0]=index;
     while(top){s16 at=stack[--top];if(++steps>4096||top>61)return -3;
      if(at==-1)continue;if(at==wanted)return 1;
      if(at<0||at>=30)return -4;
      stack[top++]=arena.nodes[at][2];stack[top++]=arena.nodes[at][3];
     }return 0;}
    static s32 check(Probe probe,s16 index,s16 wanted){s32 expect=reference(index,wanted);u32 j;
     if(expect<0)return 25;
     if(probe(index,wanted)!=expect)return 23;
     for(j=0;j<sizeof(Arena);j++)if(((u8*)&arena)[j]!=before_arena[j])return 23;
     for(j=0;j<sizeof(D_8008ABE8);j++)if(((u8*)D_8008ABE8)[j]!=before_table[j])return 23;
     return 0;}
    static s32 variant(Probe probe){u32 plan,w,count=0; s32 index,result;
     for(plan=0;plan<6561;plan++){
      setup(plan,0);
      for(index=-1;index<5;index++)for(w=0;w<sizeof(wanted_cases)/sizeof(wanted_cases[0]);w++){
       result=check(probe,(s16)index,wanted_cases[w]);if(result)return result;count++;
      }
     }
     for(plan=0;plan<4;plan++){
      setup(plan==0?0:plan==1?6560:plan==2?1234:4321,0);
      for(index=-1;index<5;index++)for(w=0;w<65536;w++){
       result=check(probe,(s16)index,(s16)(u16)w);if(result)return result;count++;
      }
     }
     setup(0,1);
     for(w=0;w<sizeof(actual_pairs)/sizeof(actual_pairs[0]);w++){
      result=check(probe,actual_pairs[w][0],actual_pairs[w][1]);if(result)return result;count++;
     }
     for(w=0;w<65536;w++){
      result=check(probe,(s16)(u16)w,(s16)(u16)w);if(result)return result;count++;
     }
     return count==EXPECTED?0:24;}
    static s32 run(void){CHECKS return 0;}
    __attribute__((force_align_arg_pointer)) void _start(void){int code=run();__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
    '''.replace('CHECKS',checks).replace('EXPECTED',str(cases))
    assert 6561*6*12+4*6*65536+65536==2110792
    source=source.replace('#include <ultra64.h>','#include <ultra64.h>\ntypedef char NativeWidths[sizeof(void*)==4&&sizeof(s16)==2&&sizeof(s32)==4?1:-1];',1)
    return source, cases


def half(value):
    value &= 65535
    return value-65536 if value&32768 else value


def public(memory):
    return {a:v for a,v in memory.items()if not STACK-0x2000<=a<STACK+0x900}


def public_trace(trace):
    return [row for row in trace if not STACK-0x2000<=row[1]<STACK+0x900]


def fixture(context,phase=0,table=TABLE,plan=None,deep=False):
    sp=STACK+phase
    memory={sp+i:(i*17+0xA5)&255 for i in range(-0x1000 if deep else -0x240,0x24)}
    if plan is None:
        pointers=context['pointers'];nodes=context['nodes']
    else:
        pointers=[0x100000+i*16 for i in range(5)]+[0]*25;nodes=[]
        for i in range(5):
            links=[]
            for _ in range(2):
                choice=plan%3;plan//=3
                links.append(-1 if i==4 or choice==0 else i+1 if choice==1 else 4)
            nodes.append(dict(pointer=pointers[i],cells=[0x5A00+i,0x6B00+i,*links]))
    assert not STACK-0x2000<=table<STACK+0x900
    for i,pointer in enumerate(pointers):put(memory,table+4*i,pointer)
    for row in nodes:
        pointer=row['pointer'];assert not STACK-0x2000<=pointer<STACK+0x900
        for offset in range(-4,12):memory.setdefault(pointer+offset,(offset*13+37)&255)
        for i,value in enumerate(row['cells']):put(memory,pointer+2*i,value,2)
    return memory


def reference(memory,index,wanted,entry=ENTRY,table=TABLE):
    trace=[];calls=[];active=[]
    wanted=half(wanted)
    def rd(address,size):
        value=read(memory,address,size);trace.append(('R',address,size,value));return value
    def visit(index,called=False):
        index=half(index)
        if called:calls.append((entry,(index&0xFFFFFFFF,wanted&0xFFFFFFFF)))
        if index==-1:return 0
        if index==wanted:return 1
        assert index not in active,('reference cycle',index,wanted)
        active.append(index)
        node=rd((table+index*4)&0xFFFFFFFF,4)
        result=visit(half(rd((node+6)&0xFFFFFFFF,2)),True)
        if not result:
            node=rd((table+index*4)&0xFFFFFFFF,4)
            result=visit(half(rd((node+4)&0xFFFFFFFF,2)),True)
        active.pop();return int(bool(result))
    return visit(index),calls,trace


class WindowBoundary(Exception):
    pass


class WindowCode(faults.TrackedCode):
    def __init__(self,values,owner,stops):
        super().__init__(values,owner);self.stops=set(stops)
    def __getitem__(self,pc):
        if pc in self.stops:
            self.owner.current_pc=pc;self.owner.delay_of=None
            raise WindowBoundary(pc)
        return super().__getitem__(pc)


class NodeOracle(TimingOracle):
    def __init__(self,words,memory,args,phase=0,entry=ENTRY,leaf=ENTRY,connected=None,stops=()):
        self.trace=[];self.attempted=None;self.leaf=leaf;self.minimum_sp=STACK+phase
        super().__init__(words,memory,phase=phase,entry=entry,arguments=args,connected=connected)
        if stops:self.code=WindowCode(self.code,self,stops)
    def execute(self,word):
        super().execute(word);self.minimum_sp=min(self.minimum_sp,self.r[29])
    def get(self,address,size):
        if self.own_instruction:self.attempted=('R',address,size)
        value=super().get(address,size)
        if self.own_instruction:self.trace.append(('R',address,size,value))
        return value
    def put(self,address,value,size):
        if self.recording and self.own_instruction:self.attempted=('W',address,size,value&((1<<(8*size))-1))
        super().put(address,value,size)
        if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(8*size))-1)))
    def record_call(self,target):
        assert target==self.leaf,hex(target)
        args=self.arguments(2);self.calls.append((target,args));self.events.append(('CALL',target,args))
    def hook(self,target):
        raise AssertionError(('unconnected recursive call',hex(target)))


class RecursiveNodeSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);cls.rom=cls.values['conker/conker.us.bin']
        name='func_1514D4B8';target=source.TARGETS[name];cls.target=target
        cls.installed=(ROOT/target['source']).read_text()==source.recovered_owner(name,cls.values[target['source']].decode())
        if cls.installed:source.audit(ROOT,cls.out)
        else:source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        cls.context=source.retail_context(cls.values)
        cls.obj,diag=source.compile_owner(ROOT,cls.out,source.ISOLATED_HEADERS+source.DECLARATIONS+source.SELECTED[name],'fresh-selected')
        if diag:raise ValueError(diag)
        images=[]
        for obj in(source.original(ROOT,cls.out,name),cls.obj,cls.out/'qualified-generated_179F30.o'):
            data,fs=source.link_owner(ROOT,cls.out,obj,target['owner'])
            images.append(list(struct.unpack_from('>43I',data,fs[name]['value'])))
        cls.images=images;cls.windows=[]
        for caller in source.CALLERS:
            off=caller['entry']-0x15000000+0x2D4B0
            cls.windows.append(list(struct.unpack_from('>%dI'%caller['words'],cls.rom,off)))
        cls.receipt=dict(installed=cls.installed)
    @classmethod
    def tearDownClass(cls):
        (cls.out/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n');print(cls.receipt)

    def compare(self,index,wanted,phase=0,plan=None,images=None,entry=ENTRY,table=TABLE,memory=None):
        memory=fixture(self.context,phase,table,plan)if memory is None else memory
        expected,calls,trace=reference(memory,index,wanted,entry,table);models=[]
        for words in images or self.images:
            m=NodeOracle(words,memory,(index,wanted),phase,entry=entry,leaf=entry).run();models.append(m)
            self.assertEqual(m.r[2],expected);self.assertEqual(m.calls,calls)
            self.assertEqual(public(m.memory),public(memory));self.assertEqual(public_trace(m.trace),trace)
            self.assertEqual(read(m.memory,STACK+phase),index&0xFFFFFFFF)
            self.assertEqual(read(m.memory,STACK+phase+4),wanted&0xFFFFFFFF)
        self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(complete(models[0]),complete(models[2]))
        return models

    def test_01_direct_C_raw_owner_actual_Make_and_stub(self):
        q=json.loads((self.out/'qualification.json').read_text());m=json.loads((self.out/'make-shadow.json').read_text())
        self.assertEqual((q['total_words'],q['new_guards'],q['compiler_only'],m['actual_Make_commands']),(43,0,True,3))
        self.assertEqual(self.images[0],self.images[1]);self.assertEqual(self.images[0],self.images[2])
        self.assertEqual(self.images[0],list(struct.unpack_from('>43I',self.rom,0x17A968)))
        raw,bindings=source.payload(self.obj,'func_1514D4B8')
        self.assertEqual(source.normalized('func_1514D4B8',raw,bindings),(raw,bindings))
        old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,ENTRY,172)
        stub=list(struct.unpack_from('>43I',old,at))
        model=NodeOracle(stub,fixture(self.context),(0,0)).run();self.assertEqual(model.r[2],0)
        self.assertEqual(self.compare(0,0)[0].r[2],1)
        actual=self.out/'make-shadow/src/game/generated_179F30.c.o'
        self.assertEqual(actual.read_bytes(),(self.out/'qualified-generated_179F30.o').read_bytes())
        self.receipt.update(words=43,frame=32,bindings=4,new_guards=0,compiler_only=True,
            actual_Make_commands=3,neighbors=q['preserved_neighbors'],old_stub_rejected_by_return_value=True,
            complete_padded_Make_object_byte_identical=True)

    def test_02_recursive_guest_semantics_homes_sparse_indices_and_coverage(self):
        phases=0;visits=set()
        for q,phase in itertools.product(self.context['terminating_native_pairs'],(0,8)):
            visits.update(self.compare(q['index'],q['wanted'],phase)[0].visits);phases+=1
        for plan,index,wanted,phase in itertools.product((0,1,3,40,1234,6560),range(-1,5),VALUES,(0,8)):
            visits.update(self.compare(index,wanted,phase,plan)[0].visits);phases+=1
        for low,high,phase in itertools.product((0,1,10,28,29,0x8000,0xFFFF),(0,0x12340000,0xFFFF0000),(0,8)):
            self.compare(high|low,(high^0xABCD0000)|low,phase);phases+=1
        sparse=0
        for index,wanted,phase in itertools.product((-32768,-2,28,29,32767),(0,1,27,-1),(0,8)):
            memory=fixture(self.context,phase)
            put(memory,(TABLE+index*4)&0xFFFFFFFF,self.context['nodes'][3]['pointer'])
            self.compare(index,wanted,phase,memory=memory);sparse+=1
        self.assertEqual(visits,set(range(ENTRY,ENTRY+172,4))-{ENTRY+152})
        self.receipt.update(guest_phases=phases,sparse_guest_phases=sparse,reachable_words=42,
            retained_unreachable_words=1,full_incoming_argument_homes=True,late_table_reload_order=True,
            sparse_native_array_legality_claimed=False)

    def test_03_native32_typed_arrays_and_twelve_defined_wrong_C(self):
        harness,cases=native_harness(source.SELECTED['func_1514D4B8'],self.context)
        self.assertEqual(cases,2111717)
        for opt in('-O0','-O2','-O3'):
            unit=self.out/('native'+opt+'.c');exe=unit.with_suffix('.elf');unit.write_text(harness)
            q=subprocess.run([*native_command(opt),'-mstackrealign',str(unit),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(q.returncode,0,q.stdout+q.stderr)
            self.assertEqual(subprocess.run([str(exe)],capture_output=True,timeout=180).returncode,0,opt)
        self.receipt.update(native_cases_per_optimization=cases,native_optimizations=3,trap_UBSan=True,
            defined_wrong_C_controls=12,all_16bit_wanted_and_equal_inputs=True,
            native_typed_arrays_and_fences=True,native_iterative_reference=True,
            native_cyclic_and_NULL_dereference_cases_excluded=True,actual_C_caller_claimed=False)

    def test_04_original_caller_entries_windows_signed_ABI_and_skip_paths(self):
        count=0;coverage=[set(),set()]
        for which,caller in enumerate(source.CALLERS):
            for root,wanted,phase,flag in itertools.product(range(28),(*range(28),-32768,-1,28,256,32767),(0,8),(0,)if which==0 else(0,1)):
                memory=fixture(self.context,phase);sp=STACK+phase
                put(memory,OWNER+0x2F4,RECORD);put(memory,RECORD+0x14,NEXT);put(memory,RECORD+0x1C,wanted,2)
                if which:
                    put(memory,sp+0x764,OWNER);put(memory,sp+0xE0,0x12345678);put(memory,sp+0x544,0x87654321)
                    memory[sp+0x54A]=root if flag else root^1
                expected_reads=[('R',OWNER+0x2F4,4,RECORD),('R',RECORD+0x1C,2,wanted&65535)]
                calls=[];result=None
                if root!=wanted:
                    pointer=self.context['pointers'][root];child=self.context['nodes'][root]['cells'][2]
                    expected_reads += [('R',TABLE+root*4,4,pointer),('R',pointer+4,2,child&65535)]
                    result,more,reads=reference(memory,child,wanted)
                    calls=[(ENTRY,(child&0xFFFFFFFF,wanted&0xFFFFFFFF))]+more;expected_reads+=reads
                    if which==0:expected_reads.append(('R',RECORD+0x14,4,NEXT)if not result else('R',RECORD+0x1C,2,wanted&65535))
                models=[]
                for image in self.images:
                    connected=dict(zip(range(ENTRY,ENTRY+172,4),image))
                    args=(OWNER,0xABCD0000|root,0x12345678,0x87654321)if which==0 else(0,0)
                    m=NodeOracle(self.windows[which],memory,args,phase,entry=caller['entry'],connected=connected,stops=caller['stops'])
                    if which:m.r[2]=flag;m.r[24]=0xABCD0000|(root^1 if flag else root)
                    with self.assertRaises(WindowBoundary):m.run()
                    models.append(m);coverage[which].update(m.visits)
                    self.assertEqual(m.calls,calls);self.assertEqual(public_trace(m.trace),expected_reads)
                    self.assertEqual(public(m.memory),public(memory));self.assertEqual(m.r[29],sp-(56 if which==0 else 0))
                    if which==0:
                        self.assertEqual(m.r[18],root);self.assertEqual(read(m.memory,sp+4),0xABCD0000|root)
                        self.assertEqual(m.r[16],NEXT if result==0 else RECORD)
                        self.assertEqual(m.current_pc,0x1514D480 if result==0 else 0x1514D440)
                    else:
                        self.assertEqual(m.memory[sp+0x54A],root);self.assertEqual(read(m.memory,sp+0xE0),root)
                        self.assertEqual(m.r[3],RECORD)
                        self.assertEqual(read(m.memory,sp+0x544),RECORD if result is not None else 0x87654321)
                        self.assertEqual(m.current_pc,0x150285C8 if result==0 else 0x15028568)
                self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(complete(models[0]),complete(models[2]));count+=1
            for root,phase,flag in itertools.product((0,27,28,255),(0,8),(0,)if which==0 else(0,1)):
                memory=fixture(self.context,phase);sp=STACK+phase;put(memory,OWNER+0x2F4,0)
                if which:
                    put(memory,sp+0x764,OWNER);memory[sp+0x54A]=root if flag else root^1
                    put(memory,sp+0xE0,0x12345678)
                models=[]
                for image in self.images:
                    connected=dict(zip(range(ENTRY,ENTRY+172,4),image))
                    m=NodeOracle(self.windows[which],memory,(OWNER,0xABCD0000|root,1,2)if which==0 else(0,0),phase,
                        entry=caller['entry'],connected=connected,stops=caller['stops'])
                    if which:m.r[2]=flag;m.r[24]=0xABCD0000|(root^1 if flag else root)
                    with self.assertRaises(WindowBoundary):m.run()
                    models.append(m);coverage[which].update(m.visits)
                    self.assertFalse(m.calls);self.assertEqual(public_trace(m.trace),[('R',OWNER+0x2F4,4,0)])
                    self.assertEqual(m.current_pc,0x15029BA4 if which else 0x1514D488)
                    if which:self.assertEqual(m.r[2],1);self.assertEqual(read(m.memory,sp+0xE0),0x12345678)
                self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(complete(models[0]),complete(models[2]));count+=1
            self.assertTrue(set(range(caller['entry'],caller['end'],4))<=coverage[which])
        self.receipt.update(caller_phases=count,caller_prefix_words=58,all_caller_prefix_words_visited=True,
            first_original_parent_entry_and_frame=True,second_original_parent_bounded_window=True,
            signed_halfword_call_arguments=True,byte_selector_annulled_store_and_NULL_list_paths=True,
            current_parent_stubs_preserved_and_uncredited=True)

    def assert_prefixes(self,models):
        for m in models[1:]:
            self.assertEqual(complete(models[0]),complete(m))
            self.assertEqual((models[0].current_pc,models[0].delay_of,models[0].attempted),
                (m.current_pc,m.delay_of,m.attempted))
            self.assertEqual(models[0].trace,m.trace)

    def test_05_fired_faults_cycles_NULL_roots_and_private_alias_prefixes(self):
        fired=cycles=nulls=aliases=0
        for index,wanted,phase in itertools.product((0,7,-1,28),(28,1),(0,8)):
            if index==28 and wanted!=28:continue
            memory=fixture(self.context,phase)
            good=NodeOracle(self.images[0],memory,(index,wanted),phase).run()
            for cut in range(good.root_accesses):
                models=[]
                for words in self.images:
                    m=NodeOracle(words,memory,(index,wanted),phase);m.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    models.append(m)
                self.assert_prefixes(models);fired+=1
        pcs=(12,28,32,84,88,92,100)
        for q,phase,cut in itertools.product(self.context['cycle_before_match_pairs'],(0,8),(*range(21),63,127)):
            memory=fixture(self.context,phase,deep=True);models=[]
            for words in self.images:
                m=NodeOracle(words,memory,(q['index'],q['wanted']),phase);m.root_fault=cut
                with self.assertRaises(faults.AccessBoundary):m.run()
                self.assertEqual(m.r[29],STACK+phase-32*(cut//7+1))
                self.assertEqual(m.current_pc,ENTRY+pcs[cut%7]);self.assertEqual(len(m.calls),cut//7)
                self.assertEqual(m.calls,[(ENTRY,(10,q['wanted']&0xFFFFFFFF))]*(cut//7))
                self.assertEqual(m.delay_of,ENTRY+96 if cut%7==6 else None);models.append(m)
            self.assert_prefixes(models);cycles+=1
        for index,wanted,phase in itertools.product((28,29),(-32768,-1,0,10,28,29),(0,8)):
            if index==wanted:continue
            memory=fixture(self.context,phase);models=[]
            for words in self.images:
                m=NodeOracle(words,memory,(index,wanted),phase)
                with self.assertRaises(AssertionError)as error:m.run()
                self.assertEqual(error.exception.args[0],('unmapped read',6,2))
                self.assertEqual((m.current_pc,m.attempted,m.r[29]),(ENTRY+88,('R',6,2),STACK+phase-32))
                self.assertFalse(m.calls);models.append(m)
            self.assert_prefixes(models);nulls+=1
        for offset,phase,cut in itertools.product((0,-4,-32,-12,-4+32),(0,8),(0,7,16,32)):
            memory=fixture(self.context,phase,deep=True);put(memory,TABLE,STACK+phase+offset);models=[];outcomes=[]
            for words in self.images:
                m=NodeOracle(words,memory,(0,1),phase);m.root_fault=cut
                try:m.run();outcome=('return',m.r[2])
                except faults.AccessBoundary:outcome=('fault',)
                except AssertionError as error:
                    self.assertIsInstance(error.args[0],tuple)
                    self.assertEqual(error.args[0][0],'unmapped read');outcome=('unmapped',error.args[0])
                models.append(m);outcomes.append(outcome)
            self.assertEqual(outcomes,[outcomes[0]]*3);self.assert_prefixes(models);aliases+=1
        self.receipt.update(fired_regular_fault_prefixes=fired,bounded_cycle_prefixes=cycles,
            NULL_root_fault_cases=nulls,private_alias_prefixes=aliases,cycle_frame_growth_and_delay_PC=True,
            portable_C_fault_or_private_alias_legality_claimed=False,cycle_guard_added=False)

    def link_words(self,obj,entry,table,label):
        name='func_1514D4B8';text,fs,rs=source.parse_object(obj)
        assembly,unknown=emit_function(text,fs[name],rs,name,{'D_8008ABE8':table,name:entry});self.assertFalse(unknown)
        p=self.out/label;a=p.with_suffix('.s');o=p.with_suffix('.o');ld=p.with_suffix('.ld');elf=p.with_suffix('.elf')
        a.write_text(assembly);ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(o),str(a)],capture_output=True,check=True)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',name,
            '--defsym=D_8008ABE8=0x%X'%table,'-o',str(elf),str(o)],capture_output=True,check=True)
        n=len(source.payload(obj,name)[0])//4;raw=sections(elf)['.text'][1]
        self.assertFalse(any(raw[n*4:]));return list(struct.unpack_from('>%dI'%n,raw))

    def test_06_independent_rebases_and_effective_order_reload_controls(self):
        links=phases=0;name='func_1514D4B8'
        objects=(source.original(ROOT,self.out,name),self.obj,self.out/'qualified-generated_179F30.o')
        for i,(entry,table)in enumerate(((ENTRY,TABLE),(0x18017FFC,0x80067FFC),(0x1A028000,0x80078000))):
            images=[self.link_words(obj,entry,table,'rebase-%d-%d'%(i,j))for j,obj in enumerate(objects)];links+=3
            self.assertEqual(images,[images[0]]*3)
            for index,wanted,phase in itertools.product((0,1,7,10,27,-1),(0,10,27,-1),(0,8)):
                if index==10 and wanted!=10:continue
                self.compare(index,wanted,phase,images=images,entry=entry,table=table);phases+=1
        selected=source.SELECTED[name]
        ordered=selected.replace('[index][3]','[index][99]').replace('[index][2]','[index][3]').replace('[index][99]','[index][2]')
        wrong,diag=source.compile_owner(ROOT,self.out,source.ISOLATED_HEADERS+source.DECLARATIONS+ordered,'wrong-order')
        self.assertFalse(diag);code=self.link_words(wrong,ENTRY,TABLE,'wrong-order-linked');links+=1
        memory=fixture(self.context);good=NodeOracle(self.images[0],memory,(0,28)).run()
        bad=NodeOracle(code,memory,(0,28)).run()
        self.assertEqual(good.r[2],bad.r[2]);self.assertNotEqual(public_trace(good.trace),public_trace(bad.trace))
        cached=selected.replace('    if (func_1514D4B8(D_8008ABE8[index][3], wanted)) return 1;',
            '    s16 *node = D_8008ABE8[index];\n    if (func_1514D4B8(node[3], wanted)) return 1;').replace('D_8008ABE8[index][2]','node[2]')
        cached=cached.replace('    if (index == -1) return 0;','    s16 *node;\n    if (index == -1) return 0;').replace('    s16 *node = D_8008ABE8[index];','    node = D_8008ABE8[index];')
        cache_obj,diag=source.compile_owner(ROOT,self.out,source.ISOLATED_HEADERS+source.DECLARATIONS+cached,'wrong-cached-node');self.assertFalse(diag)
        alias_phases=0
        for phase in(0,8):
            table=STACK+phase-4
            images=[self.link_words(obj,ENTRY,table,'alias-table-%d-%d'%(phase,j))for j,obj in enumerate(objects)];links+=3
            control=self.link_words(cache_obj,ENTRY,table,'cached-alias-table-%d'%phase);links+=1
            memory=fixture(self.context,phase,plan=0,deep=True)
            put(memory,table,0x100000)
            models=[]
            for words in images:
                m=NodeOracle(words,memory,(0,1),phase);m.root_fault=64
                with self.assertRaises(faults.AccessBoundary):m.run()
                models.append(m)
            self.assert_prefixes(models)
            bad=NodeOracle(control,memory,(0,1),phase).run();self.assertEqual(bad.r[2],0)
            self.assertNotEqual(models[0].trace,bad.trace);alias_phases+=1
        self.receipt.update(independent_GNU_links=links,rebase_phases=phases,compiled_guest_order_controls=2,
            cached_pointer_guest_alias_controls=alias_phases,HI_LO_carry_and_self_call_relocations=True,
            wrong_order_rejected_by_non_stack_reads=True,cached_control_rejected_by_return_vs_cycle_prefix=True)

    def test_07_retail_provenance_bindings_guards_and_strict_image_negatives(self):
        context=source.retail_context(self.values)
        self.assertEqual((context['table_count'],context['physical_pointer_words'],context['zero_pointer_indices']),(28,30,[28,29]))
        self.assertEqual((len(context['terminating_native_pairs']),len(context['cycle_before_match_pairs']),context['cycle_witnesses']),(925,32,[[10,10]]))
        self.assertTrue(context['external_call_child_avoids_self_cycle'])
        jal=struct.pack('>I',0x0C000000|(ENTRY>>2&0x3FFFFFF));pointer=struct.pack('>I',ENTRY)
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==jal],[0x55A08,0x17A8D8,0x17A9C8,0x17A9E8])
        self.assertFalse(any(self.rom[i:i+4]==pointer for i in range(0,len(self.rom),4)))
        guards=self.values['conker/retail_word_patches.us.csv'];self.assertEqual(source.guard_bytes(guards),guards)
        with self.assertRaises(ValueError):source.guard_bytes(guards+b'\n')
        raw,bindings=source.payload(self.obj,'func_1514D4B8');negatives=0
        for pos in(0,4,72,76,96,128,152,168):
            wrong=bytearray(raw);wrong[pos]^=1
            with self.assertRaises(ValueError):source.normalized('func_1514D4B8',bytes(wrong),bindings)
            negatives+=1
        for pos in bindings:
            wrong=dict(bindings);wrong[pos]=[]
            with self.assertRaises(ValueError):source.normalized('func_1514D4B8',raw,wrong)
            negatives+=1
        before=self.values['conker/build/conker.us.elf'];pred=source.predicted_image(before,self.rom)
        positions=[0,len(pred)-1,*[source.elf_slot_offset(before,a,4)for a in(ENTRY,TABLE,0x800A5F3C,0x1514D3B0,0x150265CC)]]
        for pos in positions:
            wrong=bytearray(pred);wrong[pos]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(wrong),self.rom)
        with self.assertRaises(ValueError):source.check_image(before,pred[:-1],self.rom)
        self.receipt.update(retail_nodes=28,physical_table_words=30,retail_finite_queries=925,retail_cyclic_queries=32,
            whole_guard_manifest_byte_identical=True,new_guards=0,raw_binding_negatives=negatives,
            strict_image_negatives=len(positions)+1,metadata_exclusions=0)

    def test_08_historical_inputs_and_installed_identity(self):
        target=self.target;name='func_1514D4B8'
        for path,old in self.values.items():
            self.assertEqual(source.digest(old),source.INPUTS[path]);expected=old
            if self.installed:
                if path==target['source']:expected=source.recovered_owner(name,old.decode()).encode()
                elif path=='conker/build/conker.us.elf':expected=source.predicted_image(old,self.rom)
            self.assertEqual((ROOT/path).read_bytes(),expected,path)
        self.receipt.update(pinned_inputs=len(self.values),all_target_and_non_target_inputs_checked=True)
