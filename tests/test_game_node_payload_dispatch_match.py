"""Filtered payload dispatch: direct words, live list mutations and complete image."""
import itertools,json,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_node_payload_dispatch_candidates as candidate
from tools.experiments import game_node_payload_dispatch_match as match
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_node_payload_dispatch_oracle as model
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=candidate.ROOT
def state(m):return complete(m),m.trace,m.current_pc,m.delay_of,m.all_accesses,m.outer_index,m.call_index,m.minimum_sp

class NodePayloadDispatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes()
        cls.context=json.loads((cls.out/'retail-node-context.json').read_text());cls.retail=list(struct.unpack_from('>66I',cls.rom,match.ROM))
        cls.raw=model.bound(cls.prepared['qualified_compact'],model.symbols());cls.words=model.bound(cls.prepared['qualified_owner'],model.symbols())
        from tools.tests.test_game_view_list_setup import ViewListSetupTests
        context=type('OriginalPayloadDispatcher',(),dict(root=ROOT,out=cls.out))
        cls.original=ViewListSetupTests.original.__func__(context,'original-node-dispatch',(ROOT/match.ASM).read_text(),match.FUNCTION)
        assert model.bound(cls.original,model.symbols())==cls.retail==cls.raw==cls.words
    def receipt(self,name,**v):(self.out/(name+'.json')).write_text(json.dumps(v,indent=2)+'\n')
    def compare(self,c,initial=None,s=None,entry=match.ENTRY,images=None,helpers=None):
        s=model.symbols()if s is None else s;initial=model.fixture(c,self.context,s)if initial is None else initial
        expected=model.reference(initial,c,s);code=model.helper_code(self.rom,c)if helpers is None else helpers;ms=[]
        for words in(self.retail,self.raw,self.words)if images is None else images:
            m=model.Oracle(words,initial,c,s,entry,code,expected).run()
            self.assertEqual(m.r[2],expected['value'],c);self.assertEqual(m.calls,expected['calls'],c);self.assertEqual(model.public(m.memory),model.public(expected['memory']),c)
            self.assertEqual(m.outer_index,len(expected['outer']));self.assertEqual(m.call_index,len(expected['calls']))
            self.assertEqual(model.read(m.memory,model.STACK+c.phase+4),model.u32(c.root));ms.append(m)
        for m in ms[1:]:self.assertEqual(state(ms[0]),state(m))
        return ms
    def test_01_raw_owner_bindings_and_literal_image(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['bindings'],q['raw_neighbors'],q['neighbors']),(66,56,0,5,77,77))
        raw,bindings=match.function_blob(self.prepared['qualified_compact']);truth=self.rom[match.ROM:match.ROM+264]
        for at in range(264):
            bad=bytearray(raw);bad[at]^=1
            with self.assertRaises(ValueError):match.normalized(bytes(bad),bindings,truth)
        for at in bindings:
            bad=dict(bindings);bad[at]=[('R_MIPS_26','foreign')]
            with self.assertRaises(ValueError):match.normalized(raw,bad,truth)
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes()
        self.assertEqual(match.strict_image(before,after,truth),207);at=match.elf_slot_offset(after,match.ENTRY,264)
        self.assertEqual(struct.unpack_from('>11I',self.rom,0x22F624),model.HANDLERS+(0,0,0))
        table=match.elf_slot_offset(after,0x8008AB64,44);self.assertEqual(after[table:table+44],self.rom[0x22F624:0x22F650])
        c=model.Case();initial=model.fixture(c,self.context);stub=list(struct.unpack_from('>66I',before,match.elf_slot_offset(before,match.ENTRY,264)))
        old=model.Oracle(stub,initial,c).run();self.assertEqual(old.r[2],0);self.assertEqual(model.reference(initial,c)['value'],1)
        offsets=(0,at,at+263,at+264,match.elf_slot_offset(after,model.SEARCH,172),match.elf_slot_offset(after,0x8008AB64,44),len(after)-1)
        for off in offsets:
            bad=bytearray(after);bad[off]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
        self.receipt('word-image-controls',words=66,guards=0,bindings=5,neighbors=77,raw_byte_controls=264,binding_controls=5,image_controls=len(offsets),literal_changed_bytes=207,exclusions=0)
    def test_02_independent_contract_live_mutations_and_actual_links(self):
        count=actual=0;seen=set()
        for c in model.cases():seen.update(self.compare(c)[0].visits);count+=1
        # Every terminating actual root-to-node search is exercised through the dispatcher.
        for root,kind in itertools.product(range(28),range(28)):
            c=model.Case(kinds=(kind,kind,kind),root=root,actual=True)
            try:expected=model.reference(model.fixture(c,self.context),c)
            except AssertionError as e:
                self.assertIn('reference cycle',str(e));continue
            seen.update(self.compare(c)[0].visits);actual+=1
        for phase in(0,8):
            c=model.Case(kinds=(0,0,0),slots=(7,)*8,leaf=True,phase=phase);seen.update(self.compare(c)[0].visits)
        self.assertEqual(set(range(match.ENTRY,match.ENTRY+264,4))-seen,set())
        self.assertTrue(set(range(model.LEAF,model.LEAF+24,4))<=seen)
        self.receipt('guest-contract',synthetic_cases_per_body=count,actual_table_cases_per_body=actual,actual_leaf_cases_per_body=2,all_66_words=True,recursive_helper_words=43,actual_leaf_words=6,last_callback_boolean=True,raw_root_home=True)
    def test_03_access_prefixes_aliases_sparse_and_cycles(self):
        cuts=aliases=faults_count=cycles=0
        for c in(model.Case(),model.Case(kinds=(1,2,3),connected=False,mutation=1),model.Case(mutation=3),model.Case(empty=True)):
            initial=model.fixture(c,self.context);expected=model.reference(initial,c);code=model.helper_code(self.rom,c)
            done=model.Oracle(self.retail,initial,c,connected=code,expected=expected).run()
            for cut in range(done.all_accesses):
                ms=[]
                for words in(self.retail,self.raw,self.words):
                    m=model.Oracle(words,initial,c,connected=code,expected=expected);m.cut=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    ms.append(m)
                for m in ms[1:]:self.assertEqual(state(ms[0]),state(m))
                cuts+=1
        for root in(-32768,-2,32767):
            c=model.Case(root=root,kinds=(0,0,0));initial=model.fixture(c,self.context)
            model.put(initial,model.symbols()['D_8008ABE8']+root*4,model.ROWS)
            self.compare(c,initial);aliases+=1
        for root,slot in((28,None),(-2,None),(0,-2),(0,8),(0,9),(0,10),(0,32767)):
            c=model.Case(root=root,kinds=(0,0,0));initial=model.fixture(c,self.context)
            if root==28:model.put(initial,model.symbols()['D_8008ABE8']+28*4,0)
            if slot is not None:model.put(initial,model.ROWS,slot,2)
            ms=[]
            for words in(self.retail,self.raw,self.words):
                m=model.Oracle(words,initial,c,connected=model.helper_code(self.rom,c))
                with self.assertRaises((AssertionError,KeyError)):m.run()
                ms.append(m)
            for m in ms[1:]:self.assertEqual(state(ms[0]),state(m))
            faults_count+=1
        for recursive in(False,True):
            c=model.Case(kinds=(1,1,1)if recursive else(0,0,0));initial=model.fixture(c,self.context)
            if recursive:
                model.put(initial,model.ROWS+16+6,1,2);model.put(initial,model.NODES[0]+0x1C,2,2)
            else:model.put(initial,model.NODES[0]+0x14,model.NODES[0])
            ms=[]
            for words in(self.retail,self.raw,self.words):
                m=model.Oracle(words,initial,c,connected=model.helper_code(self.rom,c));m.cut=250
                with self.assertRaises(faults.AccessBoundary):m.run()
                ms.append(m)
            for m in ms[1:]:self.assertEqual(state(ms[0]),state(m))
            if recursive:self.assertLess(ms[0].minimum_sp,model.STACK-56-32*4)
            cycles+=1
        self.receipt('fault-prefixes',fired_cuts=cuts,sparse_signed_roots=aliases,invalid_roots_or_slots=faults_count,bounded_cycles=cycles,recursive_stack_growth_preserved=True,portable_invalid_access_claimed=False)
    def test_04_six_original_call_delay_windows(self):
        rows=json.loads((self.out/'call-census.json').read_text());count=0
        for row,phase in itertools.product(rows,(0,8)):
            pc=row['address'];words=list(struct.unpack_from('>2I',self.rom,row['rom']));c=model.Case(phase=phase)
            initial=model.fixture(c,self.context);arguments=list(model.args(c));registers={}
            # Decode each real delay move/store and provide the source value it consumes.
            delay=words[1];op,rs,rt,rd,fn=delay>>26,delay>>21&31,delay>>16&31,delay>>11&31,delay&63
            if op==0 and fn==37:
                self.assertIn(rd,(5,6,7));value=arguments[rd-4]
                if rs:registers[rs]=value
                if rt:registers[rt]=value
                if not(rs or rt):arguments[rd-4]=0;c=replace(c,second=0)
            elif op==43:
                self.assertEqual((rs,rt,delay&65535),(29,3,0x130));registers[3]=0x13579BDF
            else:self.fail(hex(delay))
            expected=model.reference(initial,c);ms=[]
            for target in(self.retail,self.raw,self.words):
                code=model.helper_code(self.rom,c);code.update(zip(range(match.ENTRY,match.ENTRY+264,4),target))
                m=model.Oracle(words,initial,c,entry=pc,connected=code,expected=expected,arguments=tuple(arguments),dispatch_entry=match.ENTRY,dispatch_size=264)
                for reg,val in registers.items():m.r[reg]=val
                m.before=m.r[:];m.code[pc+8]=0;m.code.ends=(pc+8,)
                with self.assertRaises(model.WindowBoundary):m.run()
                self.assertEqual(m.r[2],expected['value']);self.assertEqual(m.calls,[(match.ENTRY,tuple(arguments))]+expected['calls'])
                self.assertEqual(model.public(m.memory),model.public(expected['memory']))
                if op==43:self.assertEqual(model.read(m.memory,model.STACK+phase+0x130),0x13579BDF)
                ms.append(m)
            for m in ms[1:]:self.assertEqual(state(ms[0]),state(m))
            count+=1
        self.receipt('callers',direct_sites=6,owners=4,cases_per_body=count,original_call_and_delay=True,unchanged_owner_functions=245,whole_gameplay_claimed=False)
    def test_05_independent_GNU_rebases(self):
        count=links=0
        for i,(entry,base)in enumerate(((match.ENTRY,0x17007FFC),(0x18018000,0x19018000),(0x1A02FFFC,0x1B00FFFC))):
            s=dict(D_8008AB64=0x81007FFC+i*0x10000,D_8008ABE8=0x8200FFFC+i*0x10000,func_1514D4B8=base);images=[]
            for j,obj in enumerate((self.original,self.prepared['qualified_compact'],self.prepared['qualified_owner'])):
                data,fs,rs=match.parse_object(obj);asm,unknown=emit_function(data,fs[match.FUNCTION],rs,match.FUNCTION,s);self.assertFalse(unknown)
                p=self.out/('rebase-%d-%d'%(i,j));p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>66I',sections(p.with_suffix('.elf'))['.text'][1])));links+=1
            for c in list(model.cases())[::23]:
                c=replace(c,connected=False);self.compare(c,s=s,entry=entry,images=images,helpers={});count+=1
        self.receipt('rebases',GNU_links=links,cases_per_body=count,all_five_bindings=True,HI_LO_carries=True)
    def test_06_effective_IDO_and_native_controls(self):
        witnesses=list(model.cases());effective=[]
        for name,body in model.controls().items():
            text=candidate.source_states((ROOT/candidate.SOURCE).read_text())[1].replace(candidate.SELECTED,body,1)
            obj,_=candidate.compile_owner(ROOT,self.out,text,'negative-'+name);words=model.bound(obj,model.symbols());fired=False
            for c in witnesses:
                initial=model.fixture(c,self.context);expected=model.reference(initial,c)
                try:
                    m=model.Oracle(words,initial,c,connected=model.helper_code(self.rom,c),expected=expected).run()
                    if m.r[2]!=expected['value']or m.calls!=expected['calls']or model.public(m.memory)!=model.public(expected['memory']):fired=True
                except(AssertionError,IndexError,KeyError):fired=True
                if fired:break
            self.assertTrue(fired,name);effective.append(name)
        rows=[c for c in witnesses if not c.phase]
        for name,body,opt,wanted in [('positive-'+o[1:],candidate.SELECTED,o,0)for o in('-O0','-O2','-O3')]+[(n,b,'-O2',1)for n,b in model.controls().items()]:
            p=self.out/('native-'+name+'.c');p.write_text(native_source(body,rows,self.context));exe=p.with_suffix('.elf')
            r=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'',''),name);self.assertEqual(subprocess.run([str(exe)]).returncode,wanted,name)
        self.receipt('native-controls',rows_per_profile=len(rows),profiles=['O0','O2','O3'],native_executions=3*len(rows),native_controls=len(effective),IDO_controls=effective,UBSan=True,fullword_forwarding=True)

    def test_07_complete_original_byte_source_caller(self):
        pc=0x15079390;off=pc-0x15000000+0x2D4B0;body=list(struct.unpack_from('>18I',self.rom,off));count=0
        for root,first,second,phase in itertools.product((0,1,2,5),(0,128,255),(0,255),(0,8)):
            c=model.Case(root=root,first=first,second=second,phase=phase);initial=model.fixture(c,self.context)
            model.put(initial,0x800D154C,model.OWNER)
            for at,v in((0x800D1890,root),(0x800D1891,first),(0x800D1892,second)):initial[at]=v
            expected=model.reference(initial,c);ms=[]
            for words in(self.retail,self.raw,self.words):
                code=model.helper_code(self.rom,c);code.update(zip(range(match.ENTRY,match.ENTRY+264,4),words))
                m=model.Oracle(body,initial,c,entry=pc,connected=code,expected=expected,dispatch_entry=match.ENTRY,dispatch_size=264).run()
                self.assertEqual(m.r[2],expected['value']);self.assertEqual(m.calls,[(match.ENTRY,model.args(c))]+expected['calls'])
                self.assertEqual(model.public(m.memory),model.public(expected['memory']));ms.append(m)
            for m in ms[1:]:self.assertEqual(state(ms[0]),state(m))
            count+=1
        self.receipt('complete-caller',words=18,cases_per_body=count,actual_three_byte_source_loads=True,frame=24,combined_frame=80)

