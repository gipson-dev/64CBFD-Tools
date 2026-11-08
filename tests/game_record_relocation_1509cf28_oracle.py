"""Loader varargs, live table/count aliases, relocation walks and native32."""
from dataclasses import dataclass,replace
import itertools,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
ENTRY,LOADER,GLOBAL,TABLE,LIST,ALTLIST,OUTPUT,OTHER,MARK=0x1509CF28,0x1502B6BC,0x800D2FB0,0x20000,0x30000,0x40000,0x50000,0x50100,0x60000
MASK=0x0FFFFFFF
u32=lambda n:n&0xFFFFFFFF
s8=lambda n:((n&255)^128)-128
@dataclass(frozen=True)
class Case:
    resource:int=0xFFFFFFFF
    count:int=3
    success:int=1
    write_count:int=1
    length:int=2
    seed:int=0
    alias:int=0
    mode:int=0
    phase:int=0
    malformed:int=0
    output:int=0

def symbols():return dict(D_800D2FB0=GLOBAL,func_1502B6BC=LOADER)
def countptr(c):return STACK+c.phase-16
def outptr(c,s=None):
    s=symbols()if s is None else s
    return c.output or {0:OUTPUT,1:TABLE+4,2:countptr(c),3:s['D_800D2FB0'],4:TABLE+8,5:LIST+0x100,6:LIST+0x104,7:OUTPUT,8:OUTPUT}.get(c.alias,OUTPUT)
def args(c,s=None):return(u32(c.resource),outptr(c,s))
def lists(c):return[(base+i*256,i)for base in(LIST,ALTLIST)for i in range(1,8)]
def fixture(c=Case(),s=None):
    s=symbols()if s is None else s;m={STACK+c.phase+i:(i*17+0xA5)&255 for i in range(-512,1024)}
    for base,n in((TABLE,128),(OUTPUT,32),(OTHER,32),(MARK,32),(s['D_800D2FB0']-16,48),(0x8008FF00,8)):
        for i in range(n):m[u32(base+i)]=0xA5
    for p,index in lists(c):
        for i in range(128):m[p+i]=0
        for k in range(c.length):
            put(m,p+8*k,u32((c.seed*1664525)+0x100+index*17+k*3))
            flag=0x70000000|((c.seed*65537+index*37+k*5)&MASK)
            if k==c.length-1 and not c.malformed:flag|=0x80000000
            put(m,p+8*k+4,flag)
        if c.length==1:put(m,p+12,0x71234567)
    for i in range(1,8):put(m,TABLE+8*i,LIST+256*i)
    put(m,s['D_800D2FB0'],0xBAD00000)
    if c.alias==3:
        for i in range(64):m[i]=0
        for i in range(1,8):put(m,4+8*i,ALTLIST+256*i)
    if c.alias==4:
        for i in range(64):m[i]=0
        put(m,4,0x1234);put(m,8,0x80000007);put(m,16,0x71234567)
    if c.alias==7:
        p=s['D_800D2FB0'];alt=u32(TABLE+p)
        for i in range(128):m[u32(alt+i)]=0
        for i in range(1,8):put(m,alt+8*i,p if i==1 else ALTLIST+256*i)
        put(m,TABLE+8,p);put(m,p+4,0x70000007);put(m,p+8,0x55);put(m,p+12,0x8000000F)
    if c.alias==8:
        put(m,TABLE+8,countptr(c));put(m,countptr(c)+4,0x80000007)
    return m

def public(m):return{a:b for a,b in m.items()if not STACK-512<=a<STACK+1040}
def helper_effect(m,c,home,p,s):
    put(m,MARK,0x13579BDF)
    if c.write_count:put(m,p,c.count)
    if c.mode&1:put(m,home+4,OTHER)
    if c.mode&2:put(m,s['D_800D2FB0'],0xBEEF0000)
    if c.mode&4:put(m,home,0xF00DBAAD)
    if c.mode&16:m[0x8008FF00]=0x7F;m[0x8008FF04]=0xE1

