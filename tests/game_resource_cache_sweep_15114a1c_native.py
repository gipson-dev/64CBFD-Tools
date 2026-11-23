"""Defined SDK32 typed arrays; independently generated results and source controls."""
import json,subprocess
from tools.experiments import game_resource_cache_sweep_15114a1c_match as p
from tools.tests import game_resource_cache_sweep_15114a1c_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r,o=p.ROOT,p.OUT
def mix(h,v):return((h^(v&0xffffffff))*16777619)&0xffffffff
def digest(m):
 h=2166136261
 for name in('D_800DBEF0','D_800DBEF4','D_800DBEF8','D_800DBEFC'):h=mix(h,g.read(m,g.S[name]))
 for bank in range(2):
  for base,n in((g.RECORDS[bank],1280),(g.AGES[bank],8)):
   for i in range(-16,n+16):h=mix(h,m[base+i])
  for base in(g.TABLES[bank],g.RESOURCES[bank]):
   for i in range(-16,0):h=mix(h,m[base+i])
   for i in range(8):h=mix(h,g.read(m,base+4*i))
   for i in range(32,48):h=mix(h,m[base+i])
 return h
def vectors():
 rows=[]
 for c in g.cases():
  m,calls=g.reference(g.fixture(c),c);h=2166136261
  for t,a in calls:h=mix(mix(h,t),a[0])
  rows.append('{'+','.join(str(v&0xffffffff)+'u'for v in(c.seed,c.count,c.mutation,digest(m),h,len(calls)))+'}')
 (o/'native-vectors.h').write_text('static const Vector vectors[]={\n'+',\n'.join(rows)+'\n};\n');return len(rows)
