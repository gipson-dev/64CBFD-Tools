"""Native32 owner row traversal and eight effective semantic controls."""
from pathlib import Path
import subprocess
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import game_owner_row_cleanup_oracle as g

def qualify(root,output,body):
 r,o=Path(root),Path(output)
 controls=[]
 controls.append(('omit-owner-store',body.replace('*(u8 **)(record + 0x24) = owner;','(void)owner;')))
 controls.append(('reload-freed-next',body.replace('record = D_800DD198[D_800DD190];','record = *(u8 **)(record + 8);')))
 controls.append(('ignore-live-next-slot',body.replace('    u8 *record;','    u8 *record;\n    u8 *cachedNext;').replace('D_800DD198[D_800DD190] = *(u8 **)(record + 8);','D_800DD198[D_800DD190] = *(u8 **)(record + 8);\n                cachedNext = *(u8 **)(record + 8);').replace('record = D_800DD198[D_800DD190];','record = cachedNext;')))
 controls.append(('unsigned-next-index',body.replace('record = D_800DD198[D_800DD190];','record = D_800DD198[(u8)D_800DD190];')))
 controls.append(('omit-depth-decrement',body.replace('D_800DD190--;','(void)D_800DD190;')))
 controls.append(('skip-second-row',body.replace('row += 0x1A0;','row += 0x340;')))
 controls.append(('advisory-extra-depth-exit',body.replace('while (row != rowEnd);','while (row != rowEnd && D_800DD190 >= 0);')))
 controls.append(('advisory-prime-once',body.replace('        do {','        D_800DD190++;\n        do {',1).replace('            D_800DD190++;\n','')))
 assert len(controls)==8 and all(text!=body for _,text in controls)
 rows=[];seen=set()
 for c in g.cases():
  owner=0 if c.owner==0 else 1 if c.owner==g.OWNER else 2 if c.owner==0x87654321 else 3
  key=(owner,c.depth&255,c.pattern,c.mutation,c.seed)
  if key in seen:continue
  seen.add(key);rows.append('{'+','.join('0x%Xu'%v for v in key)+'}')
 code=r'''
 #include <ultra64.h>
 typedef struct Record102 struct102;
 typedef struct {s8 depth;u8 pad[3];u8 table[0x340];u8*slots[512];u32 records[7][16];u32 owners[32];} World;
 static union {World w;u32 align;u8 b[sizeof(World)];} world,expected;
 struct Case{u32 owner,depth,pattern,mutation,seed;};static const struct Case cases[]={ROWS};static const struct Case*c;
 static u32 count,error,logNode[64],logOwner[64];static u8*activeOwner;
 #define D_800DCE50 (world.w.table)
 #define D_800DD190 (world.w.depth)
 #define D_800DD198 (world.w.slots+128)
 static u8*node(u32 n){return(u8*)world.w.records[n];}
 static u8*emap(u8*p){return expected.b+(p-world.b);}
 static void putword(u8*p,u32 v){*(u32*)p=v;}
 static u8*getptr(u8*p){return*(u8**)p;}
 static s32 depth(u32 e){return e?expected.w.depth:world.w.depth;}
 static void setdepth(u32 e,s32 value){if(e)expected.w.depth=(s8)value;else world.w.depth=(s8)value;}
 static u8**slot(u32 e){return e?expected.w.slots+128+depth(e):world.w.slots+128+depth(e);}
 static void repair(u32 e,u8*target){s32 i,n=depth(e);u8**slots=e?expected.w.slots+128:world.w.slots+128;
  for(i=0;i<n;i++)if(slots[i]==target)slots[i]=getptr(e?emap(target+8):target+8);
 }
 static void effect(u32 e,u8*record){u8*p=e?emap(record):record;u8*pending=*slot(e),*next=getptr(p+8);s32 saved;
  if(c->mutation==1)*slot(e)=0;
  if(c->mutation==2){setdepth(e,depth(e)+1);*slot(e)=pending;}
  if(c->mutation==3){putword(e?emap(world.w.table+0x21C):world.w.table+0x21C,(u32)node(6));putword(e?emap(node(6)+8):node(6)+8,0);}
  if(c->mutation==4&&next){saved=depth(e);setdepth(e,saved+1);repair(e,next);setdepth(e,saved);putword(e?emap(next+8):next+8,0);}
  putword(p+8,0);
 }
 void func_1516972C(struct102*value){u8*p=(u8*)value;u32 i;
  for(i=0;i<7;i++)if(p==node(i))break;if(i==7){error=1;return;}
  if(count>=64){error=1;return;}logNode[count]=i;logOwner[count]=(u32)getptr(p+0x24);if(logOwner[count]!=(u32)activeOwner)error=1;count++;effect(0,p);
 }
 '''.replace('ROWS',',\n'.join(rows))
 for i,(_,text)in enumerate([('selected',body)]+controls):code+=text.replace('func_1518BBF4(','root_%d('%i)+'\n'
 code+='static void(*roots[])(u8*)={'+','.join('root_%d'%i for i in range(9))+'};\n'
 code+=r'''
 static int run(void){u32 n,k,j,t,row,expectedCount,killed=0,bad,heads[2],lengths[2],chain[2][3],expectedNode[64],expectedOwner[64];u8*p,*owner;
  for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++)for(k=0;k<9;k++){
   c=&cases[n];for(j=0;j<sizeof(world.b);j++)world.b[j]=0;
   for(t=0;t<7;t++)for(j=0;j<64;j++)node(t)[j]=(j*29+c->seed*11+90)&255;
   for(t=0;t<7;t++)putword(node(t)+8,0);
   lengths[0]=lengths[1]=0;
   if(c->pattern==1){lengths[0]=1;chain[0][0]=0;}
   if(c->pattern==2){lengths[0]=2;chain[0][0]=0;chain[0][1]=1;lengths[1]=1;chain[1][0]=2;}
   if(c->pattern==3){lengths[0]=3;chain[0][0]=0;chain[0][1]=1;chain[0][2]=2;lengths[1]=2;chain[1][0]=3;chain[1][1]=4;}
   if(c->pattern==4){lengths[0]=2;chain[0][0]=0;chain[0][1]=1;lengths[1]=1;chain[1][0]=1;}
   if(c->pattern==5){lengths[1]=2;chain[1][0]=3;chain[1][1]=4;}
   for(row=0;row<2;row++){heads[row]=lengths[row]?(u32)node(chain[row][0]):0;putword(world.w.table+row*0x1A0+0x7C,heads[row]);for(j=1;j<lengths[row];j++)putword(node(chain[row][j-1])+8,(u32)node(chain[row][j]));}
   world.w.depth=(s8)c->depth;owner=c->owner?(u8*)world.w.owners+16*(c->owner-1):0;activeOwner=owner;
   for(j=0;j<sizeof(world.b);j++)expected.b[j]=world.b[j];expectedCount=0;
   if(owner)for(row=0;row<2;row++){
    p=getptr(expected.w.table+row*0x1A0+0x7C);setdepth(1,depth(1)+1);
    while(p){if(expectedCount>=64)return 9;*slot(1)=getptr(emap(p+8));putword(emap(p+0x24),(u32)owner);for(t=0;t<7;t++)if(p==node(t))break;if(t==7)return 10;expectedNode[expectedCount]=t;expectedOwner[expectedCount]=(u32)owner;expectedCount++;effect(1,p);p=*slot(1);}
    setdepth(1,depth(1)-1);
   }
   count=error=0;roots[k](owner);bad=error||count!=expectedCount;
   for(j=0;j<count&&j<expectedCount;j++)if(logNode[j]!=expectedNode[j]||logOwner[j]!=expectedOwner[j])bad=1;
   for(j=0;j<sizeof(world.b);j++)if(world.b[j]!=expected.b[j])bad=1;
   if(!k&&bad)return 2;if(k&&bad)killed|=1u<<(k-1);
  }
  return killed==255?0:3;
 }
 '''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 reports=[]
 for opt in('-O0','-O2','-O3'):
  p=o/('native12-'+opt[1:]);p.with_suffix('.c').write_text(code);q=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p.with_suffix('.c')),'-o',str(p)],cwd=r,capture_output=True,text=True);assert q.returncode==0,(q.stdout,q.stderr);q=subprocess.run([str(p)],capture_output=True);assert q.returncode==0,(opt,q.returncode,q.stdout,q.stderr)
  reports.append(dict(profile=opt,cases=len(rows),executions=len(rows)*9,complete_public_World_bytes=True,signed_indices_use_valid_interior_array=True,depth_independent_of_table_endpoint=True,live_slots_and_depth_checked=True,modeled_nested_repair=True,eight_controls_effective=True,controls=[n for n,_ in controls],UBSan=True,advisory_semantic_changes_rejected=True))
 return reports