def digest(m,s):
    values=[model.read(m,model.OWNER+0x2F4)]
    for n in model.NODES:values.extend(model.read(m,n+o,z)for o,z in((0x10,4),(0x14,4),(0x1C,2)))
    for i in range(30):
        p=model.read(m,s['D_8008ABE8']+i*4);values.extend(model.read(m,p+j*2,2)for j in range(4))
    values.extend(model.read(m,s['D_8008AB64']+i*4)for i in range(8))
    h=2166136261
    for v in values:h=((h^v)*16777619)&0xFFFFFFFF
    return h

def native_source(body,cases,context):
    rows=[]
    for c in cases:
        m=model.fixture(replace(c,empty=False),context);expected=model.reference(model.fixture(c,context),c)
        if c.empty:expected['memory']=m;model.put(m,model.OWNER+0x2F4,0)
        events=[]
        for t,a in expected['calls']:
            events.append('{%d,{%s}}'%(8 if t==model.SEARCH else model.HANDLERS.index(t),','.join('0x%Xu'%x for x in (*a,*([0]*(3-len(a)))))))
        e=expected['outer']
        outerrows=','.join('{%d,%d,0x%Xu}'%(8 if x['kind']=='search'else model.HANDLERS.index(x['target']),model.NODES.index(x['node']),x['value'])for x in e)or'{0,0,0}'
        rows.append('{{%s},{%s},{%s},%d,0x%Xu,0x%Xu,%d,%d,%d,%d,0x%Xu,%d,{%s},%d,{%s}}'%(','.join(map(str,c.kinds)),','.join(map(str,c.slots)),','.join('0x%Xu'%model.u32(v)for v in c.returns),model.half(c.root),c.first,c.second,c.mutation,c.connected,c.empty,expected['value'],digest(expected['memory'],model.symbols()),len(events),','.join(events)or'{0,{0,0,0}}',len(e),outerrows))
    owner=(ROOT/candidate.SOURCE).read_text();node_type='typedef struct GameListNode {'+owner.split('typedef struct GameListNode {',1)[1].split('} GameListNode;',1)[0]+'} GameListNode;\n'
    return '#include <ultra64.h>\n#include "structs.h"\n'+node_type+'extern s16 *D_8008ABE8[];\n'+candidate.DECLARATIONS+body+r'''
typedef struct {u32 id,args[3];} Event;
typedef struct {u32 id,node,value;} Outer;
typedef struct {s16 kinds[3],slots[8];u32 returns[3];s16 root;u32 first,second;int mutation,connected,empty,result;u32 digest;u32 count;Event events[64];u32 outerCount;Outer outer[16];} Row;
static const Row rows[]={
'''+',\n'.join(rows)+r'''
};
static u8 owner[0x310] __attribute__((aligned(16)));
static GameListNode nodes[3];static s16 records[30][4];s16 *D_8008ABE8[257];
GamePayloadCallback179F30 D_8008AB64[11];
static const Row *row;static u32 ordinal,outerOrdinal,depth;static int error;
static u32 ids[8];
static void mutate(u32 n,int search){if(n)return;GameListNode *node=&nodes[n];
 if(search&&row->mutation==1){node->unk1C=3;node->unk10=(s32)0xCAFEBABE;}
 if((search&&row->mutation==2)||(!search&&row->mutation==3))node->next=&nodes[2];
 if(!search&&row->mutation==4){records[row->root][2]=-1;D_8008AB64[1]=D_8008AB64[7];ids[1]=ids[7];}
 if(!search&&row->mutation==5)records[nodes[1].unk1C][0]=-1;
 if(!search&&row->mutation==6)*(GameListNode **)(owner+0x2F4)=0;
}
static void logcall(u32 id,u32 a,u32 b,u32 c){
 if(ordinal>=row->count){error=1;return;}const Event *e=&row->events[ordinal++];
 if(e->id!=id||e->args[0]!=a||e->args[1]!=b||(id!=8&&e->args[2]!=c))error=1;
}
static Outer getouter(u32 id){Outer fallback={id,0,0};if(outerOrdinal>=row->outerCount){error=1;return fallback;}
 Outer e=row->outer[outerOrdinal++];if(e.id!=id||e.node>=3){error=1;return fallback;}return e;}
static s32 callback(u32 id,s32 a,s32 b,s32 c){logcall(id,a,b,c);Outer e=getouter(id);mutate(e.node,0);return(s32)e.value;}
'''+ '\n'.join('static s32 cb%d(s32 a,s32 b,s32 c){return callback(%d,a,b,c);}'%(i,i)for i in range(8))+r'''
static GamePayloadCallback179F30 original[8]={cb0,cb1,cb2,cb3,cb4,cb5,cb6,cb7};
s32 func_1514D4B8(s16 index,s16 wanted){
 logcall(8,(u32)(s32)index,(u32)(s32)wanted,0);int outside=depth++==0;Outer e={8,0,0};if(outside)e=getouter(8);
 s32 value=0;
 if(!row->connected){value=(s32)e.value;mutate(e.node,1);}
 else if(index==-1)value=0;
 else if(index==wanted)value=1;
 else if(index<0||index>=30){error=1;value=0;}
 else if(depth>60){error=1;value=0;}
 else if(func_1514D4B8(records[index][3],wanted)||func_1514D4B8(records[index][2],wanted))value=1;
 depth--;return value;
}
static u32 guestnode(GameListNode *p){if(!p)return 0;for(u32 i=0;i<3;i++)if(p==&nodes[i])return 0x24000+i*0x40;error=1;return 0;}
static u32 mix(u32 h,u32 v){return(h^v)*16777619u;}
static u32 hash(void){u32 h=mix(2166136261u,guestnode(*(GameListNode **)(owner+0x2F4)));
 for(u32 i=0;i<3;i++){h=mix(h,(u32)nodes[i].unk10);h=mix(h,guestnode(nodes[i].next));h=mix(h,(u16)nodes[i].unk1C);}
 for(u32 i=0;i<30;i++)for(u32 j=0;j<4;j++)h=mix(h,(u16)records[i][j]);
 for(u32 i=0;i<8;i++)h=mix(h,ids[i]);return h;}
static s32(*volatile probe)(u8 *,s16,s32,s32)=func_1514D3B0;
typedef char widths[sizeof(void*)==4&&sizeof(s32)==4&&__builtin_offsetof(GameListNode,next)==0x14&&__builtin_offsetof(GameListNode,unk1C)==0x1C?1:-1];
static int run(void){
 for(u32 r=0;r<sizeof(rows)/sizeof(rows[0]);r++){
  row=&rows[r];ordinal=outerOrdinal=depth=0;error=0;
  for(u32 i=0;i<3;i++){nodes[i].unk10=0x31000+i*16;nodes[i].next=i<2?&nodes[i+1]:0;nodes[i].unk1C=row->kinds[i];}
  *(GameListNode **)(owner+0x2F4)=row->empty?0:&nodes[0];
  for(u32 i=0;i<30;i++){D_8008ABE8[i]=records[i];records[i][0]=row->slots[i%8];records[i][1]=0;records[i][2]=i==0?1:-1;records[i][3]=i<6?(s16)(i+1):-1;}
  D_8008ABE8[256]=records[0];
  for(u32 i=0;i<8;i++){D_8008AB64[i]=original[i];ids[i]=ORIGINAL_IDS[i];}
  s32 result=probe(owner,row->root,(s32)row->first,(s32)row->second);
  if(result!=row->result||error||ordinal!=row->count||outerOrdinal!=row->outerCount||hash()!=row->digest)return 1;
 }return 0;}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''.replace('static int run(void){','static const u32 ORIGINAL_IDS[8]={'+','.join('0x%Xu'%v for v in model.HANDLERS)+'};\nstatic int run(void){')

if __name__=='__main__':unittest.main()
