"""Selector byte gates, raw return values and the original three-word dispatcher."""
from dataclasses import dataclass,replace
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
ENTRY,JT,REGISTRATION,RECORD=0x1509C7C8,0x8009E458,0x80088498,0x30000
TARGETS=(40,120,172,224,244,256)
NAMES=('D_800C35C4','D_800C35EA','D_800C3C98','D_800C35E8','D_800C3672')
u32=lambda n:n&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
    identity:int=0x81
    selector:int=1
    unused:int=0x12345678
    flag:int=0
    mode:int=1
    player:int=0x81
    role:int=0xFE
    status:int=0x80
    incoming:int=0xDEADBEEF
    phase:int=0

def symbols(index=0):
    if index==0:return dict(jtbl_8009E458=JT,**{n:int(n.split('_')[1],16)for n in NAMES})
    base=(0x02447FFC,0x0355FFFC)[index-1]
    return dict(jtbl_8009E458=base,**dict(zip(NAMES,(base+0x10010,base+0x20004,base+0x30000,base+0x20002,base+0x40006))))
def args(c):return tuple(map(u32,(c.identity,c.selector,c.unused)))
def fixture(c=Case(),s=None,entry=ENTRY):
    s=symbols()if s is None else s;m={STACK+i:(i*17+0xA5)&255 for i in range(-256,256)}
    for n,v in zip(NAMES,(c.flag,c.mode,c.player,c.role,c.status)):m[s[n]]=v&255
    for i,target in enumerate(TARGETS):put(m,s['jtbl_8009E458']+4*i,entry+target)
    return m
def reference(initial,c=Case(),s=None,entry=ENTRY):
    s=symbols()if s is None else s;m=dict(initial);put(m,STACK+c.phase+8,u32(c.unused));reads=[]
    def get(p,size=1):
        v=read(m,p,size);reads.append((p,size,v));return v
    def byte(n):return get(s[n])
    selector=u32(c.selector)
    if not 1<=selector<=6:return m,u32(c.incoming),reads
    target=get(s['jtbl_8009E458']+4*(selector-1),4);branch=TARGETS.index(u32(target-entry))+1
    identity=u32(c.identity)
    if branch==1:
        result=0 if byte(NAMES[0])else 1 if byte(NAMES[1])==0 else int(identity!=byte(NAMES[2]))
    elif branch==2:result=int(byte(NAMES[1])==1 and identity==byte(NAMES[2]))
    elif branch in(3,6):result=int(byte(NAMES[1])==1 and identity==byte(NAMES[3]))
    elif branch==4:result=int(byte(NAMES[1])!=1)
    else:result=byte(NAMES[4])
    return m,result,reads

def cases():
    rows=[]
    for selector,mode,identity in itertools.product((1,2,3,4,6),range(256),(0x81,0xFE,0x80000081)):
        rows.append(Case(identity,selector,mode*0x1020304,mode&1,mode,status=mode,phase=8 if mode&1 else 0))
    for selector,mode,flag,identity in itertools.product(range(1,7),(0,1,2,255),(0,1,255),(0,1,127,128,255,256,0x81,0xFE,0xFFFFFFFF)):
        rows.append(Case(identity,selector,flag=flag,mode=mode,status=0xFF))
    rows.extend(Case(selector=5,status=v,unused=u32(v*0x1020304),phase=8 if v&1 else 0)for v in range(256))
    rows.extend(Case(selector=n,incoming=v)for n,v in itertools.product((0,7,8,255,0x10001,0x80000000,0xFFFFFFFF),(0,1,0xDEADBEEF)))
    return tuple(dict.fromkeys(rows))

class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),entry=ENTRY,connected=None,s=None,arguments=None):
        super().__init__(words,memory,c,entry=entry,s=symbols()if s is None else s,connected=connected,arguments=args(c)if arguments is None else arguments)
        self.r[2]=u32(c.incoming);self.before=self.r[:];self.before_f=self.f[:]
    def record_call(self,t):
        assert t==ENTRY,hex(t);self.calls.append((t,tuple(map(u32,self.arguments(3)))))
    def hook(self,t):raise AssertionError(('Unexpected selector helper',hex(t)))

def literal(m):return(m.r,m.f,m.memory,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.current_pc,m.delay_of,m.all_accesses)
def original_object(core,q,out):
    p=out/'original-reference.s';p.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.text\n'+(out/'retail-function.s').read_text()+'.size '+core.FUNCTION+',.-'+core.FUNCTION+'\n')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-I','conker/include','-o',str(p.with_suffix('.o')),str(p)],cwd=core.ROOT,check=True,capture_output=True)
    q['original'],q['original_refs']=core.function_blob(p.with_suffix('.o'))
def programs(core,q,s=None):
    s=symbols()if s is None else s;original=list(core.bound_blob(q['original'],q['original_refs'],s));normal=list(core.bound_blob(q['normal'],q['normal_refs'],s));assert original==normal
    raw_symbols={**s,'.rodata':s['jtbl_8009E458']};raw=list(core.bound_blob(q['raw'],q['refs'],raw_symbols));assert raw==normal
    return original,normal,raw
