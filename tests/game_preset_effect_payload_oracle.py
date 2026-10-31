"""Preset payload factory: byte arguments, signed halfwords and retained stack bytes."""
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
from tools.experiments import game_preset_effect_payload_match as source
r=Path.cwd();o=r/source.BUILD;F='func_150E1060';ENTRY=0x150E1060
TABLE,RESOURCE,CREATED=0x220000,0x230000,0x240000
SYMS=dict(D_800A0FE0=TABLE,func_151149AC=0x151149AC,func_1510F800=0x1510F800,func_1510FD20=0x1510FD20,func_15149130=0x15149130,memcpy=0x10022EC0)
@dataclass(frozen=True)
class Case:
    index:int=0
    variant:int=0xFF
    flags:int=1
    resource:bool=True
    allocated:bool=True
    x:int=0x8000
    y:int=0x7FFF
    handle:int=0x87654321
    phase:int=0
    mutation:int=0
    alias:int=0
def fixture(c,table=TABLE):
    m={STACK+i:(i*17+c.phase*3+0xA5)&255 for i in range(-1024,256)}
    for base,size in ((table-32,128),(RESOURCE-32,160),(CREATED-32,160)):
        m.update({base+i:(i*13+base//4096)&255 for i in range(size)})
    put(m,table,23,1);put(m,table+1,22,1)
    put(m,RESOURCE+16,c.x,2);put(m,RESOURCE+20,c.y,2)
    return m
def destination(c,table=TABLE):return (CREATED,RESOURCE,table-40)[c.alias] if c.allocated else 0
def signed16(n):return (n&65535)-65536 if n&32768 else n&65535
def public(m):return {a:b for a,b in m.items() if not STACK-1024<=a<STACK+256}
def reference(initial,c,table=TABLE):
    m=dict(initial);index=c.index&255;calls=[];payload=None
    if index>=2:return m,0,calls,payload
    calls.append((SYMS['func_151149AC'],(read(m,table+index,1),)))
    if not c.resource:return m,0,calls,payload
    calls.append((SYMS['func_1510F800'],(0,)))
    if c.mutation:put(m,RESOURCE+16,c.x^65535,2);put(m,RESOURCE+20,c.y^65535,2)
    args=(signed16(read(m,RESOURCE+16,2))&0xFFFFFFFF,signed16(read(m,RESOURCE+20,2))&0xFFFFFFFF)
    calls.append((SYMS['func_1510FD20'],args))
    calls.append((SYMS['func_15149130'],(300,0xFFFFFFFF,31,0xFFFFFFFF,0,31,16,c.variant&255,c.flags&0xFFFFFFFF)))
    created=destination(c,table)
    if created:
        start=STACK+c.phase-72+52
        payload=bytes([index,*[initial[start+i] for i in (1,2,3)]])+struct.pack('>III',RESOURCE,c.handle&0xFFFFFFFF,0)
        for i,value in enumerate(payload):put(m,created+40+i,value,1)
        calls.append((SYMS['memcpy'],(created+40,start,16)))
    return m,created,calls,payload

class Oracle(TimingOracle):
    def __init__(self,w,initial,c,entry=ENTRY,table=TABLE,connected=None,arguments=None):
        self.c,self.table,self.trace,self.payload=c,table,[],None
        super().__init__(w,initial,phase=c.phase,entry=entry,arguments=arguments or (c.index&0xFFFFFFFF,c.variant&0xFFFFFFFF,c.flags&0xFFFFFFFF),connected=connected)
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
    def record_call(self,t):
        lengths={SYMS['func_151149AC']:1,SYMS['func_1510F800']:1,SYMS['func_1510FD20']:2,SYMS['func_15149130']:9,SYMS['memcpy']:3,ENTRY:3}
        assert t in lengths,hex(t);args=tuple(self.arguments(lengths[t]));self.calls.append((t,args));self.events.append(('CALL',t,args))
        if t==SYMS['memcpy']:self.payload=bytes(read(self.memory,args[1]+i,1) for i in range(args[2]))
    def hook(self,t):
        c=self.c;args=self.calls[-1][1]
        if t==SYMS['func_151149AC']:value=RESOURCE if c.resource else 0
        elif t==SYMS['func_1510F800']:
            if c.mutation:put(self.memory,RESOURCE+16,c.x^65535,2);put(self.memory,RESOURCE+20,c.y^65535,2)
            value=0xAAAAAAAA
        elif t==SYMS['func_1510FD20']:value=c.handle&0xFFFFFFFF
        elif t==SYMS['func_15149130']:value=destination(c,self.table)
        elif t==SYMS['memcpy']:
            for i in range(args[2]):put(self.memory,args[0]+i,read(self.memory,args[1]+i,1),1)
            value=args[0]
        else:raise AssertionError(hex(t))
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
        self.r[2]=value

def linked(obj,label,entry=ENTRY,table=TABLE):
    text,fs,rs=parse_object(obj);info=fs[F];symbols=dict(SYMS,D_800A0FE0=table)
    asm,unknown=emit_function(text,info,rs,F,symbols);assert not unknown
    p=o/label;p.with_suffix('.s').write_text(asm)
    p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v) for n,v in symbols.items()))
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
    subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
    return list(struct.unpack('>59I',sections(p.with_suffix('.elf'))['.text'][1][:236]))