def reference(initial,c=Case(),s=None,cache_global=False,cache_count=False,global_post=False):
    s=symbols()if s is None else s;m=dict(initial);home=STACK+c.phase;cp=countptr(c);calls=[];touched=set();status='return';answer=None
    put(m,home,u32(c.resource));put(m,home+4,outptr(c,s));put(m,cp,0)
    calls.append((s['func_1502B6BC'],(0,0,cp,3,8,0,u32(c.resource))));helper_effect(m,c,home,cp,s)
    loaded=TABLE if c.success else 0;put(m,s['D_800D2FB0'],loaded);output=read(m,home+4)
    try:
        if not loaded:put(m,output,0);answer=0
        else:
            put(m,loaded+4,u32(read(m,cp)-1));snapshot=read(m,cp);put(m,output,u32(snapshot-1));n=snapshot if cache_count else read(m,cp);index=1;offset=8;cursor=loaded
            while index<n:
                base=loaded if cache_global else read(m,s['D_800D2FB0']);pair=read(m,u32(base+offset))
                while True:
                    table=loaded if cache_global else read(m,s['D_800D2FB0']);first=read(m,pair);descriptor=read(m,u32(pair+4));base=read(m,u32(table+offset))
                    put(m,pair,u32(first+base));touched.add(pair);put(m,u32(pair+4),descriptor&MASK);pair=u32(pair+8)
                    if descriptor&0x80000000:break
                origin=u32(read(m,s['D_800D2FB0'])+offset)if global_post else u32(cursor+8)
                record=read(m,origin);put(m,u32(record+12),(read(m,u32(record+12))&MASK)>>1)
                cursor=u32(cursor+8);offset=u32(offset+8);index=u32(index+1);n=snapshot if cache_count else read(m,cp)
            answer=1
    except KeyError:status='unmapped_read'
    return m,calls,answer,status,touched

def cases():
    rows=[]
    for count,success,write_count,length,seed,resource in itertools.product((0,1,2,3,5),(0,1),(0,1),(1,2,3,4),(0,0xFFFF,0xFFFFFFFF),(0,0xFFFFFFFF,0x80000000)):
        rows.append(Case(resource,count,success,write_count,length,seed))
    for alias,phase,length,mode in itertools.product((1,2,5,6),(0,8),(1,2,4),(0,1,2,4,7)):
        rows.append(Case(count=4,length=length,alias=alias,phase=phase,mode=mode))
    for alias,phase,mode in itertools.product((3,4,7,8),(0,8),(0,1,2,7)):
        count=5 if alias in(3,4)else u32(3-(STACK+phase-16))if alias==8 else 4
        rows.append(Case(count=count,length=2,alias=alias,phase=phase,mode=mode))
    rows.extend((Case(count=0xFFFFFFFF),Case(count=0x80000000),Case(count=3,malformed=1),Case(count=1,success=0,alias=3)))
    return tuple(dict.fromkeys(rows))

class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),entry=ENTRY,connected=None,s=None,arguments=None):
        super().__init__(words,memory,c,entry=entry,s=symbols()if s is None else s,connected=connected,arguments=args(c,s)if arguments is None else arguments)
        self.before=self.r[:];self.before_f=self.f[:];self.status='return';self.query_observations=[]
    def record_call(self,t):
        counts={self.syms['func_1502B6BC']:7,ENTRY:2,0x1509D08C:4,0x1509D054:0,0x10004074:1};assert t in counts,hex(t)
        a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
    def execute(self,w):
        if w>>26==0 and w&63==4:
            self.r[w>>11&31]=u32(self.r[w>>16&31]<<(self.r[w>>21&31]&31));self.r[0]=0;return
        return super().execute(w)
    def hook(self,t):
        a=self.calls[-1][1]
        if t==self.syms['func_1502B6BC']:
            assert a==(0,0,countptr(self.case),3,8,0,u32(self.case.resource)),a
            assert read(self.memory,a[2])==0
            helper_effect(self.memory,self.case,self.target_home,a[2],self.syms);value=TABLE if self.case.success else 0
        elif t==0x1509D08C:
            self.query_observations.append((a,read(self.memory,self.syms['D_800D2FB0'])));put(self.memory,a[2],0x2468);put(self.memory,a[3],0x1357);value=0xDEADBEEF
        elif t==0x10004074:
            put(self.memory,MARK+4,a[0]);value=0xDEADBEEF
        else:raise AssertionError(hex(t))
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)
    def finish(self):
        try:self.run()
        except KeyError:self.status='unmapped_read'
        except AssertionError as error:
            if len(error.args)!=1 or not isinstance(error.args[0],tuple)or error.args[0][0]!='unmapped read':raise
            self.status='unmapped_read'
        return self

