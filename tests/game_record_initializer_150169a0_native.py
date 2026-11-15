"""Bounded GNU native32 initializer, complete public-state hashes and controls."""
import hashlib,json,re,shutil,struct,subprocess,sys
from pathlib import Path
from tools.tests import game_record_initializer_150169a0_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command

def fingerprint_inputs():
    paths=dict(candidate=Path(g.source.__file__),oracle=Path(g.__file__),native=Path(__file__),reader=Path(sys.modules[g.read.__module__].__file__),writer=Path(sys.modules[g.put.__module__].__file__),compiler=Path(shutil.which('cc')).resolve())
    return {name:hashlib.sha256(path.read_bytes()).hexdigest()for name,path in paths.items()}

def verify_receipt():
    rows=json.loads((g.source.OUT/'native-report.json').read_text());inputs=fingerprint_inputs()
    assert len(rows)==3
    for opt,r in zip(('-O0','-O2','-O3'),rows):
        if r.get('input_fingerprints')!=inputs:raise ValueError('Native fixture inputs changed')
        profile=[*native_command(opt),'-fsanitize=float-cast-overflow','-fno-tree-loop-distribute-patterns']
        if r.get('command_profile')!=profile:raise ValueError('Native compiler profile changed')
        for file,key in(('native.c','generated_c_sha256'),('native'+opt,'executable_sha256')):
            if hashlib.sha256((g.source.OUT/file).read_bytes()).hexdigest()!=r.get(key):raise ValueError('Native artifact changed: '+file)
        if(r['optimization'],r['cases'],r['effective_controls'],r['public_bytes'])!=(opt,639,7,29090):raise ValueError('Native result scope changed')
    return rows

