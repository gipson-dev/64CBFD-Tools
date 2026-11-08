"""Record command packets, original registered dispatcher and native32 controls."""
from dataclasses import dataclass,replace
import itertools,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
ENTRY,RECORD,BASE,MARK=0x150A03B0,0x30000,0x90000,0x60000
TABLE,POINTER,REGISTRATION=0x8009F550,0x800D3098,0x800884D4
STATUS,PARAM,ORIGIN,FIELDS,RELOAD=0x150A2864,0x150A2940,0x150A3444,0x150A3398,0x151C970C
OFFSETS=(56,76,96,120,148,192)
u32=lambda n:n&0xFFFFFFFF
s16=lambda n:((n&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
    identity:int=3
    command:int=0
    values:tuple=(0x12345678,0,999,0xFFFF8001,0x12347FFF,0x87654321,0xDEADBEEF,0x13579BDF)
    record:int=RECORD
    mode:int=0
    phase:int=0

def symbols():return dict(jtbl_8009F550=TABLE,D_800D3098=POINTER,func_150A2864=STATUS,func_150A2940=PARAM,func_150A3444=ORIGIN,func_150A3398=FIELDS,func_151C970C=RELOAD)
def args(c):return(u32(c.identity),u32(c.command),c.record)
def fixture(c=Case(),s=None,entry=ENTRY):
    s=symbols()if s is None else s;m={STACK+c.phase+i:(i*17+0xA5)&255 for i in range(-512,528)};m.update({MARK+i:0xA5 for i in range(64)})
    if c.record:
        for i,v in enumerate(c.values):put(m,c.record+4*i,v)
    for i,v in enumerate(OFFSETS):put(m,s['jtbl_8009F550']+4*i,entry+v)
    put(m,s['D_800D3098'],BASE);return m
def public(m):return{a:b for a,b in m.items()if not STACK-512<=a<STACK+544}
def effect(m,c,target,s):
    put(m,MARK,target)
    if c.mode:
        if c.record:
            for i in range(2,7):put(m,c.record+4*i,read(m,c.record+4*i)^0x80010001)
        put(m,s['D_800D3098'],BASE+0x340)

def reference(initial,c=Case(),s=None):
    s=symbols()if s is None else s;m=dict(initial);cmd=u32(c.command);identity=u32(c.identity);p=c.record
    if cmd in(0,1):target=STATUS;a=(identity,cmd)
    elif cmd==2:target=PARAM;a=(identity,read(m,p+8),read(m,p+12))
    elif cmd==3:target=ORIGIN;a=(identity,*(u32(s16(read(m,p+i)))for i in(8,12,16)))
    elif cmd==4:target=FIELDS;a=(identity,read(m,p+8)&65535,*(read(m,p+i)for i in(12,16,20,24)))
    elif cmd==5:
        target=RELOAD;value=read(m,p+8);a=(2 if value==999 else 0 if value else 1,u32(read(m,s['D_800D3098'])+identity*0x34))
    else:return m,[],0
    logical=next(n for n,v in symbols().items()if v==target);t=s[logical];effect(m,c,t,s);return m,[(t,tuple(map(u32,a)))],int(cmd<3)

def cases():
    rows=[]
    for identity,command,value,mode,phase in itertools.product((0,1,7,0x80000003,0xFFFFFFFF),(0,1,2,3,4,5,6,255,0x80000000,0xFFFFFFFF),(0,1,999,0x7FFF8000,0xFFFF8001,0xFFFFFFFF),(0,1),(0,8)):
        words=list(Case().values);words[2]=value;words[3]=u32(value^0x80017FFF);words[4]=u32(value^0xFFFF0000)
        rows.append(Case(identity,command,tuple(words),mode=mode,phase=phase))
    for command in(0,1,6,0xFFFFFFFF):rows.append(Case(command=command,record=0))
    return tuple(rows)

class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),entry=ENTRY,connected=None,s=None,arguments=None):
        super().__init__(words,memory,c,entry=entry,s=symbols()if s is None else s,connected=connected,arguments=args(c)if arguments is None else arguments)
        self.before=self.r[:];self.before_f=self.f[:]
    def record_call(self,t):
        counts={self.syms['func_150A2864']:2,self.syms['func_150A2940']:3,self.syms['func_150A3444']:4,self.syms['func_150A3398']:6,self.syms['func_151C970C']:2,ENTRY:3}
        assert t in counts,hex(t);a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
    def hook(self,t):
        assert t in self.syms.values()and t not in(self.syms['jtbl_8009F550'],self.syms['D_800D3098']),hex(t)
        effect(self.memory,self.case,t,self.syms)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=0xDEADBEEF;self.hi,self.lo=0xA5000010,0xA5000011

def literal(m):return(m.r,m.f,m.memory,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.current_pc,m.delay_of,m.all_accesses)
def programs(core,q,s=None):
    s=symbols()if s is None else s;normal=list(core.bound_blob(q['normal'],q['normal_refs'],s))
    if s==symbols():assert normal==list(q['retail_words'])
    return list(q['retail_words'])if s==symbols()else normal,normal

