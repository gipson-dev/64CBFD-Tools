"""SDK32 entity-query pair, independent normalized state/trace and defined-domain controls."""
import json,re,struct,subprocess,sys
from pathlib import Path
from tools.experiments.game_entity_height_pair_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import game_entity_height_pair_oracle as guest
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
def mutations(b):
 default='D_80098D58'if 'func_15045D48'in b else'D_80098D5C'
 saved=b.replace('    s32 selected;','    s32 inputBefore;\n    s32 selected;').replace('    selected = -1;','    selected = -1;\n    inputBefore = input[0];').replace('(s32)position[2], input[0],','(s32)position[2], inputBefore,')
 result={
 'wrong-default':b.replace('result->height = '+default+';','result->height = 0.0f;'),
 'unsigned-fixed':b.replace('D_800D3300[i].fixedHeight *','(u32)D_800D3300[i].fixedHeight *'),
 'wrong-scale':b.replace('1.0f / 256.0f','1.0f / 128.0f'),
 'last-tie-wins':b.replace('height < result->height','height <= result->height').replace('result->height < height','result->height <= height'),
 'scaled-byte-offset':b.replace('+ vertexOffset)', '+ vertexOffset * 16)'),
 'cached-input':saved,
 'wrong-input-word':b.replace('input[0]','input[1]'),
 'signed-first-triangle':b.replace('entity->firstTriangle','(s16)entity->firstTriangle'),
 'missing-default-metadata':b.replace('result->metadata = entity->metadata;','result->metadata = 0;'),
 'wrong-entity-flag':b.replace('entity->flags & 0x80','entity->flags & 0x40').replace('== 0x80','== 0x40'),
 'wrong-state':b.replace('result->state = 3','result->state = 4'),
 'cleared-failure-flag':b.replace('        return 0;\n    }\n    result->flags &= ~2;','        result->flags &= ~2;\n        return 0;\n    }\n    result->flags &= ~2;')}
 assert len(result)==12 and all(v!=b for v in result.values());return result
def cases():return[c for kind in range(2)for c in guest.cases(kind)if not c.alias and c.home_selected==-2 and not c.home_input and c.home_threshold<0]
def digest(vs):
 h=2166136261
 for v in vs:h=((h^(v&0xFFFFFFFF))*16777619)&0xFFFFFFFF
 return h
