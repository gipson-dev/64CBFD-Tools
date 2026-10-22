"""Keyed removal: cached successors, unlink order, real heap helpers and caller windows."""
from dataclasses import dataclass
import itertools,json,struct,subprocess,unittest
from pathlib import Path
from tools.experiments import game_keyed_node_removal as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_projected_packet_draw import native_command

ROOT=Path(__file__).resolve().parents[2]
NAME='func_15188AD0'
ENTRY,HEAD,MARK,FREE,INTMASK,FOLLOW=0x15188AD0,0x800DF7C8,0x100043B4,0x10004074,0x10024880,0x1505F188
NODES=tuple(0x30000+i*0x100 for i in range(7))
PAYLOADS=tuple(0x50000+i*0x100 for i in range(7))
ACTOR,EXTRA=0x60000,0x70000
ANCHORS=dict(D_800DF7C8=HEAD,func_100043B4=MARK,func_10004074=FREE)


@dataclass(frozen=True)
class Case:
    length:int=4
    mask:int=5
    key:int=0x80000000
    mode:int=0
    alias:int=0


def fixture(c,phase=0,anchors=None):
    assert all(not STACK-0x800<=p<STACK+0x300 for p in NODES+PAYLOADS)
    head=(anchors or ANCHORS)['D_800DF7C8'];seed=(c.mask+c.length*17)&255
    m={STACK+phase+i:(i*17+seed)&255 for i in range(-0x600,0x200)}
    for base,size in [(head,8),(ACTOR,0x400),(EXTRA,64)]+[(p-16,80)for p in NODES+PAYLOADS]:
        m.update({base+i:0xA5 for i in range(size)})
    for i,node in enumerate(NODES):
        pointer=PAYLOADS[i]
        if c.alias==1:pointer=PAYLOADS[0]
        elif c.alias==2:pointer=head+4
        elif c.alias==3:pointer=node+16
        put(m,node+8,pointer);put(m,node+12,NODES[i+1]if i+1<c.length else 0)
        put(m,node+16,c.key if i<c.length and c.mask>>i&1 else ~c.key&0xFFFFFFFF)
        put(m,PAYLOADS[i]-4,0xFF000000|((seed+i*0x10203)&0xFFFFFF))
    put(m,head,NODES[0]if c.length else 0);return m


def public(m):
    return {a:v for a,v in m.items()if not STACK-0x800<=a<STACK+0x300}


def effect(m,c,role,args,node,ordinal,head):
    if role=='mark':
        pointer,flag=args;put(m,pointer-4,(read(m,pointer-4)&0xFFFFFF)|(flag<<24))
        if ordinal==0:
            if c.mode==1:put(m,node+12,NODES[6])
            elif c.mode==2:
                following=read(m,node+12)
                if following in NODES:put(m,following+16,c.key)
            elif c.mode==3:put(m,head,NODES[6])
            elif c.mode==4:put(m,node+8,PAYLOADS[6])
    elif node in NODES:
        for i in range(20):m[node+i]=0xDD
        put(m,node+12,0)


def reference(c,memory,anchors=None):
    syms=anchors or ANCHORS;head=syms['D_800DF7C8'];m=dict(memory);trace=[];calls=[];seen=[];ordinal=0
    def get(a):
        v=read(m,a);trace.append(('R',a,4,v));return v
    def store(a,v):
        put(m,a,v);trace.append(('W',a,4,v))
    node=get(head);previous=0
    while node:
        key=get(node+16);following=get(node+12)
        if key==c.key:
            store(previous+12 if previous else head,following)
            pointer=get(node+8)
            for role,args in [('mark',(pointer,2)),('free',(node,))]:
                target=syms['func_100043B4'if role=='mark'else 'func_10004074']
                calls.append((target,args));trace.append(('CALL',target,args));seen.append(read(m,head))
                effect(m,c,role,args,node,ordinal,head)
            ordinal+=1
        else:previous=node
        node=following
    return public(m),trace,calls,seen


