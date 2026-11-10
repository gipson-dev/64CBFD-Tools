"""SDK32 typed coordinates/results, independent state/trace digests and effective controls."""
import json,re,struct,subprocess,sys
from pathlib import Path
from tools.experiments.game_highest_height_150450cc_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import game_highest_height_150450cc_oracle as guest
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
def mutations(b):
 result={
 'early-equality':b.replace('position[1] < threshold','position[1] <= threshold'),
 'wrong-height-scale':b.replace('1.0f / 256.0f','1.0f / 128.0f'),
 'unsigned-fixed-height':b.replace('D_800D3300[i].fixedHeight *','(u32)D_800D3300[i].fixedHeight *'),
 'last-equal-wins':b.replace('result->height < height','result->height <= height'),
 'strict-upper-bound':b.replace('height <= position[1]','height < position[1]'),
 'swapped-query-coordinates':b.replace('func_150A3A70((s32)position[0], (s32)position[2])','func_150A3A70((s32)position[2], (s32)position[0])'),
 'missing-default-height':b.replace('result->height = D_80098D44;','result->height = 0.0f;'),
 'wrong-vertex-index':b.replace('vertexPointers[i][vertexIndex]','vertexPointers[i][vertexIndex + 1]'),
 'wrong-output-stride':b.replace('i * 3','i * 2'),
 'missing-metadata':b.replace('D_800DBE5C[candidate->triangle - D_800DBE3C]','0'),
 'wrong-published-state':b.replace('result->state = 1','result->state = 2'),
 'cleared-final-failure-flag':b.replace('        return 0;\n    }\n    result->flags &= ~2;','        result->flags &= ~2;\n        return 0;\n    }\n    result->flags &= ~2;')}
 assert len(result)==12 and all(v!=b for v in result.values());return result
def cases():return[c for c in guest.cases()if not c.alias and c.home_selected==-2 and not c.home_output and c.home_threshold<0]
def digest(vs):
 h=2166136261
 for v in vs:h=((h^(v&0xFFFFFFFF))*16777619)&0xFFFFFFFF
 return h
