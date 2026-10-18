"""Single-step progress, connected route selection, signed laps and timer alias order."""
import csv
import io
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_record_progress_lap as source
from tools.experiments import game_record_neighbor_selector as selector
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_view_point_projection_oracle as base
from tools.tests.test_game_record_heading_setter import SetterOracle
from tools.tests.test_game_record_neighbor_selector import reference as neighbor_reference
from tools.tests import test_game_view_list_setup as assembly
from tools.tests.test_game_projected_packet_draw import native_command

put,read,STACK=base.put,base.read,base.STACK
RECORD,ROUTES=0x50000,0x30000
HEADER='#include <ultra64.h>\nextern u8 *D_800D2350;\nextern s8 D_8008FD90;\ns32 func_150888A8(u8,u8,s8);\n'
ANCHORS=dict(D_800D2350=source.TABLE,D_800D2390=source.EVENT,D_800D23A8=source.MODE,
    D_800E0BE7=source.GOAL,D_800BE616=source.CLAMP,D_8008FD90=source.COUNT,
    D_800E0C10=source.BEST,D_800E0C18=source.TOTAL,func_150888A8=source.SELECTOR)
# fraction, delta, ticks, divisor, max lap, actor, disabled, timer, stamp,
# goal, clamp, count, event mode, event kind, record mode
DEFAULT=(0x3F666666,0x3E4CCCCD,5,3,0,0,0,100,0,2,0,4,0,0,0)


class OutsideDivisionDomain(Exception):pass


def signed(v,width=32):return ((v&((1<<width)-1))^(1<<(width-1)))-(1<<(width-1))
def addr(v):return v&0xFFFFFFFF
def public(memory):return {a:v for a,v in memory.items() if not STACK-0x400<=a<STACK+0x400}


def fixture(p=DEFAULT,alias=0,anchors=None,best_seed=300):
    a=anchors or ANCHORS
    fraction,delta,ticks,divisor,maximum,actor,disabled,timer,stamp,goal,clamp,count,mode,kind,record_mode=p
    row=(RECORD,a['D_800E0BE7']-0x27,a['D_800D2390']-0x2C,a['D_800E0C10']-0x28,
        a['D_800E0C18']-0x28,a['D_800E0C10']-0x20,a['D_800E0C18']-0x1C)[alias]
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x400,0x400)}
    for bank,n in ((ROUTES,4096),(a['D_800E0C10']-0x240,0x480),(a['D_800E0C18']-0x240,0x480),(row,0x84)):
        memory.update({bank+i:0xA5 for i in range(n)})
    for key in ('D_800D2350','D_800D2390','D_800D23A8','D_800E0BE7','D_800BE616','D_8008FD90'):
        for i in range(4):memory.setdefault(a[key]+i,0xA5)
    for i in range(256):
        for j in range(5):put(memory,ROUTES+i*16+9+j,10+(i%4)*3+j if j<3 else 255,1)
    for i in range(10,22):put(memory,ROUTES+i*16+14,0,1);put(memory,ROUTES+i*16+15,(i-10)%3,1)
    put(memory,ROUTES+2*16+15,kind,1)
    for i in range(4):put(memory,a['D_800E0C10']+i*2,best_seed*(i+1),2);put(memory,a['D_800E0C18']+i*4,1000*(i+1))
    put(memory,row+8,fraction);put(memory,row+0x18,stamp);put(memory,row+0x1C,timer)
    put(memory,row+0x24,ticks,2);put(memory,row+0x26,divisor,1);put(memory,row+0x27,0,1)
    for off,val in ((0x28,maximum),(0x2B,0),(0x2C,1),(0x2D,2),(0x2E,3),(0x2F,record_mode),(0x30,disabled),(0x31,actor)):
        put(memory,row+off,val,1)
    if alias==2:
        put(memory,row+0x2D,3 if mode else 2,1)
        if mode:
            for index,value in ((3,7),(1,8),(2,9)):put(memory,ROUTES+index*16+15,value,1)
        else:put(memory,ROUTES+2*16+15,5,1);put(memory,ROUTES+16+15,6,1)
    put(memory,a['D_800D2350'],ROUTES);put(memory,a['D_800E0BE7'],goal,1)
    put(memory,a['D_800D23A8'],mode,1);put(memory,a['D_800D2390'],0xA5,1)
    put(memory,a['D_800BE616'],clamp,1);put(memory,a['D_8008FD90'],count,1)
    return memory,(row,delta&0xFFFFFFFF)