def guest(core,q):
    seen=set();count=0
    for c in cases():
        initial=fixture(c);wanted,calls,value=reference(initial,c);ms=[]
        for body in programs(core,q):
            m=Oracle(body,initial,c);m.run();assert(public(m.memory),m.calls,m.r[2])==(public(wanted),calls,value),(c,m.calls,calls)
            assert m.r[16:24]==m.before[16:24]and m.r[28:32]==m.before[28:32]and m.f[20:]==m.before_f[20:];ms.append(m)
        assert literal(ms[0])==literal(ms[1]);seen.update(ms[0].visits);count+=1
    missing=set(range(ENTRY,ENTRY+296,4))-seen;assert missing=={ENTRY+236},list(map(hex,missing))
    cuts=0
    for command in range(7):
        c=Case(command=command,mode=1);initial=fixture(c);ps=programs(core,q);full=Oracle(ps[0],initial,c);full.run()
        for cut in range(full.all_accesses):
            ms=[]
            for body in ps:
                m=Oracle(body,initial,c);m.cut=cut
                try:m.run()
                except AccessBoundary:pass
                else:raise AssertionError(('Missing dispatch fault cut',cut))
                ms.append(m)
            assert literal(ms[0])==literal(ms[1]);cuts+=1
    return dict(cases=count,reachable_words=73,unreachable_word=hex(ENTRY+236),six_commands_and_full_word_rejects=True,halfword_widths=True,outgoing_sixth_in_delay=True,helper_return_poisoned=True,exact_literal_states_and_reads=True,executed_fault_cuts=cuts,helper_bodies_not_emulated=True)

class BoundaryCode(WindowCode):
    def __init__(self,code,m,end):super().__init__(code,m);self.m=m;self.ends=();self.end=end
    def __getitem__(self,pc):
        if pc==self.end:self.m.boundary=pc;raise WindowBoundary
        return super().__getitem__(pc)
class ReferenceCaller(Oracle):
    def hook(self,t):
        assert t==ENTRY;m,calls,value=reference(self.memory,self.case);self.memory=m;self.calls.extend(calls);self.r[2]=value

def connected(core,q):
    rom=(core.ROOT/'conker/conker.us.bin').read_bytes();window=struct.unpack_from('>26I',rom,0xDB5DC);count=0;end=0x17770000
    assert struct.unpack_from('>I',rom,0x22CFA0)[0]==ENTRY
    for command,identity,value,mode,phase in itertools.product((0,1,2,3,4,5,6,0x80000000),(0,7,0xABCD0003),(0,999,0xFFFF8001),(0,1),(0,8)):
        values=list(Case().values);values[0]=u32(identity|0x4000);values[1]=u32(command);values[2]=value;c=Case(identity,command,tuple(values),mode=mode,phase=phase);initial=fixture(c);put(initial,REGISTRATION+12,ENTRY)
        def build(body=None):
            code={end:0}
            if body is not None:code.update(zip(range(ENTRY,ENTRY+296,4),body))
            cls=ReferenceCaller if body is None else Oracle;m=cls(window,initial,c,entry=0x150AE12C,connected=code,arguments=(c.record,));m.r[31]=end;m.code=BoundaryCode(m.code,m,end);return m
        def run(m):
            try:m.run()
            except WindowBoundary:pass
            else:raise AssertionError('Missing original indirect dispatcher return')
            return m
        wanted=run(build());observe=lambda m:(m.boundary,public(m.memory),m.calls,m.r[2],m.r[16:23],m.r[29],m.r[31])
        assert wanted.calls[0]==(ENTRY,args(c)),wanted.calls[0];assert(wanted.r[29],wanted.r[31])==(STACK+phase,end)
        for body in programs(core,q):assert observe(run(build(body)))==observe(wanted),c
        count+=1
    return dict(cases=count,original_window_words=26,registration='D_800884D4[3]',registration_rom='0x22CFA0',original_JALR=True,identity_high_bits_preserved=True,full_command_word=True,result_and_SP_RA_preserved=True,nonstandard_S7_RA_wrapper=True,full_parent_not_claimed=True)