def result_values(b):return[int.from_bytes(b[:4],'big'),*[int.from_bytes(b[4+i*2:6+i*2],'big')for i in range(9)],int.from_bytes(b[22:24],'big'),int.from_bytes(b[24:28],'big'),b[28],b[29],int.from_bytes(b[30:32],'big'),int.from_bytes(b[32:36],'big')]
def snapshots(o):
 a,b,p,g=o;return[*result_values(a),*result_values(b),*[int.from_bytes(p[i:i+4],'big')for i in(0,4,8)],*g[:4],int(bool(g[4])),(g[5]-guest.TRIANGLES)//12]
def values(m,c):
 s=guest.SYMS;vs=[]
 for p in(guest.OUTPUT,guest.ALTERNATE):vs+=result_values(guest.data(m,p,36))+[m[p+i]for i in range(-16,0)]+[m[p+i]for i in range(36,52)]
 vs +=[guest.read(m,guest.POS+i*4)for i in range(3)]
 vs +=[guest.read(m,s[k])for k in('D_800DBE68','D_800DBE6C','D_800DBE70','D_800DBE74')];vs +=[int(bool(guest.read(m,s['D_800DBE5C']))),(guest.read(m,s['D_800DBE3C'])-guest.TRIANGLES)//12]
 vs +=[guest.read(m,dest)for _,dest in guest.CONTEXT_ROWS[1:]]+[guest.read(m,0x800DBE50)]
 for i in range(8):
  p=s['D_800D3300']+i*16;vs +=[guest.read(m,p),(guest.read(m,p+4)-guest.TRIANGLES)//12,guest.read(m,p+8),guest.read(m,p+12)]
 return vs
def expected(c):
 m,calls,obs,r=guest.reference(guest.fixture(c),c);trace=[]
 for(t,a),o in zip(calls,obs):trace +=[{guest.CONTEXT:0,guest.SELECT:1,guest.SCAN:2}[t],*a,*snapshots(o)]
 return digest(values(m,c)),digest(trace),len(calls),r
def program(selected):
 owner=(out/'final-owner.c').read_text();types='\n'.join(re.search(r'typedef struct '+name+r' \{[\s\S]*?\} '+name+';',owner)[0]for name in('QueryVertex71820','QueryTriangle71820','HeightCandidate71820','HeightResult71820'))
 rows=[]
 for c in cases():
  fmt=lambda v:'0x%Xu'%(v&0xFFFFFFFF);fields=[*map(fmt,(*c.position,c.threshold)),'{'+','.join(map(fmt,c.heights))+'}',*map(fmt,(c.count,c.flags,int(c.metadata),c.mutation,int(c.real_context),c.vertex_index,c.base_index,*expected(c)))];rows.append('{'+','.join(fields)+'}')
 functions='\n'.join(p.replace('func_150450CC(',name.replace('-','_')+'(')for name,p in{'candidate':selected,**mutations(selected)}.items())
 wrapper=body((root/'conker/src/game/generated_13BB20.c').read_text(),'func_1510F800').replace('func_1510F800','native_original_context_wrapper')
 text=r'''#include <ultra64.h>
TYPES
_Static_assert(sizeof(void*)==4,"SDK pointers");
_Static_assert(sizeof(QueryVertex71820)==16,"vertex stride");
_Static_assert(sizeof(QueryTriangle71820)==12,"triangle stride");
_Static_assert(sizeof(HeightCandidate71820)==16,"candidate stride");
_Static_assert(sizeof(HeightResult71820)==36,"result extent");
_Static_assert(__builtin_offsetof(HeightResult71820,metadata)==24,"metadata");
_Static_assert(__builtin_offsetof(HeightResult71820,flags)==28,"flags");
struct Case{u32 x,y,z,threshold,h[4],count,flags,metadata,mutation,real,index,base,stateHash,traceHash,calls,result;};static const struct Case rows[]={ROWS};static const struct Case*c;
struct ResultArena{u8 before[16];HeightResult71820 value;u8 after[16];};static struct ResultArena outputs[2];
HeightCandidate71820 D_800D3300[8];QueryTriangle71820*D_800DBE3C;u32*D_800DBE5C;f32 D_800DBE68,D_800DBE6C,D_800DBE70,D_800DBE74,D_80098D44;
static QueryTriangle71820 triangles[8];static QueryVertex71820 vertices[8][3][5];static u32 metadata[24],derived[4],context;
static f32 position[3];static u32 trace,calls,readonlyBefore,failure[2];
static u32 floatBits(f32 f){union{f32 f;u32 u;}v;v.f=f;return v.u;}
static f32 fromBits(u32 u){union{f32 f;u32 u;}v;v.u=u;return v.f;}
static void hash(u32*h,u32 v){*h=(*h^v)*16777619u;}
static u32 pattern(s32 off){return(u8)((off+16)*29+91);}
static u32 initialWord(s32 off){return(pattern(off)<<24)|(pattern(off+1)<<16)|(pattern(off+2)<<8)|pattern(off+3);}
static u16 initialHalf(s32 off){return(u16)((pattern(off)<<8)|pattern(off+1));}
static void hashResult(u32*h,HeightResult71820*a){u32 i;hash(h,floatBits(a->height));for(i=0;i<9;i++)hash(h,(u16)a->vertices[i]);hash(h,(u16)a->pad16);hash(h,a->metadata);hash(h,a->flags);hash(h,a->state);hash(h,a->pad1E);hash(h,(u32)a->value);}
static void snapshot(u32*h){u32 i;hashResult(h,&outputs[0].value);hashResult(h,&outputs[1].value);for(i=0;i<3;i++)hash(h,floatBits(position[i]));hash(h,floatBits(D_800DBE68));hash(h,floatBits(D_800DBE6C));hash(h,floatBits(D_800DBE70));hash(h,floatBits(D_800DBE74));hash(h,D_800DBE5C!=0);hash(h,(u32)(D_800DBE3C-triangles));}
static void record(u32 code,u32 a,u32 b){hash(&trace,code);hash(&trace,a);if(code==2)hash(&trace,b);snapshot(&trace);calls++;}
void func_150A49F4(s32 index){u32 i;if(c->real)record(1,(u32)index,0);D_800DBE3C=&triangles[c->base];for(i=0;i<4;i++)derived[i]=0x110000u+(i+1)*0x100u;context=(u32)index;}
WRAPPER
void func_1510F800(s32 index){record(0,(u32)index,0);if(c->mutation&1){position[0]=1.75f;position[1]=20.0f;position[2]=-2.75f;}native_original_context_wrapper(index);}
s32 func_150A3A70(s32 x,s32 z){u32 i;record(2,(u32)x,(u32)z);if(c->mutation&2)position[1]=2.0f;if(c->mutation&4)outputs[0].value.height=6.0f;if(c->mutation&8)for(i=0;i<8;i++)D_800D3300[i].fixedHeight=(s32)(7-i)*256;if(c->mutation&16)D_800DBE5C=0;return(s32)c->count;}
FUNCTIONS
static u32 readonlyHash(void){u32 h=2166136261u,i;u8*p;p=(u8*)triangles;for(i=0;i<sizeof(triangles);i++)hash(&h,p[i]);p=(u8*)vertices;for(i=0;i<sizeof(vertices);i++)hash(&h,p[i]);p=(u8*)metadata;for(i=0;i<sizeof(metadata);i++)hash(&h,p[i]);return h;}
static void initialize(void){u32 k,i,j;HeightResult71820*a;u8*p;
 for(k=0;k<2;k++){a=&outputs[k].value;p=(u8*)&outputs[k];for(i=0;i<sizeof(outputs[k]);i++)p[i]=(u8)(i*29+91);a->height=fromBits(initialWord(0));for(i=0;i<9;i++)a->vertices[i]=(s16)initialHalf(4+(s32)i*2);a->pad16=(s16)initialHalf(22);a->metadata=initialWord(24);a->flags=(u8)(c->flags^(k?128:0));a->state=(u8)pattern(29);a->pad1E=initialHalf(30);a->value=(s32)initialWord(32);}
 position[0]=fromBits(c->x);position[1]=fromBits(c->y);position[2]=fromBits(c->z);D_80098D44=-10000.0f;D_800DBE68=fromBits(0xBD800000u);D_800DBE6C=fromBits(0xBD800001u);D_800DBE70=fromBits(0xBD800002u);D_800DBE74=fromBits(0xBD800003u);
 for(k=0;k<8;k++){for(i=0;i<3;i++){for(j=0;j<5;j++){s32 index=(s32)j-2;vertices[k][i][j].x=(s16)(-32768+(s32)k*731+(s32)i*113+index*17);vertices[k][i][j].y=(s16)(-32768+(s32)k*731+(s32)i*113+index*17+32701);vertices[k][i][j].z=(s16)(-32768+(s32)k*731+(s32)i*113+index*17+65402);for(u32 n=0;n<10;n++)vertices[k][i][j].pad6[n]=(u8)((index*16+6+(s32)n)*13+(s32)k*37+(s32)i*19+5);}triangles[k].vertices[i]=&vertices[k][i][2];}D_800D3300[k].fixedHeight=(s32)c->h[k%4];D_800D3300[k].triangle=&triangles[k];D_800D3300[k].vertexIndex=(s32)c->index;D_800D3300[k].padC=(s32)(0x76543210u+k);}
 for(i=0;i<24;i++)metadata[i]=0x81230000u+(((s32)i-8)&65535);D_800DBE5C=c->metadata?&metadata[8]:0;D_800DBE3C=&triangles[c->base];for(i=0;i<4;i++)derived[i]=0x210000u+(i+1)*0x100u;context=0xDEADBEEFu;trace=2166136261u;calls=0;readonlyBefore=readonlyHash();
}
static u32 state(void){u32 h=2166136261u,k,i;for(k=0;k<2;k++){hashResult(&h,&outputs[k].value);for(i=0;i<16;i++)hash(&h,outputs[k].before[i]);for(i=0;i<16;i++)hash(&h,outputs[k].after[i]);}
 for(i=0;i<3;i++)hash(&h,floatBits(position[i]));hash(&h,floatBits(D_800DBE68));hash(&h,floatBits(D_800DBE6C));hash(&h,floatBits(D_800DBE70));hash(&h,floatBits(D_800DBE74));hash(&h,D_800DBE5C!=0);hash(&h,(u32)(D_800DBE3C-triangles));for(i=0;i<4;i++)hash(&h,derived[i]);hash(&h,context);
 for(i=0;i<8;i++){hash(&h,(u32)D_800D3300[i].fixedHeight);hash(&h,(u32)(D_800D3300[i].triangle-triangles));hash(&h,(u32)D_800D3300[i].vertexIndex);hash(&h,(u32)D_800D3300[i].padC);}return h;}
static int check(s32(*fn)(f32*,f32,HeightResult71820*)){u32 i;for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){s32 result;c=&rows[i];initialize();result=fn(position,fromBits(c->threshold),&outputs[0].value);failure[0]=i;if(state()!=c->stateHash){failure[1]=1;return 1;}if(trace!=c->traceHash||calls!=c->calls||(u32)result!=c->result){failure[1]=2;return 2;}if(readonlyHash()!=readonlyBefore){failure[1]=3;return 3;}}return 0;}
static int run(void){if(check(candidate))return 1;
CONTROLS
return 0;}
__attribute__((force_align_arg_pointer)) void _start(void){int r=run();if(r)__asm__ volatile(".byte 0xcd,0x80"::"a"(4),"b"(2),"c"(failure),"d"(8):"memory");__asm__ volatile(".byte 0xcd,0x80"::"a"(1),"b"(r):"memory");__builtin_unreachable();}
'''
 controls='\n'.join('if(!check('+name.replace('-','_')+')){failure[0]='+str(i)+';failure[1]=99;return 2;}'for i,name in enumerate(mutations(selected)))
 return text.replace('TYPES',types).replace('ROWS',',\n'.join(rows)).replace('WRAPPER',wrapper).replace('FUNCTIONS',functions).replace('CONTROLS',controls)
def main():
 selected=body((out/'final-owner.c').read_text(),'func_150450CC');p=out/'native.c';p.write_text(program(selected));profiles={}
 for opt in('-O0','-O2','-O3'):
  exe=out/('native'+opt);r=subprocess.run(native_command(opt)+['-fmax-errors=3','-fno-diagnostics-show-caret','-fno-strict-aliasing','-Wno-unused-variable',str(p),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert not r.returncode and not r.stdout and not r.stderr,r.stdout+r.stderr
  r=subprocess.run([str(exe)],capture_output=True,timeout=60);assert r.returncode==0 and not r.stdout and not r.stderr,(opt,r.returncode,struct.unpack('<II',r.stderr)if len(r.stderr)==8 else r.stderr);profiles[opt]=dict(exit=0,UBSan=True,cases=len(cases()),effective_controls=12)
 report=dict(profiles=profiles,SDK32_layout=True,all_result_fields_padding_and_canaries=True,readonly_triangle_vertex_metadata_canaries=True,independent_expected_state=True,original_C_context_wrapper=True,guest_frame_and_physical_aliases_excluded=True,spatial_scan_is_bounded_provider=True)
 (out/'native.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
