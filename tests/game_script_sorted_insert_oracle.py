"""Private ordered-script insertion: original words, access traces and list model."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,subprocess
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary,TrackedCode
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.experiments import game_script_sorted_insert_match as source
r=Path.cwd();o=r/source.BUILD;F='func_1509B810';ENTRY=0x1509B810
LIST,POOL,NEW=0x220000,0x230000,0x240000
@dataclass(frozen=True)
class Case:
    length:int=4
    kind:int=19
    flags:int=0
    alias:int=-1
    phase:int=0
    wrap:bool=False

def fixture(c,base=LIST):
    m={STACK+i:(i*17+0xA5)&255 for i in range(-256,256)}
    for at,size in ((base-32,80),(POOL-32,512),(NEW-32,80)):
        m.update({at+i:(i*13+0xA5)&255 for i in range(size)})
    for i in range(c.length):
        at=POOL+32*i;put(m,at,((i*17+2)&1023)|c.flags,2)
        put(m,at+24,POOL+32*(i+1) if i+1<c.length else 0)
        put(m,at+28,POOL+32*(i-1) if i else 0)
    put(m,base,65535 if c.wrap else c.length,2)
    put(m,base+4,POOL if c.length else 0);put(m,base+8,POOL+32*(c.length-1) if c.length else 0)
    node=POOL+32*c.alias if c.alias>=0 else NEW
    put(m,node,c.kind,2)
    return m,node

def reference(initial,node,base=LIST):
    m=dict(initial);length=read(m,base,2);cursor=tail=read(m,base+8);key=read(m,node,2)&1023
    if not length:
        put(m,base+4,node);put(m,base+8,node);put(m,node+24,0);put(m,node+28,0)
    else:
        count=0
        while True:
            count+=1
            if (read(m,cursor,2)&1023)<key:
                if cursor==tail:
                    put(m,node+28,cursor);put(m,node+24,0);put(m,cursor+24,node);put(m,base+8,node)
                else:
                    put(m,node+28,cursor);put(m,node+24,read(m,cursor+24))
                    put(m,read(m,cursor+24)+28,node);put(m,cursor+24,node)
                break
            # Retail always reads prev, including the final iteration.
            cursor=read(m,cursor+28)
            if count>=length:
                head=read(m,base+4);put(m,base+4,node);put(m,node+28,0);put(m,node+24,head);put(m,head+28,node)
                break
    put(m,base,(read(m,base,2)+1)&65535,2)
    return m

class Oracle(TimingOracle):
    def __init__(self,w,m,node,phase=0,entry=ENTRY,connected=None):
        self.trace=[]
        super().__init__(w,m,phase=phase,entry=entry,arguments=(node,),connected=connected)
        self.code=TrackedCode(dict(self.code),self);self.current_pc=entry;self.delay_of=None
        self.root_entry,self.root_size,self.root_accesses,self.root_fault=entry,len(w)*4,0,None
        self.hi=self.lo=0
    def get(self,p,n):
        v=super().get(p,n)
        if self.own_instruction:self.trace.append(('R',p,n,v))
        return v
    def put(self,p,v,n):
        super().put(p,v,n)
        if self.recording and self.own_instruction:self.trace.append(('W',p,n,v&((1<<(8*n))-1)))
    def record_call(self,t):raise AssertionError(('Unexpected helper',hex(t)))

def linked(obj,label,entry=ENTRY,base=LIST,normalize=False):
    text,fs,rs=parse_object(obj);info=fs[F]
    if normalize:
        at,size=info['value'],236;raw=text[at:at+size];w=list(struct.unpack('>59I',raw))
        bindings={p-at:v for p,v in rs.items() if at<=p<at+size}
        for row in json.loads((o/'new-guard-rows.json').read_text()):
            index=int(row['offset'],0)//4;assert w[index]==int(row['expected'],0) and index*4 not in bindings
            w[index]=int(row['replacement'],0)
        text=struct.pack('>59I',*w);rs=bindings;info=dict(info,value=0,size=236)
    asm,unknown=emit_function(text,info,rs,F,dict(D_800D2F48=base));assert not unknown
    p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\nD_800D2F48 = 0x%X;\n'%(entry,base))
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True)
    subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True)
    return list(struct.unpack('>59I',sections(p.with_suffix('.elf'))['.text'][1][:236]))

def images(label,entry=ENTRY,base=LIST):
    paths=('original-func_1509B810.o','selected-final.o','qualified-padded.o','make-shadow/src/game_C8950.c.o')
    roots=[linked(o/n,label+'-'+str(i),entry,base,i==1) for i,n in enumerate(paths)]
    assert all(w==roots[0] for w in roots)
    return roots,linked(o/'selected-final.o',label+'-raw',entry,base)

def corpus():
    for length,kind,flags,phase in itertools.product(range(9),(0,1,2,3,17,19,63,127,255,511,1023,0xFC00,0xFFFF),(0,0x400,0xFC00),(0,8)):
        yield Case(length,kind,flags,phase=phase)
    for length,kind,phase in itertools.product((1,2,4,8),(0,2,19,63,1023,0xFFFF),(0,8)):
        for alias in sorted({0,length//2,length-1}):yield Case(length,kind,0xFC00,alias,phase)
    yield Case(1,1023,0,wrap=True)

def compare(roots,c,entry=ENTRY,base=LIST):
    initial,node=fixture(c,base);wanted=reference(initial,node,base)
    models=[Oracle(w,initial,node,c.phase,entry).run() for w in roots[0]]
    for m in models:assert m.memory==wanted,(c,'reference memory')
    for m in models[1:]:assert complete(m)==complete(models[0]) and m.trace==models[0].trace
    raw=Oracle(roots[1],initial,node,c.phase,entry).run()
    assert raw.memory==wanted and raw.trace==models[0].trace and raw.calls==models[0].calls
    for reg in (*range(16,24),28,29,30,31):assert raw.r[reg]==models[0].r[reg]
    return models[0]

def guest_suite():
    count=aliases=cuts=delays=0;seen=set()
    for i,(entry,base) in enumerate(((ENTRY,LIST),(0x17007FFC,0x221FFF0),(0x2500FFFC,0x2318000))):
        roots=images('insert-rebase-'+str(i),entry,base)
        for c in corpus():
            m=compare(roots,c,entry,base);seen.update(p-entry for p in m.visits if entry<=p<entry+236);count+=1;aliases+=c.alias>=0
        if not i:
            for c in (Case(0),Case(4,1023),Case(4,19),Case(4,0),Case(4,19,alias=1)):
                initial,node=fixture(c,base);good=Oracle(roots[0][0],initial,node).run()
                for cut in range(good.root_accesses):
                    models=[]
                    for w in roots[0]:
                        m=Oracle(w,initial,node);m.root_fault=cut
                        try:m.run()
                        except AccessBoundary:pass
                        else:raise AssertionError('Ineffective access cut')
                        models.append(m)
                    for m in models[1:]:assert complete(m)==complete(models[0]) and m.trace==models[0].trace and (m.current_pc,m.delay_of)==(models[0].current_pc,models[0].delay_of)
                    cuts+=1;delays+=models[0].delay_of is not None
    assert set(range(0,236,4))-seen=={0x90,0xB8},sorted(set(range(0,236,4))-seen)
    return dict(cases=count,normalized_executions=count*4,raw_executions=count,aliases=aliases,independent_rebases=3,body_words=59,reachable_words=57,unreachable_offsets=['0x90','0xB8'],access_prefix_cases=cuts,branch_delay_cuts=delays,raw_memory_preserved_registers_and_trace_equal=True,raw_caller_saved_registers_not_claimed_equal=True,count_wrap=True,final_predecessor_read_preserved=True)

def caller_suite():
    rom=(o/'before-conker_conker.us.bin').read_bytes();jal=0x0C000000|((ENTRY>>2)&0x3FFFFFF)
    jals=[i for i in range(0,len(rom)-3,4) if struct.unpack_from('>I',rom,i)[0]==jal]
    pointers=[i for i in range(0,len(rom)-3,4) if struct.unpack_from('>I',rom,i)[0]==ENTRY]
    assert jals==[0xC8AE4] and pointers==[]
    parent=0x1509B5AC;parentwords=list(struct.unpack_from('>86I',rom,0xC8A5C))
    lookup,create,event,bzero=0x1509B704,0x1509B8FC,0x150ADAF0,0x100226F0
    base=0x800D2F48;roots=images('insert-original-parent',base=base)
    class Caller(Oracle):
        def __init__(self,w,initial,node,request,phase):
            self.node=node
            super().__init__(parentwords,initial,node,phase,parent,{ENTRY+4*i:v for i,v in enumerate(w)})
            self.r[4]=read(initial,node,2);self.r[5]=request
        def record_call(self,t):
            assert t in (lookup,create,event,bzero,ENTRY),hex(t)
            args=tuple(self.arguments(2 if t in (event,bzero) else 1))
            self.calls.append((t,args));self.events.append(('CALL',t,args))
        def hook(self,t):
            assert t in (lookup,create,event),hex(t)
            value=0 if t==lookup else self.node if t==create else 0xDEADBEEF
            for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
            for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
            self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
            self.r[2]=value
    count=0
    for length,kind,request,skip_event,phase in itertools.product((0,1,4,8),(0,19,1023,0xFC00,0xFFFF),(0,1),(0,1),(0,8)):
        c=Case(length,kind,0xFC00,phase=phase);initial,node=fixture(c,base)
        bits=0x250000;initial.update({bits+i:0 for i in range(8192)})
        put(initial,0x800D2E4C,bits);put(initial,0x8003C8E0,0)
        key=kind&1023
        if skip_event:
            put(initial,bits+(key>>3),1<<(key&7),1)
            put(initial,bits+(kind>>3),read(initial,bits+(kind>>3),1)|(1<<(kind&7)),1)
        early_exit=not request and skip_event
        wanted=dict(initial) if early_exit else reference(initial,node,base)
        if not early_exit and (not request or kind&0x400):put(wanted,node,kind|0x4000,2)
        models=[Caller(w,initial,node,request,phase).run() for w in roots[0]]
        raw=Caller(roots[1],initial,node,request,phase).run()
        def public(memory):return {a:b for a,b in memory.items() if not STACK-256<=a<STACK+256}
        for m in (*models,raw):
            assert public(m.memory)==public(wanted) and m.r[2]==(0 if early_exit else node),(c,request,skip_event,'caller state/return')
            assert [t for t,args in m.calls].count(ENTRY)==(0 if early_exit else 1)
            if not early_exit:assert next(args for t,args in m.calls if t==ENTRY)==(node,)
            assert m.r[29]==STACK+phase
        for m in models[1:]:assert complete(m)==complete(models[0]) and m.trace==models[0].trace
        assert raw.calls==models[0].calls and raw.trace==models[0].trace
        for reg in (*range(16,24),28,29,30,31):assert raw.r[reg]==models[0].r[reg]
        count+=1
    return dict(cases=count,normalized_executions=count*4,raw_executions=count,original_parent_words=86,aligned_JAL_sites=jals,aligned_literal_pointers=pointers,actual_argument_delay_slot=True,caller_reloads_kind_after_void_insertion=True,caller_returns_saved_node_not_insertion_V0=True,lookup_create_and_event_providers_opaque=True,producer_or_gameplay_claim=False)


def native_suite():
    s=source.HEADERS+source.SELECTED;body=s[s.index('/* Insert by'):]
    header='''typedef unsigned int u32; typedef int s32; typedef unsigned short u16; typedef unsigned char u8;
    #define NULL ((void *)0)
    typedef struct ScriptNodeC8950 {u16 kind;u8 padding[0x16];struct ScriptNodeC8950 *next,*prev;} ScriptNodeC8950;
    typedef struct {u16 length,padding;ScriptNodeC8950 *unk4,*unk8;} ScriptListC8950;
    static ScriptListC8950 state;
    #define SCRIPT_LIST_C8950 state
    typedef char node_size[sizeof(ScriptNodeC8950)==32?1:-1];
    typedef char list_size[sizeof(ScriptListC8950)==12?1:-1];
    static ScriptNodeC8950 nodes[8],added;
    '''
    harness='''
    static void initialize(u32 length,u32 kind,u32 flags) {
     u32 i,j;u8 *bytes=(u8 *)&state;
     for(i=0;i<sizeof(state);i++)bytes[i]=0xA5;
     state.length=length;state.unk4=length?&nodes[0]:NULL;state.unk8=length?&nodes[length-1]:NULL;
     for(i=0;i<8;i++){
      bytes=(u8 *)&nodes[i];for(j=0;j<sizeof(nodes[i]);j++)bytes[j]=(u8)(i*13+j*7+0xA5);
      nodes[i].kind=(u16)((i*17+2)|flags);nodes[i].prev=i?&nodes[i-1]:NULL;nodes[i].next=i+1<length?&nodes[i+1]:NULL;
     }
     bytes=(u8 *)&added;for(i=0;i<sizeof(added);i++)bytes[i]=(u8)(i*3+0xA5);
     added.kind=(u16)kind;
    }
    static int verify(u32 length,u32 kind,u32 flags) {
     u32 index=0,i,j,key=kind&1023;ScriptNodeC8950 *p,*previous=NULL,*expected;
     while(index<length && (nodes[index].kind&1023)<key)index++;
     func_1509B810(&added);
     if(state.length!=length+1||state.padding!=0xA5A5)return 1;
     p=state.unk4;
     for(i=0;i<=length;i++){
      expected=i==index?&added:&nodes[i<index?i:i-1];
      if(p!=expected||p->prev!=previous)return 1;
      previous=p;p=p->next;
     }
     if(p!=NULL||state.unk8!=previous||added.kind!=(u16)kind)return 1;
     for(i=0;i<8;i++){
      if(nodes[i].kind!=(u16)((i*17+2)|flags))return 1;
      for(j=0;j<0x16;j++)if(nodes[i].padding[j]!=(u8)(i*13+(j+2)*7+0xA5))return 1;
     }
     for(j=0;j<0x16;j++)if(added.padding[j]!=(u8)((j+2)*3+0xA5))return 1;
     return 0;
    }
    static int run(void) {
     u32 length,kind,flags;
     for(length=0;length<=8;length++)for(kind=0;kind<65536;kind++){
      flags=(kind&1)?0xFC00:0x400;
      initialize(length,kind,flags);if(verify(length,kind,flags))return 1;
     }
     initialize(1,1023,0);state.length=65535;func_1509B810(&added);
     if(state.length!=0||state.unk8!=&added||state.unk4!=&nodes[0]||nodes[0].next!=&added||added.prev!=&nodes[0]||added.next!=NULL)return 1;
     return 0;
    }
    __attribute__((force_align_arg_pointer,noreturn)) void _start(void) {
     int value=run();__asm__ volatile("int $0x80"::"a"(1),"b"(value));__builtin_unreachable();
    }
    '''
    controls=[('unmasked-kind','0xFFFF03FF','0xFFFFFFFF'),('wrong-tie','(cursor->kind & mask) >= key','(cursor->kind & mask) > key'),('missing-tail','                    SCRIPT_LIST_C8950.unk8 = node;',''),('missing-middle-prev','                cursor->next->prev = node;',''),('missing-head','    SCRIPT_LIST_C8950.unk4 = node;\n    node->prev = NULL;','    node->prev = NULL;'),('wrong-count','SCRIPT_LIST_C8950.length++;','SCRIPT_LIST_C8950.length--;'),('wrong-backlink','node->prev = cursor;','node->prev = NULL;'),('missing-tail-terminator','                    node->next = NULL;','')]
    results=[]
    for label,optimization,code,control in [(p[1:],p,body,False) for p in ('-O0','-O2','-O3')]+[(n,'-O2',body.replace(old,new),True) for n,old,new in controls]:
        assert not control or code!=body,label
        unit=o/('native-'+label+'.c');binary=o/('native-'+label);unit.write_text(header+code+harness)
        command=['gcc','-m32',optimization,'-std=c99','-fno-strict-aliasing','-ffreestanding','-nostdlib','-static','-fno-pie','-no-pie','-fno-stack-protector','-msse2','-mstackrealign','-fsanitize=undefined','-fsanitize-undefined-trap-on-error','-Wall','-Wextra','-Werror',str(unit),'-o',str(binary)]
        p=subprocess.run(command,capture_output=True,text=True);assert p.returncode==0,p.stderr
        p=subprocess.run([str(binary)],capture_output=True,timeout=30);assert p.returncode==(1 if control else 0),(label,p.returncode,p.stderr)
        results.append(dict(name=label,optimization=optimization,control=control,exit=p.returncode))
    q=dict(private_only=True,matching_credit=0,positive_cases_each=589825,profiles=['O0','O2','O3'],effective_controls=8,controls_exit_by_semantic_mismatch=True,UBSan_trapping=True,all_u16_new_kind_words=True,empty_tail_middle_head_and_equal_keys=True,node_kind_and_padding_bytes_preserved=True,count_wrap=True,invalid_alias_native_claim=False,results=results)
    return q