def literal(m):return(m.r,m.f,m.memory,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.current_pc,m.delay_of,m.all_accesses,m.status)
def programs(core,q,s=None):
    s=symbols()if s is None else s;normal=list(core.bound_blob(q['normal'],q['normal_refs'],s))
    if s==symbols():assert normal==list(q['retail_words'])
    return list(q['retail_words'])if s==symbols()else normal,normal,list(core.bound_blob(q['raw'],q['refs'],s))

def guest(core,q):
    seen=set();count=0;statuses={'return':0,'unmapped_read':0}
    for c in cases():
        initial=fixture(c);wanted,calls,value,status,touched=reference(initial,c);ms=[]
        for body in programs(core,q):
            m=Oracle(body,initial,c).finish();assert(public(m.memory),m.calls,m.status)==(public(wanted),calls,status),(c,m.calls,calls,m.status,status)
            if status=='return':
                assert m.r[2]==value,(c,m.r[2],value);assert m.r[16:24]==m.before[16:24]and m.r[28:32]==m.before[28:32]and m.f[20:]==m.before_f[20:]
            ms.append(m)
        assert literal(ms[0])==literal(ms[1]),c
        assert(ms[0].memory,ms[0].trace,ms[0].calls)==(ms[2].memory,ms[2].trace,ms[2].calls),c
        seen.update(ms[0].visits);statuses[status]+=1;count+=1
    assert seen==set(range(ENTRY,ENTRY+300,4)),[hex(x)for x in set(range(ENTRY,ENTRY+300,4))-seen]
    cuts=0
    for c in(Case(success=0),Case(count=0),Case(count=1),Case(length=4),Case(alias=2),Case(alias=7),Case(count=u32(3-countptr(Case())),alias=8),Case(malformed=1)):
        initial=fixture(c);ps=programs(core,q)[:2];full=Oracle(ps[0],initial,c).finish()
        for cut in range(full.all_accesses):
            ms=[]
            for body in ps:
                m=Oracle(body,initial,c);m.cut=cut
                try:m.finish()
                except AccessBoundary:pass
                else:raise AssertionError(('Missing relocation fault cut',cut))
                ms.append(m)
            assert literal(ms[0])==literal(ms[1]);cuts+=1
    controls={}
    for name,c,kw in(('cached_global',Case(alias=7),dict(cache_global=True)),('global_post_cursor',Case(alias=7),dict(global_post=True)),('cached_count',Case(alias=2,count=4),dict(cache_count=True))):
        initial=fixture(c);a=reference(initial,c);b=reference(initial,c,**kw);assert(public(a[0]),a[2:4])!=(public(b[0]),b[2:4]),name;controls[name]=True
    return dict(cases=count,statuses=statuses,reachable_words=75,alias_modes=9,raw_and_normalized_memory_and_read_order_equal=True,literal_original_normalized_states_equal=True,executed_fault_cuts=cuts,live_global_count_and_original_cursor_controls=controls,malformed_and_large_count_prefixes=True,helper_bodies_not_emulated=True)

class BoundaryCode(WindowCode):
    def __init__(self,code,m,ends):super().__init__(code,m);self.m=m;self.ends=ends
    def __getitem__(self,pc):
        if pc in self.ends:self.m.boundary=pc;raise WindowBoundary
        return super().__getitem__(pc)
class ReferenceCaller(Oracle):
    def hook(self,t):
        if t!=ENTRY:return super().hook(t)
        m,calls,value,status,_=reference(self.memory,self.case,s=self.syms);assert status=='return';self.memory=m;self.calls.extend(calls);self.r[2]=value