def program():
 body=p.MANIFEST['body'].replace('func_15114A1C(','subject(')
 return '#include <ultra64.h>\n'+r'''
typedef struct {u32 seed,count,mutation,digest,events,calls;} Vector;
typedef struct {u8 pre[16];void *entry[8];u8 post[16];} Table;
typedef struct {u8 pre[16];u32 entry[8];u8 post[16];} Resources;
_Static_assert(sizeof(void*)==4&&sizeof(long)==4&&sizeof(Table)==64&&sizeof(Resources)==64,"SDK32 arrays");
_Static_assert((s32)0xffffffffu==-1,"SDK32 signed integers");
#include "native-vectors.h"
static u8 records[2][1312],ages[2][40];static Table tables[2];static Resources resources[2];
static const Vector *v;static u32 count,eventHash;static int invalid;
s32 D_800DBEF0;u8 *D_800DBEF4,*D_800DBEFC;void **D_800DBEF8;
static u32 mix(u32 h,u32 x){return(h^x)*16777619u;}
static u32 pointer(void *p){u32 b,i;if(!p)return 0;for(b=0;b<2;b++)for(i=0;i<8;i++)if(p==&resources[b].entry[i])return 0x70000+b*4096+4*i;invalid=1;return 0xffffffffu;}
static void func_10004074(void *p){
 u32 bank;count++;eventHash=mix(mix(eventHash,0x10004074),pointer(p));*(u32*)p=0xab000000u+count;
 if(count==1){if(v->mutation&1)D_800DBEF8=tables[1].entry;if(v->mutation&2){D_800DBEF4=records[1]+16;D_800DBEFC=ages[1]+16;}if(v->mutation&4)D_800DBEF0=8;if(v->mutation&8)D_800DBEF0=-1;}
 if(v->mutation&2){bank=count==1?1:0;records[bank][16+7*160+0x70]^=1;ages[bank][16+7]=0;}
}
'''+body+r'''
static void caller(void){subject();}
static u32 digest(void){
 u32 h=2166136261u,b,i;h=mix(h,(u32)D_800DBEF0);
 if(D_800DBEF4==records[0]+16)h=mix(h,0x30000);else if(D_800DBEF4==records[1]+16)h=mix(h,0x31000);else invalid=1;
 if(D_800DBEF8==tables[0].entry)h=mix(h,0x50000);else if(D_800DBEF8==tables[1].entry)h=mix(h,0x51000);else invalid=1;
 if(D_800DBEFC==ages[0]+16)h=mix(h,0x60000);else if(D_800DBEFC==ages[1]+16)h=mix(h,0x61000);else invalid=1;
 for(b=0;b<2;b++){
  for(i=0;i<1312;i++)h=mix(h,records[b][i]);for(i=0;i<40;i++)h=mix(h,ages[b][i]);
  for(i=0;i<16;i++)h=mix(h,tables[b].pre[i]);for(i=0;i<8;i++)h=mix(h,pointer(tables[b].entry[i]));for(i=0;i<16;i++)h=mix(h,tables[b].post[i]);
  for(i=0;i<16;i++)h=mix(h,resources[b].pre[i]);for(i=0;i<8;i++)h=mix(h,resources[b].entry[i]);for(i=0;i<16;i++)h=mix(h,resources[b].post[i]);
 }return h;
}
static u8 pattern(s32 i,u32 seed){return(u8)(i*29+(s32)seed*11+0x51);}
static int run(void){
 u32 n,b,i,k;for(n=0;n<sizeof(vectors)/sizeof(vectors[0]);n++){
  v=&vectors[n];invalid=0;count=0;eventHash=2166136261u;
  for(b=0;b<2;b++){
   for(i=0;i<1312;i++)records[b][i]=pattern((s32)i-16,v->seed);for(i=0;i<40;i++)ages[b][i]=pattern((s32)i-16,v->seed);
   for(i=0;i<16;i++){tables[b].pre[i]=resources[b].pre[i]=pattern((s32)i-16,v->seed);tables[b].post[i]=resources[b].post[i]=pattern((s32)i+32,v->seed);}
   for(i=0;i<8;i++){k=v->seed+i*13+b*7;records[b][16+i*160+0x70]=(u8)(k*7);records[b][16+i*160+0x6f]=(u8)(k*17);records[b][16+i*160+0x4e]=(u8[]){0,3,255,2}[(k/2)%4];ages[b][16+i]=(u8[]){0,1,2,127,128,255}[k%6];tables[b].entry[i]=k%5==0?0:&resources[b].entry[i];resources[b].entry[i]=0xc0de0000u+b*16+i;}
  }
  D_800DBEF0=(s32)v->count;D_800DBEF4=records[0]+16;D_800DBEF8=tables[0].entry;D_800DBEFC=ages[0]+16;
  caller();if(digest()!=v->digest||eventHash!=v->events||count!=v->calls||invalid)return 1;
 }return 0;
}
'''+START
def main():
 count=vectors();source=program();profiles={}
 def run(label,text,opt):
  f=o/(label+'.c');exe=o/label;f.write_text(text);q=subprocess.run(native_command(opt)+['-fstrict-aliasing','-fmax-errors=1',str(f),'-o',str(exe)],cwd=r,capture_output=True,text=True);(o/(label+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(q.stdout+q.stderr)[-5000:];q=subprocess.run([str(exe)],capture_output=True,timeout=60);assert b'runtime error:'not in q.stderr;return q
 for opt in('-O0','-O2','-O3'):
  result=run('native'+opt,source,opt);assert result.returncode==0,(opt,result.returncode,result.stderr);profiles[opt]=dict(cases=count,SDK32=True,UBSan=True,strict_aliasing=True,typed_resource_and_pointer_arrays=True,full_backing_and_guard_digest=True)
 controls={'wrong-owned-bit':('(record[0x70] & 1) != 1','(record[0x70] & 2) != 2'),'wrong-retain-bit':('record[0x6F] & 0x80','record[0x6F] & 0x40'),'wrong-type':('record[0x4E] != 3','record[0x4E] != 2'),'no-age-decrement':('(*age)--;','(*age) = *age;'),'early-release':('if (*age != 0)','if (*age == 0)'),'wrong-stride':('offset += 0xA0','offset += 0x90'),'no-post-call-clear':('func_10004074(resource);\n                        D_800DBEF8[index] = NULL;','func_10004074(resource);\n                        D_800DBEF8[index] = resource;')}
 rejected=[]
 for label,(a,b)in controls.items():
  assert a in source;bad=source.replace(a,b);q=run('control-'+label,bad,'-O2');assert q.returncode!=0,(label,'Ineffective control');rejected.append(label)
 q=dict(profiles=profiles,effective_source_controls=rejected,source_installed=p.installed(),matching_credit=0);(o/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
