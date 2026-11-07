"""SDK native32 owner search, defined request fields and effective controls."""
from tools.experiments import game_owner_record_lookup_candidates as c
from tools.tests import game_owner_record_lookup_oracle as g

def controls():
    b=c.SELECTED
    return dict(one_row=b.replace('end = (u8 *)&D_800DD190','end = D_800DCE50 + 0x1A0'),second_row_only=b.replace('row = D_800DCE50;','row = D_800DCE50 + 0x1A0;'),wrong_head=b.replace('row + 0x7C','row + 0x78'),pointer_only=b.replace(' || owner[0x3B] == record[0x28]',''),tag_only=b.replace('*(u8 **)(record + 0x24) == owner || ',''),both_required=b.replace(' || ',' && '),wrong_tag=b.replace('owner[0x3B] ==','owner[0x3A] =='),reject_zero=b.replace('        case 0:\n',''),wrong_special_kind=b.replace('        case 7:','        case 8:'),wrong_first_base=b.replace('request.firstBase = 10.0f','request.firstBase = 11.0f'),wrong_range=b.replace('request.secondRange = 5.0f','request.secondRange = 6.0f'),wrong_first_limit=b.replace('request.firstChoiceLimit = 5','request.firstChoiceLimit = 6'),wrong_second_limit=b.replace('request.secondChoiceLimit = 55','request.secondChoiceLimit = 54'),wrong_subtype=b.replace('request.subtype = 19','request.subtype = 18'),wrong_priority=b.replace('&request, priority, context','&request, priority ^ 1, context'),wrong_context=b.replace('&request, priority, context','&request, priority, context ^ 1'),ignore_result=b.replace('return result;','(void)result; return owner;'),failed_allocation_returns_owner=b.replace('return result;','return result ? result : owner;'),stub='void *func_1518BA90(u8 *owner,u8 priority,s32 context){return NULL;}')