def connected(core,q):
    rom=(core.ROOT/'conker/conker.us.bin').read_bytes();count=0;cleanup=struct.unpack_from('>14I',rom,0xCA504)
    for which,success,n,length,phase,mode in itertools.product((0,1),(0,1),(0,1,3),(1,3),(0,8),(0,1,2,4,16)):
        home=STACK+phase;c=Case(resource=s8(0x80),count=n,success=success,length=length,phase=phase,mode=mode,output=home+(0xB4 if which==0 else 0x2C));initial=fixture(c);initial[0x70000]=0 if mode&1 else 0xFF;initial[0x8008FF00]=0x80;initial[0x8008FF04]=0xFE
        window=struct.unpack_from('>%dI'%(10 if which==0 else 13),rom,0x20CBE4 if which==0 else 0x21059C);entry=0x151DF734 if which==0 else 0x151E30EC;ends=(0x151DF75C,0x151DF818)if which==0 else(0x151E3120,)
        def build(body=None):
            code=dict(zip(range(0x1509D054,0x1509D08C,4),cleanup))if which else{}
            code.update({a:0 for a in ends})
            if body is not None:code.update(zip(range(ENTRY,ENTRY+300,4),body))
            cls=ReferenceCaller if body is None else Oracle;m=cls(window,initial,c,entry=entry,connected=code,arguments=(u32(c.resource),));m.r[19]=0x70000;m.r[17]=0x40;m.code=BoundaryCode(m.code,m,ends);return m
        def run(m):
            try:m.run()
            except WindowBoundary:pass
            else:raise AssertionError('Missing original caller continuation boundary')
            return m
        wanted=run(build());observe=lambda m:(m.boundary,public(m.memory),m.calls,m.query_observations,m.r[16:24],m.r[29],m.r[31],m.r[2]if which==0 else None,m.r[11]if which==0 else None)
        assert wanted.calls[0]==(ENTRY,args(c)),wanted.calls[0]
        if which:
            query=next(a for t,a in wanted.calls if t==0x1509D08C);assert query==(u32(s8(0x7F if mode&16 else 0x80)),0xE1 if mode&16 else 0xFE,home+0x28,home+0x24)
            assert read(wanted.memory,GLOBAL)==0
        else:
            assert wanted.boundary==(0x151DF75C if success else 0x151DF818);assert wanted.r[11]==u32(1<<(read(wanted.memory,home+0xB4)&31))
        for body in programs(core,q):assert observe(run(build(body)))==observe(wanted),(which,c)
        count+=1
    return dict(cases=count,first_window_words=10,second_window_words=13,first_result_and_count_branch=True,second_signed_resource_reload_and_query=True,original_cleanup_words=14,original_release_call=True,home_mutation_and_live_globals=True,full_parents_not_claimed=True)