def value_id(v):return 0xE0000000+(v-guest.ENTITIES)//160 if guest.ENTITIES<=v<guest.ENTITIES+1280 and(v-guest.ENTITIES)%160==0 else v
def result_values(b):return[int.from_bytes(b[:4],'big'),*[int.from_bytes(b[4+i*2:6+i*2],'big')for i in range(9)],int.from_bytes(b[22:24],'big'),int.from_bytes(b[24:28],'big'),b[28],b[29],int.from_bytes(b[30:32],'big'),value_id(int.from_bytes(b[32:36],'big'))]
def snapshots(o):
 b,p,inp,alt,base,tri,scratch=o;return[*result_values(b),*[int.from_bytes(p[i:i+4],'big')for i in(0,4,8)],inp,alt,(base-guest.ENTITIES)//160,(tri-guest.TRIANGLES)//12,*scratch]
def values(m,c):
 s=guest.SYMS;vs=result_values(guest.data(m,guest.OUTPUT,36))+[m[guest.OUTPUT+i]for i in range(-16,0)]+[m[guest.OUTPUT+i]for i in range(36,52)]
 vs +=[guest.read(m,guest.POS+i*4)for i in range(3)]+[guest.read(m,p+i*4)for p in(guest.INPUT,guest.ALT_INPUT)for i in range(2)]
 vs +=[(guest.read(m,s['D_800DBEF4'])-guest.ENTITIES)//160,(guest.read(m,s['D_800DBE3C'])-guest.TRIANGLES)//12]+[m[s['D_800D3830']+i]for i in range(128)]
 for row in range(8):
  p=s['D_800D3300']+row*16;vs +=[guest.read(m,p),(guest.read(m,p+4)-guest.TRIANGLES)//12,guest.read(m,p+8),guest.read(m,p+12)]
 for row in range(8):
  p=guest.ENTITIES+row*160;table=guest.read(m,p+0x44);vs +=[guest.read(m,p+0x40),((table-guest.METADATA)//4+8)if table else 0xFFFFFFFF,guest.read(m,p+0x58,2)];vs +=[m[p+i]for i in range(160)if i not in(*range(0x40,0x48),0x58,0x59)]
 return vs
def expected(c):
 m,calls,obs,r=guest.reference(guest.fixture(c),c);trace=[]
 for(t,args),o in zip(calls,obs):
  a=list(args);a[1 if t==guest.CONTEXT else 3]-=guest.SYMS['D_800D3830'];trace +=[int(t==guest.SCAN),*a,*snapshots(o)]
 return digest(values(m,c)),digest(trace),len(calls),r
def program(parts):
 source=(out/'final-owner.c').read_text();types='\n'.join(re.search(r'typedef struct '+name+r' \{[\s\S]*?\} '+name+';',source)[0]for name in('QueryVertex71820','QueryTriangle71820','HeightCandidate71820','HeightResult71820','HeightEntity71820'))
 rows=[];fmt=lambda v:'0x%Xu'%(v&0xFFFFFFFF)
 for c in cases():
  fields=[*map(fmt,(c.kind,*c.position,c.threshold)),'{'+','.join(map(fmt,c.heights))+'}',*map(fmt,(c.count,c.flags,c.entity_flags,int(c.metadata),c.first_triangle,c.base_index,c.byte_offset,c.input_word,c.mutation,*expected(c)))];rows.append('{'+','.join(fields)+'}')
 functions=[]
 for kind,b in enumerate(parts):
  for name,part in{'candidate':b,**mutations(b)}.items():functions.append(part.replace(guest.FUNCTIONS[kind]+'(',name.replace('-','_')+'_'+str(kind)+'('))
 text=r'''#include <ultra64.h>
TYPES
_Static_assert(sizeof(void*)==4,"SDK pointers");
_Static_assert(sizeof(QueryVertex71820)==16,"vertex stride");
_Static_assert(sizeof(QueryTriangle71820)==12,"triangle stride");
_Static_assert(sizeof(HeightCandidate71820)==16,"candidate stride");
_Static_assert(sizeof(HeightResult71820)==36,"result extent");
_Static_assert(sizeof(HeightEntity71820)==160,"entity stride");
_Static_assert(__builtin_offsetof(HeightEntity71820,metadataTable)==0x44,"table offset");
_Static_assert(__builtin_offsetof(HeightEntity71820,firstTriangle)==0x58,"unsigned first triangle");
_Static_assert(__builtin_offsetof(HeightEntity71820,flags)==0x6F,"entity flags");
struct Case{u32 kind,x,y,z,threshold,h[4],count,flags,entityFlags,metadata,first,base,offset,input,mutation,stateHash,traceHash,calls,result;};static const struct Case rows[]={ROWS};static const struct Case*c;
struct ResultArena{u8 before[16];HeightResult71820 value;u8 after[16];};static struct ResultArena output;
HeightCandidate71820 D_800D3300[8];HeightEntity71820*D_800DBEF4;QueryTriangle71820*D_800DBE3C;u8 D_800D3830[128] __attribute__((aligned(4)));f32 D_80098D58,D_80098D5C;
static QueryTriangle71820 triangles[8];static QueryVertex71820 vertices[8][3][40];static HeightEntity71820 entities[8];static u32 metadata[65560];static f32 position[3];static s32 input[2],alternate[2];
static u32 trace,calls,readonlyBefore,failure[2];
static u32 floatBits(f32 f){union{f32 f;u32 u;}v;v.f=f;return v.u;}static f32 fromBits(u32 u){union{f32 f;u32 u;}v;v.u=u;return v.f;}
static void hash(u32*h,u32 v){*h=(*h^v)*16777619u;}
static u32 pattern(s32 off){return(u8)((off+16)*29+91);}static u32 word(s32 off){return(pattern(off)<<24)|(pattern(off+1)<<16)|(pattern(off+2)<<8)|pattern(off+3);}static u16 half(s32 off){return(u16)((pattern(off)<<8)|pattern(off+1));}
static u32 valueId(u32 v){u32 base=(u32)entities;if(v>=base&&v<base+sizeof(entities)&&(v-base)%160==0)return 0xE0000000u+(v-base)/160;return v;}
static void hashResult(u32*h){HeightResult71820*a=&output.value;u32 i;hash(h,floatBits(a->height));for(i=0;i<9;i++)hash(h,(u16)a->vertices[i]);hash(h,(u16)a->pad16);hash(h,a->metadata);hash(h,a->flags);hash(h,a->state);hash(h,a->pad1E);hash(h,valueId((u32)a->value));}
static void snapshot(u32*h){u32 i;hashResult(h);for(i=0;i<3;i++)hash(h,floatBits(position[i]));hash(h,(u32)input[0]);hash(h,(u32)alternate[0]);hash(h,(u32)(D_800DBEF4-entities));hash(h,(u32)(D_800DBE3C-triangles));for(i=0;i<16;i++)hash(h,D_800D3830[i]);}
static void record(u32 code,u32 a,u32 b,u32 d,u32 e){hash(&trace,code);hash(&trace,a);hash(&trace,b);hash(&trace,d);if(code)hash(&trace,e);snapshot(&trace);calls++;}
void func_150A44F0(s32 value,void*scratch,s32 mode){u32 i;u8*p=scratch;record(0,(u32)value,(u32)p-(u32)D_800D3830,(u32)mode,0);for(i=0;i<16;i++)p[i]=(u8)((u32)value+i*17);if(c->mutation&1){position[0]=1.75f;position[1]=2.0f;position[2]=-2.75f;}if(c->mutation&2)input[0]=77;}
s32 func_150A43E0(s32 x,s32 z,s32 value,void*scratch){u32 i;record(1,(u32)x,(u32)z,(u32)value,(u32)scratch-(u32)D_800D3830);if(c->mutation&4)position[1]=c->kind?1.0f:4.0f;if(c->mutation&8)output.value.height=c->kind?6.0f:0.5f;if(c->mutation&16)for(i=0;i<8;i++)D_800D3300[i].fixedHeight=(s32)(7-i)*256;if(c->mutation&32)D_800DBEF4=&entities[1];if(c->mutation&64){entities[1].metadataTable=0;entities[1].flags^=128;}if(c->mutation&128)for(i=0;i<8;i++)D_800D3300[i].padC=3;return(s32)c->count;}
FUNCTIONS
static u32 readonlyHash(void){u32 h=2166136261u,i;u8*p;p=(u8*)triangles;for(i=0;i<sizeof(triangles);i++)hash(&h,p[i]);p=(u8*)vertices;for(i=0;i<sizeof(vertices);i++)hash(&h,p[i]);for(i=0;i<40;i++)hash(&h,metadata[i]);return h;}
static void initialize(void){u32 row,axis,j,k;u8*p;HeightResult71820*a=&output.value;
 p=(u8*)&output;for(j=0;j<sizeof(output);j++)p[j]=(u8)(j*29+91);a->height=fromBits(word(0));for(j=0;j<9;j++)a->vertices[j]=(s16)half(4+(s32)j*2);a->pad16=(s16)half(22);a->metadata=word(24);a->flags=(u8)c->flags;a->state=(u8)pattern(29);a->pad1E=half(30);a->value=(s32)word(32);
 position[0]=fromBits(c->x);position[1]=fromBits(c->y);position[2]=fromBits(c->z);input[0]=(s32)c->input;input[1]=0x76543210;alternate[0]=(s32)(c->input^0xA55AFFFFu);alternate[1]=(s32)0xFEDCBA98u;
 for(j=0;j<128;j++)D_800D3830[j]=(u8)(j*29+91);D_80098D58=fromBits(0x47C34FF3u);D_80098D5C=-10000.0f;
 for(row=0;row<8;row++){for(axis=0;axis<3;axis++){for(j=0;j<40;j++){s32 index=(s32)j-20;QueryVertex71820*v=&vertices[row][axis][j];v->x=(s16)(-32768+(s32)row*731+(s32)axis*113+index*17);v->y=(s16)(-32768+(s32)row*731+(s32)axis*113+index*17+32701);v->z=(s16)(-32768+(s32)row*731+(s32)axis*113+index*17+65402);for(k=0;k<10;k++)v->pad6[k]=(u8)((index*16+6+((s32)k^1))*13+(s32)row*37+(s32)axis*19+5);}triangles[row].vertices[axis]=&vertices[row][axis][20];}
 D_800D3300[row].fixedHeight=(s32)c->h[row%4];D_800D3300[row].triangle=&triangles[row];D_800D3300[row].vertexIndex=(s32)c->offset;D_800D3300[row].padC=(s32)((row+1)%4);
 p=(u8*)&entities[row];for(j=0;j<160;j++)p[j]=(u8)((row*160+j)*29+91);entities[row].metadata=0x91570000u+row;entities[row].metadataTable=c->metadata?&metadata[8+c->first+row]:0;entities[row].firstTriangle=(u16)c->first;entities[row].flags=(u8)(c->entityFlags^(row*17));}
 for(j=0;j<40;j++)metadata[j]=0x81230000u+(((s32)j-8)&65535);D_800DBEF4=entities;D_800DBE3C=&triangles[c->base];trace=2166136261u;calls=0;readonlyBefore=readonlyHash();
}
static u32 state(void){u32 h=2166136261u,i,j;u8*p;hashResult(&h);for(i=0;i<16;i++)hash(&h,output.before[i]);for(i=0;i<16;i++)hash(&h,output.after[i]);for(i=0;i<3;i++)hash(&h,floatBits(position[i]));for(i=0;i<2;i++)hash(&h,(u32)input[i]);for(i=0;i<2;i++)hash(&h,(u32)alternate[i]);hash(&h,(u32)(D_800DBEF4-entities));hash(&h,(u32)(D_800DBE3C-triangles));for(i=0;i<128;i++)hash(&h,D_800D3830[i]);
 for(i=0;i<8;i++){hash(&h,(u32)D_800D3300[i].fixedHeight);hash(&h,(u32)(D_800D3300[i].triangle-triangles));hash(&h,(u32)D_800D3300[i].vertexIndex);hash(&h,(u32)D_800D3300[i].padC);}
 for(i=0;i<8;i++){HeightEntity71820*e=&entities[i];hash(&h,e->metadata);hash(&h,e->metadataTable?(u32)(e->metadataTable-metadata):0xFFFFFFFFu);hash(&h,e->firstTriangle);p=(u8*)e;for(j=0;j<160;j++)if(!(j>=0x40&&j<0x48)&&j!=0x58&&j!=0x59)hash(&h,p[j]);}return h;}
typedef s32(*Subject)(f32*,f32,s32*,HeightResult71820*);
static int check(Subject low,Subject high){u32 i;for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){s32 result;c=&rows[i];initialize();result=(c->kind?high:low)(position,fromBits(c->threshold),input,&output.value);failure[0]=i;if(state()!=c->stateHash){failure[1]=1;return 1;}if(trace!=c->traceHash||calls!=c->calls||(u32)result!=c->result){failure[1]=2;return 2;}if(readonlyHash()!=readonlyBefore){failure[1]=3;return 3;}}return 0;}
static int run(void){if(check(candidate_0,candidate_1))return 1;
CONTROLS
return 0;}
__attribute__((force_align_arg_pointer)) void _start(void){int r=run();if(r)__asm__ volatile(".byte 0xcd,0x80"::"a"(4),"b"(2),"c"(failure),"d"(8):"memory");__asm__ volatile(".byte 0xcd,0x80"::"a"(1),"b"(r):"memory");__builtin_unreachable();}
'''
 controls='\n'.join('if(!check('+(name.replace('-','_')+'_0'if kind==0 else'candidate_0')+','+(name.replace('-','_')+'_1'if kind==1 else'candidate_1')+')){failure[0]='+str(i*2+kind)+';failure[1]=99;return 2;}'for i,name in enumerate(mutations(parts[0]))for kind in range(2))
 return text.replace('TYPES',types).replace('ROWS',',\n'.join(rows)).replace('FUNCTIONS','\n'.join(functions)).replace('CONTROLS',controls)
def main():
 source=(out/'final-owner.c').read_text();parts=[body(source,f)for f in guest.FUNCTIONS];p=out/'native.c';p.write_text(program(parts));profiles={}
 for opt in('-O0','-O2','-O3'):
  exe=out/('native'+opt);r=subprocess.run(native_command(opt)+['-fmax-errors=3','-fno-diagnostics-show-caret','-fno-strict-aliasing','-Wno-unused-variable',str(p),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert not r.returncode and not r.stdout and not r.stderr,r.stdout+r.stderr
  r=subprocess.run([str(exe)],capture_output=True,timeout=60);assert r.returncode==0 and not r.stdout and not r.stderr,(opt,r.returncode,struct.unpack('<II',r.stderr)if len(r.stderr)==8 else r.stderr);profiles[opt]=dict(exit=0,UBSan=True,cases=len(cases()),effective_controls=24)
 report=dict(profiles=profiles,SDK32_layout=True,all_result_entity_and_candidate_fields=True,retained_bytes_and_canaries=True,unsigned_first_triangle_65535=True,negative_in_array_metadata_indices=True,helpers_are_bounded_providers=True,guest_frame_and_physical_aliases_excluded=True)
 (out/'native.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