def program():
    cases=[x for x in g.cases()if not x.connected and not x.alias]
    # Public mutation at the bounded constructor also checks captured inputs.
    cases += [g.Case(kind=k,mutation=m,outcome=o)for k in(0,7)for m in(1,2,3)for o in(0,1)]
    arr=lambda xs:'{'+','.join(arr(x)if isinstance(x,(tuple,list))else'0x%Xu'%g.u32(x)for x in xs)+'}'
    rows=[]
    for x in cases:
        e=g.reference(g.fixture(x),x);p=e['packets'][0]if e['packets']else bytes(28)
        rows.append(arr([x.null,x.kind,x.tag,x.priority,x.context,x.heads,x.pointers,x.tags,x.owner_node,x.outcome,x.mutation,x.constants,e['value'],len(e['calls']),[int.from_bytes(p[i:i+4],'big')for i in range(0,16,4)],[int.from_bytes(p[i:i+2],'big')for i in(16,18)]]))
    text='#include <ultra64.h>\nextern u8 D_800DCE50[832];\n/* Both retail names delimit one table; keep that object relation visible to GCC. */\n#define D_800DD190 (*(D_800DCE50+832))\n'+c.SUPPORT+'\n'+c.SELECTED+'\n'
    variants=controls()
    for n,b in variants.items():assert b!=c.SELECTED,n;text+=b.replace('func_1518BA90','negative_'+n)+'\n'
    text+='typedef char ABI[(sizeof(void*)==4&&sizeof(OwnerRecordRequest)==28&&__builtin_offsetof(OwnerRecordRequest,firstChoiceLimit)==16&&__builtin_offsetof(OwnerRecordRequest,owner)==20&&__builtin_offsetof(OwnerRecordRequest,tag)==24&&__builtin_offsetof(OwnerRecordRequest,subtype)==26)?1:-1];\n'
    text+='typedef struct{u32 null,kind,tag,priority,context,heads[2],pointers,tags,owner_node,outcome,mutation,constants[3],result,calls,values[4],limits[2];}Row;\nstatic const Row rows[]={'+',\n'.join(rows)+'};\n'
    text+=r'''
typedef union{u64 align;u8 bytes[128];}Storage;
u8 D_800DCE50[832] __attribute__((aligned(8)));
f32 D_800A7434,D_800A7438,D_800A743C;
static Storage owner,other,nodes[6],output,expectedOwner,expectedOther,expectedNodes[6],expectedOutput;
static u8 expectedTable[832];static const Row*row;static u8*input;static u32 bad,step;
static void fill(u8*p,u32 n,u8 v){u32 i;for(i=0;i<n;i++)p[i]=v;}
static void copy(u8*d,const u8*s,u32 n){u32 i;for(i=0;i<n;i++)d[i]=s[i];}
static u32 equal(const u8*a,const u8*b,u32 n){u32 i;for(i=0;i<n;i++)if(a[i]!=b[i])return 0;return 1;}
static u32 word(const void*p){u32 x;copy((u8*)&x,p,4);return x;}
static void setword(void*p,u32 x){copy(p,(u8*)&x,4);}
static void *address(u32 v){if(!v)return NULL;if(v==0x240000)return output.bytes;return nodes[(v-0x230000)/128].bytes;}
void *func_1518BCD0(void*packet,u8 priority,s32 context){OwnerRecordRequest*p=packet;u32 i;
 if(step++||priority!=(u8)row->priority||(u32)context!=row->context||p->owner!=input||p->tag!=(u8)row->tag||p->mode!=5||p->subtype!=19||p->firstChoiceLimit!=(s16)row->limits[0]||p->secondChoiceLimit!=(s16)row->limits[1])bad=1;
 for(i=0;i<4;i++)if(word((u8*)p+4*i)!=row->values[i])bad=1;
 /* Only the deliberately unwritten retained byte is initialized by the fixture. */
 p->retained=0xA5;
 if(row->mutation&1)input[59]^=0x55;
 if(row->mutation&2){*(void**)(D_800DCE50+0x7C)=NULL;setword(&D_800A7434,0x7FC12345);}
 if(row->outcome)output.bytes[0]^=0xA5;
 return row->outcome?output.bytes:NULL;
}
static u32 run(void*(*fn)(u8*,u8,s32)){u32 n,i,j,fail=0;void*result;
 for(n=0;n<sizeof(rows)/sizeof(rows[0]);n++){row=&rows[n];fill(owner.bytes,128,0x5A);fill(other.bytes,128,0x5A);fill(output.bytes,128,0x5A);fill(D_800DCE50,832,0);
  input=row->null?NULL:(s32)row->owner_node<0?owner.bytes:nodes[row->owner_node].bytes;
  for(i=0;i<6;i++){fill(nodes[i].bytes,128,0x5A);*(void**)(nodes[i].bytes+8)=(i==2||i==5)?NULL:nodes[i+1].bytes;*(void**)(nodes[i].bytes+36)=(row->pointers>>i&1)?input:other.bytes;nodes[i].bytes[40]=(row->tags>>i&1)?row->tag:row->tag+1+i;}
  if(input){input[4]=row->kind;input[59]=row->tag;}
  for(i=0;i<2;i++)*(void**)(D_800DCE50+124+416*i)=(s32)row->heads[i]<0?NULL:nodes[row->heads[i]].bytes;
  setword(&D_800A7434,row->constants[0]);setword(&D_800A7438,row->constants[1]);setword(&D_800A743C,row->constants[2]);
  copy(expectedOwner.bytes,owner.bytes,128);copy(expectedOther.bytes,other.bytes,128);copy(expectedOutput.bytes,output.bytes,128);copy(expectedTable,D_800DCE50,832);for(i=0;i<6;i++)copy(expectedNodes[i].bytes,nodes[i].bytes,128);
  if(row->calls){if(row->mutation&1){u8*p=(s32)row->owner_node<0?expectedOwner.bytes:expectedNodes[row->owner_node].bytes;p[59]^=0x55;}if(row->mutation&2)*(void**)(expectedTable+124)=NULL;if(row->outcome)expectedOutput.bytes[0]^=0xA5;}
  step=bad=0;result=fn(input,(u8)row->priority,(s32)row->context);
  if(result!=address(row->result)||bad||step!=row->calls||!equal(owner.bytes,expectedOwner.bytes,128)||!equal(other.bytes,expectedOther.bytes,128)||!equal(output.bytes,expectedOutput.bytes,128)||!equal(D_800DCE50,expectedTable,832))fail++;
  for(i=0;i<6;i++)if(!equal(nodes[i].bytes,expectedNodes[i].bytes,128))fail++;
  for(j=0;j<3;j++){void*p=j==0?(void*)&D_800A7434:j==1?(void*)&D_800A7438:(void*)&D_800A743C;u32 expected=j==0&&row->calls&&(row->mutation&2)?0x7FC12345:row->constants[j];if(word(p)!=expected)fail++;}
 }return fail;}
void _start(void){u32 mask=0;int result;if(run(func_1518BA90))goto failure;
'''
    for i,n in enumerate(variants):text+='if(run(negative_'+n+'))mask|='+str(1<<i)+';\n'
    text+='if(mask!='+str((1<<len(variants))-1)+')goto failure;result=0;goto finish;\nfailure:result=1;\nfinish:__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}\n'
    return text,list(variants),len(cases)
