"""Bounded native cache storage and complete loader-entry observations."""
import json,subprocess
from tools.tests import game_resource_cache_15016850_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command

def values(snapshot):
    cache,a,b,count,table=snapshot
    return[cache[0],*[int.from_bytes(cache[8+2*i:10+2*i],'big')for i in range(8)],*[int.from_bytes(cache[24+4*i:28+4*i],'big')for i in range(8)],count,int(table==g.ALT),*[a[i*48+4]for i in range(8)],*[b[i*48+4]for i in range(8)]]

def main():
    arr=lambda xs:'{'+','.join('0x%Xu'%(v&0xffffffff)for v in xs)+'}';rows=[]
    for initial,args,native in g.corpus():
        if not native or args[2]:continue
        want,calls,obs=g.model(initial,args);final=values(g.snapshot(want,args));snapshots=[values(o)+[packet[1][3]]for o,packet in zip(obs,calls)]
        assert final[0]<=8 and len(calls)<=8 and all(v[0]<=8 for v in snapshots)
        snapshots+=[[0]*36]*(8-len(snapshots))
        rows.append('{'+','.join((arr([initial[g.LIST+i*48+4]for i in range(8)]+[initial[g.ALT+i*48+4]for i in range(8)]),str(initial[g.COUNT]),str(args[0]),str(args[1]),str(len(calls)),arr(final),'{'+','.join(map(arr,snapshots))+'}'))+'}')
    body=g.source.SELECTED
    reset=body.replace('do {','do {\n        handle = 0;')
    narrow=body.replace('resource == D_800BE598[index]','resource == (u8)D_800BE598[index]')
    cached_table=body.replace('void *handle;','void *handle;\n    u8 *records;').replace('handle = 0;','handle = 0;\n    records = (u8 *)D_800D20FC;').replace('((u8 *)D_800D20FC)[offset + 4]','records[offset + 4]')
    at=body.index('void '+g.source.NAME)
    prefix,function=body[:at],body[at:]
    function=function.replace('D_800D2100','initialCount').replace('void *handle;','void *handle;\n    s32 initialCount;').replace('handle = 0;','handle = 0;\n    initialCount = D_800D2100;')
    cached_count=prefix+function
    candidates=(body,reset,body.replace('resource < 187','resource <= 187'),narrow,body.replace('D_800BE590++;','D_800BE590 = 0;'),cached_table,cached_count)
    assert all(c!=body for c in candidates[1:])
    code=r'''
#include <ultra64.h>
#include "structs.h"
typedef union{struct{u8 count,pad[7];u16 ids[8];void*handles[8];u8 tail[1224];}f;u8 bytes[1280];}Cache;
Cache cache;u8 D_800D2100;struct258 *D_800D20FC;
__asm__(".globl D_800BE590\n.set D_800BE590,cache\n.globl D_800BE598\n.set D_800BE598,cache+8\n.globl D_800BE5A8\n.set D_800BE5A8,cache+24\n");
typedef char LayoutCheck[sizeof(Cache)==1280&&__builtin_offsetof(Cache,f.handles)==24?1:-1];
struct Case{u32 resources[16],count,response,mode,calls,final[35],snapshots[8][36];};
static const struct Case cases[]={ROWS};static const struct Case *active;
static u8 lists[2][384] __attribute__((aligned(4)));static u32 callCount,bad;static void **firstOutput;
static u32 invariant(void){u32 i,j;for(i=1;i<8;i++)if(cache.bytes[i]!=0xa5)return 1;for(i=56;i<1280;i++)if(cache.bytes[i]!=0xa5)return 1;for(j=0;j<2;j++)for(i=0;i<384;i++)if(i%48!=4&&lists[j][i]!=0xa5)return 1;return 0;}
static u32 check(const u32 *expected){u32 i;if(cache.f.count!=expected[0]||D_800D2100!=expected[17]||(u32)((u8*)D_800D20FC==lists[1])!=expected[18])return 1;
for(i=0;i<8;i++)if(cache.f.ids[i]!=expected[1+i]||(u32)cache.f.handles[i]!=expected[9+i]||lists[0][i*48+4]!=expected[19+i]||lists[1][i*48+4]!=expected[27+i])return 1;return invariant();}
__attribute__((noinline)) u32 func_1502B7F0(void **output,u32 depth,...){__builtin_va_list ap;u32 key,resource,n,value,write=1;const u32 *expected;
__asm__ volatile("":::"memory");__builtin_va_start(ap,depth);key=__builtin_va_arg(ap,u32);resource=__builtin_va_arg(ap,u32);__builtin_va_end(ap);
n=callCount++;if(n>=active->calls||n>=8){bad=1;return 0;}expected=active->snapshots[n];if(!n)firstOutput=output;
if(output!=firstOutput||!output||depth!=2||key!=18||resource!=expected[35]||check(expected))bad=1;
value=0x60000u+resource*16u;if(active->response==1&&resource&1)value=0;else if(active->response==2)write=n==0;else if(active->response==3){write=(n+1)&1;value=0;}if(write)*output=(void*)value;
if(active->mode&1&&n==0)D_800D2100=6;if(active->mode&2)D_800D20FC=(struct258*)lists[(n+1)&1];if(active->mode&4){cache.f.count=2;cache.f.ids[0]=0x1201;}if(active->mode&8)((u8*)D_800D20FC)[4]^=0x55;
__asm__ volatile("":::"memory");return 0x87654321u;}
CANDIDATES
static void(*tests[])(void)={TESTS};static u32 caseIndex;
static u32 run(void){u32 k,t,i,j,killed=0,failed;for(k=0;k<sizeof(cases)/sizeof(cases[0]);k++){active=cases+k;caseIndex=k;for(t=0;t<7;t++){
for(i=0;i<1280;i++)cache.bytes[i]=0xa5;for(i=0;i<8;i++){cache.f.ids[i]=0xa500+i;cache.f.handles[i]=(void*)(0x90000000u+i);}for(j=0;j<2;j++){for(i=0;i<384;i++)lists[j][i]=0xa5;for(i=0;i<8;i++)lists[j][i*48+4]=(u8)active->resources[j*8+i];}
D_800D2100=(u8)active->count;D_800D20FC=(struct258*)lists[0];callCount=bad=0;firstOutput=0;__asm__ volatile("":::"memory");tests[t]();__asm__ volatile("":::"memory");failed=bad||callCount!=active->calls||check(active->final);
if(!t&&failed)return 10;if(t&&failed)killed|=1u<<(t-1);
}}return killed==63?0:30;}
__attribute__((force_align_arg_pointer)) void _start(void){u32 status=run();if(status){u32 data[]={status,caseIndex};__asm__ volatile("int $0x80"::"a"(4),"b"(1),"c"(data),"d"(sizeof(data)):"memory");}__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''
    code=code.replace('ROWS',',\n'.join(rows)).replace('CANDIDATES','\n'.join(c.replace('void '+g.source.NAME,'__attribute__((noinline)) void candidate_'+str(i))for i,c in enumerate(candidates))).replace('TESTS',','.join('candidate_'+str(i)for i in range(7)))
    src=g.source.OUT/'native.c';src.write_text(code);reports=[]
    for opt in('-O0','-O2','-O3'):
        exe=g.source.OUT/('native'+opt);command=[*native_command(opt),'-o',str(exe),str(src)]
        assert all(flag in command for flag in('-m32',opt,'-fsanitize=undefined','-fsanitize-undefined-trap-on-error'))
        p=subprocess.run(command,cwd=g.source.ROOT,capture_output=True,text=True);(g.source.OUT/('native'+opt+'-diagnostics.txt')).write_text(p.stdout+p.stderr);assert p.returncode==0,p.stderr[-4000:]
        p=subprocess.run([str(exe)],capture_output=True);assert p.returncode==0,(opt,p.returncode,p.stdout.hex())
        reports.append(dict(optimization=opt,cases=len(rows),effective_controls=6,cache_bytes=1280,record_bytes=768,complete_loader_entry_snapshots=True,native_capacity=8,undefined_sanitizer=True,guest_aliases_or_full_count_range_claimed=False))
    (g.source.OUT/'native-report.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps(reports),flush=True)
if __name__=='__main__':main()