def main():
    arr=lambda xs:'{'+','.join('0x%Xu'%(v&0xffffffff)for v in xs)+'}'
    digest=lambda s:arr(struct.unpack('>8I',bytes.fromhex(s)))
    rows=[]
    for c in g.corpus():
        if c.phase or c.players>26:continue
        initial=g.fixture(c);want,calls,observations=g.reference(initial,c)
        assert len(calls)<=64
        events=[]
        for (target,args),h in zip(calls,observations):
            events.append('{'+','.join((hex(target)+'u',str(len(args)),arr(list(args)+[0]*(5-len(args))),digest(h)))+'}')
        params=(c.category,c.selected,c.players,c.mask,c.split,c.scene,c.added,c.mode,c.phase,c.seed)
        rows.append('{'+','.join((arr(params),str(len(calls)),digest(g.snapshot(want,tuple(sorted(g.public(want))))),'{'+','.join(events)+'}'))+'}')
    selected=g.source.SELECTED;at=selected.index('void '+g.source.NAME+'(');prefix,function=selected[:at],selected[at:]
    cached_actor=function.replace('s32 selected = func_150859AC((s16)slot, 1);','f32 cachedX = D_800CC2D0[slot].x_position;\n        s32 selected = func_150859AC((s16)slot, 1);').replace('(s16)(s32)D_800CC2D0[slot].x_position','(s16)(s32)cachedX')
    old='if (RECORD150169A0(identityIndex * 48).identity == 0)\n            RECORD150169A0(identityIndex * 48).identity = func_15083DA0();'
    new='if (RECORD150169A0(identityIndex * 48).identity == 0) {\n            Record150169A0 *cached = &RECORD150169A0(identityIndex * 48);\n            cached->identity = func_15083DA0();\n        }'
    assert old in function
    bodies=(function,function.replace('case 0x1A: case 0x24:','case 0x24:'),function.replace('D_800D2101 = D_800D2100;','D_800D2101 = 0;'),function.replace('bytes = count * 2;','bytes = D_800D2100 * 2;'),cached_actor,function.replace(old,new),function.replace('0.7f','0.6f'),function.replace('.disabled = 0;','.disabled = 1;'))
    assert all(b!=function for b in bodies[1:])
    code=r'''
#include <ultra64.h>
#include "structs.h"
PREFIX
u8 D_800D2100,D_800D2101;struct258 *D_800D20FC;u8 *D_800D210C;s16 *D_800D2110;
s32 D_800D1548,D_800BE9F0;s8 D_8008FD8C,D_8008FD90;u16 D_800D2340;struct127 D_800CC2D0[26];
static Record150169A0 records[2][64],romRecords[21];static u8 byteBuffer[256],halfBuffer[512] __attribute__((aligned(4))),marker[32];
__asm__(".globl D_1A33F0\n.set D_1A33F0,romRecords\n.globl D_1A34E0\n.set D_1A34E0,romRecords+240\n.globl D_1A37E0\n.set D_1A37E0,romRecords+1008\n");
typedef char ActorLayout[sizeof(struct127)==812&&__builtin_offsetof(struct127,x_position)==20&&__builtin_offsetof(struct127,unk76)==118?1:-1];
struct Event{u32 target,n,args[5],hash[8];};struct Input{u32 p[10],calls,hash[8];struct Event events[64];};
static const struct Input cases[]={ROWS};static const struct Input *active;static u32 ordinal[12],callIndex,bad,caseIndex;
static const u32 targets[]={0x15004f30,0x1502b9b4,0x10003c40,0x10004514,0x1502b8e0,0x15017114,0x100226f0,0x150859ac,0x15016850,0x15083da0,0x1508295c,0x15172ca8};
static u32 load32(const void*p){u32 v;__builtin_memcpy(&v,p,4);return v;}static u32 load16(const void*p){u16 v;__builtin_memcpy(&v,p,2);return v;}
static void store32(void*p,u32 v){__builtin_memcpy(p,&v,4);}static void store16(void*p,u32 v){u16 h=(u16)v;__builtin_memcpy(p,&h,2);}
static u32 be32(const u8*p){return(u32)p[0]<<24|(u32)p[1]<<16|(u32)p[2]<<8|p[3];}static void putbe(u8*p,u32 v){p[0]=v>>24;p[1]=v>>16;p[2]=v>>8;p[3]=v;}
static void fixRecords(u8*p,u32 n){u32 i,j,v;for(i=0;i<n;i++,p+=48){for(j=6;j<12;j+=2){v=(u32)p[j]<<8|p[j+1];store16(p+j,v);}for(j=24;j<=36;j+=4)if(j!=28){v=be32(p+j);store32(p+j,v);}}}
static u32 guestAddress(const void*p){u32 a=(u32)p,b=(u32)records[0];if(a>=b&&a<b+3072)return 0x30000+a-b;b=(u32)records[1];if(a>=b&&a<b+3072)return 0x60000+a-b;b=(u32)romRecords;if(a>=b&&a<b+1008)return 0x1a33f0+a-b;if(p==byteBuffer)return 0x50000;if(p==halfBuffer)return 0x51000;return a;}
struct SHA{u32 h[8],bytes,used;u8 block[64];};
static u32 rr(u32 x,u32 n){return x>>n|x<<(32-n);}
static void shaBlock(struct SHA*s){
static const u32 k[]={0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
u32 w[64],a,b,c,d,e,f,g,h,i,t1,t2;for(i=0;i<16;i++)w[i]=be32(s->block+4*i);for(;i<64;i++)w[i]=w[i-16]+(rr(w[i-15],7)^rr(w[i-15],18)^(w[i-15]>>3))+w[i-7]+(rr(w[i-2],17)^rr(w[i-2],19)^(w[i-2]>>10));
a=s->h[0];b=s->h[1];c=s->h[2];d=s->h[3];e=s->h[4];f=s->h[5];g=s->h[6];h=s->h[7];for(i=0;i<64;i++){t1=h+(rr(e,6)^rr(e,11)^rr(e,25))+((e&f)^(~e&g))+k[i]+w[i];t2=(rr(a,2)^rr(a,13)^rr(a,22))+((a&b)^(a&c)^(b&c));h=g;g=f;f=e;e=d+t1;d=c;c=b;b=a;a=t1+t2;}s->h[0]+=a;s->h[1]+=b;s->h[2]+=c;s->h[3]+=d;s->h[4]+=e;s->h[5]+=f;s->h[6]+=g;s->h[7]+=h;}
static void shaInit(struct SHA*s){static const u32 init[]={0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};u32 i;for(i=0;i<8;i++)s->h[i]=init[i];s->bytes=s->used=0;}
static void shaByte(struct SHA*s,u32 b){s->block[s->used++]=(u8)b;s->bytes++;if(s->used==64){shaBlock(s);s->used=0;}}
static void shaWord(struct SHA*s,u32 w){shaByte(s,w>>24);shaByte(s,w>>16);shaByte(s,w>>8);shaByte(s,w);}
static void shaEnd(struct SHA*s){u32 bits=s->bytes*8;shaByte(s,128);while(s->used!=56)shaByte(s,0);shaWord(s,0);shaWord(s,bits);}
static u32 recByte(const u8*p,u32 i){u32 j=i%48,b=i-j;if(j>=6&&j<12){u32 k=j&~1u;return load16(p+b+k)>>((1-(j&1))*8)&255;}if((j>=24&&j<28)||(j>=32&&j<40))return load32(p+b+(j&~3u))>>((3-(j&3))*8)&255;return p[i];}
static u32 actorByte(u32 i){const u8*p=(const u8*)D_800CC2D0;u32 j=i%812,b=i-j;if(j>=20&&j<32)return load32(p+b+(j&~3u))>>((3-(j&3))*8)&255;if(j>=118&&j<120)return load16(p+b+118)>>((119-j)*8)&255;return p[i];}
static u32 checkHash(const u32*want){struct SHA s;u32 i;shaInit(&s);for(i=0;i<3072;i++)shaByte(&s,recByte((u8*)records[0],i));for(i=0;i<256;i++)shaByte(&s,byteBuffer[i]);for(i=0;i<512;i++)shaByte(&s,halfBuffer[i]);for(i=0;i<3072;i++)shaByte(&s,recByte((u8*)records[1],i));for(i=0;i<32;i++)shaByte(&s,marker[i]);for(i=0;i<1008;i++)shaByte(&s,recByte((u8*)romRecords,i));shaByte(&s,(u8)D_8008FD8C);shaByte(&s,(u8)D_8008FD90);shaWord(&s,(u32)D_800BE9F0);for(i=0;i<26*812;i++)shaByte(&s,actorByte(i));shaWord(&s,(u32)D_800D1548);shaWord(&s,guestAddress(D_800D20FC));shaByte(&s,D_800D2100);shaByte(&s,D_800D2101);shaWord(&s,guestAddress(D_800D210C));shaWord(&s,guestAddress(D_800D2110));shaByte(&s,D_800D2340>>8);shaByte(&s,D_800D2340);shaEnd(&s);for(i=0;i<8;i++)if(s.h[i]!=want[i])return 1;return 0;}
static u32 observe(u32 t,u32 n,u32 a,u32 b,u32 c,u32 d,u32 e){u32 i,args[]={a,b,c,d,e};const struct Event*event;__asm__ volatile("":::"memory");if(!bad){if(callIndex>=active->calls)bad=1;else{event=active->events+callIndex;if(event->target!=targets[t]||event->n!=n)bad=1;for(i=0;i<n;i++)if(event->args[i]!=args[i])bad=1;if(checkHash(event->hash))bad=1;}}callIndex++;return ++ordinal[t];}
static void mark(u32 t,u32 n){putbe(marker,targets[t]);putbe(marker+4,n);__asm__ volatile("":::"memory");}
void func_15004F30(void){u32 n=observe(0,0,0,0,0,0,0);mark(0,n);}
u32 func_1502B9B4(u32 depth,...){__builtin_va_list ap;u32 key,n;__builtin_va_start(ap,depth);key=__builtin_va_arg(ap,u32);__builtin_va_end(ap);n=observe(1,2,depth,key,0,0,0);mark(1,n);return active->p[6]*48;}
void *allocate_memory(s32 size,s32 mode,s32 pool,s32 flags){u32 n=observe(2,4,(u32)size,(u32)mode,(u32)pool,(u32)flags,0);void*p=n==1?(void*)records[0]:n==2?(void*)byteBuffer:(void*)halfBuffer;if(active->p[7]&16&&n==2)D_800D2100=2;mark(2,n);return p;}
s32 func_10004514(s32 address,void*dst,u32 size,s32 mode){u32 i,n=observe(3,4,guestAddress((void*)address),guestAddress(dst),size,(u32)mode,0);for(i=0;i<size;i++)((u8*)dst)[i]=((u8*)address)[i];mark(3,n);return(s32)(0x98760000+n);}
u32 func_1502B8E0(void*dst,u32 cap,u32 depth,...){__builtin_va_list ap;u32 key,category,i,n;__builtin_va_start(ap,depth);key=__builtin_va_arg(ap,u32);category=__builtin_va_arg(ap,u32);__builtin_va_end(ap);n=observe(4,5,guestAddress(dst),cap,depth,key,category);for(i=0;i<active->p[6]*48;i++)((u8*)dst)[i]=(u8)(i*7+0x31);for(i=0;i<active->p[6];i++)((u8*)dst)[i*48+40]=0;fixRecords(dst,active->p[6]);mark(4,n);return active->p[6]*48;}
s32 func_15017114(s32 category){u32 n=observe(5,1,(u32)category,0,0,0,0);if(active->p[7]&1)D_800D2100=3;if(active->p[7]&32)D_800D2100=0;mark(5,n);return(s32)(0x98760000+n);}
void bzero(void*dst,int size){u32 i,n=observe(6,2,guestAddress(dst),(u32)size,0,0,0);for(i=0;i<(u32)size;i++)((u8*)dst)[i]=0;mark(6,n);}
s32 func_150859AC(s16 slot,s16 field){u32 n=observe(7,2,(u32)(s32)slot,(u32)(s32)field,0,0,0);if(active->p[7]&2){D_800D20FC=(struct258*)records[n&1];D_800CC2D0[(u16)slot].x_position=-10.0f;}mark(7,n);return(s32)active->p[1];}
void func_15016850(void){u32 n=observe(8,0,0,0,0,0,0);if(active->p[7]&4){D_800D20FC=(struct258*)records[1];D_800D2100=3;}if(active->p[7]&64)D_800D2100=0;mark(8,n);}
s32 func_15083DA0(void){u32 n=observe(9,0,0,0,0,0,0);if(active->p[7]&8){D_800D20FC=(struct258*)records[n&1];D_800D2100=2;}mark(9,n);return(s32)((n*17+3)&255);}
s32 func_1508295C(s32 category,u8*mode,s32 enabled){u32 n=observe(10,3,(u32)category,(u32)mode,(u32)enabled,0,0);mark(10,n);return(s32)(0x98760000+n);}
void func_15172CA8(s32 mode){u32 n=observe(11,1,(u32)mode,0,0,0,0);mark(11,n);}
CANDIDATES
static void(*tests[])(s32)={TESTS};
static void initialize(void){u32 i,j;u8*p;for(j=0;j<2;j++){p=(u8*)records[j];for(i=0;i<3072;i++)p[i]=(u8)(i*29+active->p[9]*11+0x5a);for(i=0;i<64;i++)p[i*48+40]=0;fixRecords(p,64);}for(i=0;i<256;i++)byteBuffer[i]=(u8)(i*29+active->p[9]*11+0x5a);for(i=0;i<512;i++)halfBuffer[i]=(u8)(i*29+active->p[9]*11+0x5a);for(i=0;i<32;i++)marker[i]=(u8)(i*29+active->p[9]*11+0x5a);p=(u8*)romRecords;for(i=0;i<1008;i++)p[i]=(u8)(i*29+active->p[9]*11+0x5a);for(i=0;i<5;i++)p[i*48+40]=(active->p[9]&1)&&(i&1)?i+1:0;for(i=0;i<16;i++)p[240+i*48+40]=(active->p[9]&1)&&(i&1)?i+1:0;fixRecords(p,21);p=(u8*)D_800CC2D0;for(i=0;i<26*812;i++)p[i]=(u8)(i*29+active->p[9]*11+0x5a);for(i=0;i<26;i++){D_800CC2D0[i].x_position=(f32)i*1.25f-32769.75f;D_800CC2D0[i].y_position=-(f32)i*3.5f+100.75f;D_800CC2D0[i].z_position=65537.75f-(f32)i;D_800CC2D0[i].unk76=(u16)(0x8000+i*0x321);}D_800D20FC=(struct258*)records[0];D_800D2100=0xa5;D_800D2101=0xa6;D_800D210C=(u8*)0xdeadbeef;D_800D2110=(s16*)0xa5a5a5a5;D_8008FD8C=(s8)active->p[2];D_8008FD90=(s8)active->p[4];D_800D2340=(u16)active->p[3];D_800BE9F0=(s32)active->p[5];D_800D1548=(s32)0x87654321;for(i=0;i<12;i++)ordinal[i]=0;callIndex=bad=0;__asm__ volatile("":::"memory");}
static u32 run(void){u32 k,t,killed=0,failed;for(k=0;k<sizeof(cases)/sizeof(cases[0]);k++){caseIndex=k;active=cases+k;for(t=0;t<8;t++){initialize();tests[t]((s32)active->p[0]);__asm__ volatile("":::"memory");failed=bad||callIndex!=active->calls;if(!failed)failed=checkHash(active->hash);if(!t&&failed)return 10;if(t&&failed)killed|=1u<<(t-1);}}return killed==127?0:30;}
__attribute__((force_align_arg_pointer)) void _start(void){u32 status=run();if(status){u32 data[]={status,caseIndex,callIndex,bad};__asm__ volatile("int $0x80"::"a"(4),"b"(1),"c"(data),"d"(sizeof(data)):"memory");}__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''
    selftest='static u32 shaSelf(void){struct SHA s;u32 i;const u32 empty[8]='+digest(hashlib.sha256(b'').hexdigest())+',abc[8]='+digest(hashlib.sha256(b'abc').hexdigest())+';shaInit(&s);shaEnd(&s);for(i=0;i<8;i++)if(s.h[i]!=empty[i])return 40;shaInit(&s);shaByte(&s,97);shaByte(&s,98);shaByte(&s,99);shaEnd(&s);for(i=0;i<8;i++)if(s.h[i]!=abc[i])return 41;return 0;}\n'
    code=code.replace('static u32 run(void){u32 k,t,killed=0,failed;','static u32 run(void){u32 k,t,killed=0,failed;if(shaSelf())return 40;')
    code=code.replace('CANDIDATES',selftest+'CANDIDATES')
    code=re.sub(r'^(void|u32|s32|void \*)\s*(func_[A-Za-z0-9]+|allocate_memory|bzero)(\([^\n;]*\)\{)',r'__attribute__((noinline)) \1 \2\3',code,flags=re.M)
    code=code.replace('PREFIX',prefix).replace('ROWS',',\n'.join(rows)).replace('CANDIDATES','\n'.join(b.replace('void '+g.source.NAME+'(','__attribute__((noinline)) void candidate_'+str(i)+'(')for i,b in enumerate(bodies))).replace('TESTS',','.join('candidate_'+str(i)for i in range(8)))
    path=g.source.OUT/'native.c';path.write_text(code);reports=[]
    for opt in('-O0','-O2','-O3'):
        exe=g.source.OUT/('native'+opt);command=[*native_command(opt),'-fsanitize=float-cast-overflow','-fno-tree-loop-distribute-patterns','-o',str(exe),str(path)]
        assert all(flag in command for flag in('-m32',opt,'-fsanitize=undefined','-fsanitize-undefined-trap-on-error','-fsanitize=float-cast-overflow'))
        p=subprocess.run(command,cwd=g.source.ROOT,capture_output=True,text=True);(g.source.OUT/('native'+opt+'-diagnostics.txt')).write_text(p.stdout+p.stderr);assert p.returncode==0,p.stderr[-4000:]
        p=subprocess.run([str(exe)],capture_output=True);assert p.returncode==0,(opt,p.returncode,p.stdout.hex())
        r=dict(optimization=opt,cases=len(rows),effective_controls=7,record_bytes=6144,actor_bytes=26*812,rom_bytes=1008,other_buffer_bytes=800,public_bytes=29090,public_state_sha256=True,helper_entry_packets=True,native_player_capacity=26,undefined_and_float_cast_traps=True,sha256_known_vectors=2,gnu_linker_alias_views=True,guest_alias_or_full_fault_claimed=False,input_fingerprints=fingerprint_inputs(),command_profile=command[:command.index('-o')],generated_c_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),executable_sha256=hashlib.sha256(exe.read_bytes()).hexdigest())
        reports.append(r);print(json.dumps(r),flush=True)
    (g.source.OUT/'native-report.json').write_text(json.dumps(reports,indent=2)+'\n')

if __name__=='__main__':main()