def guest(core,q):
    original_object(core,q,core.ROOT/core.BUILD);seen=set();count=0;invalid=0;returns=set()
    for c in cases():
        initial=fixture(c);wanted,value,reads=reference(initial,c);models=[]
        for body in programs(core,q)[:2]:
            m=Oracle(body,initial,c).run();assert(m.memory,m.r[2],m.reads)==(wanted,value,reads),c
            assert m.r[16:24]==m.before[16:24]and m.r[28:32]==m.before[28:32]and m.f==m.before_f and not m.calls
            models.append(m)
        assert literal(models[0])==literal(models[1]);seen.update(models[0].visits);returns.add(value);count+=1;invalid+=not 1<=u32(c.selector)<=6
    assert seen==set(range(ENTRY,ENTRY+308,4))
    aliases=[]
    for name,byte,phase in itertools.product(NAMES,range(4),(0,8)):
        c=Case(unused=0x010080FF,phase=phase);s=symbols();s[name]=STACK+phase+8+byte;aliases.append((c,s))
    for selector in(1,2,5,6):
        c=Case(selector=selector,unused=ENTRY+244);s=symbols();s['jtbl_8009E458']=STACK+8;aliases.append((c,s))
    for c,s in aliases:
        initial=fixture(c,s);wanted,value,reads=reference(initial,c,s);models=[Oracle(body,initial,c,s=s).run()for body in programs(core,q,s)[:2]]
        assert all((m.memory,m.r[2],m.reads)==(wanted,value,reads)for m in models);assert literal(models[0])==literal(models[1])
    cuts=0
    for c,s in([(Case(selector=n),symbols())for n in(0,1,2,3,4,5,6,7)]+aliases):
        initial=fixture(c,s);ps=programs(core,q,s)[:2];full=Oracle(ps[0],initial,c,s=s).run()
        for cut in range(full.all_accesses):
            models=[]
            for body in ps:
                m=Oracle(body,initial,c,s=s);m.cut=cut
                try:m.run()
                except AccessBoundary:pass
                else:raise AssertionError(('Missing selector cut',cut))
                models.append(m)
            assert literal(models[0])==literal(models[1]);cuts+=1
    # A defined-zero default is a real compiler/source regression, not an
    # interpretation of the original indeterminate C return path.
    out=core.ROOT/core.BUILD;body=core.SELECTED;changed=body[:-2]+'    return 0;\n}\n';obj,diag=core.compile_owner(core.ROOT,out,'#include <ultra64.h>\n'+changed,'control-defined-default');assert not diag
    raw,refs=core.function_blob(obj);s={**symbols(),'.rodata':JT};program=list(core.bound_blob(raw,refs,s));c=Case(selector=0,incoming=0xDEADBEEF);m=Oracle(program,fixture(c),c).run();assert m.r[2]==0 and m.r[2]!=c.incoming
    return dict(cases=count,invalid_selector_cases=invalid,reachable_words=77,raw_status_values=len(set(range(256))&returns),alias_cases=len(aliases),executed_fault_cuts=cuts,independent_full_memory_and_read_order=True,literal_original_normalized_states_equal=True,compiled_zero_default_rejected=True,invalid_selector_return_is_guest_ABI_only=True)

class BoundaryCode(WindowCode):
    def __init__(self,code,m,end):super().__init__(code,m);self.m=m;self.end=end;self.ends=()
    def __getitem__(self,pc):
        if pc==self.end:self.m.boundary=pc;raise WindowBoundary
        return super().__getitem__(pc)
class ReferenceCaller(Oracle):
    def hook(self,t):
        assert t==ENTRY;home=STACK+self.case.phase;old=self.case;actual=replace(old,identity=self.r[4],selector=self.r[5],unused=self.r[6],phase=old.phase-16,incoming=self.r[2]);memory,value,reads=reference(self.memory,actual,self.syms);self.memory=memory;self.r[2]=value
