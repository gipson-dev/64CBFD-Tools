import json,subprocess,sys
from pathlib import Path
from tools.experiments import game_record_tail_release_15114b94_match as p
out=p.out;root=p.root
from tools.tests import game_record_tail_release_15114b94_oracle as g
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 selected=body((out/'independent-selected.c').read_text(),'func_15114B94')
 controls={
  'bound':('index < (u32)D_800DBEF0','index <= (u32)D_800DBEF0'),
  'index':('index * 0xA0','(index + 1) * 0xA0'),
  'release':('func_1516972C(*(struct102 **)(record + 0x94));','(void)*(struct102 **)(record + 0x94);'),
  'clear':('= NULL;','= *(struct102 **)(D_800DBEF4 + offset + 0x94);'),
  'flag':('|= 8;','|= 4;'),
  'marker':('[offset + 0x6E] = 1','[offset + 0x6E] = 2'),
  'tail_flag':('+ 0x70] & 8','+ 0x70] & 4'),
  'boundary':('boundary = count - D_800DBF98','boundary = count'),
  'reserve_compare':('count - 1 >= boundary','count - 1 > boundary'),
  'reserve_decrement':('D_800DBF98--','D_800DBF98 -= 2'),
  'count_store':('D_800DBEF0 = --count;','D_800DBEF0 = --count + 1;'),
 }
 code=r'''#include <ultra64.h>
 #include "structs.h"
 _Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
 typedef struct {u8 pad00[0x6e];u8 marker,pad6f,flags,pad71[0x23];struct102 *child;u8 pad98[8];} Entry;
 _Static_assert(sizeof(Entry)==0xa0 && __builtin_offsetof(Entry,marker)==0x6e && __builtin_offsetof(Entry,flags)==0x70 && __builtin_offsetof(Entry,child)==0x94,"record layout");
 s32 D_800DBEF0;u8 *D_800DBEF4;u32 D_800DBF98;static Entry A[10],B[10];static struct102 children[10];
 struct Case {u32 count,index,mask,reserved,child,mutate;u8 flags_a[10],flags_b[10],marker_a[10],marker_b[10],child_a[10],child_b[10];u32 out_count,out_reserved,out_b,calls;};
 static const struct Case cases[]={
 '''
 for c in g.cases():
  m,calls=g.reference(c);vals=[c.count,c.index,c.mask,c.reserved,c.child,c.mutate];arrays=[]
  for off,size in ((0x70,1),(0x6e,1),(0x94,4)):
   for base in (g.A,g.B):arrays.append([int(g.read(m,base+0xa0*i+off,size)!=0) if off==0x94 else g.read(m,base+0xa0*i+off,size) for i in range(10)])
  arr=lambda xs:'{'+','.join(str(v)for v in xs)+'}'
  code+='{'+','.join('0x%Xu'%v for v in vals)+','+','.join(arr(x)for x in arrays)+','+','.join(str(v)for v in (g.read(m,g.COUNT),g.read(m,g.RESERVED),int(g.read(m,g.BASE)==g.B),len(calls)))+'},\n'
 code+=r'''};
 static const struct Case *current;static u32 calls,bad;
 void func_1516972C(struct102 *child){calls++;if(child!=&children[current->index])bad=1;if(current->mutate){D_800DBEF4=(u8*)B;B[current->index].flags^=0x40;if(current->mutate==2){D_800DBEF0=current->count?current->count-1:0;D_800DBF98=2;}}}
 '''
 for key,text in {'selected':selected,**{n:selected.replace(a,b,1) for n,(a,b) in controls.items()}}.items():
  if key!='selected':assert text!=selected,key
  code+='\n'+text.replace('func_15114B94','test_'+key,1)+'\n'
 code+=r'''
 typedef void(*T)(u32);
 static int check(T test){u32 n,i;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
  const struct Case*c=&cases[n];u8 before_a[sizeof A],before_b[sizeof B];u8*a=(u8*)A,*b=(u8*)B;
  for(i=0;i<sizeof A;i++){a[i]=(i*13+11)&255;b[i]=(i*13+11)&255;}
  D_800DBEF0=c->count;D_800DBEF4=(u8*)A;D_800DBF98=c->reserved;
  for(i=0;i<10;i++){A[i].flags=((i%2)?0x40:0x20)|((c->mask&(1u<<i))?8:0);B[i].flags=(((i+1)%2)?0x40:0x20)|((c->mask&(1u<<i))?8:0);A[i].child=B[i].child=c->child?&children[i]:NULL;}
  for(i=0;i<sizeof A;i++){before_a[i]=a[i];before_b[i]=b[i];}current=c;calls=bad=0;test(c->index);
  if(bad||calls!=c->calls||(u32)D_800DBEF0!=c->out_count||D_800DBF98!=c->out_reserved||D_800DBEF4!=(u8*)(c->out_b?B:A))return 1;
  for(i=0;i<10;i++)if(A[i].flags!=c->flags_a[i]||B[i].flags!=c->flags_b[i]||A[i].marker!=c->marker_a[i]||B[i].marker!=c->marker_b[i]||(A[i].child!=NULL)!=c->child_a[i]||(B[i].child!=NULL)!=c->child_b[i])return 2;
  for(i=0;i<sizeof A;i++){u32 p=i%0xa0;if(p!=0x6e&&p!=0x70&&(p<0x94||p>=0x98)&&(a[i]!=before_a[i]||b[i]!=before_b[i]))return 3;}
  }return 0;}
 static int run(void){int v=check(test_selected);if(v)return v;
 '''
 for i,name in enumerate(controls):code+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 src=out/'native_15114B94_screen.c';src.write_text(code);reports={}
 for opt in ('-O0','-O2','-O3'):
  exe=out/('native_15114B94_screen'+opt);v=subprocess.run(native_command(opt)+['-fno-builtin',str(src),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert v.returncode==0 and not v.stdout and not v.stderr,(opt,v.stdout,v.stderr)
  v=subprocess.run([str(exe)],capture_output=True);assert v.returncode==0,(opt,v.returncode,v.stderr);reports[opt]=dict(cases=len(g.cases()),negative_controls=len(controls),UBSan=True)
 report=dict(profiles=reports,helper='modeled with table and count mutations',valid_disjoint_records=True,source_installed=False);(out/'native_15114B94_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
