"""Packed scalar model, original callback paths and bounded IEEE-single checks.

This checks nontrapping round-to-nearest arithmetic. It is not a hardware FCSR
or legacy-NaN emulator. Identical FP instructions and operand snapshots also
qualify that the four integer scheduling guards do not change FP execution.
"""
from dataclasses import dataclass,replace
import itertools,json,math,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_view_fov_transfer import fp
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.game_path_heading_turn_roles import bound_blob
ENTRY,STATE,TICKS,TABLE,SCRIPT=0x15115F68,0x30000,0x800BE9E4,0x80088C90,0x70000
byte=lambda n:((n&255)^128)-128
u32=lambda n:n&0xFFFFFFFF
def pack(d,i,u,l):return(d&255)|((u&255)<<8)|((i&255)<<16)|((l&255)<<24)
VALUES=(0,0x80000000,1,0x80000001,bits(1.),bits(-1.),bits(20.),bits(-20.),
        0x3F800001,0xBF800001,0x4B7FFFFF,0x4B800000,0x7F7FFFFF,0xFF7FFFFF,
        0x7F800000,0xFF800000,0x7FC12345)
@dataclass(frozen=True)
class Case:
    packed:int=pack(1,-3,20,-20)
    value:int=bits(1.)
    pending:int=bits(3.)
    ticks:int=1
    alias:int=0
    phase:int=0
    seed:int=0
def symbol(c):return(TICKS,STATE,STATE+0x3C,STATE+0x7C,STATE+0x80)[c.alias]
def fixture(c):
    m={STACK+c.phase+j:(j*17+0xA5)&255 for j in range(-64,128)}
    m.update({STATE+j:(j*29+c.seed*11+0x59)&255 for j in range(-16,176)})
    put(m,TICKS,c.ticks);put(m,STATE,c.value);put(m,STATE+0x3C,c.packed)
    put(m,STATE+0x7C,c.pending);put(m,STATE+0x80,0x80000000)
    return m
def public(m):return{a:b for a,b in m.items()if not STACK-64<=a<STACK+136}
def reference(initial,c):
    m=dict(initial);word=read(m,STATE+0x3C)
    d,i,u,l=byte(word),byte(word>>16),byte(word>>8),byte(word>>24)
    if d:
        change=fp(fp(read(m,STATE+0x7C),bits(float(d)),'div'),bits(float(i)),'add')
    else:change=bits(float(signed(u32(i*read(m,symbol(c))))))
    value=fp(read(m,STATE),change,'add');put(m,STATE,value)
    if float(u)<floating(value):put(m,STATE,bits(float(u)))
    elif floating(value)<float(l):put(m,STATE,bits(float(l)))
    put(m,STATE+0x80,0);put(m,STATE+0x7C,0)
    return m
def cases():
    rows=[]
    for field,v in itertools.product(range(4),range(256)):
        b=[1,-3,20,-20];b[field]=v;rows.append(Case(pack(*b),seed=v%3))
    for d,i,value,ticks in itertools.product((0,1,-1,3,-128),(0,1,-1,-128,127),VALUES,(0,1,0xFFFFFFFF,0x80000000)):
        rows.append(Case(pack(d,i,20,-20),value,VALUES[(value+ticks)%len(VALUES)],ticks))
    for d,alias,phase,bounds in itertools.product((0,1,-3),range(5),(0,8),((20,-20),(-20,20),(0,0),(-128,127))):
        rows.append(Case(pack(d,-1,*bounds),bits(0.5),bits(1.25),0x7FFFFFFF,alias,phase))
    rows.append(Case(pack(1,1,127,-128),bits(-16777216.),bits(16777216.)))
    return tuple(dict.fromkeys(rows))
