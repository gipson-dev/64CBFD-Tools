"""Native32 typed C, defined descriptor bytes and exact public-object snapshots."""
from pathlib import Path
import importlib.util,json,subprocess,sys,time
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import game_inverse_motion_151a4638_oracle as g
O=g.O;R=g.R

def make_source():
 rows=[];array=lambda values:'{'+','.join(str(v)for v in values)+'}'
 for c in g.cases():
  initial=g.fixture(c);expected,calls,answer,ops=g.reference(initial,c);factory=next(v for v in calls if v[0]==g.FACTORY)
  scalar=(c.seed,c.flips,c.success,c.mutation,c.alias,c.sample,c.dt,factory[1][3],g.read(expected,g.DT),g.read(expected,g.MARK),*(g.integer(i,c)for i in range(3)),*g.inputs(c))
  images=[g.data(m,p,192)for m in(initial,expected)for p in(g.E,g.OUT)]
  rows.append('{'+','.join('0x%Xu'%g.u32(v)for v in scalar)+','+','.join(array(v)for v in images)+','+array(factory[2])+'}')
 types=g.source.PIN['declarations'];body=g.source.PIN['body']
 prefix='''#include <ultra64.h>
typedef struct {f32 x,y,z;} RingPosition151A361C;
s32 func_150ADA20(void);void *memcpy(void *,const void *,u32);
__attribute__((noreturn))static void quit(int c){__asm__ volatile(".byte 0xcd,0x80"::"a"(1),"b"(c):"memory");__builtin_unreachable();}
static void check(int v){if(!v)quit(3);}
static f32 number(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
static u32 bits(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
static u32 be32(const u8 *p){return(u32)p[0]<<24|(u32)p[1]<<16|(u32)p[2]<<8|p[3];}
'''+types+'''
typedef struct {u32 seed,flips,success,mutation,alias,sample,dt,slot,finalDT,mark,r0,r1,r2,x,y,z,vx,vy,vz;u8 ie[192],io[192],fe[192],fo[192],packet[112];} Row;
static const Row rows[]={
'''+',\n'.join(rows)+'''
};
static const Row *row;static u8 owner[192],output[192];static u32 ri,reals,factories,copies,mark;
f32 D_800A8D60,D_800BE9A8;
static void mutate(u32 target,u32 index){
 if(target==1&&index==0&&(row->mutation&1)){owner[12]^=0x55;D_800BE9A8=2.0f;}
 if(target==2&&(row->mutation&2)){owner[12]^=0xa6;D_800BE9A8=-.5f;}
 if(target==1&&index==1&&(row->mutation&4)){owner[12]^=0x81;D_800BE9A8=3.0f;}
 if(target==3){mark=0x13579bdf;if(row->mutation&16){owner[12]^=0x37;D_800BE9A8=-4.0f;}}
}
__attribute__((noinline,noclone))s32 func_150ADA20(void){u32 i=ri++;check(i<3);mutate(1,i);return(s32)(i==0?row->r0:i==1?row->r1:row->r2);}
__attribute__((noinline,noclone))f32 func_150ADA68(void){check(reals++==0);mutate(2,0);return number(row->sample);}
static int defined(u32 i){return !(i>=0x3c&&i<0x48)&&!(i>=0x5c&&i<0x60)&&!(i>=0x64&&i<0x70);}
static void comparePacket(const InverseMotionEffect151A4638 *p){
 static const u8 words[]={0,4,12,16,36,40,44,48,52,56,72,76,80,84,88};
 static const u8 shorts[]={8,10,30,32,34};const u8 *b=(const u8*)p;
 for(u32 f=0;f<sizeof(words);f++){u32 off=words[f],v=(u32)b[off]|(u32)b[off+1]<<8|(u32)b[off+2]<<16|(u32)b[off+3]<<24;check(v==be32(row->packet+off));}
 for(u32 f=0;f<sizeof(shorts);f++){u32 off=shorts[f];check(((u32)b[off]|(u32)b[off+1]<<8)==((u32)row->packet[off]<<8|row->packet[off+1]));}
 for(u32 i=0x14;i<0x1e;i++)check(b[i]==row->packet[i]);
 for(u32 i=0x60;i<0x64;i++)check(b[i]==row->packet[i]);
}
__attribute__((noinline,noclone))void *func_15130374(void *p,u8 mode,s32 bytes,u8 slot,s32 context){
 check(factories++==0&&mode==0&&bytes==12&&slot==row->slot&&context==1);comparePacket(p);
 if(row->mutation&8)for(u32 i=0;i<112;i++)if(defined(i))((u8*)p)[i]^=0x5a;
 mutate(3,0);return row->success?(row->alias?owner:output):(void*)0;
}
__attribute__((noinline,noclone))void *memcpy(void *destination,const void *source,u32 n){
 check(copies++==0&&n==12&&destination==(row->alias?owner:output)+0xa8);
 static const s16 params[]={16,15,13,19,17,-24};const u8 *s=source;u8 *d=destination;
 for(u32 i=0;i<6;i++)check(((u32)s[2*i]|(u32)s[2*i+1]<<8)==(u16)params[i]);
 for(u32 i=0;i<n;i++){d[i]=s[i];}return destination;
}
'''
 suffix='''
_Static_assert(sizeof(InverseMotionEffect151A4638)==112,"factory consumes full descriptor");
_Static_assert(__builtin_offsetof(InverseMotionEffect151A4638,position)==0x30&&__builtin_offsetof(InverseMotionEffect151A4638,velocity)==0x48&&__builtin_offsetof(InverseMotionEffect151A4638,flags)==0x58,"packet fields");
static void(*volatile invoke)(f32,f32,f32,f32,f32,f32,u8*)=func_151A4638;
static int run(void){for(u32 n=0;n<sizeof(rows)/sizeof(rows[0]);n++){
 row=&rows[n];for(u32 i=0;i<192;i++){owner[i]=row->ie[i];output[i]=row->io[i];}
 D_800A8D60=number(0x3db22d0eu);D_800BE9A8=number(row->dt);ri=reals=factories=copies=0;mark=0;
 invoke(number(row->x),number(row->y),number(row->z),number(row->vx),number(row->vy),number(row->vz),owner);
 check(ri==3&&reals==1&&factories==1&&copies==row->success&&mark==row->mark&&bits(D_800BE9A8)==row->finalDT);
 for(u32 i=0;i<192;i++){
  u32 j=(row->success&&row->alias&&i>=0xa8&&i<0xb4)?i^1:i;check(owner[j]==row->fe[i]);
  j=(row->success&&!row->alias&&i>=0xa8&&i<0xb4)?i^1:i;check(output[j]==row->fo[i]);
 }
 }return 0;}
'''
 return prefix,body,suffix,len(rows)

