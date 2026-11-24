"""Defined SDK32 node callbacks, logical pointer cells and effective controls."""
import json,subprocess
from tools.experiments import game_descriptor_matrix_history_15188f84_match as p
from tools.tests import game_descriptor_matrix_history_15188f84_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r,o=p.ROOT,p.OUT
def mix(h,v):return((h^(v&0xffffffff))*16777619)&0xffffffff
def hashed(values):
 h=2166136261
 for v in values:h=mix(h,v)
 return h
def main():
 rows=[];excluded=0
 for c in g.cases():
  if c.residue or c.alias in(3,4):excluded+=1;continue
  m,q=g.reference(g.fixture(c),c);values=[getattr(c,n)for n in c.__dataclass_fields__]
  values += [hashed(m[a+i]for a,n in g.banks(c)for i in range(n)),hashed(v for t,a in q.calls for v in(t,len(a),*a)),hashed(v for row in q.observed for v in row),hashed(v for packet in q.copies for v in packet)]
  rows.append('{{'+','.join(str(v&0xffffffff)+'u'for v in values)+'}}')
 (o/'native-vectors.h').write_bytes(('static const Vector vectors[]={\n'+',\n'.join(rows)+'\n};\n').encode())
 prefix='''#include <ultra64.h>
typedef struct ListNode15188A58 {u8 active,kind,cleared,opacity,mode,retained05;s16 timer;u8 *buffer;struct ListNode15188A58 *next;s32 key;} ListNode15188A58;
typedef struct {u16 identity,retained;} MatrixDescriptorIndex15188F84;
typedef struct {u32 f[15];} Vector;
#include "native-vectors.h"
typedef struct {u8 before[16];ListNode15188A58 node;u8 rest[44];u8 after[16];} NodeBox;
typedef struct {u8 before[16];MatrixDescriptorIndex15188F84 entries[16];u8 after[16];} EntryBox;
typedef struct {MatrixDescriptorIndex15188F84 *ids[4];Mtx *matrices[2];u16 counts[4];u32 retained20;u8 *descriptors;u8 tail[24];} Globals;
typedef struct {u8 before[16];Globals value;u8 after[16];} GlobalBox;
typedef struct {MatrixDescriptorIndex15188F84 **ids[4];Mtx **matrices[2];u8 tail[40];} Rodata;
typedef struct {u8 before[16];Rodata value;u8 after[16];} RodataBox;
typedef struct {u8 before[16];u8 value;u8 after[16];} FlagBox;
typedef struct {u8 before[16];Mtx matrices[65536];u8 after[16];} MatrixBox;
typedef struct {u8 before[16];Mtx matrices[1024];u8 after[16];} HistoryBox;
static NodeBox nodeBox;static EntryBox entryBox;static GlobalBox globals;static RodataBox rodata;static FlagBox flag;
static MatrixBox matrixA,matrixB;static HistoryBox historyA,historyB;static u8 descriptors[65536*160];
static const Vector *v;static u32 callHash,observedHash,copyHash,calls,error;
void func_15188F84(ListNode15188A58 *);
static void (*callback[2])(ListNode15188A58 *);
#define D_800BE9C0 flag.value
#define D_800DBEE8 globals.value.counts
#define D_800DBEF4 globals.value.descriptors
#define D_80089240 rodata.value.ids
#define D_80089250 rodata.value.matrices
#define NODE nodeBox.node
#define OFF(t,m) __builtin_offsetof(t,m)
_Static_assert(sizeof(void*)==4&&sizeof(s32)==4&&sizeof(Mtx)==64&&(s32)0xffffffffu==-1,"SDK32");
_Static_assert(sizeof(ListNode15188A58)==20&&OFF(ListNode15188A58,buffer)==8&&OFF(ListNode15188A58,key)==16,"node prefix");
_Static_assert(sizeof(Globals)==64&&OFF(Globals,matrices)==16&&OFF(Globals,counts)==24&&OFF(Globals,descriptors)==36&&sizeof(Rodata)==64,"global pointer cells");
static u32 mix(u32 h,u32 x){return(h^x)*16777619u;}
static u32 word(const void *p){u32 x;__builtin_memcpy(&x,p,4);return x;}
static u16 be16(const void *p){const u8 *b=p;return(u16)(((u32)b[0]<<8)|b[1]);}
static u32 logical(const void *p){u32 x=(u32)p,bases[]={@NODE@-16,@IDS@-16,@GLOBALS@-16,@RODATA@-16,@FLAG@-16,@MATRICES@-16,@OTHER@-16,@HISTA@-16,@HISTB@-16,@DESCS@};
 u8 *native[]={(u8*)&nodeBox,(u8*)&entryBox,(u8*)&globals,(u8*)&rodata,(u8*)&flag,(u8*)&matrixA,(u8*)&matrixB,(u8*)&historyA,(u8*)&historyB,descriptors};
 u32 sizes[]={sizeof(nodeBox),sizeof(entryBox),sizeof(globals),sizeof(rodata),sizeof(flag),sizeof(matrixA),sizeof(matrixB),sizeof(historyA),sizeof(historyB),sizeof(descriptors)},i,start;
 if(!p)return 0;for(i=0;i<10;i++){start=(u32)native[i];if(x>=start&&x<start+sizes[i])return bases[i]+x-start;}
 if(x==(u32)func_15188F84)return @ENTRY@;error=1;return 0xffffffffu;
}
static u8 *mapped(u32 a){u32 bases[]={@NODE@-16,@IDS@-16,@GLOBALS@-16,@RODATA@-16,@FLAG@-16,@MATRICES@-16,@OTHER@-16,@HISTA@-16,@HISTB@-16,@DESCS@,@CALLBACK@+4};
 u8 *native[]={(u8*)&nodeBox,(u8*)&entryBox,(u8*)&globals,(u8*)&rodata,(u8*)&flag,(u8*)&matrixA,(u8*)&matrixB,(u8*)&historyA,(u8*)&historyB,descriptors,(u8*)&callback[1]};
 u32 sizes[]={sizeof(nodeBox),sizeof(entryBox),sizeof(globals),sizeof(rodata),sizeof(flag),sizeof(matrixA),sizeof(matrixB),sizeof(historyA),sizeof(historyB),sizeof(descriptors),4},i;
 for(i=0;i<11;i++)if(a>=bases[i]&&a<bases[i]+sizes[i])return native[i]+a-bases[i];error=1;return (u8*)&error;
}
static u32 byte(u32 a){u32 at,x;
 if(a>=@NODE@+8&&a<@NODE@+20){at=(a-@NODE@)&~3u;x=logical((void*)word((u8*)&NODE+at));return(x>>(8*(3-((a-@NODE@)&3))))&255;}
 if(a>=@NODE@+6&&a<@NODE@+8){x=(u16)NODE.timer;return(x>>(8*(1-(a-@NODE@-6))))&255;}
 if(a>=@IDS@&&a<@IDS@+64&&((a-@IDS@)&3)<2){x=entryBox.entries[(a-@IDS@)/4].identity;return(x>>(8*(1-((a-@IDS@)&1))))&255;}
 if(a>=@GLOBALS@&&a<@GLOBALS@+24){at=(a-@GLOBALS@)&~3u;x=logical((void*)word((u8*)&globals.value+at));return(x>>(8*(3-((a-@GLOBALS@)&3))))&255;}
 if(a>=@GLOBALS@+24&&a<@GLOBALS@+32){x=globals.value.counts[(a-@GLOBALS@-24)/2];return(x>>(8*(1-((a-@GLOBALS@)&1))))&255;}
 if(a>=@GLOBALS@+36&&a<@GLOBALS@+40){x=logical(globals.value.descriptors);return(x>>(8*(3-(a-@GLOBALS@-36))))&255;}
 if(a>=@RODATA@&&a<@RODATA@+24){at=(a-@RODATA@)&~3u;x=logical((void*)word((u8*)&rodata.value+at));return(x>>(8*(3-((a-@RODATA@)&3))))&255;}
 if(a>=@CALLBACK@+4&&a<@CALLBACK@+8){x=logical((void*)callback[1]);return(x>>(8*(3-(a-@CALLBACK@-4))))&255;}
 return *mapped(a);
}
static u32 ranges[13][2];static u32 rangeCount;
static void region(u32 at,u32 n){u32 i;ranges[rangeCount][0]=at;ranges[rangeCount++][1]=n;for(i=0;i<n;i++)*mapped(at+i)=(u8)((at+i)*13+v->f[10]*7+89);}
static u32 publicHash(void){u32 h=2166136261,i,j;for(i=0;i<rangeCount;i++)for(j=0;j<ranges[i][1];j++)h=mix(h,byte(ranges[i][0]+j));return h;}
static void observe(void){u32 a[]={D_800BE9C0,NODE.kind,NODE.cleared,logical(NODE.buffer),logical((void*)NODE.key),D_800DBEE8[0],logical(globals.value.matrices[0]),entryBox.entries[0].identity},i;for(i=0;i<8;i++)observedHash=mix(observedHash,a[i]);}
void bcopy(const void *source,void *destination,int length){u8 temporary[64];u32 i,a[]={logical(source),logical(destination),(u32)length};calls++;callHash=mix(mix(callHash,@COPY@),3);for(i=0;i<3;i++)callHash=mix(callHash,a[i]);observe();if(length!=64){error=1;return;}
 for(i=0;i<64;i++){temporary[i]=((const u8*)source)[i];copyHash=mix(copyHash,temporary[i]);}for(i=0;i<64;i++)((u8*)destination)[i]=temporary[i];
 if(calls==1){if(v->f[6]&1){D_800BE9C0^=1;NODE.kind=(u8)(v->f[2]+1);NODE.cleared=(u8)v->f[2];}
 if(v->f[6]&2)NODE.buffer=(u8*)historyB.matrices;
 if(v->f[6]&4){globals.value.matrices[v->f[3]]=matrixB.matrices;NODE.key=(s32)(descriptors+777*160);}
 if(v->f[6]&8)NODE.cleared=255;
 if(v->f[6]&16){D_800DBEE8[0]=0;D_800DBEF4=descriptors+160;entryBox.entries[0].identity=65535;}
 if(v->f[6]&32){u8 *at=NODE.buffer+(((v->f[3]^1)*v->f[2])+2)*64;for(i=0;i<8;i++)at[i]^=0x5a;}}
}
'''
 suffix='''
static void initialize(void){u32 i,cur,alias=v->f[7];s32 off;error=calls=0;callHash=observedHash=copyHash=2166136261;rangeCount=0;
 cur=alias?@HISTA@+(alias==2?0:(v->f[2]-1+v->f[3]*v->f[2])*64):@MATRICES@+v->f[5]*64;
 region(@NODE@-16,96);region(@IDS@-16,4*(v->f[0]<16?v->f[0]:16)+32);region(@GLOBALS@-16,80);region(@RODATA@-16,64);region(@RODATA@,64);region(@FLAG@-16,33);region(@CALLBACK@+4,4);region(cur-16,96);region(@OTHER@+v->f[5]*64-16,96);
 for(i=0;i<2;i++){region((i?@HISTB@:@HISTA@)-16,(v->f[2]+1)*64+32);region((i?@HISTB@:@HISTA@)+v->f[2]*64-16,(v->f[2]+1)*64+32);}
 for(i=0;i<4;i++){globals.value.ids[i]=entryBox.entries;D_80089240[i]=&globals.value.ids[i];globals.value.counts[i]=be16(&globals.value.counts[i]);}
 for(i=0;i<2;i++){globals.value.matrices[i]=(Mtx*)mapped(cur-v->f[5]*64);D_80089250[i]=&globals.value.matrices[i];}
 D_800DBEE8[0]=(u16)v->f[0];D_800DBEF4=descriptors;D_800BE9C0=(u8)v->f[3];
 for(i=0;i<16;i++)entryBox.entries[i].identity=be16(&entryBox.entries[i].identity);
 for(i=0;i<(v->f[0]<16?v->f[0]:16);i++)entryBox.entries[i].identity=(u16)(i==v->f[1]?v->f[5]:16+i);
 NODE.active=1;NODE.kind=(u8)v->f[2];NODE.cleared=(u8)v->f[4];NODE.opacity=61;NODE.timer=10;NODE.buffer=(u8*)historyA.matrices;NODE.next=0;NODE.key=(s32)(descriptors+(v->f[1]!=0xffffffffu?v->f[5]:999)*160);callback[1]=func_15188F84;
 (void)off;
}
static int run(void){u32 i;for(i=0;i<sizeof(vectors)/sizeof(*vectors);i++){v=&vectors[i];initialize();callback[1](&NODE);if(error)return 10;if(publicHash()!=v->f[11])return 11;if(callHash!=v->f[12])return 12;if(observedHash!=v->f[13])return 13;if(copyHash!=v->f[14])return 14;}return 0;}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 tokens=dict(NODE=g.NODE,IDS=g.IDS,GLOBALS=g.S['_id_cells'],RODATA=g.S['D_80089240'],FLAG=g.S['D_800BE9C0'],MATRICES=g.MATRICES,OTHER=g.OTHER_MATRICES,HISTA=g.BUFFERS[0],HISTB=g.BUFFERS[1],DESCS=g.DESCRIPTORS,ENTRY=g.ENTRY,COPY=g.S['bcopy'],CALLBACK=g.S['_registry'])
 for token,value in tokens.items():prefix=prefix.replace('@'+token+'@',hex(value)+'u');suffix=suffix.replace('@'+token+'@',hex(value)+'u')
 def run(body,label,opt):
  f=o/label;src=f.with_suffix('.c');src.write_bytes((prefix+body+suffix).encode());q=subprocess.run(native_command(opt)+['-fstrict-aliasing',str(src),'-o',str(f)],cwd=r,capture_output=True,text=True);(o/(label+'-compile.txt')).write_bytes((q.stdout+q.stderr).encode());assert q.returncode==0,q.stderr[-5000:];q=subprocess.run([str(f)],capture_output=True,text=True,timeout=30);assert not q.stderr;return q.returncode
 body=p.MANIFEST['body'];profiles={}
 for opt in('-O0','-O2','-O3'):
  code=run(body,'native-'+opt[1:],opt);assert code==0,(opt,code);profiles[opt]=dict(cases=len(rows),SDK32=True,UBSan=True,strict_aliasing=True,compatible_callback_type=True,all_mapped_public_guard_bytes_hashed=True,all_calls_observations_copy_bytes_hashed=True)
 controls=[('missing-clear','record->cleared = 0','record->cleared = 1'),('wrong-stride','entries->identity * 0xA0','entries->identity * 0xA4'),('wrong-page','D_800BE9C0 * snapshots','(D_800BE9C0 ^ 1) * snapshots'),('wrong-other-page','(D_800BE9C0 ^ 1) * snapshots','D_800BE9C0 * snapshots'),('last-slot','snapshots == next','snapshots == index'),('wrong-source-slot','index + other + 1','index + other'),('wrong-destination-slot','buffer + current','buffer + current + 1'),('wrong-copy-length','destination, 64','destination, 63'),('copy-direction','bcopy(source, destination','bcopy(destination, source'),('stale-buffer','    Mtx *buffer;','    Mtx *buffer = (Mtx *)record->buffer;'),('stale-filled','record->cleared != record->kind','record->cleared != snapshots'),('missing-final-increment','record->cleared++;','record->cleared = record->cleared;')]
 outcomes=[]
 for name,old,new in controls:
  assert old in body,name;bad=body.replace(old,new)
  if name=='stale-buffer':bad=bad.replace('                buffer = (Mtx *)record->buffer;\n','')
  code=run(bad,'control-'+name,'-O2');assert code in(10,11,12,13,14),(name,code);outcomes.append(dict(control=name,comparison_exit=code,source_sha256=p.sha(o/('control-'+name+'.c')),binary_sha256=p.sha(o/('control-'+name))))
 q=dict(profiles=profiles,effective_source_controls=outcomes,guest_only_unaligned_or_partial_matrix_alias_cases=excluded,no_signal_or_UBSan_trap_counted=True,void_result_not_compared=True,source_installed=p.installed(),matching_credit=0);(o/'native.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(dict(cases=len(rows),excluded=excluded,controls=len(outcomes),profiles=list(profiles))),flush=True);return q