def native(core,out):
    body=core.SELECTED;typedef='typedef struct { u8 bytes[0x34]; } DispatchRecord150A03B0;'
    controls=dict(stub='s32 func_150A03B0(u32 identity,u32 command,u32*record){return 0;}',wrong_status=body.replace('identity, 0','identity, 1'),
      wrong_word=body.replace('record[2], record[3]','record[3], record[2]'),wrong_signed_half=body.replace('(s16)record[2]','(s16)(record[2] >> 16)'),
      byte_mask=body.replace('(u16)record[2]','(u8)record[2]'),wrong_outgoing_last=body.replace('record[5], record[6]','record[6], record[5]'),
      wrong_999=body.replace('== 999','== 998'),wrong_boolean=body.replace('record[2] != 0 ? 0 : 1','record[2] != 0 ? 1 : 0'),wrong_record=body.replace('&D_800D3098[identity]','&D_800D3098[identity + 1]'),
      zero_success=body.replace('return 1;','return 0;'),nonzero_failure=body.replace('break;','return 1;'),nonzero_default=body.replace('    return 0;','    return 1;'),narrow_command=body.replace('switch (command)','switch ((u8)command)'))
    assert all(v!=body for v in controls.values());rows=[]
    for c in cases():
        if c.identity>7 or c.phase:continue
        wanted,calls,value=reference(fixture(c),c);packet=(0,)*8
        if calls:
            t,a=calls[0]
            if t==RELOAD:a=(a[0],a[1]-BASE)
            packet=(t,len(a),*a,*([0]*(6-len(a))))
        arr=lambda vs:'{'+','.join(str(u32(x))+'u'for x in vs)+'}'
        final=tuple(read(wanted,c.record+4*i)for i in range(8))if c.record else c.values
        rows.append('{%su,%su,%s,%su,%su,%su,%s,%s}'%(c.identity,u32(c.command),arr(c.values),int(bool(c.record)),c.mode,value,arr(final),arr(packet)))
    code='#include <ultra64.h>\n'+typedef+'\nstatic DispatchRecord150A03B0 records[16];DispatchRecord150A03B0 *D_800D3098=records;static u32 input[8],packet[8];\n'
    code+='typedef struct{u32 identity,command,values[8],present,mode,result,final[8],packet[8];}Case;static const Case cases[]={'+',\n'.join(rows)+'};static const Case*current;\n'
    code+='''_Static_assert(sizeof(void*)==4,"native32");_Static_assert(sizeof(DispatchRecord150A03B0)==0x34,"record stride");
    static void event(u32 t,u32 n,u32 a,u32 b,u32 c,u32 d,u32 e,u32 f){u32 i;packet[0]=t;packet[1]=n;packet[2]=a;packet[3]=b;packet[4]=c;packet[5]=d;packet[6]=e;packet[7]=f;if(current->mode){if(current->present)for(i=2;i<7;i++)input[i]^=0x80010001u;D_800D3098=records+16;}}
    void func_150A2864(u32 a,s32 b){event(STATUS,2,a,(u32)b,0,0,0,0);}
    void func_150A2940(u32 a,s32 b,s32 c){event(PARAM,3,a,(u32)b,(u32)c,0,0,0);}
    void func_150A3444(s32 a,s16 b,s16 c,s16 d){event(ORIGIN,4,(u32)a,(u32)(s32)b,(u32)(s32)c,(u32)(s32)d,0,0);}
    void func_150A3398(s32 a,u16 b,s32 c,s32 d,s32 e,s32 f){event(FIELDS,6,(u32)a,b,(u32)c,(u32)d,(u32)e,(u32)f);}
    void func_151C970C(s32 a,s32 b){event(RELOAD,2,(u32)a,(u32)b-(u32)records,0,0,0,0);}
    '''
    for name,v in dict(STATUS=STATUS,PARAM=PARAM,ORIGIN=ORIGIN,FIELDS=FIELDS,RELOAD=RELOAD).items():code=code.replace(name,str(v)+'u')
    for i,(_,b)in enumerate(dict(selected=body,**controls).items()):code+=b.replace(typedef,'').replace('func_150A03B0(','candidate_%d('%i)+'\n'
    code+='static s32(*candidates[])(u32,u32,u32*)={'+','.join('candidate_%d'%i for i in range(len(controls)+1))+'};\n'
    code+='''static int run(void){u32 n,j,i,bad,killed=0,v;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){current=&cases[n];for(j=0;j<sizeof(candidates)/sizeof(candidates[0]);j++){
    D_800D3098=records;for(i=0;i<8;i++){input[i]=current->values[i];packet[i]=0;}v=(u32)candidates[j](current->identity,current->command,current->present?input:0);bad=v!=current->result;
    for(i=0;i<8;i++)bad|=packet[i]!=current->packet[i]||input[i]!=current->final[i];if(!j&&bad)return 2;if(j&&bad)killed|=1u<<(j-1);}}
    for(j=0;j<CONTROLS;j++)if(!(killed&(1u<<j)))return 10+j;return 0;}
    '''.replace('CONTROLS',str(len(controls)))
    code+=START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)');p=out/'dispatch-native.c';p.write_text(code)
    for opt in('-O0','-O2','-O3'):
        exe=out/('dispatch-native-'+opt[1:]);build=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=core.ROOT,capture_output=True,text=True)
        assert build.returncode==0 and not build.stdout and not build.stderr,build.stdout+build.stderr
        run=subprocess.run([str(exe)],capture_output=True);assert run.returncode==0,(opt,run.returncode,run.stderr)
    return dict(cases_per_executable=len(rows),profiles=['-O0','-O2','-O3'],trapping_UBSan=True,effective_controls=list(controls),record_stride_52=True,logical_six_word_provider=True,full_word_rejects_and_ignored_null_records=True)