def images(label,entry=ENTRY,table=TABLE):
    paths=('original-func_150E1060.o','selected-final.o','qualified-padded.o','make-shadow/src/game/generated_10E240.c.o')
    roots=[linked(o/n,label+'-'+str(i),entry,table) for i,n in enumerate(paths)]
    assert all(w==roots[0] for w in roots)
    return roots
def compare(roots,c,entry=ENTRY,table=TABLE,connected=None):
    initial=fixture(c,table);wanted,answer,calls,payload=reference(initial,c,table)
    models=[Oracle(w,initial,c,entry,table,connected).run() for w in roots]
    for m in models:assert public(m.memory)==public(wanted) and m.r[2]==answer and m.calls==calls and m.payload==payload,(c,'semantic state/calls/payload')
    for m in models[1:]:assert complete(m)==complete(models[0]) and m.trace==models[0].trace
    return models[0]
def corpus():
    for index in range(256):yield Case(index)
    for index,variant,allocated,resource,mutation,phase in itertools.product((0,1),(0,0xFF,0x100,0xFFFFFFFF),(False,True),(False,True),(0,1),(0,8)):
        yield Case(index,variant,0x87654321,resource,allocated,0xFFFF,0x8000,0xFFFFFFFF,phase,mutation)
    for index,x,y,phase in itertools.product((0,1),(0,1,0x7FFF,0x8000,0xFFFF),(0,0x7FFF,0xFFFF),(0,8)):
        yield Case(index,0xABCD,0,True,True,x,y,0,phase)
    for index,alias,phase in itertools.product((0,1),(1,2),(0,8)):yield Case(index,alias=alias,phase=phase)
def guest_suite():
    count=cuts=delays=0;seen=set()
    for i,(entry,table) in enumerate(((ENTRY,TABLE),(0x17007FFC,0x2217FF0),(0x1F00FFFC,0x2318000))):
        roots=images('preset-rebase-'+str(i),entry,table)
        for c in corpus():
            m=compare(roots,c,entry,table);seen.update(p-entry for p in m.visits if entry<=p<entry+236);count+=1
        if not i:
            for c in (Case(),Case(255),Case(resource=False),Case(allocated=False),Case(mutation=1,alias=2)):
                initial=fixture(c,table);good=Oracle(roots[0],initial,c).run()
                for cut in range(good.root_accesses):
                    models=[]
                    for w in roots:
                        m=Oracle(w,initial,c);m.root_fault=cut
                        try:m.run()
                        except AccessBoundary:pass
                        else:raise AssertionError('Ineffective prefix cut')
                        models.append(m)
                    for m in models[1:]:assert complete(m)==complete(models[0]) and m.trace==models[0].trace and (m.current_pc,m.delay_of)==(models[0].current_pc,models[0].delay_of)
                    cuts+=1;delays+=models[0].delay_of is not None
    assert set(range(0,236,4))-seen=={0x20,0x24},sorted(set(range(0,236,4))-seen)
    return dict(cases=count,executions=count*4,independent_rebases=3,body_words=59,reachable_words=57,unreachable_offsets=['0x20','0x24'],frame=72,access_prefix_cases=cuts,branch_delay_cuts=delays,all_byte_indices=True,signed_halfword_coordinates=True,variant_low_byte=True,reset_callback_mutation=True,allocation_and_lookup_failure=True,retained_stack_padding_bytes=3,padding_initial_values_not_zeroed=True,all_architectural_state_and_traces_equal=True)
def connected_suite():
    roots=images('preset-connected');rom=(o/'before-conker_conker.us.bin').read_bytes();copy=list(struct.unpack_from('>11I',rom,0x22EC0));connected={SYMS['memcpy']+4*i:w for i,w in enumerate(copy)};count=0
    for c in corpus():compare(roots,c,connected=connected);count+=1
    return dict(cases=count,executions=count*4,original_memcpy_words=11,copy_destination_plus_0x28=True,three_retained_stack_bytes_preserved=True,other_helpers_opaque=True)