class Oracle(FactoryOracle):
    def __init__(self,words,memory,c,entry=ENTRY,connected=None):
        super().__init__(words,memory,c,entry=entry,s={},arguments=(STATE,),connected=connected)
        self.before=self.r[:];self.before_f=self.f[:];self.fp_trace=[]
    def execute(self,w):
        op,fmt,rt,fs,fd,fn=w>>26,(w>>21)&31,(w>>16)&31,(w>>11)&31,(w>>6)&31,w&63
        if op!=17 or fmt==8:return super().execute(w)
        if fmt==0:self.r[rt]=self.f[fs]
        elif fmt==4:self.f[fs]=self.r[rt]
        elif fmt==20 and fn==32:self.f[fd]=bits(float(signed(self.f[fs])))
        elif fmt==16:
            a,b=self.f[fs],self.f[rt]
            self.fp_trace.append((self.current_pc,w,a,b))
            if fn in(0,3):self.f[fd]=fp(a,b,'add'if fn==0 else'div')
            elif fn==60:self.condition=floating(a)<floating(b)
            else:raise AssertionError(('foreign scalar FP op',hex(w)))
        else:raise AssertionError(('foreign scalar COP1',hex(w)))
        self.r[0]=0
    def record_call(self,t):
        assert t==ENTRY,hex(t);a=(self.r[4],);self.calls.append((t,a));self.events.append(('CALL',t,a))
    def hook(self,t):raise AssertionError(('Unexpected scalar helper',hex(t)))
def state(m):return(m.r,m.f,m.memory,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.current_pc,m.delay_of,m.all_accesses,m.fp_trace)
def verify(m,initial,c):
    assert public(m.memory)==public(reference(initial,c)),c
    assert m.r[16:24]==m.before[16:24]and m.r[28:31]==m.before[28:31]and m.f[20:]==m.before_f[20:],c
def programs(core,q,c):
    syms={'D_800BE9E4':symbol(c)}
    # Retail/normalized words are literally equal at the original bindings.
    normal=list(bound_blob(q['normal'],q['normal_refs'],syms));raw=list(bound_blob(q['raw'],q['refs'],syms))
    truth=list(struct.unpack('>60I',(core.ROOT/'conker/conker.us.bin').read_bytes()[core.ROM:core.ROM+240]))
    addr=symbol(c);truth[1]=(truth[1]&0xFFFF0000)|((addr+0x8000)>>16&65535);truth[28]=(truth[28]&0xFFFF0000)|(addr&65535)
    assert truth==normal
    return truth,normal,raw
def guest(core,q):
    count=0;visited=set()
    for c in cases():
        initial=fixture(c);machines=[]
        for words in programs(core,q,c):
            m=Oracle(words,initial,c);m.run();verify(m,initial,c);machines.append(m)
        assert state(machines[0])==state(machines[1])==state(machines[2]),c
        visited.update(machines[0].visits);count+=1
    missing=set(range(ENTRY,ENTRY+240,4))-visited
    # The compiler retains a duplicate lower-byte MTC1 after an unconditional
    # upper-clamp branch. The branch-likely delay provides the reachable copy.
    assert missing=={ENTRY+184},list(map(hex,missing))
    prefixes=0
    for c in(Case(),Case(packed=pack(0,-128,127,-128),ticks=0x80000000),Case(value=bits(100.)),Case(value=bits(-100.)),Case(alias=1,packed=pack(0,-1,-20,20))):
        initial=fixture(c);ps=programs(core,q,c);full=Oracle(ps[0],initial,c);full.run()
        for cut in range(full.all_accesses):
            ms=[]
            for p in ps:
                m=Oracle(p,initial,c);m.cut=cut
                try:m.run()
                except AccessBoundary:pass
                else:raise AssertionError(('Missing scalar fault cut',cut))
                ms.append(m)
            assert state(ms[0])==state(ms[1])==state(ms[2]);prefixes+=1
    return dict(cases=count,reachable_words=59,unreachable_words=[hex(ENTRY+184)],
                literal_raw_normalized_states_equal=True,FP_instruction_operands_equal=True,
                all_four_signed_bytes_exhausted=True,alias_layouts=5,executed_fault_cuts=prefixes,
                FP_model='bounded nontrapping IEEE single round-to-nearest; not hardware FCSR or legacy NaNs')
