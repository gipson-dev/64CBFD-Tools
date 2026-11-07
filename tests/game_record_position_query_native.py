"""SDK native32 payloads/live tables, bounded pointers and effective controls."""
from tools.experiments import game_record_position_query_candidates as source
from tools.tests import game_record_position_query_oracle as g
def controls():
    b=source.SELECTED
    count=b.replace('(u32)D_800D3094','limit').replace('    s32 offset;','    s32 offset;\n    u32 limit = (u32)D_800D3094;')
    base=b.replace('D_800D3098','base').replace('    s32 offset;','    s32 offset;\n    GeneratedCDE80Record *base = D_800D3098;')
    return dict(wrong_stride=b.replace('offset += 0x34','offset += 0x38'),wrong_kind=b.replace('>> 2','>> 1'),wrong_subtype=b.replace('== subtype','== (subtype ^ 1)'),wrong_old_z=b.replace('query.old_z_position = z','query.old_z_position = x'),narrow_x=b.replace('query.x_position = x','query.x_position = (s16)x'),inverted_result=b.replace(', 0) == 0)',', 0) != 0)'),cached_count=count,cached_base=base)
def code(address):
    if not address:return 0
    base=g.A if address<g.B else g.B;return(8 if base==g.B else 0)+(address-base)//52+1
def program():
    rows=[];arr=lambda xs:'{'+','.join('0x%Xu'%g.u32(v)for v in xs)+'}'
    cases=list(g.cases())
    for c in cases:
        initial=g.fixture(c);m,calls,result,obs=g.reference(initial,c)
        meta=lambda memory:'{'+','.join('{'+','.join(arr(memory[base+i*52+at]for at in(20,21,23))for i in range(8))+'}'for base in(g.A,g.B))+'}'
        payload='{'+','.join('{'+str(code(r))+','+arr(int.from_bytes(data[at:at+4],'big')for at in g.FIELDS)+'}'for r,data in obs)+'}'
        rows.append('{'+','.join((str(g.u32(c.kind)),str(g.u32(c.subtype)),arr(c.coords),str(c.count),str(c.mutation),str(len(c.outcomes)),arr(c.outcomes),str(len(calls)),str(code(result)),str(g.read(m,g.COUNT)),str(int(g.read(m,g.BASE)==g.B)),meta(initial),meta(m),payload))+'}')
    text='#include <ultra64.h>\n#include "structs.h"\n'+source.SUPPORT+'\n'+source.SELECTED+'\n';variants=controls()
    for n,b in variants.items():assert b!=source.SELECTED,n;text+=b.replace(source.FUNCTION,'negative_'+n)+'\n'
    text+=r'''
typedef char ABI_actor[(sizeof(struct127)==812)?1:-1];
typedef char ABI_record[(sizeof(GeneratedCDE80Record)==52)?1:-1];
typedef char ABI_pointer[(sizeof(void*)==4)?1:-1];
typedef char ABI_y[(__builtin_offsetof(struct127,y_position)==0x18)?1:-1];
typedef char ABI_previous[(__builtin_offsetof(struct127,unk180)==0x180)?1:-1];
s32 D_800D3094;GeneratedCDE80Record*D_800D3098;
typedef struct{u32 record,fields[7];}Payload;
typedef struct{u32 kind,subtype,coords[3],count,mutation,nout,outcomes[3],calls,result,finalCount,finalBase;u8 initial[2][8][3],final[2][8][3];Payload payload[8];}Row;
static const Row rows[]={'''+',\n'.join(rows)+r'''};
static GeneratedCDE80Record records[2][8];static const Row*c;static u32 calls,bad;static struct127*escaped;
static u32 bits(f32 f){union{f32 f;u32 u;}v;v.f=f;return v.u;}
static u32 recordCode(GeneratedCDE80Record*p){u32 i,j;for(j=0;j<2;j++)for(i=0;i<8;i++)if(p==&records[j][i])return j*8+i+1;return 0;}
s32 func_150A1DA0(struct127*q,s32 address,s32 zero){u32 i,n=calls++,bank;GeneratedCDE80Record*r=(GeneratedCDE80Record*)address;f32 fields[7];u8*bytes;
 fields[0]=q->x_position;fields[1]=q->y_position;fields[2]=q->z_position;fields[3]=q->old_x_position;fields[4]=q->old_y_position;fields[5]=q->old_z_position;fields[6]=q->unk180;
 if(zero||n>=c->calls||n>=8)bad=1;else{if(recordCode(r)!=c->payload[n].record)bad=1;for(i=0;i<7;i++)if(bits(fields[i])!=c->payload[n].fields[i])bad=1;}
 if(escaped&&escaped!=q)bad=1;escaped=q;
 if(c->mutation&1)D_800D3098=records[(n+1)&1];
 if(c->mutation&2){s32 limit=(s32)c->count+(((n+1)&1)?1:-2);if(limit<0)limit=0;if(limit>8)limit=8;D_800D3094=limit;}
 if(c->mutation&4){f32 k=(f32)(n+1);q->x_position=k*.5f;q->y_position=-k-.25f;q->z_position=k*2.f;q->old_x_position=k+1.f;q->old_y_position=k+2.f;q->old_z_position=-k*3.f;q->unk180=k+.5f;}
 if(c->mutation&16){bank=(u32)(D_800D3098==records[1]);bytes=(u8*)&records[bank][(n+4)%8];bytes[20]=0;bytes[21]=(u8)((c->kind&63)*4+2);bytes[23]=(u8)c->subtype;}
 return(s32)c->outcomes[n%c->nout];}
static u32 run(GeneratedCDE80Record*(*fn)(s32,s32,s32,s32,s32),u32 control){u32 n,i,j,k,fail=0;GeneratedCDE80Record*result;
 for(n=0;n<sizeof(rows)/sizeof(rows[0]);n++){c=&rows[n];if(control&&c->count>8)continue;calls=bad=0;escaped=0;
  for(j=0;j<2;j++)for(i=0;i<8;i++){u8*p=(u8*)&records[j][i];for(k=0;k<52;k++)p[k]=0;p[20]=c->initial[j][i][0];p[21]=c->initial[j][i][1];p[23]=c->initial[j][i][2];}
  D_800D3094=(s32)c->count;D_800D3098=records[0];result=fn((s32)c->kind,(s32)c->subtype,(s32)c->coords[0],(s32)c->coords[1],(s32)c->coords[2]);
  if(bad||calls!=c->calls||recordCode(result)!=c->result||(u32)D_800D3094!=c->finalCount||D_800D3098!=records[c->finalBase])fail++;
  for(j=0;j<2;j++)for(i=0;i<8;i++){u8*p=(u8*)&records[j][i];if(p[20]!=c->final[j][i][0]||p[21]!=c->final[j][i][1]||p[23]!=c->final[j][i][2])fail++;for(k=0;k<52;k++)if(k!=20&&k!=21&&k!=23&&p[k])fail++;}
 }return fail;}
void _start(void){u32 mask=0;int result;if(run(func_150A3194,0))goto failure;
'''
    for i,n in enumerate(variants):text+='if(run(negative_'+n+',1))mask|='+str(1<<i)+';\n'
    text+='if(mask!=255)goto failure;result=0;goto finish;\nfailure:result=1;\nfinish:__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}\n';return text,list(variants),len(cases)
