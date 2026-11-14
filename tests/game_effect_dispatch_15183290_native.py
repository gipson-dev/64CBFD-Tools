import sys,json,subprocess
from pathlib import Path
from tools.tests import game_effect_dispatch_15183290_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.experiments.game_remaining_donor_candidates import body

def main():
    chosen=[];rows=[]
    for c in g.cases():
        if c.mode&2 or c.view not in (0,1,3):continue
        if len(chosen)%3==0 or c.kind<12:chosen.append(c)
    for c in chosen:
        want,calls,result=g.reference(g.fixture(c),c)
        callrows=[]
        for t,a in calls:
            callrows.append('{0x%Xu,%du,{%s}}'%(t,len(a),','.join('0x%Xu'%v for v in a)))
        callrows.extend(['{0,0,{0}}']*(5-len(callrows)))
        fields=[','.join('0x%Xu'%v for v in g.args(c)),','.join(map(str,c.busy)),','.join('0x%Xu'%v for v in c.coords),
                str(c.valid),str(c.mode),str(c.seed),'0x%Xu'%result,
                ','.join(str(want[g.POOL+i]) for i in range(4)),str(len(calls)),','.join(callrows)]
        rows.append('{{%s},{%s},{%s},%s,%s,%s,%s,{%s},%s,{%s}}'%tuple(fields))
    code='#include <ultra64.h>\n'+(g.source.OUT/'extra.c').read_text()+r'''
struct Log {u32 target,count,args[18];};
struct Case {s32 args[11];u8 busy[4];u32 coords[3],valid,mode,seed,result;u8 final[4];u32 count;struct Log logs[5];};
static const struct Case cases[]={ROWS};
u8 D_800DDF5C[4],D_800CC2E4[4];u8 *D_800DBFF0;
FLOATDEFS
static u32 views[0x9A0],actorWords[128],callCount,error;
static const struct Case *c;
static u32 word(f32 v){union{u32 u;f32 f;}a;a.f=v;return a.u;}
static void record(u32 t,u32 n,u32 *a){
    const struct Log *l;u32 i;
    if(callCount>=c->count){error=1;return;}
    l=&c->logs[callCount];if(t!=l->target||n!=l->count)error=2;
    for(i=0;i<n;i++){
        u32 expected=l->args[i];
        if(t==0x15184118&&i==0)expected=(u32)actorWords;
        if(t==0x15177F90&&i==1&&expected)expected=(u32)D_800CC2E4;
        if(a[i]!=expected)error=3;
    }
    callCount++;
    if(c->mode&1){
        for(i=0;i<4;i++)D_800DDF5C[i]=(u8)(callCount*17+i);
        D_800DBFF0=(u8*)views+0x1000;
        *(u32*)((u8*)views+(u32)c->args[6]*0x9A0+0x3D0)=(u32)actorWords+0x1000;
        MUTATEFLOATS
    }
}
HELPERS
SELECTED
static u32 run(void){
    u32 i,j,result;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
        c=&cases[i];callCount=0;error=0;
        for(j=0;j<4;j++)D_800DDF5C[j]=c->busy[j];
        D_800DBFF0=(u8*)views;*(u32*)((u8*)views+(u32)c->args[6]*0x9A0+0x3D0)=(u32)actorWords;
        for(j=0;j<3;j++)actorWords[5+j]=c->coords[j];actorWords[15]=word(3.25f);
        INITFLOATS
        result=func_15183290(ARGS);
        if(error||result!=c->result||callCount!=c->count)return 10+error;
        for(j=0;j<4;j++)if(D_800DDF5C[j]!=c->final[j])return 20;
    }return 0;
}
__attribute__((force_align_arg_pointer)) void _start(void){u32 status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''
    prototypes={0x15177f90:['s32','void *',*(['s32']*9)],0x15175390:[*(['s32']*15),'f32','f32','s32'],
                0x15174bf0:[*(['s32']*6),'f32','f32','s32'],0x15174fa4:[*(['s32']*8),'f32','f32'],
                0x151838b0:['s32'],0x15183974:['s32'],0x151839f0:['s32','s32'],0x15183acc:['s32'],
                0x15184118:['u8 *'],0x1517aa20:['f32',*(['s32']*4)]}
    helpers=[]
    for t,types in prototypes.items():
        name='func_%08X'%t;ret='s32' if t==0x15184118 else 'void'
        values=['word(a%d)'%i if typ=='f32' else '(u32)a%d'%i for i,typ in enumerate(types)]
        helpers.append('%s %s(%s){u32 a[]={%s};record(0x%Xu,%d,a);%s}'%(ret,name,','.join(typ+' a%d'%i for i,typ in enumerate(types)),','.join(values),t,len(types),'return c->valid;' if ret=='s32' else ''))
    names=['D_%08X'%a for a in g.FLOATS]
    swaps={'ROWS':',\n'.join(rows),'FLOATDEFS':'f32 '+','.join(names)+';',
           'INITFLOATS':'\n'.join('%s=.125f*%d+(c->seed%%3);'%(n,i+1) for i,n in enumerate(names)),
           'MUTATEFLOATS':'\n'.join('%s=callCount*.25f+%d+.5f;'%(n,i) for i,n in enumerate(names)),
           'HELPERS':'\n'.join(helpers),'SELECTED':(g.source.OUT/'selected-body.c').read_text(),
           'ARGS':','.join('c->args[%d]'%i for i in range(11))}
    for k,v in swaps.items():code=code.replace(k,v)
    src=g.source.OUT/'native.c';src.write_text(code);reports=[]
    for opt in ('-O0','-O2','-O3'):
        exe=g.source.OUT/('native'+opt);p=subprocess.run([*native_command(opt),'-o',str(exe),str(src)],cwd=g.source.ROOT,capture_output=True,text=True)
        (g.source.OUT/('native'+opt+'-diagnostics.txt')).write_text(p.stdout+p.stderr)
        if p.returncode:raise ValueError(p.stderr[-6000:])
        p=subprocess.run([str(exe)],capture_output=True);assert p.returncode==0,(opt,p.returncode,p.stderr)
        reports.append({'optimization':opt,'cases':len(chosen),'undefined_sanitizer':True})
    controls={
        'claim-burst':code.replace('if (kind != 9)', 'if (1)'),
        'wrong-parameter-scale':code.replace('(u32)param0 << 4','(u32)param0 << 3'),
        'wrong-return-slot':code.replace('return slot;', 'return 0;'),
    }
    for label,changed in controls.items():
        assert changed!=code
        p=g.source.OUT/(label+'.c');p.write_text(changed);exe=p.with_suffix('')
        r=subprocess.run([*native_command('-O2'),'-o',str(exe),str(p)],cwd=g.source.ROOT,capture_output=True,text=True)
        assert r.returncode==0,r.stderr
        r=subprocess.run([str(exe)],capture_output=True);assert 0<r.returncode<128,(label,r.returncode)
    reports.append({'effective_semantic_controls':len(controls)})
    (g.source.OUT/'native-report.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps(reports),flush=True)
if __name__=='__main__':main()
