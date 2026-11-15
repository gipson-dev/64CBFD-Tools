"""GNU native32 payload tables: all public bytes, opaque effects and controls."""
import ast,hashlib,json,re,shutil,struct,subprocess,sys
from pathlib import Path
from tools.tests import game_record_payload_tables_15017114_oracle as g
from tools.tests import game_record_initializer_150169a0_native as sha_provider
from tools.tests.test_game_projected_packet_draw import native_command

def fingerprints():
    paths=dict(candidate=Path(g.source.__file__),oracle=Path(g.__file__),native=Path(__file__),sha_provider=Path(sha_provider.__file__),reader=Path(sys.modules[g.read.__module__].__file__),writer=Path(sys.modules[g.put.__module__].__file__),compiler=Path(shutil.which('cc')).resolve())
    return{k:hashlib.sha256(p.read_bytes()).hexdigest()for k,p in paths.items()}
def command(opt):return[*native_command(opt),'-fno-tree-loop-distribute-patterns']
def verify_receipt():
    rows=json.loads((g.source.OUT/'native-report.json').read_text());assert len(rows)==3;inputs=fingerprints()
    for opt,r in zip(('-O0','-O2','-O3'),rows):
        if r['input_fingerprints']!=inputs:raise ValueError('Payload native inputs changed')
        if r['command_profile']!=command(opt):raise ValueError('Payload native profile changed')
        for name,key in(('native.c','generated_c_sha256'),('native'+opt,'executable_sha256')):
            if hashlib.sha256((g.source.OUT/name).read_bytes()).hexdigest()!=r[key]:raise ValueError('Payload native artifact changed')
        if(r['cases'],r['effective_controls'],r['public_bytes'])!=(380,6,21025):raise ValueError('Payload native scope changed')
    return rows

