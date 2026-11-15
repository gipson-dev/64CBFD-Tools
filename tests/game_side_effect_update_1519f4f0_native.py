"""Native32 real typed objects, endian-normalized complete public snapshots."""
import json,subprocess,struct
from tools.experiments import game_side_effect_update_1519f4f0_match as s
from tools.experiments import game_side_effect_constructor_1519f1c8_match as ctor
from tools.tests import game_side_effect_update_1519f4f0_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
FLOATS=dict(x=0,z=4,height=8,phase=12,velocityX=28,velocityZ=32)
SHORTS=dict(alpha=16,delay=18,light=20,reserved16=22,lifetime=24,reserved1A=26)

def source():
    eligible=[c for c in g.cases() if c.alias==0 and c.cap<=10 and c.pattern<=5 and c.rule=='left']
    corpus=eligible[::max(1,len(eligible)//256)]+[c for c in eligible if c.tick in (-2147483648,2147483647) or c.count<0]
    byte_array=lambda values:'{'+','.join(str(v) for v in values)+'}'
    rows=[]
    for c in corpus:
        m=g.fixture(c);expected,result,calls,_=g.reference(m,c);assert len(calls)<=10
        spans=[]
        for memory in (m,expected):
            for at,n in ((g.EFFECT,160),(g.PACKET,80),(g.RECORDS,36*c.cap)):
                values=bytes(memory[at+i] for i in range(n));spans.append(byte_array(values))
        query_rows=['{'+','.join('0x%Xu'%v for v in (args[2],*struct.unpack('>3I',snap)))+'}' for _,args,snap in calls]
        query_rows+=['{0,0,0,0}']*(10-len(query_rows))
        globals=[g.read(expected,g.symbols()[n]) for n in ('D_800BE9E4','D_800BE9A4','D_800A8CF0')]
        header=(c.cap,c.effects,c.hit,c.tick&0xFFFFFFFF,c.scale,result,len(calls),*globals)
        rows.append('{'+','.join('0x%Xu'%v for v in header)+','+','.join(spans)+',{'+','.join(query_rows)+'}}')
    prefix='#include <ultra64.h>\n'+ctor.PIN['declarations']+'\n'+s.PIN['declarations']+'''
s32 D_800BE9E4;
f32 D_800BE9A4,D_800A8CF0;
f32 fabsf(f32);
typedef struct {
 u32 cap,effects,hit,tick,scale,want,nquery,finalTick,finalScale,finalLimit;
 u8 initialEffect[160],initialPacket[80],initialEntries[360];
 u8 finalEffect[160],finalPacket[80],finalEntries[360];
 u32 queries[10][4];
} NativeCase;
static SideEffect1519F4F0 effect;
static SidePayload1519F1C8 packet,otherPacket;
static SideEntry1519F4F0 entries[10],otherEntries[10];
static const NativeCase *current;
static u32 ordinal,failure;
static f32 number(u32 v){union {u32 u;f32 f;} x;x.u=v;return x.f;}
static u32 word(f32 v){union {u32 u;f32 f;} x;x.f=v;return x.u;}
f32 fabsf(f32 v){return number(word(v)&0x7FFFFFFFu);}
static void copy(u8 *d,const u8 *p,u32 n){for(u32 i=0;i<n;i++)d[i]=p[i];}
static u32 get32(const u8 *p){return (u32)p[0]<<24|(u32)p[1]<<16|(u32)p[2]<<8|p[3];}
static s32 get16(const u8 *p){u32 v=(u32)p[0]<<8|p[1];return (s32)v-(v&0x8000?65536:0);}
static void put32(u8 *p,u32 v){p[0]=v>>24;p[1]=v>>16;p[2]=v>>8;p[3]=v;}
static void put16(u8 *p,u32 v){p[0]=v>>8;p[1]=v;}
static int same(const u8 *a,const u8 *b,u32 n){for(u32 i=0;i<n;i++)if(a[i]!=b[i])return 0;return 1;}
typedef char effect_size[sizeof(effect)==160?1:-1];
typedef char packet_size[sizeof(packet)==80?1:-1];
typedef char entry_size[sizeof(entries[0])==36?1:-1];
typedef char floor_size[sizeof(effect.floor)==36?1:-1];
typedef char floor_offset[__builtin_offsetof(SideEffect1519F4F0,floor)==0x60?1:-1];
typedef char entries_offset[__builtin_offsetof(SideEffect1519F4F0,entries)==0x94?1:-1];
s32 func_15045800(f32 *point,u16 selector,f32 bottom,void *output){
 u32 n=ordinal++;
 if(n>=current->nquery){failure=1;return 0;}
 if(selector||output!=&effect.floor||word(bottom)!=current->queries[n][0])failure=2;
 for(u32 i=0;i<3;i++)if(word(point[i])!=current->queries[n][i+1])failure=3;
 for(u32 i=0;i<36;i++)((u8 *)output)[i]=(n*31+i*7+0xA5)&255;
 effect.floor.height=20.25f+n;
 if(current->effects&1){D_800BE9E4=n+2;D_800BE9A4=.25f*(n+1);packet.height=3;packet.limit=2.f;packet.count=-7;}
 if(current->effects&2){effect.entries=otherEntries;effect.payload=&otherPacket;}
 if((current->effects&4)&&n==0){effect.head=(current->initialEffect[0x2D]+1)%current->cap;effect.count=(u8)(effect.count+1);}
 if(current->effects&8)D_800A8CF0=0.f;
 for(u32 i=0;i<3;i++)point[i]=number(word(point[i])^0x5A5A5A5Au);
 return current->hit<2?current->hit:n&1;
}
'''
    harness='\nstatic const NativeCase cases[]={\n'+',\n'.join(rows)+'\n};\n'
    harness+='''static int run(void){
 for(u32 which=0;which<sizeof(cases)/sizeof(cases[0]);which++){
  const NativeCase *c=&cases[which];current=c;ordinal=failure=0;
  copy((u8 *)&effect,c->initialEffect,160);copy((u8 *)&packet,c->initialPacket,80);
  effect.entries=entries;effect.payload=&packet;
  for(u32 i=0;i<3;i++)effect.position[i]=number(get32(c->initialEffect+0x54+4*i));
  effect.floor.height=number(get32(c->initialEffect+0x60));
  packet.height=get16(c->initialPacket+0x34);packet.limit=number(get32(c->initialPacket+0x3C));packet.zero46=get16(c->initialPacket+0x46);packet.count=get16(c->initialPacket+0x48);
  for(u32 i=0;i<c->cap;i++){
   const u8 *p=c->initialEntries+36*i;copy((u8 *)&entries[i],p,36);
'''
    for name,offset in FLOATS.items():harness+='   entries[i].%s=number(get32(p+%d));\n'%(name,offset)
    for name,offset in SHORTS.items():harness+='   entries[i].%s=get16(p+%d);\n'%(name,offset)
    harness+='''  }
  D_800BE9E4=c->tick;D_800BE9A4=number(c->scale);D_800A8CF0=100000.f;
  if((u32)func_1519F4F0(&effect)!=c->want||ordinal!=c->nquery||failure)return 151;
  if((u32)D_800BE9E4!=c->finalTick||word(D_800BE9A4)!=c->finalScale||word(D_800A8CF0)!=c->finalLimit)return 152;
  u8 e[160],p[80],records[360];copy(e,(u8 *)&effect,160);copy(p,(u8 *)&packet,80);
  put32(e+0x94,effect.entries==entries?0x50000:effect.entries==otherEntries?0x70000:0);
  put32(e+0x98,effect.payload==&packet?0x60000:effect.payload==&otherPacket?0x70100:0);
  for(u32 i=0;i<3;i++)put32(e+0x54+4*i,word(effect.position[i]));put32(e+0x60,word(effect.floor.height));
  put16(p+0x34,packet.height);put32(p+0x3C,word(packet.limit));put16(p+0x46,packet.zero46);put16(p+0x48,packet.count);
  for(u32 i=0;i<c->cap;i++){
   u8 *dst=records+36*i;copy(dst,(u8 *)&entries[i],36);
'''
    for name,offset in FLOATS.items():harness+='   put32(dst+%d,word(entries[i].%s));\n'%(offset,name)
    for name,offset in SHORTS.items():harness+='   put16(dst+%d,entries[i].%s);\n'%(offset,name)
    harness+='''  }
  if(!same(e,c->finalEffect,160)||!same(p,c->finalPacket,80)||!same(records,c->finalEntries,36*c->cap))return 153;
 }
 return 0;
}
'''
    return prefix+s.PIN['source']+harness+START,len(corpus)

def main():
    text,count=source();path=s.OUT/'native.c';path.write_text(text);profiles=[];controls=0
    body=s.PIN['source']
    changes={'gate':('effect->count < 2','effect->count < 3'),'light':('entry->light = 255','entry->light = 254'),
             'height-span':('entry->height + 30.0f','entry->height + 31.0f'),'counter':(' + (u32)packet->count',' - (u32)packet->count')}
    mutants={}
    for label,(old,new) in changes.items():assert body.count(old)==1;mutants[label]=text.replace(body,body.replace(old,new))
    for opt in ('-O0','-O2','-O3'):
        for alias in ('-fstrict-aliasing','-fno-strict-aliasing'):
            exe=s.OUT/('native'+opt+alias);p=subprocess.run(native_command(opt)+['-mstackrealign',alias,'-o',str(exe),str(path)],capture_output=True,text=True);assert p.returncode==0,p.stderr
            q=subprocess.run([str(exe)],capture_output=True);assert q.returncode==0,(opt,alias,q.returncode,q.stderr);profiles.append(opt+alias)
        for label,wrong in mutants.items():
            control_path=s.OUT/('native-control-'+label+'.c');control_path.write_text(wrong);exe=control_path.with_suffix('')
            p=subprocess.run(native_command(opt)+['-mstackrealign','-o',str(exe),str(control_path)],capture_output=True,text=True);assert p.returncode==0,p.stderr
            assert subprocess.run([str(exe)],capture_output=True).returncode in (151,152,153),label;controls+=1
    report=dict(cases_per_profile=count,profiles=profiles,complete_effect_packet_entry_snapshots=True,actual_36_byte_floor=True,UBSan=True,effective_source_controls=controls,guest_alias_and_nonfinite_cases_excluded=True)
    (s.OUT/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