class RemovalOracle(TimingOracle):
    def __init__(self,words,c,phase=0,entry=ENTRY,anchors=None,connected=None,memory=None,arguments=None,frame_offset=0):
        self.case,self.anchors=c,anchors or ANCHORS;self.trace=[];self.observations=[];self.ordinal=0;self.mask=0x003FFF01
        super().__init__(words,fixture(c,phase,self.anchors)if memory is None else memory,phase=phase,entry=entry,
            arguments=arguments or (c.key,0x87654321,0x12345678,0xABCDEF01),connected=connected)
        self.r[29]=self.before[29]=STACK+phase+frame_offset

    def execute(self,word):
        if word>>26==32:
            self.dispatched_word=word;self.own_instruction=True
            try:
                rs,rt=word>>21&31,word>>16&31;imm=word&65535
                address=(self.r[rs]+(imm if imm<32768 else imm-65536))&0xFFFFFFFF
                value=self.get(address,1);self.r[rt]=((value^128)-128)&0xFFFFFFFF;self.r[0]=0
            finally:self.own_instruction=False
        else:super().execute(word)

    def get(self,address,size):
        value=super().get(address,size)
        if self.own_instruction and not STACK-0x800<=address<STACK+0x300:self.trace.append(('R',address,size,value))
        return value

    def put(self,address,value,size):
        if self.recording and self.own_instruction:assert all(address+i in self.memory for i in range(size)),(address,size)
        super().put(address,value,size)
        if self.recording and self.own_instruction and not STACK-0x800<=address<STACK+0x300:
            self.trace.append(('W',address,size,value&((1<<(size*8))-1)))

    def record_call(self,target):
        widths={self.anchors['func_100043B4']:2,self.anchors['func_10004074']:1,ENTRY:1,INTMASK:1,FOLLOW:1}
        args=tuple(self.r[4:4+widths[target]])
        self.calls.append((target,args));self.events.append(('CALL',target,args));self.trace.append(('CALL',target,args))
        self.observations.append(read(self.memory,self.anchors['D_800DF7C8']))

    def hook(self,target):
        args=self.calls[-1][1]
        if target==INTMASK:value=self.mask;self.mask=args[0]
        elif target==FOLLOW:value=0x76543210
        else:
            role='mark'if target==self.anchors['func_100043B4']else 'free'
            assert target==self.anchors['func_100043B4'if role=='mark'else 'func_10004074']
            node=self.r[17]if role=='mark'else args[0]
            effect(self.memory,self.case,role,args,node,self.ordinal,self.anchors['D_800DF7C8'])
            if role=='free':self.ordinal+=1
            value=0xCA000000+len(self.calls)
        for i in range(4):put(self.memory,self.r[29]+i*4,0xB5000000+i)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0x87654321,0x12345678;self.r[2]=value


