"""Owner rotation scaling: ordered float operations, live globals and fixed output."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,math,struct,subprocess
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_fixed_matrix_oracle import integer,reference as fixed_reference
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary,TrackedCode
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.experiments import game_owner_matrix_scale_match as source
r=Path.cwd();o=r/source.BUILD;F='func_15108D24';ENTRY=0x15108D24
OWNER,SCALE,PAGE=0x220000,0x230000,0x240000
ROTATE,CONVERT=0x150A8050,0x150A7790
SCALES=(0,0x80000000,0x3F800000,0xBF800000,0x3F000000,0x40000000,1,0x00800000,0x7F7FFFFF,0x7F800000,0x7FC12345)
@dataclass(frozen=True)
class Case:
    pattern:int=0
    scale:int=0x3F000000
    page:int=0
    offset:int=0x100
    mutation:int=0
    phase:int=0
    unused:int=0x87654321
def seed(pattern):
    if pattern<4:return [bits((i%5-2)*(0.25 if pattern&1 else 0.5)) if i%4!=3 else bits(1.0 if i==15 else 0.0) for i in range(16)]
    pool=(0,0x80000000,1,0x007FFFFF,0x00800000,0x3F800000,0xBF800000,0x7F7FFFFF)
    return [pool[(i+pattern)%len(pool)] for i in range(16)]
def fixture(c,s=None):
    s=s or dict(D_800A2490=SCALE,D_800BE9C0=PAGE)
    m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,512)}
    m.update({OWNER+i:(i*13+0xA5)&255 for i in range(-32,0x4200)})
    for a in s.values():m.update({a+i:0xA5 for i in range(-4,8)})
    put(m,OWNER+0x50,c.offset&0xFFFFFFFF);state=OWNER+c.offset+0xF8
    put(m,state,bits(0.25));put(m,state+4,bits(-0.5));put(m,state+0x10,bits(-3.75))
    put(m,s['D_800A2490'],c.scale);put(m,s['D_800BE9C0'],c.page,1)
    return m
def mutate(m,c,s,state):
    if c.mutation&1:
        put(m,s['D_800A2490'],bits(-0.25));put(m,s['D_800BE9C0'],(c.page+1)&255,1);put(m,state+0x10,bits(7.5))
    if c.mutation&2:
        put(m,OWNER+0x50,0x400);put(m,OWNER+0x400+0xF8+0x10,bits(123.0))
def public(m):return {a:b for a,b in m.items() if not STACK-2048<=a<STACK+512}
def reference(initial,c,s,real=False,rounding=0):
    m=dict(initial);state=OWNER+signed(read(m,OWNER+0x50))+0xF8;matrix=STACK+c.phase-96+32
    calls=[(ROTATE,(matrix,read(m,state),0,read(m,state+4)))]
    values=seed(c.pattern)
    for i,w in enumerate(values):put(m,matrix+4*i,w)
    mutate(m,c,s,state);values[13]=read(m,state+0x10);put(m,matrix+52,values[13])
    scale=read(m,s['D_800A2490'])
    for i in (0,1,2,4,5,6,8,9,10):values[i]=bits(floating(values[i])*floating(scale));put(m,matrix+4*i,values[i])
    dest=OWNER+(read(m,s['D_800BE9C0'],1)<<6)+0x78;calls.append((CONVERT,(matrix,dest)))
    if real:m,_=fixed_reference(m,dest,rounding,matrix)
    else:
        for i,w in enumerate(values):put(m,dest+4*i,w)
    return m,calls,tuple(values),dest
class Oracle(TimingOracle):
    def __init__(self,w,m,c=Case(),entry=ENTRY,s=None,connected=None,rounding=0):
        self.c,self.s,self.trace,self.observations,self.rounding=c,s or dict(D_800A2490=SCALE,D_800BE9C0=PAGE),[],[],rounding
        self.saved_state=OWNER+signed(read(m,OWNER+0x50))+0xF8
        super().__init__(w,m,phase=c.phase,entry=entry,arguments=(OWNER,c.unused&0xFFFFFFFF),connected=connected)
        self.code=TrackedCode(dict(self.code),self);self.current_pc=entry;self.delay_of=None
        self.root_entry,self.root_size,self.root_accesses,self.root_fault=entry,len(w)*4,0,None;self.hi=self.lo=0
    def execute(self,w):
        if w>>26==32:
            previous=self.own_instruction;self.own_instruction=True
            try:
                imm=w&65535;imm=imm-65536 if imm&32768 else imm
                value=self.get((self.r[w>>21&31]+imm)&0xFFFFFFFF,1)
                self.r[w>>16&31]=(value-256 if value&128 else value)&0xFFFFFFFF;self.r[0]=0
            finally:self.own_instruction=previous
        elif w>>26==17 and w>>21&31==16 and w&63==36:self.f[w>>6&31]=integer(self.f[w>>11&31],self.rounding)
        else:super().execute(w)
    def get(self,a,n):
        v=super().get(a,n)
        if self.own_instruction:self.trace.append(('R',a,n,v))
        return v
    def put(self,a,v,n):
        super().put(a,v,n)
        if self.recording and self.own_instruction:self.trace.append(('W',a,n,v&((1<<(8*n))-1)))
    def record_call(self,t):
        assert t in (ROTATE,CONVERT,ENTRY),hex(t);args=tuple(self.arguments(4 if t==ROTATE else 2));self.calls.append((t,args));self.events.append(('CALL',t,args))
        if t==CONVERT:self.observations.append(tuple(read(self.memory,args[0]+4*i) for i in range(16)))
    def hook(self,t):
        args=self.calls[-1][1]
        if t==ROTATE:
            for i,v in enumerate(seed(self.c.pattern)):put(self.memory,args[0]+4*i,v)
            mutate(self.memory,self.c,self.s,self.saved_state)
        elif t==CONVERT:
            for i in range(16):put(self.memory,args[1]+4*i,read(self.memory,args[0]+4*i))
        else:raise AssertionError(hex(t))
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
def linked(obj,label,entry=ENTRY,s=None,normalize=False):
    s=s or dict(D_800A2490=SCALE,D_800BE9C0=PAGE);text,fs,rs=parse_object(obj);info=fs[F]
    if normalize:
        at=info['value'];raw=text[at:at+236];words=list(struct.unpack('>59I',raw));bindings={p-at:v for p,v in rs.items() if at<=p<at+236}
        for row in json.loads((o/'new-guard-rows.json').read_text()):
            offset=int(row['offset'],0);assert words[offset//4]==int(row['expected'],0);words[offset//4]=int(row['replacement'],0)
        text=struct.pack('>59I',*words);rs=bindings;info=dict(info,value=0,size=236)
    symbols=dict(s,func_150A8050=ROTATE,guMtxF2L=CONVERT);asm,unknown=emit_function(text,info,rs,F,symbols);assert not unknown
    p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v) for n,v in symbols.items()))
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
    subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
    return list(struct.unpack('>59I',sections(p.with_suffix('.elf'))['.text'][1][:236]))
def images(label,entry=ENTRY,s=None):
    paths=('original-func_15108D24.o','selected-final.o','qualified-padded.o','make-shadow/src/game/generated_135D00.c.o')
    roots=[linked(o/n,label+'-'+str(i),entry,s,i==1) for i,n in enumerate(paths)];assert all(w==roots[0] for w in roots)
    return roots,linked(o/'selected-final.o',label+'-raw',entry,s)
def compare(roots,c,entry=ENTRY,s=None,connected=None,rounding=0):
    s=s or dict(D_800A2490=SCALE,D_800BE9C0=PAGE);initial=fixture(c,s);wanted,calls,values,dest=reference(initial,c,s,connected is not None,rounding)
    models=[Oracle(w,initial,c,entry,s,connected,rounding).run() for w in roots[0]]
    for m in models:assert public(m.memory)==public(wanted) and m.calls==calls and m.observations==[values] and m.r[2]==1,(c,'state/calls/matrix')
    for m in models[1:]:assert complete(m)==complete(models[0]) and m.trace==models[0].trace
    raw=Oracle(roots[1],initial,c,entry,s,connected,rounding).run();assert raw.memory==models[0].memory and raw.calls==models[0].calls and raw.observations==models[0].observations and raw.trace==models[0].trace and raw.r[2]==1
    for reg in (*range(16,24),28,29,30,31):assert raw.r[reg]==models[0].r[reg]
    return models[0]
def guest_suite():
    count=cuts=delays=0;seen=set()
    for i,(entry,s) in enumerate(((ENTRY,dict(D_800A2490=SCALE,D_800BE9C0=PAGE)),(0x17007FFC,dict(D_800A2490=0x2237FFC,D_800BE9C0=0x2248000)),(0x1F00FFFC,dict(D_800A2490=0x2338000,D_800BE9C0=0x234FFFC)))):
        roots=images('matrix-rebase-'+str(i),entry,s)
        for pattern,scale,page,offset,mutation,phase in itertools.product((0,3,5),SCALES,(0,1,255),(-0x80,0x100),(0,3),(0,8)):
            m=compare(roots,Case(pattern,scale,page,offset,mutation,phase),entry,s);seen.update(p-entry for p in m.visits if entry<=p<entry+236);count+=1
        if not i:
            for c in (Case(),Case(mutation=3),Case(offset=-0x80,page=255)):
                initial=fixture(c,s);good=Oracle(roots[0][0],initial,c).run()
                for cut in range(good.root_accesses):
                    ms=[]
                    for w in roots[0]:
                        m=Oracle(w,initial,c);m.root_fault=cut
                        try:m.run()
                        except AccessBoundary:pass
                        else:raise AssertionError('Ineffective prefix cut')
                        ms.append(m)
                    for m in ms[1:]:assert complete(m)==complete(ms[0]) and m.trace==ms[0].trace and (m.current_pc,m.delay_of)==(ms[0].current_pc,ms[0].delay_of)
                    cuts+=1;delays+=ms[0].delay_of is not None
    assert seen==set(range(0,236,4)),sorted(set(range(0,236,4))-seen)
    return dict(cases=count,normalized_executions=count*4,raw_executions=count,body_words=59,reachable_words=59,frame=96,independent_rebases=3,access_prefix_cases=cuts,branch_delay_cuts=delays,all_nine_basis_products=True,height_preserved_unscaled=True,captured_state_pointer_and_live_scale_page=True,raw_memory_preserved_registers_and_trace_equal=True,raw_temporary_registers_not_equal=True,nonfinite_guest_only_no_fixed_conversion_claim=True)
def connected_suite():
    roots=images('matrix-original-converter');rom=(o/'before-conker_conker.us.bin').read_bytes();copy=list(struct.unpack_from('>116I',rom,0xD4C40));connected={CONVERT+4*i:w for i,w in enumerate(copy)};count=0
    for pattern,scale,page,mutation,phase,mode in itertools.product((0,1,3),(0,0x80000000,0x3F000000,0xBF800000),(0,1,255),(0,3),(0,8),range(4)):
        compare(roots,Case(pattern,scale,page,0x100,mutation,phase),connected=connected,rounding=mode);count+=1
    return dict(cases=count,normalized_executions=count*4,raw_executions=count,original_converter_words=116,FCSR_rounding_modes=4,finite_in_range_conversion_domain=True,rotation_provider_opaque=True)

def caller_suite():
    from dataclasses import replace
    rom=(o/'before-conker_conker.us.bin').read_bytes();jal=0x0C000000|((ENTRY>>2)&0x3FFFFFF)
    jals=[at for at in range(0,len(rom)-3,4) if struct.unpack_from('>I',rom,at)[0]==jal]
    pointers=[at for at in range(0,len(rom)-3,4) if struct.unpack_from('>I',rom,at)[0]==ENTRY]
    assert jals==[] and pointers==[0x22E6EC]
    table=rom[0x22E6E8:0x22E704];assert len(table)==28 and struct.unpack_from('>I',table,4)[0]==ENTRY
    parent=0x1513B83C;words=list(struct.unpack_from('>75I',rom,0x168CEC));s=dict(D_800A2490=0x800A2490,D_800BE9C0=0x800BE9C0)
    roots=images('owner-matrix-original-parent',s=s);cursor=0x250000;count=0
    class Caller(Oracle):
        def __init__(self,callee,initial,c,view):
            super().__init__(words,initial,c,parent,s,{ENTRY+4*i:w for i,w in enumerate(callee)})
            self.r[4:7]=[cursor,OWNER,view&0xFFFFFFFF]
    for page,view,enabled,gate,mutation,phase in itertools.product((0,1,255),(0,1,3,0x10001,0xFFFF),(False,True),(0,1,2),(0,3),(0,8)):
        signed_view=(view&65535)-65536 if view&32768 else view&65535
        c=Case(1,0x3F000000,page,0x100,mutation,phase,signed_view)
        initial=fixture(c,s);initial.update({cursor+i:0xA5 for i in range(64)})
        for i,b in enumerate(table):put(initial,0x80089C28+i,b,1)
        put(initial,OWNER+0x10,2 if gate else 0,1);put(initial,OWNER+0x49,255 if gate==1 else 0,1);put(initial,OWNER+0x12,1 if enabled else 255,1)
        put(initial,OWNER+0x54,0x80012340)
        # Model the parent's live page/view lookup, including the callback's
        # possible page update. The actual table fetch and JALR are executed.
        blocked=bool(gate and not(read(initial,OWNER+0x49,1)&(1<<(signed_view&31))))
        if blocked:wanted=dict(initial);wanted_calls=[];observations=[];answer=cursor
        else:
            if enabled:
                wanted,expected_calls,values,dest=reference(initial,replace(c,phase=phase-32),s)
                wanted_calls=[(ENTRY,(OWNER,signed_view&0xFFFFFFFF)),*expected_calls];observations=[values]
            else:wanted=dict(initial);wanted_calls=[];observations=[]
            live_page=read(wanted,s['D_800BE9C0'],1)
            for at,value in ((cursor,0xDA380003),(cursor+4,OWNER+(live_page<<6)+0x78),(cursor+8,0xDB060004),(cursor+12,read(wanted,OWNER+0x58+(live_page<<4)+signed_view*4)),(cursor+16,0xDE000000),(cursor+20,read(wanted,OWNER+0x54))):put(wanted,at,value)
            answer=cursor+24
        models=[Caller(w,initial,c,view).run() for w in roots[0]];raw=Caller(roots[1],initial,c,view).run()
        for m in (*models,raw):assert public(m.memory)==public(wanted) and m.calls==wanted_calls and m.observations==observations and m.r[2]==answer,(c,view,enabled,gate,'parent')
        for m in models[1:]:assert complete(m)==complete(models[0]) and m.trace==models[0].trace
        assert raw.trace==models[0].trace
        for reg in (*range(16,24),28,29,30,31):assert raw.r[reg]==models[0].r[reg]
        count+=1
    return dict(cases=count,normalized_executions=count*4,raw_executions=count,original_parent_words=75,aligned_JAL_sites=jals,aligned_literal_pointers=pointers,original_callback_table_slot=1,actual_table_fetch_and_JALR_delay_slot=True,callback_second_argument_signed_halfword=True,callback_true_result_enables_three_graphics_commands=True,original_skip_and_visibility_gates=True,rotation_and_converter_providers_opaque=True,full_renderer_or_gameplay_claim=False)


def native_suite():
    s=source.HEADERS+source.SELECTED;body=s[s.index('/* Scale'):]
    header='''typedef unsigned int u32;typedef int s32;typedef unsigned char u8;typedef unsigned long long u64;typedef float f32;
    typedef union {u64 align;u8 bytes[64];} Mtx;
    f32 D_800A2490;u8 D_800BE9C0;
    void func_150A8050(f32 [4][4],f32,f32,f32);void guMtxF2L(f32 [4][4],Mtx *);
    static union {u64 align;u8 bytes[0x4200];} ownerStore;
    static u32 pattern,initialScale,page,mutation,unusedWord;
    static s32 stateOffset;static u8 *stateBefore;static int calls,failed;
    static u32 expected[16];
    static f32 number(u32 w){union {u32 u;f32 f;} v;v.u=w;return v.f;}
    static u32 word(f32 f){union {u32 u;f32 f;} v;v.f=f;return v.u;}
    static u32 seed(u32 i){static const u32 values[]={0,0x80000000u,1,0x007FFFFFu,0x00800000u,0x3F800000u,0xBF800000u,0x7F7FFFFFu};return values[(i+pattern)%8];}
    static int same(u32 a,u32 b){return a==b||((a&0x7F800000u)==0x7F800000u&&(a&0x7FFFFFu)&&(b&0x7F800000u)==0x7F800000u&&(b&0x7FFFFFu));}
    '''
    harness='''
    void func_150A8050(f32 m[4][4],f32 x,f32 y,f32 z){
     u32 i;f32 *flat=&m[0][0];
     if(calls++!=0||word(x)!=0x3E800000u||word(y)!=0||word(z)!=0xBF000000u)failed=1;
     for(i=0;i<16;i++)flat[i]=number(seed(i));
     if(mutation&1){D_800A2490=-0.25f;D_800BE9C0=(u8)(page+1);*(f32 *)(stateBefore+0x10)=7.5f;}
     if(mutation&2){*(s32 *)(ownerStore.bytes+0x50)=0x400;*(f32 *)(ownerStore.bytes+0x508)=123.0f;}
    }
    void guMtxF2L(f32 m[4][4],Mtx *out){
     u32 i;f32 *flat=&m[0][0];u8 *wanted=ownerStore.bytes+((u32)D_800BE9C0<<6)+0x78;
     if(calls++!=1||(u8 *)out!=wanted){failed=1;return;}
     for(i=0;i<16;i++){if(!same(word(flat[i]),expected[i]))failed=1;((u32 *)out)[i]=word(flat[i]);}
    }
    static int run(void){
     static const u32 scales[]={0,0x80000000u,0x3F800000u,0xBF800000u,0x3F000000u,0x40000000u,1,0x00800000u,0x7F7FFFFFu,0x7F800000u,0x7FC12345u};
     static const u32 pages[]={0,1,128,255},words[]={0,1,0x7FFFFFFFu,0x80000000u,0xFFFFFFFFu};
     static const s32 offsets[]={-0x80,0x100};u32 si,pi,oi,ui,i;f32 scale;u8 *dest;
     for(pattern=0;pattern<8;pattern++)for(si=0;si<11;si++)for(pi=0;pi<4;pi++)for(oi=0;oi<2;oi++)for(mutation=0;mutation<4;mutation++)for(ui=0;ui<5;ui++){
      initialScale=scales[si];page=pages[pi];stateOffset=offsets[oi];unusedWord=words[ui];
      for(i=0;i<sizeof(ownerStore.bytes);i++)ownerStore.bytes[i]=(u8)(i*13+0xA5);
      *(s32 *)(ownerStore.bytes+0x50)=stateOffset;stateBefore=ownerStore.bytes+stateOffset+0xF8;
      *(f32 *)stateBefore=0.25f;*(f32 *)(stateBefore+4)=-0.5f;*(f32 *)(stateBefore+0x10)=-3.75f;
      D_800A2490=number(initialScale);D_800BE9C0=(u8)page;
      scale=(mutation&1)?-0.25f:D_800A2490;
      for(i=0;i<16;i++){
       expected[i]=seed(i);
       if(i/4<3&&i%4<3){volatile f32 a=number(expected[i]),b=scale,c=a*b;expected[i]=word(c);}
      }
      expected[13]=word((mutation&1)?7.5f:-3.75f);calls=failed=0;
      if(func_15108D24(ownerStore.bytes,(s32)unusedWord)!=1||calls!=2||failed)return 1;
      dest=ownerStore.bytes+((u32)D_800BE9C0<<6)+0x78;
      for(i=0;i<16;i++)if(!same(((u32 *)dest)[i],expected[i]))return 1;
     }
     return 0;
    }
    __attribute__((force_align_arg_pointer,noreturn)) void _start(void){int value=run();__asm__ volatile("int $0x80"::"a"(1),"b"(value));__builtin_unreachable();}
    '''
    controls=[('wrong-return','return 1;','return 0;'),('missing-basis','    matrix[2][2] *= D_800A2490;',''),('wrong-basis','matrix[0][2] *=','matrix[0][3] *='),('scaled-height','matrix[3][1] = *(f32 *)(state + 0x10);','matrix[3][1] = *(f32 *)(state + 0x10) * D_800A2490;'),('wrong-page','D_800BE9C0 << 6','D_800BE9C0 << 5'),('wrong-destination',' + 0x78',' + 0x80'),('wrong-middle-angle','state, 0.0f,','state, 1.0f,'),('wrong-first-angle','matrix, *(f32 *)state,','matrix, *(f32 *)(state + 4),'),('recomputed-state','*(f32 *)(state + 0x10)','*(f32 *)(owner + *(s32 *)(owner + 0x50) + 0x108)'),('stale-scale','    matrix[0][0] *= D_800A2490;','    matrix[0][0] *= 1.0f;')]
    results=[]
    for label,opt,code,control in [(p[1:],p,body,False) for p in ('-O0','-O2','-O3')]+[(n,'-O2',body.replace(a,b),True) for n,a,b in controls]:
        assert not control or code!=body,label
        unit=o/('native-'+label+'.c');binary=o/('native-'+label);unit.write_text(header+code+harness)
        cmd=['gcc','-m32',opt,'-std=c99','-fno-strict-aliasing','-ffreestanding','-nostdlib','-static','-fno-pie','-no-pie','-fno-stack-protector','-msse2','-mfpmath=sse','-mstackrealign','-ffp-contract=off','-fsanitize=undefined','-fsanitize-undefined-trap-on-error','-Wall','-Wextra','-Werror','-Wno-unused-parameter',str(unit),'-o',str(binary)]
        p=subprocess.run(cmd,capture_output=True,text=True);assert p.returncode==0,p.stderr
        p=subprocess.run([str(binary)],capture_output=True,timeout=30);assert p.returncode==(1 if control else 0),(label,p.returncode,p.stderr)
        results.append(dict(name=label,optimization=opt,control=control,exit=p.returncode))
    q=dict(private_only=True,matching_credit=0,positive_cases_each=14080,profiles=['O0','O2','O3'],effective_controls=10,controls_exit_by_semantic_mismatch=True,UBSan_trapping=True,bit_exact_finite_signed_zero_and_subnormal_observations=True,nonfinite_NaN_classification_not_payload_claim=True,all_nine_basis_products=True,unscaled_height=True,live_scale_page_after_rotation=True,captured_state_pointer=True,pages=[0,1,128,255],results=results)
    return q