def connected(core,q):
    rom=(core.ROOT/'conker/conker.us.bin').read_bytes();window=struct.unpack_from('>31I',rom,0xDB5C8);assert struct.unpack_from('>I',rom,0x22CF58)[0]==ENTRY;count=0;end=0x17770000
    for selector,identity,status,incoming,phase in itertools.product((0,1,2,3,4,5,6,7,0x80000000),(0x81,0xFE,0xABCD0081),(0,128,255),(0,0xDEADBEEF),(0,8)):
        c=Case(identity,selector,RECORD,status=status,incoming=incoming,phase=phase);initial=fixture(c);initial.update({RECORD+i:0xA5 for i in range(32)});put(initial,RECORD,u32(identity|0x1000));put(initial,RECORD+4,u32(selector));put(initial,REGISTRATION,ENTRY)
        def build(body=None):
            code={end:0}
            if body is not None:code.update(zip(range(ENTRY,ENTRY+308,4),body))
            cls=ReferenceCaller if body is None else Oracle;m=cls(window,initial,c,entry=0x150AE118,connected=code,arguments=(RECORD,));m.r[31]=end;m.code=BoundaryCode(m.code,m,end);return m
        def run(m):
            try:m.run()
            except WindowBoundary:pass
            else:raise AssertionError('Missing original selector dispatcher return')
            return m
        wanted=run(build());expected_identity=u32(identity|0x1000)&0xFFFF0FFF;assert wanted.calls==[(ENTRY,(expected_identity,u32(selector),RECORD))]
        assert(wanted.r[29],wanted.r[31])==(STACK+phase,end)
        observe=lambda m:(m.boundary,m.memory,m.calls,m.r[2],m.r[16:23],m.r[29],m.r[31])
        for body in programs(core,q):assert observe(run(build(body)))==observe(wanted),c
        count+=1
    return dict(cases=count,original_window_words=31,registration='D_80088498[0]',registration_rom='0x22CF58',original_JALR=True,identity_high_bits_preserved=True,full_selector_word=True,third_argument_home_and_result_SP_RA_preserved=True,invalid_selector_incoming_V0_preserved=True,nonstandard_S7_RA_wrapper=True,full_parent_not_claimed=True)

def native(core,out):
    body=core.SELECTED
    controls=dict(stub='s32 func_1509C7C8(u32 identity,u32 selector,u32*record){return 0;}',
      ignore_flag=body.replace('if (D_800C35C4 != 0) return 0;',''),
      wrong_first_mode=body.replace('D_800C35EA == 0','D_800C35EA != 0'),
      nonzero_mode=body.replace('D_800C35EA == 1','D_800C35EA != 0'),
      narrowed_identity=body.replace('identity ==','(u8)identity =='),
      wrong_role=body.replace('identity == D_800C35E8','identity == D_800C3C98'),
      boolean_status=body.replace('return D_800C3672;','return D_800C3672 != 0;'),
      wrong_inverse=body.replace('return D_800C35EA != 1;','return D_800C35EA == 1;'))
    assert all(b!=body for b in controls.values());rows=[]
    for c in cases():
        if not 1<=u32(c.selector)<=6:continue
        _,value,_=reference(fixture(c),c);row=(*args(c),c.flag,c.mode,c.player,c.role,c.status,value)
        rows.append('{'+','.join(str(u32(v))+'u'for v in row)+'}')
    code='#include <ultra64.h>\nu8 '+','.join(NAMES)+';\nstatic u8 canary[64];\n'
    code+='typedef struct{u32 identity,selector,unused,flag,mode,player,role,status,result;}Case;static const Case cases[]={'+',\n'.join(rows)+'};\n'
    for i,b in enumerate([body,*controls.values()]):code+=b.replace('func_1509C7C8(','candidate_%d('%i)+'\n'
    code+='static s32(*candidates[])(u32,u32,u32*)={'+','.join('candidate_%d'%i for i in range(len(controls)+1))+'};\n'
    code+='''static int run(void){u32 n,j,i,bad,killed=0,value;const Case*c;
    for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){c=&cases[n];for(j=0;j<sizeof(candidates)/sizeof(candidates[0]);j++){
      D_800C35C4=c->flag;D_800C35EA=c->mode;D_800C3C98=c->player;D_800C35E8=c->role;D_800C3672=c->status;
      for(i=0;i<sizeof(canary);i++)canary[i]=(u8)(i*17u+0xA5u);
      value=(u32)candidates[j](c->identity,c->selector,(u32*)c->unused);bad=value!=c->result;
      bad|=D_800C35C4!=c->flag||D_800C35EA!=c->mode||D_800C3C98!=c->player||D_800C35E8!=c->role||D_800C3672!=c->status;
      for(i=0;i<sizeof(canary);i++)bad|=canary[i]!=(u8)(i*17u+0xA5u);
      if(!j&&bad)return 2;if(j&&bad)killed|=1u<<(j-1);
    }}for(j=0;j<CONTROL_COUNT;j++)if(!(killed&(1u<<j)))return 10+j;return 0;}
    '''.replace('CONTROL_COUNT',str(len(controls)))
    code+=START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)');p=out/'selector-native.c';p.write_text(code)
    for opt in('-O0','-O2','-O3'):
        exe=out/('selector-native-'+opt[1:]);build=subprocess.run(native_command(opt)+['-Wno-return-type',str(p),'-o',str(exe)],cwd=core.ROOT,capture_output=True,text=True)
        assert build.returncode==0 and not build.stdout and not build.stderr,build.stdout+build.stderr
        run=subprocess.run([str(exe)],capture_output=True,timeout=30);assert run.returncode==0,(opt,run.returncode,run.stderr)
    return dict(cases_per_executable=len(rows),profiles=['-O0','-O2','-O3'],trapping_UBSan=True,effective_controls=list(controls),all_globals_unchanged=True,full_status_byte=True,only_defined_selectors_1_through_6=True,return_type_warning_disabled_for_original_fallthrough=True,invalid_selector_machine_return_and_home_aliases_guest_only=True)