class PoisonCode(WindowCode):
    def __getitem__(self,pc):
        if pc==self.owner.return_pc:self.owner.r[2]=self.owner.poison;self.owner.poison_hits+=1
        return super().__getitem__(pc)
def connections(core,q):
    rom=(core.ROOT/'conker/conker.us.bin').read_bytes();seen=set();n=0
    windows=((0x15113EE0,0x141390,7,(0x15113EB4,0x15113EFC),0x15113EF0),
             (0x15113FB8,0x141468,9,(0x15113FDC,),0x15113FC8),
             (0x15113FA0,0x141450,15,(0x15113FDC,),0x15113FC8))
    for va,off,length,ends,return_pc in windows:
        body=struct.unpack_from('>%dI'%length,rom,off)
        for divisor,poison,loop in itertools.product((0,1,-128),(0,0xFFFFFFFF),(0,1)):
            c=Case(pack(divisor,-1,20,-20));initial=fixture(c);put(initial,STATE+0x38,ENTRY)
            put(initial,0x800D23C0,0x60000);put(initial,0x60002,0x1234,2)
            expected=reference(initial,c);ms=[]
            for p in programs(core,q,c):
                code=dict(zip(range(ENTRY,ENTRY+240,4),p));m=Oracle(body,initial,c,va,code)
                m.r[16]=STATE;m.r[17]=0 if va==0x15113FA0 else 0x60000;m.r[18]=loop;m.r[23]=0;m.r[30]=0
                m.before=m.r[:];m.return_pc=return_pc;m.poison=poison;m.poison_hits=0
                m.code=PoisonCode(m.code,m);m.code.ends=ends
                try:m.run()
                except WindowBoundary:pass
                else:raise AssertionError('Missing scalar caller boundary')
                assert public(m.memory)==public(expected)and m.calls==[(ENTRY,(STATE,))]and m.poison_hits==1 and m.r[2]==poison
                seen.update(m.visits);ms.append(m)
            assert state(ms[0])==state(ms[1])==state(ms[2]);n+=1
        assert all(va+j*4 in seen for j in range(length)) if va!=0x15113FA0 else va+4 in seen
    c=Case();initial=fixture(c);initial.update({SCRIPT+j:0xA5 for j in range(32)})
    for j in range(3):put(initial,TABLE+60+j*4,struct.unpack_from('>I',rom,0x22D78C+j*4)[0])
    assert struct.unpack_from('>3I',rom,0x22D78C)==(ENTRY,0x15115EDC,0)
    put(initial,SCRIPT+8,5);expected=dict(initial);put(expected,STATE+0x38,ENTRY);put(expected,STATE+0x78,0x15115EDC);expected[STATE+0x92]=0
    va=0x1509EBBC;m=Oracle(struct.unpack_from('>22I',rom,0xCC06C),initial,c,va)
    m.r[16]=SCRIPT;m.r[2]=STATE;m.code=WindowCode(m.code,m);m.code.ends=(0x1509ED5C,)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Missing scalar installer boundary')
    assert public(m.memory)==public(expected)and all(va+j*4 in m.visits for j in range(22))
    return dict(caller_cases=n,body_variants=3,window_words=[7,9,15],both_JALR_sites=True,
                branch_delay_callback_load=True,return_poison_ignored=True,installer_words=22,
                installer_table_row=5,installer_all_words_executed=True,complete_parent_not_claimed=True)