def main():
 prefix,body,suffix,count=make_source();variants={'selected':body,
 'counter-modulus':body.replace('% 5U','% 4U'),
 'random-flag':body.replace('flags |= 0x40','flags |= 0x20'),
 'owner-channel':body.replace('owner[0xC]','owner[0xD]'),
 'parameter-value':body.replace('parameters[5] = -24','parameters[5] = -23'),
 'factory-extent':body.replace('0, sizeof(parameters), owner','0, sizeof(parameters) - 2, owner'),
 'copy-destination':body.replace('created + 0xA8','created + 0xAC'),
 'inverse-x-component':body.replace('-vx * scale','-(vx + vy) * scale'),
 'last-sentinel':body.replace('packet.field63 = -1','packet.field63 = 0')}
 results=[];dest=O/'native-qualification';dest.mkdir(exist_ok=True)
 for label,fn in variants.items():
  assert label=='selected'or fn!=body,label
  for opt in(('-O0','-O2')if label=='selected'else('-O2',)):
   path=dest/('native-'+label+opt+'.c');exe=path.with_suffix('');path.write_text(prefix+fn+suffix+START);start=time.monotonic()
   q=subprocess.run(native_command(opt)+['-mstackrealign','-fstrict-aliasing',str(path),'-o',str(exe)],cwd=R,capture_output=True,text=True);assert q.returncode==0 and not q.stderr,(label,q.stdout,q.stderr)
   q=subprocess.run([str(exe)],capture_output=True,timeout=30);assert q.returncode==(0 if label=='selected'else 3),(label,opt,q.returncode)
   record=dict(label=label,opt=opt,exit_code=q.returncode,seconds=round(time.monotonic()-start,3));results.append(record);print(json.dumps(record),flush=True)
 report=dict(cases_per_profile=count,runs=results,defined_descriptor_bytes=84,unobserved_unmutated_indeterminate_bytes=28,native32=True,strict_aliasing=True,UB_traps=True,complete_public_objects=True,successful_typed_payload_endian_conversion_only=True,source_installed=False,c_match_credit=0)
 (O/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=count,runs=len(results),passes=True)),flush=True);return report
if __name__=='__main__':main()
