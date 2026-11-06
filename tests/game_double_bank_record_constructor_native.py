"""SDK native32 constructor ABI, retained bytes and actual factory C integration."""
from dataclasses import replace
from tools.experiments import game_double_bank_record_constructor_candidates as c
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests import game_double_bank_record_constructor_oracle as g
from tools.tests.test_game_row_destination_fill import START

def cases():
    rows=[replace(x,phase=0,mutation=x.mutation&9) for x in g.cases() if x.owner in (0,g.OWNER,g.RESULT+4)]
    rows += [g.Case(flags=f,outcome=o,mutation=m,factory=True) for f in (0,1,2,0xFFFFFFFF) for o in (0,1) for m in (0,1,8,9)]
    return list(dict.fromkeys(rows))

def program(root):
    rows=[]
    for case in cases():
        initial=g.fixture(case);want,_,_=g.reference(initial,case)
        expected=bytearray(want[g.RESULT-16+i] for i in range(0x160))
        if case.outcome:
            for off in (*g.HALVES,*(range(0x128,0x13A,2) if case.flags&1 else ())):
                expected[16+off:18+off]=g.read(want,g.RESULT+off,2).to_bytes(2,'little')
            if case.factory:expected[16+0x20:20+0x20]=(0xAABBCCDD).to_bytes(4,'little')
            expected[16+0x110:20+0x110]=bytes(4)
        owner=0 if case.owner==0 else 1 if case.owner==g.OWNER else 2
        rows.append('{0x%08Xu,%d,0x%08Xu,0x%08Xu,0x%08Xu,%d,%d,%d,"%s"}' % (
            case.kind,owner,case.mode,case.flags,case.variant,case.outcome,case.mutation,case.factory,
            ''.join('\\x%02X'%v for v in expected)))
    factory=body((root/'conker/src/game_1944C0.c').read_text(encoding='utf-8'),'func_15167A68').replace('func_15167A68','factory_impl',1)
    text='#include <ultra64.h>\n'+c.HEADERS+'''
typedef char pointer_width[sizeof(void*)==4?1:-1];
typedef char vertex_size[sizeof(Vtx)==16?1:-1];
typedef char vertex_flag[__builtin_offsetof(Vtx,v.flag)==6?1:-1];
typedef char vertex_tc[__builtin_offsetof(Vtx,v.tc)==8?1:-1];
static u8 storage[0x160] __attribute__((aligned(16))), ownerStorage[0x400];
static u8 *record=storage+16;
static u32 bad,outcome,mutation,flags,useFactory,calls[3];
static void put32(u8*p,u32 v){union{u32 w;u8 b[4];}x;u32 i;x.w=v;for(i=0;i<4;i++)p[i]=x.b[i];}
static void effects(void){u32 i;
 if(mutation&1)for(i=0;i<0x13A;i++)record[i]=(u8)(i*7+0x31);
 if(mutation&8)put32(ownerStorage+0x10,0x33445566);
}
void *func_10003C6C(s32 size,s32 tag,s32 pool,s32 zero,u8 mode){
 calls[1]++;if(size!=((flags&1)?0x13A:0x128)||tag!=1||pool!=1||zero!=0||mode!=1)bad=1;
 effects();return outcome?record:(void*)0;
}
void func_15168A4C(u8*p,s32 kind){calls[2]++;if(p!=record||kind!=0x4B)bad=1;put32(p+0x20,0xAABBCCDD);p[0x44]=0xE7;}
'''+factory+'''
void *func_15167A68(s32 kind,s32 context,s32 size,s32 pool,u8 channel,u8 allocation){
 calls[0]++;if(kind!=0x4B||context!=0||size!=((flags&1)?0x13A:0x128)||pool!=1||channel!=255||allocation!=1)bad=1;
 if(useFactory)return factory_impl(kind,context,size,pool,channel,allocation);
 effects();return outcome?record:(void*)0;
}
'''
    for name,value in dict(selected=c.SELECTED,**g.controls()).items():text+=value.replace(c.FUNCTION,name)+'\n'
    text+='''
typedef struct {u32 kind,owner,mode,flags,variant,outcome,mutation,factory;u8 expected[0x160];} Row;
static const Row rows[]={
'''+',\n'.join(rows)+'''};
typedef void*(*Construct)(s32,void*,s32,s32,s32);
__attribute__((noinline,noclone))static void *invoke(Construct f,s32 k,void*o,s32 m,s32 flags,s32 v){return f(k,o,m,flags,v);}
static int variant(Construct fn,u32 wrapped){
 u32 i,j,r;void *owner,*got;u8 expected[0x160];const Row*row;
 for(r=0;r<sizeof(rows)/sizeof(rows[0]);r++){
  row=rows+r;outcome=row->outcome;mutation=row->mutation;flags=row->flags;useFactory=row->factory;
  for(i=0;i<0x160;i++){storage[i]=(u8)(i*13+89);expected[i]=row->expected[i];}
  for(i=0;i<0x400;i++)ownerStorage[i]=(u8)(i*13+89);
  owner=row->owner==0?(void*)0:row->owner==1?(void*)ownerStorage:(void*)(record+4);
  if(outcome)put32(expected+16+0x110,(u32)owner);
  bad=0;calls[0]=calls[1]=calls[2]=0;
  got=wrapped?invoke(fn,(s32)row->kind,owner,(s32)row->mode,(s32)flags,(s32)row->variant):fn((s32)row->kind,owner,(s32)row->mode,(s32)flags,(s32)row->variant);
  if(bad||got!=(outcome?(void*)record:(void*)0)||calls[0]!=1||calls[1]!=useFactory||calls[2]!=(useFactory&&outcome))return 1;
  for(i=0;i<0x160;i++)if(storage[i]!=expected[i])return 1;
  for(i=0;i<0x400;i++){
   j=(i*13+89)&255;
   if((mutation&8)&&i>=0x10&&i<0x14)j=(0x33445566u>>(8*(i-0x10)))&255;
   if(ownerStorage[i]!=j)return 1;
  }
 }return 0;
}
static int run(void){if(variant(selected,0)||variant(selected,1))return 1;
'''
    for i,name in enumerate(g.controls()):text+=' if(variant(%s,0)!=1)return %d;\n'%(name,i+2)
    return text+'return 0;}\n'+START,len(rows)