def caller_suite():
    rom=(o/'before-conker_conker.us.bin').read_bytes();jal=0x0C000000|((ENTRY>>2)&0x3FFFFFF)
    sites=[at for at in range(0,len(rom)-3,4) if struct.unpack_from('>I',rom,at)[0]==jal]
    pointers=[at for at in range(0,len(rom)-3,4) if struct.unpack_from('>I',rom,at)[0]==ENTRY]
    assert sites==[0xCA974] and pointers==[]
    parent,continuation,actor=0x1509D4BC,0x1509D76C,0x260000
    words=list(struct.unpack_from('>6I',rom,0xCA96C));roots=images('preset-original-caller-window')
    class WindowDone(Exception):pass
    class WindowCode(TrackedCode):
        def __getitem__(self,pc):
            if pc==continuation:raise WindowDone
            return super().__getitem__(pc)
    class Window(Oracle):
        def __init__(self,callee,initial,c):
            super().__init__(words,initial,c,parent,TABLE,{ENTRY+4*i:w for i,w in enumerate(callee)})
            self.r[16]=actor;self.code=WindowCode(dict(self.code),self)
    count=0
    for index,resource,allocated,phase,mutation in itertools.product((0,1,2,127,128,255),(False,True),(False,True),(0,8),(0,1)):
        c=Case(index,255,1,resource,allocated,0x8000,0xFFFF,0x87654321,phase,mutation)
        initial=fixture(c);initial.update({actor+i:0xA5 for i in range(16)});put(initial,actor+7,index,1)
        saved=0xD00DFEED;put(initial,STACK+phase+0xC4,saved)
        wanted,answer,calls,payload=reference(initial,c);models=[]
        for callee in roots:
            m=Window(callee,initial,c)
            try:m.run()
            except WindowDone:pass
            else:raise AssertionError('Caller window did not reach original continuation')
            assert public(m.memory)==public(wanted) and m.r[2]==saved and m.payload==payload
            assert m.calls==[(ENTRY,(index,255,1)),*calls]
            assert m.r[16]==actor and m.r[29]==STACK+phase
            models.append(m)
        for m in models[1:]:assert complete(m)==complete(models[0]) and m.trace==models[0].trace
        count+=1
    return dict(cases=count,executions=count*4,original_window_words=6,aligned_JAL_sites=sites,aligned_literal_pointers=pointers,actual_byte_load_and_call_delay_slot=True,original_postcall_branch_delay_reloads_saved_V0=True,callee_pointer_return_ignored=True,caller_continuation=continuation,full_parent_dispatcher_claim=False)