def main():
    arr=lambda xs:'{'+','.join('0x%Xu'%(n&0xffffffff)for n in xs)+'}'
    digest=lambda value:arr(struct.unpack('>8I',bytes.fromhex(value)))
    rows=[]
    for c in g.corpus():
        if c.alias or c.phase:continue
        initial=g.fixture(c);want,calls,observations=g.reference(initial,c);addresses=tuple(sorted(g.public(initial)))
        assert len(addresses)==21025 and len(calls)<=259,(c,len(addresses),len(calls))
        events=[]
        for(target,args),snap in zip(calls,observations):events.append('{0x%Xu,%d,%s,%s}'%(target,len(args),arr(args),digest(snap)))
        fields=(c.n,c.original,c.players,c.success,int(c.write_output),c.mode,c.alias,c.phase,c.category,c.seed)
        rows.append('{%s,%d,%s,{%s}}'%(arr(fields),len(events),digest(g.snapshot(want,addresses)),','.join(events)))
    function=g.source.SELECTED[g.source.SELECTED.index('/* Initialize'):]
    controls=(function.replace('metadata = 0;','metadata = (u8 *)1;'),
              function.replace('allocate_memory(count, 1, 0, 0)','allocate_memory(D_800D2100, 1, 0, 0)'),
              function.replace('allocate_memory(16, 1, 2, 0)','allocate_memory(16, 1, 0, 0)'),
              function.replace('D_800D2104[index] = metadata +','D_800D2104[index] = (u8 *)'),
              function.replace('].status;','].offset;'),
              function.replace('index = D_800D2101;','index = D_800D2101 + 2;'))
    assert all(v!=function for v in controls)
    tree=ast.parse(Path(sha_provider.__file__).read_text())
    template=next(n.value.value for n in ast.walk(tree)if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='code'for t in n.targets)and isinstance(n.value,ast.Constant)and isinstance(n.value.value,str))
    sha=template[template.index('struct SHA{'):template.index('static u32 recByte(')]
    code=r'''
#include <ultra64.h>
typedef struct {u32 offset,status;} RecordPayloadMetadata15017114;
struct Globals {u8 count,original,pad2[2];u8 **ptrs;u8 *status;u8 padC[4];};
typedef char GlobalLayout[sizeof(struct Globals)==16&&__builtin_offsetof(struct Globals,ptrs)==4&&__builtin_offsetof(struct Globals,status)==8?1:-1];
static struct Globals globals;static s8 players;
#define D_800D2100 globals.count
#define D_800D2101 globals.original
#define D_800D2104 globals.ptrs
#define D_800D2108 globals.status
#define D_8008FD8C players
static u8 *pointers[2][256];static u8 flags[2][256],buffers[128][16],marker[16];static RecordPayloadMetadata15017114 arenas[2][1024];
static void **exposedOutput;
struct Event {u32 target,n,args[4],hash[8];};struct Input {u32 p[10],calls,hash[8];struct Event events[259];};
static const struct Input cases[]={ROWS};static const struct Input *active;static u32 ordinals[3],callIndex,bad,caseIndex;
static u32 load32(const void*p){u32 v;__builtin_memcpy(&v,p,4);return v;}static void store32(void*p,u32 v){__builtin_memcpy(p,&v,4);}
static u32 be32(const u8*p){return(u32)p[0]<<24|(u32)p[1]<<16|(u32)p[2]<<8|p[3];}static void putbe(u8*p,u32 v){p[0]=v>>24;p[1]=v>>16;p[2]=v>>8;p[3]=v;}
static u32 guestAddress(const void*p){u32 a=(u32)p,b,j;for(j=0;j<2;j++){b=(u32)pointers[j];if(a>=b&&a<b+1024)return(j?0x32000:0x30000)+a-b;b=(u32)flags[j];if(a>=b&&a<b+256)return(j?0x35000:0x34000)+a-b;b=(u32)arenas[j];if(a>=b&&a<b+8192)return(j?0x44000:0x38000)+a-b;}b=(u32)buffers;if(a>=b&&a<b+2048)return 0x50000+a-b;if(exposedOutput&&p==exposedOutput)return OUTPUT;return a;}
SHA
static u32 checkHash(const u32*want){struct SHA s;u32 i,j;shaInit(&s);for(j=0;j<2;j++)for(i=0;i<256;i++)shaWord(&s,guestAddress(pointers[j][i]));for(j=0;j<2;j++)for(i=0;i<256;i++)shaByte(&s,flags[j][i]);for(j=0;j<2;j++)for(i=0;i<2048;i++)shaWord(&s,load32((u8*)arenas[j]+i*4));for(i=0;i<2048;i++)shaByte(&s,((u8*)buffers)[i]);for(i=0;i<16;i++)shaByte(&s,marker[i]);shaByte(&s,(u8)players);shaByte(&s,globals.count);shaByte(&s,globals.original);shaByte(&s,globals.pad2[0]);shaByte(&s,globals.pad2[1]);shaWord(&s,guestAddress(globals.ptrs));shaWord(&s,guestAddress(globals.status));for(i=0;i<4;i++)shaByte(&s,globals.padC[i]);shaEnd(&s);for(i=0;i<8;i++)if(s.h[i]!=want[i])return 1;return 0;}
static u32 observe(u32 slot,u32 target,u32 n,u32 a,u32 b,u32 c,u32 d){u32 i,args[]={a,b,c,d};const struct Event *e;__asm__ volatile("":::"memory");if(callIndex>=active->calls)bad=1;else{e=active->events+callIndex;if(e->target!=target||e->n!=n)bad=1;for(i=0;i<n;i++)if(e->args[i]!=args[i])bad=1;if(checkHash(e->hash))bad=1;}callIndex++;return++ordinals[slot];}
static void mark(u32 t,u32 n){putbe(marker,t);putbe(marker+4,n);__asm__ volatile("":::"memory");}
__attribute__((noinline)) void *allocate_memory(s32 size,s32 mode,s32 pool,s32 extra){u32 n=observe(0,0x10003c40,4,(u32)size,(u32)mode,(u32)pool,(u32)extra);void *result=n==1?(void*)pointers[0]:n==2?(void*)flags[0]:(void*)buffers[n-3];if((active->p[5]&1)&&n==1)globals.count=3;if((active->p[5]&4)&&n>=2)globals.ptrs=pointers[n&1];mark(0x10003c40,n);return result;}
__attribute__((noinline)) void bzero(void*dst,int size){u32 i,n=observe(1,0x100226f0,2,guestAddress(dst),(u32)size,0,0);for(i=0;i<(u32)size;i++)((u8*)dst)[i]=0;if(active->p[5]&2){if(n==2)players=3;else if(n==3)players=2;}if((active->p[5]&4)&&n>=3){globals.ptrs=pointers[n&1];globals.status=flags[n&1];}mark(0x100226f0,n);}
__attribute__((noinline)) u32 func_1502B7F0(void **output,u32 depth,...){__builtin_va_list ap;u32 key,category,n;exposedOutput=output;if(*output!=0)bad=1;__builtin_va_start(ap,depth);key=(u32)__builtin_va_arg(ap,int);category=(u32)__builtin_va_arg(ap,s32);__builtin_va_end(ap);n=observe(2,0x1502b7f0,4,guestAddress(output),depth,key,category);if(active->p[4])*output=arenas[active->p[9]&1]+512;if(active->p[5]&8){globals.count=6;globals.original=1;}mark(0x1502b7f0,n);return active->p[3];}
CANDIDATES
static void(*tests[])(s32)={TESTS};
static void fill(void*p,u32 size){u32 i;for(i=0;i<size;i++)((u8*)p)[i]=(u8)(i*29+active->p[9]*11+0x5a);}
static void initialize(void){u32 i,j,v;s32 k;u8*p;fill(&globals,16);fill(marker,16);fill(buffers,2048);for(j=0;j<2;j++){fill(pointers[j],1024);for(i=0;i<256;i++){v=be32((u8*)pointers[j]+i*4);store32(pointers[j]+i,v);}fill(flags[j],256);fill(arenas[j],8192);for(i=0;i<2048;i++){p=(u8*)arenas[j]+i*4;v=be32(p);store32(p,v);}for(k=-256;k<256;k++){arenas[j][k+512].offset=((k%3+3)%3)==0?0:32+((k%5+5)%5)*16;arenas[j][k+512].status=(u32)(k*7+0x102);}}globals.count=(u8)active->p[0];globals.original=(u8)active->p[1];globals.ptrs=(u8**)0xdeadbeef;globals.status=(u8*)0xa5a5a5a5;players=(s8)active->p[2];for(i=0;i<3;i++)ordinals[i]=0;exposedOutput=0;callIndex=bad=0;__asm__ volatile("":::"memory");}
SELFTEST
static u32 run(void){u32 k,t,killed=0,failed;if(shaSelf()||guestAddress((void*)0)!=0)return 40;for(k=0;k<sizeof(cases)/sizeof(cases[0]);k++){caseIndex=k;active=cases+k;for(t=0;t<7;t++){initialize();tests[t]((s32)active->p[8]);__asm__ volatile("":::"memory");failed=bad||callIndex!=active->calls;if(!failed)failed=checkHash(active->hash);if(!t&&failed)return 10;if(t&&failed)killed|=1u<<(t-1);}}return killed==63?0:30;}
__attribute__((force_align_arg_pointer)) void _start(void){u32 status=run();if(status){u32 data[]={status,caseIndex,callIndex,bad};__asm__ volatile("int $0x80"::"a"(4),"b"(1),"c"(data),"d"(sizeof(data)):"memory");}__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''
    selftest='static u32 shaSelf(void){struct SHA s;u32 i;const u32 empty[8]='+digest(hashlib.sha256(b'').hexdigest())+',abc[8]='+digest(hashlib.sha256(b'abc').hexdigest())+';shaInit(&s);shaEnd(&s);for(i=0;i<8;i++)if(s.h[i]!=empty[i])return 40;shaInit(&s);shaByte(&s,97);shaByte(&s,98);shaByte(&s,99);shaEnd(&s);for(i=0;i<8;i++)if(s.h[i]!=abc[i])return 41;return 0;}'
    bodies=(function,*controls)
    code=code.replace('ROWS',',\n'.join(rows)).replace('OUTPUT','0x%Xu'%((g.STACK-8)&0xffffffff)).replace('SHA\n',sha+'\n').replace('SELFTEST',selftest).replace('CANDIDATES','\n'.join(body.replace('void '+g.source.NAME+'(','__attribute__((noinline)) void candidate_'+str(i)+'(')for i,body in enumerate(bodies))).replace('TESTS',','.join('candidate_'+str(i)for i in range(7)))
    path=g.source.OUT/'native.c';path.write_text(code);reports=[]
    for opt in('-O0','-O2','-O3'):
        exe=g.source.OUT/('native'+opt);argv=[*command(opt),'-o',str(exe),str(path)]
        assert all(v in argv for v in('-m32',opt,'-fsanitize=undefined','-fsanitize-undefined-trap-on-error'))
        q=subprocess.run(argv,cwd=g.source.ROOT,capture_output=True,text=True);(g.source.OUT/('native'+opt+'-diagnostics.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,q.stderr[-5000:]
        q=subprocess.run([str(exe)],capture_output=True);assert q.returncode==0,(opt,q.returncode,q.stdout.hex())
        r=dict(optimization=opt,cases=len(rows),effective_controls=6,public_bytes=21025,helper_packets_and_public_snapshots=True,undefined_traps=True,sha256_known_vectors=2,player_capacity=128,record_capacity=256,metadata_backing_records=1024,guest_aliases_not_native=True,input_fingerprints=fingerprints(),command_profile=command(opt),generated_c_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),executable_sha256=hashlib.sha256(exe.read_bytes()).hexdigest())
        reports.append(r);print(json.dumps(r),flush=True)
    (g.source.OUT/'native-report.json').write_text(json.dumps(reports,indent=2)+'\n')
if __name__=='__main__':main()