def native_harness(body):
    return '#include <ultra64.h>\n'+source.DECLARATIONS+"""
typedef struct {u32 header; s32 data[3];}Payload;
typedef struct {u32 before[4]; KeyedNode15188AD0 nodes[7]; Payload payloads[7]; u32 after[4];}State;
typedef char Width[(sizeof(void*)==4&&sizeof(KeyedNode15188AD0)==20&&__builtin_offsetof(KeyedNode15188AD0,payload)==8&&__builtin_offsetof(KeyedNode15188AD0,next)==12&&__builtin_offsetof(KeyedNode15188AD0,key)==16)?1:-1];
u8 *D_800DF7C8;static u8 *wantedHead;
static State actual,expected;static u32 logs[16][4],wanted[16][4],count,wantCount,mode,key,bad;
static u32 keys[4]={0,0x7FFFFFFFu,0x80000000u,0xFFFFFFFFu};
static u32 loc(State *s,void *p){u32 a=(u32)p,b=(u32)s;if(!a)return 0;return a>=b&&a<b+sizeof(*s)?a-b+0x10000u:a;}
static void provider(State *s,u8 **head,u32 role,void *p,u32 flag,u32 out[16][4],u32 *number){
 u32 i,n=*number,ordinal=n/2;KeyedNode15188AD0 *node=0;
 if(n>=16){bad=1;return;}
 out[n][0]=role;out[n][1]=loc(s,p);out[n][2]=flag;out[n][3]=loc(s,*head);(*number)++;
 if(role==1){
  for(i=0;i<7;i++)if(s->payloads[i].data==p){node=&s->nodes[i];break;}
  if(!node){bad=1;return;}s->payloads[i].header=(s->payloads[i].header&0xFFFFFFu)|(flag<<24);
  if(!ordinal){
   if(mode==1)node->next=&s->nodes[6];
   if(mode==2&&node->next)node->next->key=(s32)key;
   if(mode==3)*head=(u8*)&s->nodes[6];
   if(mode==4)node->payload=s->payloads[6].data;
  }
 }else{
  for(i=0;i<7;i++)if(&s->nodes[i]==p){node=&s->nodes[i];break;}
  if(!node){bad=1;return;}
  for(i=0;i<sizeof(*node);i++)((u8*)node)[i]=0xDD;
  node->next=0;
 }
}
void func_100043B4(s32 *p,u32 flag){provider(&actual,&D_800DF7C8,1,p,flag,logs,&count);}
void func_10004074(void *p){provider(&actual,&D_800DF7C8,2,p,0,logs,&count);}
"""+body+"""
static void initialize(State *s,u32 length,u32 mask){
 u32 i,seed=(mask+length*17)&255u;
 for(i=0;i<sizeof(*s);i++)((u8*)s)[i]=0xA5;
 for(i=0;i<7;i++){
  s->nodes[i].payload=s->payloads[i].data;
  s->nodes[i].next=i+1<length?&s->nodes[i+1]:0;
  s->nodes[i].key=(s32)(i<length&&(mask>>i&1)?key:~key);
  s->payloads[i].header=0xFF000000u|((seed+i*0x10203u)&0xFFFFFFu);
 }
}
static int run(void){
 u32 length,mask,k,i,j,a,b;KeyedNode15188AD0 *node,*previous,*next;
 for(length=0;length<=6;length++)for(mask=0;mask<(1u<<length);mask++)for(k=0;k<4;k++)for(mode=0;mode<5;mode++){
  key=keys[k];count=wantCount=bad=0;initialize(&actual,length,mask);initialize(&expected,length,mask);
  for(i=0;i<16;i++)for(j=0;j<4;j++)logs[i][j]=wanted[i][j]=0;
  D_800DF7C8=length?(u8*)&actual.nodes[0]:0;wantedHead=length?(u8*)&expected.nodes[0]:0;
  previous=0;node=(KeyedNode15188AD0*)wantedHead;
  while(node){
   next=node->next;
   if((u32)node->key==key){
    if(previous)previous->next=next;else wantedHead=(u8*)next;
    provider(&expected,&wantedHead,1,node->payload,2,wanted,&wantCount);
    provider(&expected,&wantedHead,2,node,0,wanted,&wantCount);
   }else previous=node;
   node=next;
  }
  func_15188AD0((s32)key);
  if(bad||count!=wantCount||loc(&actual,D_800DF7C8)!=loc(&expected,wantedHead))return 23;
  for(i=0;i<16;i++)for(j=0;j<4;j++)if(logs[i][j]!=wanted[i][j])return 23;
  for(i=0;i<7;i++){
   if(loc(&actual,actual.nodes[i].payload)!=loc(&expected,expected.nodes[i].payload)||
      loc(&actual,actual.nodes[i].next)!=loc(&expected,expected.nodes[i].next))return 23;
  }
  for(i=0;i<sizeof(actual);i++){
   a=b=0;
   for(j=0;j<7;j++)if(i>=__builtin_offsetof(State,nodes)+j*20+8&&i<__builtin_offsetof(State,nodes)+j*20+16)a=b=1;
   if(!a&&!b&&((u8*)&actual)[i]!=((u8*)&expected)[i])return 23;
  }
 }return 0;
}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
"""


class KeyedNodeRemovalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.installed=source.digest((ROOT/source.SOURCE).read_bytes())!=source.INPUTS[source.SOURCE]
        if cls.installed:source.audit(ROOT,cls.out)
        else:source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        cls.values=source.snapshot(cls.out);cls.rom=cls.values['conker/conker.us.bin']
        cls.obj,diag=source.compile_owner(ROOT,cls.out,source.ISOLATED_HEADER+source.DECLARATIONS+source.SELECTED[NAME],'fresh-selected')
        if diag:raise ValueError(diag)
        text,fs=source.link_owner(ROOT,cls.out,cls.obj,source.OWNER)
        cls.words=list(struct.unpack_from('>41I',text,fs[NAME]['value']));cls.truth=list(struct.unpack_from('>41I',cls.rom,0x1B5F80))
        cls.receipt=dict(installed=cls.installed)

    @classmethod
    def tearDownClass(cls):
        (cls.out/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n');print(cls.receipt)

    def compare(self,c,phase=0,images=None,anchors=None,entry=ENTRY):
        memory=fixture(c,phase,anchors);expected,trace,calls,seen=reference(c,memory,anchors)
        models=[RemovalOracle(code,c,phase,entry,anchors,memory=memory).run()for code in images or (self.truth,self.words)]
        for m in models:self.assertEqual(public(m.memory),expected);self.assertEqual(m.trace,trace);self.assertEqual(m.calls,calls);self.assertEqual(m.observations,seen)
        self.assertEqual(complete(models[0]),complete(models[1]));return models

    def test_01_direct_body_GNU_bindings_neighbors_and_actual_Make(self):
        self.assertEqual(self.words,self.truth)
        raw,bindings=source.payload(self.obj,NAME);self.assertEqual(bindings,source.BINDINGS)
        self.assertEqual(source.payload(source.original(ROOT,self.out,NAME),NAME),(raw,bindings))
        q=json.loads((self.out/'qualification.json').read_text());self.assertEqual((q['total_words'],q['preserved_neighbors']),(41,14))
        self.assertEqual(json.loads((self.out/'make-shadow.json').read_text())['actual_Make_commands'],3)
        before=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(before,ENTRY,164);c=Case()
        old=RemovalOracle(list(struct.unpack_from('>41I',before,at)),c).run()
        self.assertEqual(old.calls,[]);self.assertNotEqual(public(old.memory),reference(c,fixture(c))[0])
        self.receipt.update(body_words=41,frame=48,bindings=4,new_guards=0,neighbors=14,alignment_filler_words=0)

    def test_02_all_list_shapes_widths_mutations_and_guest_aliases(self):
        visits=set();count=aliases=0
        for length in range(7):
            for mask,key,mode,phase in itertools.product(range(1<<length),(0,0x7FFFFFFF,0x80000000,0xFFFFFFFF),range(5),(0,8)):
                models=self.compare(Case(length,mask,key,mode),phase);visits.update(models[0].visits);count+=1
        for length,mask,key,mode,phase,alias in itertools.product((1,3,6),(0x15,0x3F),(0,0xFFFFFFFF),range(5),(0,8),(1,2,3)):
            self.compare(Case(length,mask,key,mode,alias),phase);aliases+=1
        self.assertEqual(visits,set(range(ENTRY,ENTRY+164,4))-{0x15188B2C,0x15188B48})
        self.receipt.update(guest_phases=count,guest_alias_phases=aliases,reachable_words=39,unreachable_duplicate_words=2,
            cached_successor_before_helpers=True,unlink_before_payload_read_and_mark=True,all_matching_nodes_removed=True,
            full_volatile_register_and_argument_home_clobbers=True,guest_aliases_not_portable_C_claim=True,incidental_V0_not_semantic_return=True)

    def native(self,body,label,opt='-O2'):
        path=self.out/(label+opt+'.c');exe=path.with_suffix('.elf');path.write_text(native_harness(body))
        p=subprocess.run(native_command(opt)+[str(path),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        return subprocess.run([str(exe)],capture_output=True,timeout=20).returncode

    def test_03_native_typed_nodes_order_fences_and_wrong_C(self):
        body=source.SELECTED[NAME]
        for opt in ('-O0','-O2','-O3'):self.assertEqual(self.native(body,'native',opt),0)
        controls=[('gate','key == node->key','key != node->key'),
            ('one-pass','node = next;','(void)next; return;'),
            ('previous','func_10004074(node);','func_10004074(node); previous = node;'),
            ('late-next','node = next;','(void)next; node = node->next;'),
            ('head','D_800DF7C8 = (u8 *)next','D_800DF7C8 = (u8 *)node'),
            ('flag','node->payload, 2','node->payload, 3'),
            ('free-payload','func_10004074(node);','func_10004074(node->payload);')]
        block='            func_100043B4(node->payload, 2);\n            func_10004074(node);'
        wrong=body.replace(block,'').replace('            if (previous == NULL) {',block+'\n            if (previous == NULL) {')
        controls.append(('late-unlink',body,wrong))
        for label,a,b in controls:
            wrong=body.replace(a,b);self.assertNotEqual(wrong,body);self.assertNotEqual(self.native(wrong,'wrong-'+label),0,label)
        self.receipt.update(native_cases_per_optimization=2540,native_optimizations=3,trap_UBSan=True,effective_wrong_C_controls=8,
            real_typed_node_and_payload_objects=True,poison_provider_not_actual_deallocation=True)

    def test_04_two_original_caller_windows_and_ignored_result(self):
        count=0
        for key,condition,phase in itertools.product((0,0x80000000,0xFFFFFFFF),(0,1),(0,8)):
            c=Case(4,5,key);models=[];memory=fixture(c,phase);frame=STACK+phase-0xD0
            for code in (self.truth,self.words):
                connected=dict(zip(range(ENTRY,ENTRY+164,4),code))
                connected.update(zip(range(0x1502A88C,0x1502A8A0,4),struct.unpack_from('>5I',self.rom,0x57D3C)))
                put(memory,frame+0xE4,key);put(memory,frame+0xF4,condition);memory[ACTOR+4]=1
                m=RemovalOracle(list(struct.unpack_from('>17I',self.rom,0x57C64)),c,phase,entry=0x1502A7B4,connected=connected,memory=memory,frame_offset=-0xD0)
                put(m.memory,frame+0x3C,0xDEAD0000);put(m.memory,frame+0x38,m.before[16]);m.r[16]=ACTOR;m.before[29]+=0xD0
                m.run();self.assertEqual(m.r[2],1);self.assertEqual(sum(t==ENTRY for t,_ in m.calls),int(bool(key and condition)));models.append(m)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        for extra,phase in itertools.product((0,EXTRA),(0,8)):
            c=Case(4,5,ACTOR);models=[];memory=fixture(c,phase);frame=STACK+phase-32;put(memory,ACTOR+0x31C,extra)
            for code in (self.truth,self.words):
                connected=dict(zip(range(ENTRY,ENTRY+164,4),code))
                m=RemovalOracle(list(struct.unpack_from('>14I',self.rom,0x8E660)),c,phase,entry=0x150611B0,connected=connected,memory=memory,frame_offset=-32)
                for offset,reg in ((0x14,16),(0x18,17),(0x1C,31)):put(m.memory,frame+offset,m.before[reg])
                m.r[17]=ACTOR;m.r[4]=ACTOR;m.before[29]+=32;m.run()
                self.assertEqual(m.calls[0],(ENTRY,(ACTOR,)));self.assertEqual(m.calls[-1],(FOLLOW,(ACTOR,)))
                self.assertEqual(sum(t==FREE for t,_ in m.calls),2+bool(extra));models.append(m)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.receipt.update(original_caller_window_phases=count,both_direct_call_sites=True,command_caller_returns_one=True,
            actor_caller_ignores_target_result=True,complete_parents_or_current_stub_execution_claimed=False)

    def test_05_independent_GNU_symbol_rebases(self):
        from tools.experiments.alternative_source_draft_word_screen import emit_function
        original=source.original(ROOT,self.out,NAME);links=count=0
        for i in range(3):
            entry=0x17007FFC+i*0x10000;syms=dict(D_800DF7C8=0x80208000+i*0x10004,func_100043B4=0x17203000+i*0x1000,func_10004074=0x1730FFFC+i*0x20000);images=[]
            for label,obj in [('original',original),('C',self.obj)]:
                text,fs,rs=source.parse_object(obj);assembly,unknown=emit_function(text,fs[NAME],rs,NAME,syms);self.assertFalse(unknown)
                stem=self.out/('rebase-%d-%s'%(i,label));asm=stem.with_suffix('.s');out=stem.with_suffix('.o');ld=stem.with_suffix('.ld');elf=stem.with_suffix('.elf')
                asm.write_text(assembly);ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(out),str(asm)],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',NAME,*['--defsym=%s=0x%X'%p for p in syms.items()],'-o',str(elf),str(out)],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>41I',sections(elf)['.text'][1])));links+=1
            self.assertEqual(images[0],images[1])
            for mask,phase,mode in itertools.product((0,5,63),(0,8),(0,1,3)):self.compare(Case(6,mask,0xFFFFFFFF,mode),phase,images,syms,entry);count+=1
        self.receipt.update(independent_GNU_links=links,rebase_phases=count,all4_bindings_and_signed_low_carries=True)

    def test_06_original_heap_marker_and_free_with_bounded_interrupts(self):
        connected={}
        for entry,rom,words in ((MARK,0x43B4,22),(FREE,0x4074,119)):
            raw=self.rom[rom:rom+words*4];at=source.elf_slot_offset(self.values['conker/build/conker.us.elf'],entry,words*4)
            self.assertEqual(self.values['conker/build/conker.us.elf'][at:at+words*4],raw)
            connected.update(zip(range(entry,entry+words*4,4),struct.unpack('>%dI'%words,raw)))
        visits=set();count=0
        for mask,key,phase in itertools.product((0,1),(0,0x80000000,0xFFFFFFFF),(0,8)):
            c=Case(1,mask,key);models=[]
            for code in (self.truth,self.words):
                memory=fixture(c,phase);block=NODES[0]-12
                for a,v in ((block,0),(block+4,0),(block+8,0x01000020),(0x800380B4,block),(0x800380B8,0),
                            (0x800380BC,0),(0x800380B0,0),(0x8002AC30,0)):put(memory,a,v)
                m=RemovalOracle(code,c,phase,connected=connected,memory=memory).run()
                self.assertEqual(m.mask,0x003FFF01)
                self.assertEqual(sum(t==INTMASK for t,_ in m.calls),4*mask)
                if mask:
                    self.assertEqual(read(m.memory,HEAD),0);self.assertEqual(read(m.memory,PAYLOADS[0]-4)>>24,2)
                    self.assertEqual(read(m.memory,block+8),0x20);self.assertEqual(read(m.memory,0x800380B8),block)
                    self.assertEqual(read(m.memory,0x800380BC),block);self.assertEqual(read(m.memory,0x800380B0),block)
                    self.assertEqual(read(m.memory,0x8002AC30),0x20)
                visits.update(m.visits);models.append(m)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.assertTrue(set(range(MARK,MARK+88,4))<=visits)
        self.receipt.update(original_helper_static_words=141,marker_words_visited=22,free_words_visited=len(visits&set(range(FREE,FREE+476,4))),
            connected_helper_phases=count,empty_free_list_single_block_path=True,interrupt_mask_restored=True,
            full119word_free_coverage_or_hardware_interrupt_or_gameplay_claimed=False)

    def test_07_fired_root_fault_prefixes(self):
        count=0
        for mask,mode,phase in itertools.product((0,5,63),(0,1),(0,8)):
            c=Case(6,mask,0xFFFFFFFF,mode);good=RemovalOracle(self.truth,c,phase).run()
            for cut in range(good.root_accesses):
                models=[RemovalOracle(code,c,phase)for code in (self.truth,self.words)]
                for m in models:m.root_fault=cut
                for m in models:
                    with self.assertRaises(faults.AccessBoundary):m.run()
                self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(models[0].trace,models[1].trace)
                self.assertEqual((models[0].current_pc,models[0].delay_of),(models[1].current_pc,models[1].delay_of));count+=1
        self.assertGreater(count,300);self.receipt.update(fired_root_fault_prefixes=count,portable_fault_or_MMU_claimed=False)

    def test_08_strict_image_27_inputs_and_corruptions(self):
        before=self.values['conker/build/conker.us.elf'];expected=source.predicted_image(before,self.rom)
        self.assertEqual(expected,(self.out/'first-linked.elf').read_bytes());at=source.elf_slot_offset(before,ENTRY,164)
        sym=next(pos for pos,n,f,_ in source.symbol_rows(before)if n==NAME and f[1:3]==(ENTRY,12))
        for pos in (0,len(expected)-1,at,at+159,at+163,at+164,sym+8):
            bad=bytearray(expected);bad[pos]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),self.rom)
        with self.assertRaises(ValueError):source.check_image(before,expected[:-1],self.rom)
        self.assertEqual(len(self.values),27)
        for name,old in self.values.items():
            self.assertEqual(source.digest(old),source.INPUTS[name])
            current=source.recovered_owner(old.decode()).encode()if self.installed and name==source.SOURCE else expected if self.installed and name=='conker/build/conker.us.elf'else old
            self.assertEqual((ROOT/name).read_bytes(),current)
        self.assertEqual(source.digest((self.out/'before-padded.o').read_bytes()),source.BEFORE_OBJECT_SHA)
        self.receipt.update(strict_image_corruptions_rejected=8,live_and_historical_inputs=27,old_object_pinned=True,
            metadata_exclusions=0,guard_manifest_unchanged=True)


if __name__=='__main__':
    unittest.main()