def native(core,out):
    body=core.SELECTED
    controls=dict(stub='s32 func_1509CF28(s32 resource,u32 *lastIndex){return 0;}',wrong_initial_count=body.replace('count = 0;','count = 1;'),
      wrong_depth=body.replace('(s32 *)&count, 3, 8, 0','(s32 *)&count, 2, 8, 0'),wrong_path=body.replace('(s32 *)&count, 3, 8, 0','(s32 *)&count, 3, 9, 0'),wrong_resource=body.replace('8, 0, resource','8, 0, resource + 1U'),
      wrong_failure_output=body.replace('*lastIndex = 0;','*lastIndex = 1;'),wrong_header_count=body.replace('*(u32 *)(loaded + 4) = count - 1','*(u32 *)(loaded + 4) = count'),wrong_output=body.replace('*lastIndex = count - 1','*lastIndex = count'),
      skip_first=body.replace('index = 1;','index = 2;'),wrong_offset=body.replace('offset = 8;','offset = 16;'),subtract_base=body.replace('pair[0] +=','pair[0] -='),
      wrong_terminal_bit=body.replace('0x80000000U','0x40000000U'),retain_header_bits=body.replace('0x0FFFFFFF','0x7FFFFFFF'),wrong_footer_shift=body.replace('>> 1','>> 2'),
      skip_final_data=body.replace('pair[0] +=','if ((pair[1] & 0x80000000U) == 0) pair[0] +='),wrong_return=body.replace('return 1;','return 0;'))
    assert all(v!=body for v in controls.values());rows=[]
    for c in cases():
        if c.phase or c.alias not in(0,1,5,6)or c.mode&~2:continue
        initial=fixture(c);wanted,calls,value,status,touched=reference(initial,c)
        if status!='return':continue
        arr=lambda vs:'{'+','.join(str(u32(x))+'u'for x in vs)+'}'
        finals=[tuple(read(wanted,LIST+256*i+4*k)for k in range(8))for i in range(1,8)]
        masks=[sum(1<<k for k in range(4)if LIST+256*i+8*k in touched)for i in range(1,8)]
        packet=(0,0,0xC0,3,8,0,u32(c.resource),0)
        rows.append('{%su,%su,%su,%su,%su,%su,%su,%su,%su,%s,%s,{%s},%s}'%(u32(c.resource),u32(c.count),c.success,c.write_count,c.length,c.seed,c.alias,c.mode,value,arr(tuple(read(wanted,TABLE+4*k)for k in range(32))),arr(masks),','.join(arr(v)for v in finals),arr(packet)))
    code='#include <ultra64.h>\nstatic u32 table[32],data[7][32],output;u8 *D_800D2FB0;\n'
    code+='typedef struct{u32 resource,count,success,write_count,length,seed,alias,mode,result,table[32],touched[7],final[7][8],packet[8];}Case;static const Case cases[]={'+',\n'.join(rows)+'};static const Case*current;static u32 packets[8],calls;\n'
    code+='''_Static_assert(sizeof(void*)==4,"native32");
    void*func_1502B6BC(s32 *size,s32 count,s32 *relocated,s32 depth,...){__builtin_va_list ap;s32 a,b,c;__builtin_va_start(ap,depth);a=__builtin_va_arg(ap,s32);b=__builtin_va_arg(ap,s32);c=__builtin_va_arg(ap,s32);__builtin_va_end(ap);
    calls++;packets[0]=(u32)size;packets[1]=(u32)count;packets[2]=relocated?0xC0u:0;packets[3]=(u32)depth;packets[4]=(u32)a;packets[5]=(u32)b;packets[6]=(u32)c;packets[7]=(u32)*relocated;
    if(current->write_count)*relocated=(s32)current->count;if(current->mode&2)D_800D2FB0=(u8*)0xBEEF0000u;return current->success?(void*)table:0;}
    '''
    for i,(_,b)in enumerate(dict(selected=body,**controls).items()):code+=b.replace('func_1509CF28(','candidate_%d('%i)+'\n'
    code+='static s32(*candidates[])(s32,u32*)={'+','.join('candidate_%d'%i for i in range(len(controls)+1))+'};\n'
    code+='''static int run(void){u32 n,j,i,k,v,want,bad,killed=0,*out;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){current=&cases[n];for(j=0;j<sizeof(candidates)/sizeof(candidates[0]);j++){
    for(i=0;i<32;i++)table[i]=0xA5A5A5A5u;for(i=0;i<7;i++){for(k=0;k<32;k++)data[i][k]=0;for(k=0;k<current->length;k++){data[i][2*k]=current->seed*1664525u+0x100u+(i+1)*17u+k*3u;data[i][2*k+1]=0x70000000u|((current->seed*65537u+(i+1)*37u+k*5u)&0x0FFFFFFFu);if(k==current->length-1)data[i][2*k+1]|=0x80000000u;}if(current->length==1)data[i][3]=0x71234567u;table[2*(i+1)]=(u32)data[i];}
    output=0xA5A5A5A5u;calls=0;for(i=0;i<8;i++)packets[i]=0;D_800D2FB0=(u8*)0xBAD00000u;out=current->alias==1?&table[1]:current->alias==5?&data[0][0]:current->alias==6?&data[0][1]:&output;
    v=(u32)candidates[j]((s32)current->resource,out);bad=v!=current->result||calls!=1||D_800D2FB0!=(current->success?(u8*)table:0);
    for(i=0;i<8;i++)bad|=packets[i]!=current->packet[i];
    for(i=0;i<32;i++){want=(i>=2&&i<=14&&!(i&1))?(u32)data[i/2-1]:current->table[i];bad|=table[i]!=want;}
    for(i=0;i<7;i++)for(k=0;k<32;k++){want=k<8?current->final[i][k]:0;if(k<8&&!(k&1)&&(current->touched[i]&(1u<<(k/2))))want+=(u32)data[i]-(0x30000u+256u*(i+1));bad|=data[i][k]!=want;}
    if(current->alias==0)bad|=output!=(current->success?(current->write_count?current->count:0)-1u:0);
    if(!j&&bad)return 2;if(j&&bad)killed|=1u<<(j-1);}}
    for(j=0;j<CONTROL_COUNT;j++)if(!(killed&(1u<<j)))return 10+j;return 0;}
    '''.replace('CONTROL_COUNT',str(len(controls)))
    code+=START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)');p=out/'relocation-native.c';p.write_text(code)
    for opt in('-O0','-O2','-O3'):
        exe=out/('relocation-native-'+opt[1:]);build=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=core.ROOT,capture_output=True,text=True)
        assert build.returncode==0 and not build.stdout and not build.stderr,build.stdout+build.stderr
        run=subprocess.run([str(exe)],capture_output=True,timeout=30);assert run.returncode==0,(opt,run.returncode,run.stderr)
    return dict(cases_per_executable=len(rows),profiles=['-O0','-O2','-O3'],trapping_UBSan=True,effective_controls=list(controls),actual_varargs=True,all_table_and_list_words=True,header_and_pair_output_aliases=True,private_frame_global_aliases_and_malformed_prefixes_guest_only=True)