def native_suite():
    s=source.HEADERS+source.SELECTED;s=s.replace('#include <ultra64.h>','typedef unsigned int u32;typedef int s32;typedef unsigned char u8;typedef signed char s8;typedef short s16;typedef unsigned short u16;typedef float f32;\n#define NULL ((void *)0)')
    a=s.index('/* Build');headers,body=s[:a],s[a:]
    harness='''
    u8 D_800A0FE0[2]={23,22};
    static PresetHeader preset;
    static u8 storage[128];
    static u32 inputIndex,inputVariant,inputFlags,xword,yword,mutation,hasResource,hasAllocation;
    static s32 resultHandle;static int calls,failed;
    typedef char payload_size[sizeof(PresetPayload)==16?1:-1];
    PresetHeader *func_151149AC(u32 id) {
     if(calls++!=0||id!=(inputIndex?22u:23u))failed=1;
     return hasResource?&preset:NULL;
    }
    void func_1510F800(s32 value) {
     if(calls++!=1||value!=0)failed=1;
     if(mutation){preset.x=(s16)(xword^65535u);preset.y=(s16)(yword^65535u);}
    }
    s32 func_1510FD20(s32 x,s32 y) {
     if(calls++!=2||x!=(s32)preset.x||y!=(s32)preset.y)failed=1;
     return resultHandle;
    }
    void *func_15149130(s16 a,s8 b,s8 c,s8 d,u8 e,u8 f,s32 n,u8 variant,s32 flags) {
     if(calls++!=3||a!=300||b!=-1||c!=31||d!=-1||e!=0||f!=31||n!=16||variant!=(u8)inputVariant||(u32)flags!=inputFlags)failed=1;
     return hasAllocation?storage:NULL;
    }
    void *memcpy(void *dst,const void *src,u32 n) {
     const PresetPayload *p=(const PresetPayload *)src;union {f32 f;u32 u;} zero;u32 i;
     if(calls++!=4||dst!=storage+40||n!=16){failed=1;return dst;}
     zero.f=p->zero;
     if(p->index!=inputIndex||p->resource!=&preset||p->handle!=resultHandle||zero.u!=0)failed=1;
     /* Padding is intentionally opaque in portable C; the guest suite checks it. */
     for(i=0;i<n;i++)((u8 *)dst)[i]=((const u8 *)src)[i];
     return dst;
    }
    static int run(void) {
     static const u32 variants[]={0,255,256,0xFFFFFFFFu},flags[]={0,1,0x80000000u,0xFFFFFFFFu};
     static const u32 xs[]={0,0x8000,0xFFFF,0x7FFF},ys[]={0,0x7FFF,0x8000,0xFFFF};
     u32 vi,fi,pat,i;void *answer;
     for(inputIndex=0;inputIndex<256;inputIndex++)for(vi=0;vi<4;vi++)for(fi=0;fi<4;fi++)for(hasResource=0;hasResource<2;hasResource++)for(hasAllocation=0;hasAllocation<2;hasAllocation++)for(mutation=0;mutation<2;mutation++)for(pat=0;pat<4;pat++){
      inputVariant=variants[vi];inputFlags=flags[fi];xword=xs[pat];yword=ys[pat];resultHandle=(s32)(flags[fi]^0x87654321u);
      preset.x=(s16)xword;preset.y=(s16)yword;
      for(i=0;i<sizeof(storage);i++)storage[i]=(u8)(i*17+0xA5);
      calls=failed=0;answer=func_150E1060((u8)inputIndex,(u8)inputVariant,(s32)inputFlags);
      if(failed)return 1;
      if(inputIndex>=2){if(answer!=NULL||calls!=0)return 1;}
      else if(!hasResource){if(answer!=NULL||calls!=1)return 1;}
      else if(!hasAllocation){if(answer!=NULL||calls!=4)return 1;}
      else if(answer!=storage||calls!=5)return 1;
      for(i=0;i<sizeof(storage);i++)if((i<40||i>=56||inputIndex>=2||!hasResource||!hasAllocation)&&storage[i]!=(u8)(i*17+0xA5))return 1;
     }
     return 0;
    }
    __attribute__((force_align_arg_pointer,noreturn)) void _start(void) {int value=run();__asm__ volatile("int $0x80"::"a"(1),"b"(value));__builtin_unreachable();}
    '''
    controls=[('wrong-bound','index >= 2','index >= 1'),('wrong-table','D_800A0FE0[index]','D_800A0FE0[index ^ 1]'),('unsigned-coordinate','packet.resource->x, packet.resource->y','(u16)packet.resource->x, packet.resource->y'),('wrong-context','func_1510F800(0)','func_1510F800(1)'),('wrong-type','(300,-1,31,-1','(301,-1,31,-1'),('wrong-variant','16,variant,flags','16,(u8)(variant+1),flags'),('wrong-destination','created + 0x28','created + 0x2C'),('wrong-zero','packet.zero = 0.0f','packet.zero = 1.0f'),('wrong-return','return created;','return NULL;')]
    results=[]
    for label,opt,code,control in [(p[1:],p,body,False) for p in ('-O0','-O2','-O3')]+[(n,'-O2',body.replace(old,new),True) for n,old,new in controls]:
        assert not control or code!=body,label
        unit=o/('native-'+label+'.c');binary=o/('native-'+label);unit.write_text(headers+code+harness)
        cmd=['gcc','-m32',opt,'-std=c99','-fno-strict-aliasing','-ffreestanding','-nostdlib','-static','-fno-pie','-no-pie','-fno-stack-protector','-msse2','-mstackrealign','-fsanitize=undefined','-fsanitize-undefined-trap-on-error','-Wall','-Wextra','-Werror','-Wno-type-limits',str(unit),'-o',str(binary)]
        p=subprocess.run(cmd,capture_output=True,text=True);assert p.returncode==0,p.stderr
        p=subprocess.run([str(binary)],capture_output=True,timeout=30);assert p.returncode==(1 if control else 0),(label,p.returncode,p.stderr)
        results.append(dict(name=label,optimization=opt,control=control,exit=p.returncode))
    q=dict(private_only=True,matching_credit=0,positive_cases_each=131072,profiles=['O0','O2','O3'],effective_controls=9,controls_exit_by_semantic_mismatch=True,UBSan_trapping=True,all_byte_indices=True,variant_low_byte=True,signed_halfwords=True,lookup_and_allocation_failures=True,callback_coordinate_mutation=True,payload_initialized_fields_and_output_boundary_verified=True,padding_portable_initial_value_claim=False,results=results)
    return q
