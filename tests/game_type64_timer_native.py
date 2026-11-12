import itertools,json,subprocess,sys
from pathlib import Path
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import game_type64_timer_oracle as oracle
from tools.experiments import game_type64_timer_match as match
root=match.ROOT;out=match.OUT;ns=vars(oracle)
Case=ns['Case'];reference=ns['reference'];read=ns['read'];REC,OWNER,OTHER,ACTOR,ALT,ALT_ACTOR,FLAG=(ns[n]for n in ('REC','OWNER','OTHER','ACTOR','ALT','ALT_ACTOR','FLAG'))
STARTFN,AUDIO,END,ADJUST,FADE,RELEASE=(ns[n]for n in ('START','AUDIO','END','ADJUST','FADE','RELEASE'))
ids={REC:1,OWNER:2,OTHER:3,ACTOR:4,ALT:5,ALT_ACTOR:6}

def main():
    cases=[]
    for selector,timer,delta,height,mutation in itertools.product((0,1,2),(0,15),(0,20),(0x4197ffff,0x41980000),(0,1)):
     cases.append(Case(0,selector,timer,0,1,delta,height,mutation,0))
    for state,timer,fade,ticks,mutation in itertools.product((1,2,3,4),(0,180),(0,11,255),(0,1,10),(0,1)):
     cases.append(Case(state,0,timer,fade,ticks,1,0x41980000,mutation,0))
    edge=(-2147483648,-2147483647,-214748365,-1,0,1,214748364,214748365,2147483647)
    for state,timer,fade,ticks,mutation in itertools.product((0,1,2,3),(0,1,65535),(0,1,254,255),edge,(0,1)):
     cases.append(Case(state,1,timer,fade,ticks,ticks,0x41980000,mutation,0))
    rows=[]
    for c in cases:
     m,events=reference(c);converted=[]
     for t,args in events:
      kind={STARTFN:1,AUDIO:2,END:3,ADJUST:4,FADE:5,RELEASE:6}[t];a=list(args)+[0]*(5-len(args))
      if t in (ADJUST,RELEASE):a[0]=ids[a[0]]
      converted.append((kind,*a))
     converted += [(0,0,0,0,0,0)]*(8-len(converted));owner=ids[read(m,REC+0x10)];other=ids[read(m,REC+0x14)]
     rows.append('{%d,%d,%d,%d,0x%Xu,0x%Xu,0x%Xu,%d,%d,%d,%d,%d,%d,%d,%d,0x%Xu,0x%Xu,{'%(c.state,c.selector,c.timer,c.fade,c.ticks&0xFFFFFFFF,c.delta&0xFFFFFFFF,c.height,c.mutation,read(m,REC+0x18,2),m[REC+0x1a],m[REC+0x1b],m[FLAG],owner,other,len(events),int.from_bytes(bytes(m[ACTOR+0x674+i] for i in range(4)),'little'),int.from_bytes(bytes(m[ALT_ACTOR+0x674+i] for i in range(4)),'little'))+','.join('{'+','.join('0x%Xu'%x for x in e)+'}' for e in converted)+'}}')
    prefix='#include <ultra64.h>\n'+match.MANIFEST['header'];body=match.MANIFEST['body']
    code=prefix+r"""
    _Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
    static u32 recbuf[0x30/4],ownerbuf[0x400/4],otherbuf[0x200/4],actorbuf[0x800/4],posbuf[0x20/4],altbuf[0x400/4],altactorbuf[0x800/4];
    #define REC ((u8*)recbuf)
    #define OWNER ((u8*)ownerbuf)
    #define OTHER ((u8*)otherbuf)
    #define ACTOR ((u8*)actorbuf)
    #define POS ((u8*)posbuf)
    #define ALT ((u8*)altbuf)
    #define ALT_ACTOR ((u8*)altactorbuf)
    s32 D_800BE9E4,D_800BEA08;u8 D_800BEA0C;static u32 mutation,count;
    struct Event {u32 kind,a,b,c,d,e;};static struct Event observed[8];
    static u32 id(void *p){return p==REC?1:p==OWNER?2:p==OTHER?3:p==ACTOR?4:p==ALT?5:p==ALT_ACTOR?6:99;}
    static void event(u32 k,u32 a,u32 b,u32 c,u32 d,u32 e){if(count<8)observed[count]=(struct Event){k,a,b,c,d,e};count++;}
    void func_100176C4(void){event(1,0,0,0,0,0);if(mutation){*(u8**)(REC+0x10)=ALT;*(u8**)(REC+0x14)=ALT;}}
    void func_10010F30(s32 a,u16 b,u8 c,s16 d,u8 e){event(2,(u32)a,b,c,(u32)d,e);}
    void func_1000E2F4(s32 a){event(3,(u32)a,0,0,0,0);}
    void func_151254F4(struct108 *a,s32 b){event(4,id(a),(u32)b,0,0,0);if(mutation)*(u8**)(OWNER+0x318)=ALT_ACTOR;}
    void func_151D66F0(s32 a,s32 b){event(5,(u32)a,(u32)b,0,0,0);}
    void func_1516972C(struct102 *a){event(6,id(a),0,0,0,0);}
    """+body+r"""
    struct Case {u32 state,selector,timer,fade,ticks,delta,height,mutation,expected_timer,expected_state,expected_fade,expected_flag,expected_owner,expected_other,n,actor,altactor;struct Event events[8];};
    static const struct Case cases[]={
    """+',\n'.join(rows)+r"""
    };
    static void fill(u8*p,u32 n){u32 i;for(i=0;i<n;i++)p[i]=(i*13+0x21)&255;}
    static int run(void){u32 i,j;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
     const struct Case *c=&cases[i];fill(REC,0x30);fill(OWNER,0x400);fill(OTHER,0x200);fill(ACTOR,0x800);fill(POS,0x20);fill(ALT,0x400);fill(ALT_ACTOR,0x800);
     *(u8**)(REC+0x10)=OWNER;*(u8**)(REC+0x14)=OTHER;*(u16*)(REC+0x18)=c->timer;REC[0x1a]=c->state;REC[0x1b]=c->fade;REC[0x1c]=c->selector;
     *(u8**)(OWNER+0x2d0)=POS;*(u8**)(OWNER+0x318)=ACTOR;*(u8**)(ALT+0x318)=ALT_ACTOR;OWNER[0x13f]=0x37;OTHER[0x13f]=0x71;*(u32*)(POS+8)=c->height;D_800BEA08=c->ticks;D_800BE9E4=c->delta;D_800BEA0C=0;mutation=c->mutation;count=0;
     func_151041E4(REC);
     if(*(u16*)(REC+0x18)!=c->expected_timer||REC[0x1a]!=c->expected_state||REC[0x1b]!=c->expected_fade||D_800BEA0C!=c->expected_flag||id(*(u8**)(REC+0x10))!=c->expected_owner||id(*(u8**)(REC+0x14))!=c->expected_other||count!=c->n||*(u32*)(ACTOR+0x674)!=c->actor||*(u32*)(ALT_ACTOR+0x674)!=c->altactor)return 1;
     for(j=0;j<count;j++){const u32*a=(const u32*)&observed[j],*b=(const u32*)&c->events[j];u32 k;for(k=0;k<6;k++)if(a[k]!=b[k])return 2;}
     }return 0;}
    """+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
    results={}
    for variant in ('selected','threshold','signed-overflow'):
     candidate=code
     if variant=='threshold':
      assert candidate.count('height >= 19.0f')==1
      candidate=candidate.replace('height >= 19.0f','height > 19.0f')
     if variant=='signed-overflow':
      candidate=candidate.replace('(s32)((u32)record[0x1B] + (u32)D_800BEA08 * 10U)','record[0x1B] + D_800BEA08 * 10')
      candidate=candidate.replace('(s32)((u32)record[0x1B] - (u32)D_800BEA08 * 10U)','record[0x1B] - D_800BEA08 * 10')
      candidate=candidate.replace('(s32)((u32)value * 210U)','value * 210')
      candidate=candidate.replace('(u16)((u32)*(u16 *)(record + 0x18) - (u32)D_800BE9E4)','*(u16 *)(record + 0x18) - D_800BE9E4')
      candidate=candidate.replace('(u16)((u32)*(u16 *)(record + 0x18) - (u32)D_800BEA08)','*(u16 *)(record + 0x18) - D_800BEA08')
     sourcefile=out/('native-'+variant+'.c');sourcefile.write_text(candidate)
     for opt in ('-O0','-O2','-O3'):
      exe=out/('native-'+variant+opt);proc=subprocess.run(native_command(opt)+['-fno-builtin','-Wno-unused-variable',str(sourcefile),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert proc.returncode==0,(variant,opt,proc.stdout,proc.stderr[-4000:]);proc=subprocess.run([str(exe)],capture_output=True,preexec_fn=lambda:__import__('resource').setrlimit(__import__('resource').RLIMIT_CORE,(0,0)))
      if variant=='selected':assert proc.returncode==0,(variant,opt,proc.returncode)
      elif variant=='threshold':assert proc.returncode==1,(variant,opt,proc.returncode)
      else:assert proc.returncode<0,(variant,opt,proc.returncode)
      results[variant+opt]=proc.returncode
    (out/'native-summary.json').write_text(json.dumps(dict(cases=len(cases),results=results),indent=2)+'\n');print(json.dumps(dict(cases=len(cases),results=results)),flush=True)


if __name__ == "__main__": main()