def reference(initial,args,anchors=None):
    a=anchors or ANCHORS;memory=dict(initial);trace=[];calls=[];row=args[0]
    def get(at,n=4):
        at=addr(at);v=read(memory,at,n);trace.append(('R',at,n,v));return v
    def store(at,v,n=4):
        at=addr(at);trace.append(('W',at,n,v&((1<<(n*8))-1)));put(memory,at,v,n)
    def query(x,y,mode):
        actual=(x,y,mode&0xFFFFFFFF);calls.append((a['func_150888A8'],actual))
        result,reads=neighbor_reference(memory,actual,a['D_800D2350'])
        trace.extend(('R',at,n,v) for at,n,v in reads);return result
    fraction=base.add(get(row+8),args[1]);store(row+8,fraction);fraction=get(row+8);step=0
    if base.floating(fraction)<0.:
        last,middle=get(row+0x2D,1),get(row+0x2C,1);previous=get(row+0x2B,1);mode=signed(get(row+0x2F,1),8)
        store(row+0x2E,last,1);store(row+8,base.add(fraction,base.bits(1.)))
        store(row+0x2D,middle,1);store(row+0x2C,previous,1)
        store(row+0x2B,query(middle,previous,mode),1);step=-1
    elif 1.<=base.floating(fraction):
        previous,middle,last=get(row+0x2C,1),get(row+0x2D,1),get(row+0x2E,1)
        store(row+8,base.sub(fraction,base.bits(1.)));mode=signed(get(row+0x2F,1),8)
        store(row+0x2B,previous,1);store(row+0x2C,middle,1);store(row+0x2D,last,1)
        store(row+0x2E,query(middle,last,mode),1);step=1
        mode=signed(get(a['D_800D23A8'],1),8);index=get(row+0x2C,1);bank=get(a['D_800D2350']);kind=get(bank+index*16+15,1)
        if mode==0:
            if kind==5:
                store(a['D_800D2390'],1,1);index=get(row+0x2C,1);kind=get(bank+index*16+15,1)
            if kind==6:store(a['D_800D2390'],2,1)
        else:
            for k,value in ((7,1),(8,2),(9,3)):
                if kind==k:
                    store(a['D_800D2390'],value,1)
                    if k!=9:index=get(row+0x2C,1);kind=get(bank+index*16+15,1)
    if not step:return memory,0,trace,calls
    old=signed(get(row+0x24,2),16);goal=signed(get(a['D_800E0BE7'],1),8);divisor=signed(get(row+0x26,1),8)
    store(row+0x24,old+step,2);ticks=signed(get(row+0x24,2),16);actor=signed(get(row+0x31,1),8)
    if divisor==0:raise OutsideDivisionDomain((memory,trace,calls))
    quotient=(abs(ticks)//abs(divisor))*(-1 if (ticks<0)!=(divisor<0) else 1)
    store(row+0x27,quotient,1);clamp=get(a['D_800BE616'],1)
    if clamp:
        lap=signed(get(row+0x27,1),8)
        if goal<lap:store(row+0x27,goal+1,1)
    lap=signed(get(row+0x27,1),8);maximum=signed(get(row+0x28,1),8)
    if maximum>=lap:return memory,step&0xFFFFFFFF,trace,calls
    store(row+0x28,lap,1);count=signed(get(a['D_8008FD90'],1),8);score=False
    if actor<count:
        disabled=signed(get(row+0x30,1),8)
        if disabled==0:
            timer=signed(get(row+0x1C))
            if timer>0:score=True
    maximum=signed(get(row+0x28,1),8)
    if score:
        if goal>=maximum:
            stamp=get(row+0x18);elapsed=signed((timer-stamp)&0xFFFFFFFF);elapsed=min(elapsed,32000)
            best_at=addr(a['D_800E0C10']+actor*2);old_best=signed(get(best_at,2),16)
            if old_best<=0 or elapsed<old_best:store(best_at,elapsed,2)
            store(row+0x20,elapsed);maximum=signed(get(row+0x28,1),8)
        if goal==maximum:
            finish=signed(get(row+0x1C));store(a['D_800E0C18']+actor*4,min(finish,360000))
        maximum=signed(get(row+0x28,1),8)
    if goal==maximum:store(row+0x18,-get(row+0x1C))
    elif maximum<goal:store(row+0x18,get(row+0x1C))
    return memory,step&0xFFFFFFFF,trace,calls


class LapOracle(SetterOracle):
    def __init__(self,words,memory,args,helper,phase=0,entry=source.ENTRY,anchors=None,connected=None):
        self.a=anchors or ANCHORS;self.trace=[];self.setter_reads=[];self.setter_writes=[];self.forwarded=[]
        code=dict(connected or {});code.update(zip(range(self.a['func_150888A8'],self.a['func_150888A8']+352,4),helper))
        base.PointProjectionOracle.__init__(self,words,memory,args,[],phase,entry,code)

    def execute(self,word):
        if word>>26==0 and word&63==26 and self.r[(word>>16)&31]==0:raise OutsideDivisionDomain('Unqualified DIV by zero')
        return super().execute(word)

    def get(self,at,n):
        v=super().get(at,n)
        if self.own_instruction and not STACK-0x400<=at<STACK+0x400:self.trace.append(('R',at,n,v))
        return v

    def put(self,at,v,n):
        super().put(at,v,n)
        if self.own_instruction and not STACK-0x400<=at<STACK+0x400:self.trace.append(('W',at,n,v&((1<<(n*8))-1)))

    def record_call(self,target):
        if target==source.ENTRY:self.forwarded.append(self.arguments(2));return
        if target!=self.a['func_150888A8']:raise AssertionError('Unexpected progress/lap helper')
        self.calls.append((target,self.arguments(3)))

    def hook(self,target):raise AssertionError('Progress/lap helper must execute its real body')


def changed(p,**fields):
    names=('fraction','delta','ticks','divisor','maximum','actor','disabled','timer','stamp','goal','clamp','count','mode','kind','record_mode')
    values=list(p)
    for key,value in fields.items():values[names.index(key)]=value
    return tuple(values)


def corpus():
    floats=((.5,0.),(.9,.2),(.1,-.2),(-.25,0.),(1.,0.),(2.5,0.),(-2.5,0.),(-0.,0.),
        (.5,.5),(1.,-2**-24),(float('nan'),0.),(float('inf'),0.),(-float('inf'),0.))
    profiles=(dict(ticks=0),dict(ticks=2),dict(ticks=5,actor=1),dict(ticks=7,maximum=2),
        dict(ticks=32767,divisor=-1,maximum=-128,actor=3),dict(ticks=-32768,divisor=-128,clamp=1),
        dict(disabled=128),dict(timer=0,count=0),dict(ticks=11,clamp=1),dict(timer=0),dict(timer=0xFFFFFFFF))
    for (fraction,delta),mode,kind,profile in itertools.product(floats,(0,1,128),(0,5,6,7,8,9),profiles):
        yield changed(DEFAULT,fraction=base.bits(fraction),delta=base.bits(delta),mode=mode,kind=kind,record_mode=mode,**profile)
    for timer,stamp,goal,maximum,ticks in itertools.product((31999,32000,32001,359999,360000,360001,0x7FFFFFFF),
            (0,1,0xFFFFFFFF,0x80000000),(-128,0,1,2,127),(-128,-1,0,1),(2,5)):
        yield changed(DEFAULT,timer=timer,stamp=stamp,goal=goal,maximum=maximum,ticks=ticks)
    for divisor,ticks,delta in itertools.product(range(1,256),(-32768,-1,0,1,32767),(.2,-1.2)):
        yield changed(DEFAULT,divisor=divisor,ticks=ticks,delta=base.bits(delta),maximum=127)
    for count,actor in itertools.product(range(256),range(4)):yield changed(DEFAULT,count=count,actor=actor)


def controls():
    b=source.SELECTED
    no_event_reload=b.replace('D_800D2390 = 1;\n                kind = routes[record[0x2C] * 0x10 + 0xF];','D_800D2390 = 1;')
    late_goal=b.replace('        goal = D_800E0BE7;\n','').replace(
        '        if (D_800BE616 != 0', '        goal = D_800E0BE7;\n        if (D_800BE616 != 0')
    cached=b.replace('    s32 previousBest;', '    s32 previousBest;\n    s32 cachedMax;')
    marker='            *(s8 *)(record + 0x28) = *(s8 *)(record + 0x27);'
    start=cached.index(marker)+len(marker)
    cached=cached[:start]+'\n            cachedMax = *(s8 *)(record + 0x28);'+cached[start:].replace('*(s8 *)(record + 0x28)','cachedMax')
    return {
        'wrong-wrap':b.replace('fraction + 1.0f','fraction + 2.0f').replace('fraction - 1.0f','fraction - 2.0f'),
        'wrong-selector-order':b.replace('func_150888A8(middle, next,','func_150888A8(next, middle,'),
        'wrong-selector-mode':b.replace('func_150888A8(middle, next, *(s8 *)(record + 0x2F))','func_150888A8(middle, next, 0)'),
        'wrong-event-kind':b.replace('kind == 5','kind == 4').replace('kind == 7','kind == 6'),
        'unsigned-divisor':b.replace('/ *(s8 *)(record + 0x26)','/ *(u8 *)(record + 0x26)'),
        'inclusive-max':b.replace('*(s8 *)(record + 0x28) < *(s8 *)(record + 0x27)',
            '*(s8 *)(record + 0x28) <= *(s8 *)(record + 0x27)'),
        'wrong-clamp':b.replace('= goal + 1;','= goal;'),
        'wrong-best-cap':b.replace('elapsed = 32000;','elapsed = 31999;'),
        'wrong-empty-best':b.replace('previousBest <= 0 || elapsed < previousBest','elapsed < previousBest'),
        'wrong-finish-cap':b.replace('finish = 360000;','finish = 359999;'),
        'no-event-reload':no_event_reload,
        'late-goal':late_goal,
        'cached-max':cached,
    }


NATIVE=HEADER+r'''
typedef struct {u8 pad0[8];f32 fraction;u8 padC[12];s32 stamp,timer,elapsed;s16 ticks;
 s8 divisor,lap,maximum;u8 pad29[2];u8 previous,current,next,after;s8 mode,disabled,actor;u8 tail[82];} Record;
struct Case {u32 in[15],out[15],best[4],total[4],event,result,bestSeed;};
static const struct Case cases[]={ROWS};static const struct Case arithmetic=ARITHMETIC;
static Record record,expected;static u8 routes[4096],routeBefore[4096];
u8*D_800D2350;s8 D_8008FD90,D_800D23A8,D_800D2390,D_800E0BE7;u8 D_800BE616;
s16 D_800E0C10[4];s32 D_800E0C18[4];
static f32 real(u32 b){union{u32 u;f32 f;}v;v.u=b;return v.f;}
static u32 word(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
static u32 nanword(u32 u){return (u&0x7F800000u)==0x7F800000u&&(u&0x7FFFFFu);}
s32 func_15088A08(u8*,f32);
static int check(const struct Case*c){u32 i,j;const u32*p=c->in,*o=c->out;s32 result;
 for(i=0;i<sizeof(record);i++){((u8*)&record)[i]=0xA5;((u8*)&expected)[i]=0xA5;}
 for(i=0;i<4096;i++)routes[i]=0xA5;
 for(i=0;i<256;i++)for(j=0;j<5;j++)routes[i*16+9+j]=(u8)(j<3?10+(i%4)*3+j:255);
 for(i=10;i<22;i++){routes[i*16+14]=0;routes[i*16+15]=(u8)((i-10)%3);}
 routes[2*16+15]=(u8)p[13];for(i=0;i<4096;i++)routeBefore[i]=routes[i];
 for(i=0;i<4;i++){D_800E0C10[i]=(s16)((s32)c->bestSeed*(s32)(i+1));D_800E0C18[i]=(s32)(1000*(i+1));}
 record.fraction=real(p[0]);record.stamp=(s32)p[8];record.timer=(s32)p[7];record.elapsed=(s32)0xA5A5A5A5u;
 record.ticks=(s16)p[2];record.divisor=(s8)p[3];record.lap=0;record.maximum=(s8)p[4];
 record.previous=0;record.current=1;record.next=2;record.after=3;record.mode=(s8)p[14];record.disabled=(s8)p[6];record.actor=(s8)p[5];
 expected.fraction=real(o[0]);expected.stamp=(s32)o[1];expected.timer=(s32)o[2];expected.elapsed=(s32)o[3];
 expected.ticks=(s16)o[4];expected.divisor=(s8)o[5];expected.lap=(s8)o[6];expected.maximum=(s8)o[7];
 expected.previous=(u8)o[8];expected.current=(u8)o[9];expected.next=(u8)o[10];expected.after=(u8)o[11];
 expected.mode=(s8)o[12];expected.disabled=(s8)o[13];expected.actor=(s8)o[14];
 D_800D2350=routes;D_800E0BE7=(s8)p[9];D_800BE616=(u8)p[10];D_8008FD90=(s8)p[11];
 D_800D23A8=(s8)p[12];D_800D2390=(s8)0xA5;
 result=func_15088A08((u8*)&record,real(p[1]));if((u32)result!=c->result)return 23;
 if(nanword(word(record.fraction))&&nanword(word(expected.fraction)))expected.fraction=record.fraction;
 for(i=0;i<sizeof(record);i++)if(((u8*)&record)[i]!=((u8*)&expected)[i])return 23;
 if(D_800D2350!=routes||(u8)D_800D2390!=c->event||(u8)D_800D23A8!=(p[12]&255u)||
 (u8)D_800E0BE7!=(p[9]&255u)||D_800BE616!=(p[10]&255u)||(u8)D_8008FD90!=(p[11]&255u))return 23;
 for(i=0;i<4;i++)if((u16)D_800E0C10[i]!=c->best[i]||(u32)D_800E0C18[i]!=c->total[i])return 23;
 for(i=0;i<4096;i++)if(routes[i]!=routeBefore[i])return 23;return 0;}
static int run(void){u32 i,n=0,ticks;struct Case c=arithmetic;int status;
 if(sizeof(void*)!=4||sizeof(Record)!=0x84||__builtin_offsetof(Record,ticks)!=0x24||
 __builtin_offsetof(Record,previous)!=0x2B||__builtin_offsetof(Record,actor)!=0x31)return 29;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){status=check(cases+i);if(status)return status;n++;}
 for(i=0;i<65536;i++){c.in[2]=i;ticks=(i+1u)&65535u;c.out[4]=ticks;c.out[6]=(u32)((s16)ticks/3)&255u;
 status=check(&c);if(status)return status;n++;}return n==CASE_COUNT+65536u?0:28;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''


def native_case(p,best_seed=300):
    memory,args=fixture(p,best_seed=best_seed);expected,result,_,_=reference(memory,args);row=args[0]
    offsets=((8,4),(0x18,4),(0x1C,4),(0x20,4),(0x24,2),(0x26,1),(0x27,1),(0x28,1),
        (0x2B,1),(0x2C,1),(0x2D,1),(0x2E,1),(0x2F,1),(0x30,1),(0x31,1))
    out=[read(expected,row+off,n) for off,n in offsets]
    groups=(p,out,[read(expected,source.BEST+i*2,2) for i in range(4)],[read(expected,source.TOTAL+i*4) for i in range(4)])
    return '{'+','.join('{'+','.join('0x%Xu'%(v&0xFFFFFFFF) for v in g)+'}' for g in groups)+',0x%Xu,0x%Xu,0x%Xu}'%(read(expected,source.EVENT,1),result,best_seed&0xFFFFFFFF)


class ProgressLapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD;cls.stage=source.verify(cls.root,cls.out)
        with source.historical_view(cls.root,cls.out):cls.obj,cls.padded,cls.words,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=source.raw_read(cls.root/'conker/conker.us.bin');cls.truth=struct.unpack_from('>212I',cls.rom,source.ROM)
        image=source.raw_read(cls.out/'before-01');at=source.elf_slot_offset(image,source.SELECTOR,352)
        cls.helper=struct.unpack_from('>88I',image,at);assert image[at:at+352]==cls.rom[0xB5D58:0xB5EB8]
        cls.fixed=source.normalized(cls.words)

    def receipt(self,name,**data):(self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def compare(self,memory,args,phase=0,bodies=None,entry=source.ENTRY,anchors=None,helper=None):
        expected,result,trace,calls=reference(memory,args,anchors);models=[]
        for words in bodies or (self.words,self.fixed,self.truth):
            m=LapOracle(words,memory,args,helper or self.helper,phase,entry,anchors).run()
            self.assertEqual(public(m.memory),public(expected));self.assertEqual((m.r[2],m.calls,m.trace),(result,calls,trace))
            self.assertEqual(m.f[20:],m.saved_f)
            for r in (*range(16,24),28,29,30,31):self.assertEqual(m.r[r],m.before[r])
            models.append(m)
        self.assertEqual((models[1].r,models[1].f),(models[2].r,models[2].f));return models

    def test_01_single_step_laps_timer_gates_and_guest_aliases(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences'],self.row['neighbors']),(212,24,88,72))
        self.assertEqual(self.fixed,list(self.truth));count=0;seen=set()
        for p in corpus():
            memory,args=fixture(p);m=self.compare(memory,args,(count&1)*8);seen.update(m[0].visits);count+=1
        for seed,actor,timer in itertools.product((-32768,-1,0,1,32767),range(4),(100,1000,32001)):
            memory,args=fixture(changed(DEFAULT,actor=actor,timer=timer),best_seed=seed);self.compare(memory,args);count+=1
        for alias,mode,clamp,goal,timer in itertools.product(range(1,7),(0,1),(0,1),(1,2,3),(100,360001,0x7FFFFFFF)):
            memory,args=fixture(changed(DEFAULT,mode=mode,clamp=clamp,goal=goal,timer=timer),alias);self.compare(memory,args);count+=1
        for actor,count_byte in itertools.product((-128,-1,127),(0,4,127,128)):
            memory,args=fixture(changed(DEFAULT,actor=actor,count=count_byte));self.compare(memory,args);count+=1
        self.receipt('guest',three_way_cases=count,connected_real_helper=True,exact_trace=True,complete_public_memory=True,
            target_words_visited=len({pc for pc in seen if source.ENTRY<=pc<source.ENTRY+848}),guest_alias_patterns=6,
            target_words_unvisited=[i for i in range(212) if source.ENTRY+i*4 not in seen])

    def test_02_native32_O2_O0_UBSan_all_halfwords_and_result_controls(self):
        rows=[native_case(p) for p in corpus()]
        rows.extend(native_case(changed(DEFAULT,actor=actor,timer=timer),seed) for seed,actor,timer in
            itertools.product((-32768,-1,0,1,32767),range(4),(100,1000,32001)))
        rows.extend(native_case(changed(DEFAULT,fraction=base.bits(v),delta=0,divisor=0)) for v in (.5,-0.,float('nan')))
        harness=self.out/'native-driver.c'
        harness.write_text(NATIVE.replace('ROWS',','.join(rows)).replace('ARITHMETIC',native_case(changed(DEFAULT,maximum=127))).replace('CASE_COUNT',str(len(rows))))
        helper=self.out/'native-selector.c';helper.write_text(HEADER+selector.SELECTED)
        native_controls={n:b for n,b in controls().items() if n not in ('no-event-reload','late-goal','cached-max')}
        for name,opt,body,status in [('O2','-O2',source.SELECTED,0),('O0','-O0',source.SELECTED,0)]+[
                (n,'-O2',b,23) for n,b in native_controls.items()]:
            unit=self.out/('native-'+name+'.c');unit.write_text(HEADER+body);exe=unit.with_suffix('')
            c=subprocess.run([*native_command(opt),'-mstackrealign',str(unit),str(helper),str(harness),'-o',str(exe)],cwd=self.root,capture_output=True,text=True)
            self.assertEqual(c.returncode,0,c.stderr)
            self.assertEqual(subprocess.run([str(exe)],capture_output=True,timeout=180).returncode,status,name)
        self.receipt('native',cases_per_profile=len(rows)+65536,all65536_tick_halfwords=True,UBSan=True,
            connected_real_C_selector=True,controls=len(native_controls),fullRecordAndRouteTableBytes=True,
            valid_nonalias_objects_and_actor_indices=True,nonzero_division_when_crossing=True,native_NaN_class_not_payload=True)

    def test_03_guest_controls_change_public_results(self):
        cases=[fixture(changed(DEFAULT,mode=m,goal=g,timer=t),alias=a) for a,m,g,t in
            itertools.product(range(1,7),(0,1),(1,2,3),(100,360001))]
        cases.extend(fixture(p) for i,p in enumerate(corpus()) if i<2000)
        cases.extend(fixture(changed(DEFAULT,actor=actor),best_seed=seed) for seed,actor in itertools.product((-32768,-1,0,1),range(4)))
        for name,body in controls().items():
            obj,diagnostics=source.compile_owner(self.root,self.out,HEADER+body,'negative-'+name);self.assertFalse(diagnostics)
            data,functions=source.link_owner(self.root,self.out,obj,source.OWNER);f=functions[source.FUNCTION]
            words=struct.unpack_from('>%dI'%(f['size']//4),data,f['value'])
            for memory,args in cases:
                expected,result,_,_=reference(memory,args)
                m=LapOracle(words,memory,args,self.helper).run()
                if (public(m.memory),m.r[2])!=(public(expected),result):break
            else:self.fail('Ineffective progress/lap control: '+name)
        self.receipt('controls',observable_guest_controls=len(controls()),native_controls=len(controls())-3,native_wrong_result_status=23)

    def test_04_independent_original_raw_padded_and_connected_helper_rebases(self):
        context=type('OriginalContext',(),dict(root=self.root,out=self.out))
        original=assembly.ViewListSetupTests.original.__func__(context,'original-progress',source.raw_text(self.root/'conker/asm/B3020.s'),source.FUNCTION)
        raws=[]
        for obj in (self.obj,self.padded):
            text,functions,rel=source.parse_object(obj);f=functions[source.FUNCTION]
            raws.append((text[f['value']:f['value']+f['size']],{at-f['value']:v for at,v in rel.items() if f['value']<=at<f['value']+f['size']}))
        text,functions,rel=source.parse_object(self.padded);f=functions[selector.FUNCTION]
        helper_raw=text[f['value']:f['value']+f['size']]
        helper_bindings={at-f['value']:v for at,v in rel.items() if f['value']<=at<f['value']+f['size']}
        placements=[(source.ENTRY,ANCHORS),(0x16218004,dict(zip(ANCHORS,(0x12347FFC,0x23458004,0x34567FF0,
            0x800D7FFF,0x800B8004,0x80087FFC,0x800E7FFC,0x800E8004,0x16217000)))),
            (0x18FFF000,dict(zip(ANCHORS,(0x12348004,0x23457FFC,0x34568010,
            0x800D8003,0x800B7FFC,0x80088004,0x800E8004,0x800E800C,0x18FFE000))))]
        count=0
        for k,(entry,anchors) in enumerate(placements):
            objects=[original]
            for label,raw,bindings,function in [('raw',*raws[0],source.FUNCTION),('padded',*raws[1],source.FUNCTION),
                    ('helper',helper_raw,helper_bindings,selector.FUNCTION)]:
                emitted,missing=emit_function(raw,dict(value=0,size=len(raw)),bindings,function,anchors);self.assertFalse(missing)
                path=self.out/('rebase-%s-%d.s'%(label,k));path.write_text(emitted);obj=path.with_suffix('.o')
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(path)],check=True,capture_output=True);objects.append(obj)
            bodies=[]
            for j,obj in enumerate(objects):
                pc=anchors['func_150888A8'] if j==3 else entry;fn=selector.FUNCTION if j==3 else source.FUNCTION
                script=self.out/('rebase-%d-%d.ld'%(k,j));elf=script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%pc)
                subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',fn,
                    *['--defsym=%s=0x%X'%v for v in anchors.items() if v[0]!=fn],'-o',str(elf),str(obj)],check=True,capture_output=True)
                bodies.append(list(struct.unpack_from('>%dI'%(88 if j==3 else 212),sections(elf)['.text'][1])))
            self.assertEqual(bodies[0],bodies[2]);self.assertEqual(source.normalized(bodies[1]),bodies[0])
            for alias,mode,delta,phase in itertools.product((0,1,2,3,4,6),(0,1),(.2,-1.2),(0,8)):
                memory,args=fixture(changed(DEFAULT,mode=mode,record_mode=mode,goal=1,delta=base.bits(delta),timer=360001),alias,anchors)
                self.assertNotEqual(read(memory,args[0]+0x26,1),0,'Rebase fixture must retain a nonzero divisor')
                self.compare(memory,args,phase,(bodies[1],bodies[2],bodies[0]),entry,anchors,bodies[3]);count+=1
        self.receipt('rebases',independent_main_links=9,independent_helper_links=3,three_way_cases=count,all26_bindings=True)

    def test_05_fault_prefixes_and_undefined_division_fail_closed(self):
        states=count=0
        for alias,mode,delta in itertools.product((0,1,2,3,4,6),(0,1),(.2,-1.2)):
            memory,args=fixture(changed(DEFAULT,mode=mode,record_mode=mode,goal=1,delta=base.bits(delta),timer=360001),alias)
            full=LapOracle(self.fixed,memory,args,self.helper).run()
            for fault in range(full.all_accesses):
                models=[]
                for w in (self.words,self.fixed,self.truth):
                    m=LapOracle(w,memory,args,self.helper);m.access_fault=fault
                    with self.assertRaises(base.faults.AccessBoundary):m.run()
                    models.append(m)
                self.assertEqual((models[0].memory,models[0].trace),(models[2].memory,models[2].trace))
                self.assertEqual(base.state(models[1]),base.state(models[2]));count+=1
            states+=1
        rejected=0
        for ticks,delta in itertools.product((-32768,0,32767),(.2,-1.2)):
            memory,args=fixture(changed(DEFAULT,ticks=ticks,divisor=0,delta=base.bits(delta)))
            with self.assertRaises(OutsideDivisionDomain) as raised:reference(memory,args)
            expected,trace,calls=raised.exception.args[0];models=[]
            for w in (self.words,self.fixed,self.truth):
                m=LapOracle(w,memory,args,self.helper)
                with self.assertRaises(OutsideDivisionDomain):m.run()
                self.assertEqual((public(m.memory),m.trace,m.calls),(public(expected),trace,calls));models.append(m)
            self.assertEqual(base.state(models[1]),base.state(models[2]));rejected+=1
        self.receipt('faults',states=states,equal_public_and_stack_fault_prefixes=count,
            full_normalized_retail_state=True,raw_dead_GPR_states_not_claimed=True,zero_division_cases_rejected=rejected,
            undefined_DIV_quotient_and_trap_state_not_invented=True,overflow_trap_unreachable_for_s16_dividend=True)

    def test_06_three_original_caller_windows_deliver_pointer_float_and_step(self):
        owner=source.raw_read(self.out/'before-00').decode()
        for name in ('func_15087350','func_15088D58'):
            lo,hi=source.function_span(owner,name);self.assertEqual(owner[lo:hi],'s32 '+name+'() {\n    return 0;\n}')
        windows=((0x15087658,6,17),(0x15087720,9,16),(0x15088E24,3,20));count=0
        for entry,length,record_reg in windows:
            window=struct.unpack_from('>%dI'%length,self.rom,entry-0x14FD2B50);exit_pc=entry+length*4
            for phase,delta,ticks in itertools.product((0,8),(.2,-1.2),(0,2,5)):
                actual_delta=base.bits(1.) if record_reg==20 else base.add(base.bits(delta/2),base.bits(delta/2)) if record_reg==16 else base.bits(delta)
                memory,args=fixture(changed(DEFAULT,delta=actual_delta,ticks=ticks))
                expected,result,trace,calls=reference(memory,args);sp=STACK+phase
                for w in (self.words,self.fixed):
                    connected=dict(zip(range(source.ENTRY,source.ENTRY+848,4),w))
                    connected.update({exit_pc:0x8FBF03F0,exit_pc+4:0x03E00008,exit_pc+8:0})
                    m=LapOracle(window,memory,args,self.helper,phase,entry,connected=connected)
                    m.r[record_reg]=m.before[record_reg]=args[0]
                    m.f[8]=base.bits(delta);m.f[18]=0x3F123456;m.f[20]=base.bits(1.);m.saved_f[0]=m.f[20]
                    put(m.memory,sp+0x1D0,base.bits(delta/2));put(m.memory,sp+0x3F0,m.r[31]);m.run()
                    self.assertEqual(m.forwarded,[args]);self.assertEqual((public(m.memory),m.r[2],m.calls),(public(expected),result,calls))
                    if record_reg==17:self.assertEqual((m.f[18],read(m.memory,sp+0x15A,1)),(0x3F123456,result&255))
                count+=1
        self.receipt('caller',paired_bounded_windows=count,all_three_JAL_sites=True,actual_float_word_delivery=True,
            first_window_F18_and_low_step_byte=True,parent_production_stubs=True,whole_parent_gameplay_not_claimed=True)

    def test_07_fail_closed_words_bindings_guards_inputs_and_installation(self):
        text,functions,rel=source.parse_object(self.obj);f=functions[source.FUNCTION];raw,bindings=source.checked_object(self.obj)
        for i in range(212):
            bad=bytearray(text);bad[f['value']+i*4]^=1
            with patch.object(source,'parse_object',return_value=(bytes(bad),functions,rel)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        for i in bindings:
            bad=dict(rel);bad[f['value']+i]=[]
            with patch.object(source,'parse_object',return_value=(text,functions,bad)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        reader=csv.DictReader(io.StringIO(source.raw_read(self.out/'qualified-guards.csv').decode()));all_rows=list(reader)
        for row in source.owner_guards(raw,bindings):
            path=self.out/'bad-guard.csv';wrong=[dict(r,expected='0x%08X'%(int(r['expected'],16)^1))
                if (r['filename'],r['function'],r['offset'])==(row['filename'],row['function'],row['offset']) else r for r in all_rows]
            with path.open('w',newline='') as stream:
                w=csv.DictWriter(stream,fieldnames=reader.fieldnames);w.writeheader();w.writerows(wrong)
            with self.assertRaisesRegex(ValueError,source.FUNCTION):
                source.emit_padded_assembly(self.obj,self.root/'conker/asm/B3020.s',filename=source.OWNER,word_patches_path=path)
        with source.historical_view(self.root,self.out):
            read_bytes=Path.read_bytes
            for index,p in enumerate(source.INPUTS):
                for path in (self.root/p,self.out/('before-%02d'%index)):
                    with patch.object(Path,'read_bytes',lambda x:read_bytes(x)+b'\n' if x==path else read_bytes(x)):
                        with self.assertRaises(ValueError):source.freeze(self.root,self.out)
            with self.assertRaisesRegex(RuntimeError,'cannot nest'):
                with source.historical_view(self.root,self.out):pass
        self.assertEqual(source.verify(self.root,self.out),self.stage)
        if self.stage=='after':self.assertEqual(source.audit(self.root,self.out)['functions'],6057)


if __name__=='__main__':unittest.main()
