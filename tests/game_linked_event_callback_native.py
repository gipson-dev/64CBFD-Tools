"""SDK native32 C, numeric word/byte fixtures and effective semantic controls."""
import itertools
from dataclasses import replace
from tools.experiments import game_linked_event_callback_candidates as source
from tools.tests import game_linked_event_callback_oracle as g
def controls():
    b=source.SELECTED
    return dict(wrong_event=b.replace('selector == 0x2D','selector == 0x2C'),wrong_kind=b.replace('== 0x22','== 0x23'),wrong_first_update=b.replace('= *(u32 *)(pair + 4);','= *(u32 *)pair;'),wrong_second_tag=b.replace('pair[8]','pair[9]'),wrong_clear_tag=b.replace('== pair[4]','== pair[9]'),wrong_flag=b.replace('& 0x100','& 0x200'),missing_helper=b.replace('func_151B9660(owner);','(void)owner;'),wrong_event_argument=b.replace('callback(owner, pair, event);','callback(owner, pair, event ^ 1);'),stub='void '+source.FUNCTION+'(u8 *owner,u8 *pair,u8 event) {}')
def program():
    cases=[replace(c,second=0x87878787)for c in g.cases()if c.phase==0]
    rows=[];arr=lambda vs:'{'+','.join('0x%Xu'%g.u32(v)for v in vs)+'}'
    def observed(snapshot):
        o,p=snapshot
        rd=lambda b,at,n=4:int.from_bytes(b[at:at+n],'big')
        return(rd(o,0x7C),o[0x80],rd(o,0x60),o[0x68],rd(p,0),rd(p,4),p[8],p[9])
    for c in cases:
        initial=g.fixture(c);m,calls,obs=g.reference(initial,c);o,p=g.addresses(c)
        callrows=[]
        for (t,a),ob in zip(calls,obs):
            tag=0 if t==g.HELPER else 1+((t&0x7F)//16)+(8 if t>=0x18000000 else 0)
            callrows.append('{'+str(tag)+','+arr(observed(ob))+'}')
        helper=any(t==g.HELPER for t,a in calls)
        final=[g.read(m,o+0x7C),m[o+0x80],g.read(m,o+0x60),m[o+0x68],g.read(m,p),g.read(m,p+4),m[p+8],m[p+9],g.read(m,g.MARK)]
        fields=[g.u32(c.event),c.kind,c.flags,c.index,c.match,c.tag,c.first,c.second,c.callback,c.mutation,len(calls),int(helper)]
        rows.append('{'+','.join(('0x%Xu'%v for v in fields))+','+arr(final)+',{'+','.join(callrows)+'}}')
    text='#include <ultra64.h>\n'+source.SUPPORT+'\n'+source.SELECTED+'\n';variants=controls()
    for n,b in variants.items():assert b!=source.SELECTED;text+=b.replace(source.FUNCTION,'negative_'+n)+'\n'
    text+=r'''
typedef char ABI_pointer[(sizeof(void*)==4)?1:-1];
typedef char ABI_word[(sizeof(u32)==4&&sizeof(u16)==2&&sizeof(u8)==1)?1:-1];
typedef struct{u32 tag,value[8];}Call;
typedef struct{u32 event,kind,flags,index,match,tag,first,second,callback,mutation,calls,helper,final[9];Call observations[2];}Row;
static const Row rows[]={'''+',\n'.join(rows)+r'''};
static u32 own[0x194/4],payload[3];static const Row*c;static u32 calls,bad,marks;static u8*O=(u8*)own,*P=(u8*)payload;
LinkedEventCallback15F680 D_800899F8[256];
static u32 word(u8*p,u32 a){return*(u32*)(p+a);}
static void store(u8*p,u32 a,u32 v){*(u32*)(p+a)=v;}
static void observe(u32 tag,u8*o,u8*p,u8 event){u32 v[8],i,n=calls++;
 v[0]=word(o,0x7C);v[1]=o[0x80];v[2]=word(o,0x60);v[3]=o[0x68];v[4]=word(p,0);v[5]=word(p,4);v[6]=p[8];v[7]=p[9];
 if(o!=O||p!=P||event!=(u8)c->event||n>=c->calls||n>=2){bad=1;return;}
 if(tag!=c->observations[n].tag)bad=1;for(i=0;i<8;i++)if(v[i]!=c->observations[n].value[i])bad=1;
}
static void callback_effect(u8*o,u8*p){marks++;if(c->mutation&16){store(o,0x7C,0xEEDDCCBB);o[0x80]=0x73;store(p,4,0x13579BDF);}}
'''
    for i in range(16):text+='static void cb%d(u8*o,u8*p,u8 e){observe(%d,o,p,e);callback_effect(o,p);}\n'%(i,i+1)
    text+='static LinkedEventCallback15F680 callbacks[16]={'+','.join('cb'+str(i)for i in range(16))+'};\n'
    text+=r'''
void func_151B9660(u8*o){u32 i;observe(0,o,P,(u8)c->event);
 if(c->mutation&1){store(o,0x60,256);o[0x68]=(u8)(c->index+1);}
 if(c->mutation&2){store(o,0x7C,0xCAFEBABE);o[0x80]=0xD1;store(P,0,0xBAD5EED);}
 if(c->mutation&4)for(i=0;i<256;i++)D_800899F8[i]=callbacks[8+(i&7)];
 if(c->mutation&8){store(o,0x60,word(o,0x60)^256);P[9]^=0x55;}
 *(f32*)(o+0x188)=5.0f;*(f32*)(o+0x18C)=.25f;*(f32*)(o+0x190)=-2.5f;
}
static u32 run(LinkedEventCallback15F680 fn){u32 n,i,fail=0,final[9];
 for(n=0;n<sizeof(rows)/sizeof(rows[0]);n++){c=&rows[n];calls=bad=marks=0;
  for(i=0;i<sizeof(own);i++)O[i]=0;for(i=0;i<sizeof(payload);i++)P[i]=0;
  for(i=0;i<256;i++)D_800899F8[i]=c->callback?callbacks[i&7]:0;
  store(O,0x60,c->flags);*(u16*)(O+0x66)=(u16)c->kind;O[0x68]=(u8)c->index;
  store(P,0,c->first);store(P,4,c->second);P[8]=0x38;P[9]=0xC7;
  store(O,0x7C,c->match==0?c->first:c->match==1?c->second:c->first^0x11223344);O[0x80]=(u8)c->tag;
  fn(O,P,(u8)c->event);
  final[0]=word(O,0x7C);final[1]=O[0x80];final[2]=word(O,0x60);final[3]=O[0x68];final[4]=word(P,0);final[5]=word(P,4);final[6]=P[8];final[7]=P[9];final[8]=marks;
  if(bad||calls!=c->calls)fail++;for(i=0;i<9;i++)if(final[i]!=c->final[i])fail++;
  if(word(O,0x188)!=(c->helper?0x40A00000:0)||word(O,0x18C)!=(c->helper?0x3E800000:0)||word(O,0x190)!=(c->helper?0xC0200000:0))fail++;
  for(i=0;i<sizeof(own);i++)if(!(i>=0x60&&i<0x64)&&i!=0x66&&i!=0x67&&i!=0x68&&!(i>=0x7C&&i<=0x80)&&!(i>=0x188&&i<0x194)&&O[i])fail++;
 }return fail;
}
void _start(void){u32 mask=0;int result;if(run(func_15133588))goto failure;
'''
    for i,n in enumerate(variants):text+='if(run(negative_'+n+'))mask|='+str(1<<i)+';\n'
    text+='if(mask!='+str((1<<len(variants))-1)+')goto failure;result=0;goto finish;\nfailure:result=1;\nfinish:__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}\n'
    return text,list(variants),len(cases)