def native(core,out):
    body=core.SELECTED
    controls=dict(stub='void func_15115F68(u8 *state) {(void)state;}',
      unsigned_divisor=body.replace('s8 divisor','u8 divisor'),
      unsigned_increment=body.replace('s8 increment','u8 increment'),
      unsigned_upper=body.replace('s8 upper','u8 upper'),
      unsigned_lower=body.replace('s8 lower','u8 lower'),
      wrong_pending=body.replace('*(f32 *)(state + 0x7C) /','*(f32 *)(state + 0x80) /'),
      wrong_division=body.replace('/ (f32)divisor','* (f32)divisor'),
      wrong_addition_order=body.replace('*(f32 *)state += *(f32 *)(state + 0x7C) / (f32)divisor + (f32)increment;',
          '*(f32 *)state = (*(f32 *)state + *(f32 *)(state + 0x7C) / (f32)divisor) + (f32)increment;'),
      wrong_tick=body.replace('(u32)D_800BE9E4','((u32)D_800BE9E4 & 0x7F)'),
      independent_clamps=body.replace('else if (*(f32 *)state','if (*(f32 *)state'),
      wrong_clear=body.replace('*(f32 *)(state + 0x80) = 0.0f','*(f32 *)(state + 0x84) = 0.0f'),
      negative_zero_clear=body.replace('= 0.0f','= -0.0f'))
    assert all(v!=body for v in controls.values())
    rows=[]
    def image(m):
        v=bytearray(m[STATE+j]for j in range(-16,176))
        for at in(0,0x3C,0x7C,0x80):v[at+16:at+20]=v[at+16:at+20][::-1]
        return v
    arr=lambda v:'{'+','.join(str(b)for b in v)+'}'
    for c in cases():
        if c.alias or c.phase or math.isnan(floating(c.value))or math.isnan(floating(c.pending)):continue
        initial=fixture(c);expected=reference(initial,c)
        if math.isnan(floating(read(expected,STATE))):continue
        rows.append('{0x%Xu,%s,%s}'%(c.ticks,arr(image(initial)),arr(image(expected))))
    code='#include <ultra64.h>\ns32 D_800BE9E4;\n_Static_assert(sizeof(void*)==4,"native32");\n'
    for i,(_,b)in enumerate(dict(selected=body,**controls).items()):code+=b.replace('func_15115F68(','candidate_%d('%i)+'\n'
    code+='typedef struct {u32 ticks;u8 input[192],expected[192];}Case;\nstatic const Case cases[]={'+',\n'.join(rows)+'};\n'
    code+='static void (*candidates[])(u8*)={'+','.join('candidate_%d'%i for i in range(len(controls)+1))+'};\n'
    code+='static union{u32 align[48];u8 bytes[192];}record;\n'
    code+='''static int run(void){u32 i,j,k,killed=0;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++)for(j=0;j<sizeof(candidates)/sizeof(candidates[0]);j++){
    u32 bad=0;for(k=0;k<192;k++)record.bytes[k]=cases[i].input[k];D_800BE9E4=(s32)cases[i].ticks;
    candidates[j](record.bytes+16);for(k=0;k<192;k++)if(record.bytes[k]!=cases[i].expected[k])bad=1;
    if(!j&&bad)return 2;if(j&&bad)killed|=1u<<(j-1);}
    return killed==MASK?0:3;}\n'''.replace('MASK',str((1<<len(controls))-1)+'u')
    code+=START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
    p=out/'scalar-native.c';p.write_text(code)
    for opt in('-O0','-O2','-O3'):
        exe=out/('scalar-native-'+opt[1:]);build=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=core.ROOT,capture_output=True,text=True)
        assert build.returncode==0 and not build.stdout and not build.stderr,build.stdout+build.stderr
        run=subprocess.run([str(exe)],capture_output=True);assert run.returncode==0,(opt,run.returncode,run.stderr)
    return dict(cases_per_executable=len(rows),profiles=['-O0','-O2','-O3'],trapping_UBSan=True,
                entire_state_and_canaries=True,effective_controls=list(controls),native_aliases_not_claimed=True)
