"""Embedded actor link: actual dispatcher, typed native cases and guest order."""
from dataclasses import dataclass
from pathlib import Path
import csv,io,itertools,json,struct,subprocess,unittest

from tools.experiments import game_payload_owner_link_event as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_route_node_search_oracle import SearchOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT=Path(__file__).resolve().parents[2]
OWNER,EVENT,ALT=0x20000,0x24000,0x26000
HELPER,SCAN,DEFAULT,RELEASE,PROVIDER=0x1516972C,0x151696DC,0x15169804,0x15168B10,0x15600000
COUNT,SLOTS,DESTRUCTORS=0x800DD190,0x800DD198,0x8008B4D0
WORDS=(0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0x12345678)


@dataclass(frozen=True)
class Case:
    command:int=45
    relation:int=0
    pattern:int=0
    alias:int=0
    mode:int=0


def fixture(target,c,phase=0):
    sp=STACK+phase;state=OWNER+target['offset']
    event={1:state,2:state+4,3:state-4,4:OWNER+8,5:sp+8,6:sp-4}.get(c.alias,EVENT)
    m={sp+i:(i*17+0xA5)&255 for i in range(-0x100,0x80)}
    for base,n in((OWNER-16,0x1B0),(event-16,64),(ALT-16,32)):
        for i in range(n):m.setdefault(base+i,(i*13+37)&255)
    first=WORDS[c.pattern%6];second=first^0x87654321
    if c.relation==4:second=first
    put(m,event,first);put(m,event+4,second);m[event+8]=0x12;m[event+9]=0xE7
    first,second=read(m,event),read(m,event+4)
    put(m,state,first if c.relation in(0,4)else second if c.relation==1 else first^second^0xB5B5B5B5)
    m[state+4]=m[event+4]if c.relation==3 else m[event+4]^1
    return m,event


def public(memory):
    return {a:v for a,v in memory.items()if not STACK-0x100<=a<STACK+0x88}


def effect(memory,owner,target,mode):
    if mode&1:memory[owner+0x31]^=0x55
    if mode&2:put(memory,owner+target['offset'],ALT)


def reference(target,c,memory,event,phase=0):
    m=dict(memory);sp=STACK+phase;state=OWNER+target['offset'];trace=[];calls=[]
    def rd(a,n=4):
        value=read(m,a,n);trace.append(('R',a,n,value));return value
    def wr(a,value,n=4):
        put(m,a,value,n);trace.append(('W',a,n,value&((1<<(8*n))-1)))
    wr(sp+8,c.command);wr(sp-4,0xDEAD0000)
    command=c.command&255
    if command==45:
        current=rd(state);first=rd(event)
        if current==first:
            wr(state,rd(event+4));wr(state+4,rd(event+9,1),1)
        elif rd(event+4)==current:
            wr(state,first);wr(state+4,rd(event+8,1),1)
    elif command==0:
        first=rd(event);current=rd(state)
        if first==current or rd(state+4,1)==rd(event+4,1):
            calls.append((HELPER,(OWNER,)));effect(m,OWNER,target,c.mode)
    return m,calls,trace


class LinkOracle(TimingOracle):
    def __init__(self,words,memory,args,target,phase=0,mode=0,entry=None,connected=None,
                 helper=HELPER,other_callbacks=()):
        self.trace=[];self.visits=set();self.link_target=target;self.effect_mode=mode
        self.helper_address=helper
        self.allowed={target['entry']:3,helper:1,SCAN:1,DEFAULT:1,RELEASE:2,PROVIDER:1,
                      **{p:3 for p in other_callbacks if p}}
        super().__init__(words,memory,phase=phase,entry=target['entry']if entry is None else entry,
            arguments=args,connected=connected)

    def execute(self,word):
        if word>>26==32:
            self.dispatched_word=word;self.own_instruction=True
            try:SearchOracle.execute(self,word)
            finally:self.own_instruction=False
        else:super().execute(word)

    def get(self,address,size):
        value=super().get(address,size)
        if self.own_instruction:self.trace.append(('R',address,size,value))
        return value

    def put(self,address,value,size):
        super().put(address,value,size)
        if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(8*size))-1)))

    def record_call(self,target):
        assert target in self.allowed,hex(target)
        args=self.arguments(self.allowed[target]);named=HELPER if target==self.helper_address else target
        self.calls.append((named,args));self.events.append(('CALL',named,args))

    def hook(self,target):
        assert target in self.allowed and target not in(SCAN,DEFAULT,self.link_target['entry'])
        effect(self.memory,self.r[4],self.link_target,self.effect_mode)
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0x12345678,0x87654321


def controls(body):
    return dict(selected=body,
        command45=body.replace('command == 0x2D','command == 0x2E'),
        command0=body.replace('command == 0)','command == 1)'),
        andGate=body.replace('first == link->owner ||','first == link->owner &&'),
        forwardOwner=body.replace('link->owner = event->after;','link->owner = event->before;'),
        reverseOwner=body.replace('link->owner = event->before;','link->owner = event->after;'),
        forwardIdentity=body.replace('link->identity = event->after_identity;','link->identity = event->before_identity;'),
        reverseIdentity=body.replace('link->identity = event->before_identity;','link->identity = event->after_identity;'),
        narrowKey=body.replace('current == event->before','(u8)(u32)current == (u8)(u32)event->before'),
        wrongByte=body.replace('((u8 *)event)[4]','event->after_identity'),
        omittedRelease=body.replace('            func_1516972C((struct102 *)owner);',''),
        unmatchedReverse=body.replace('} else if (current == event->after) {','} else {'),
        wrongFirstMatch=body.replace('current == event->before','current == event->before && current != event->after'))


def native_harness(name,target,parent,table):
    bodies='\n'.join(body.replace(name,label)for label,body in controls(source.SELECTED[name]).items())
    array='D_8008A8D8'
    parent_name='func_%08X'%target['parent']
    init='\n'.join('%s[%d]=%s;'%(array,i,'target'if i==target['index']else'other'if word else'0')for i,word in enumerate(table))
    checks='\n'.join('if(variant(%s)!=%d)return %d;'%(label,0 if label=='selected'else 23,40+i)
        for i,label in enumerate(controls(source.SELECTED[name])))
    count=257*256*5*4*2
    return source.ISOLATED_HEADERS+source.DECLARATIONS+'''
typedef char LinkSize[sizeof(EmbeddedOwnerLink)==8?1:-1];
typedef char EventSize[sizeof(OwnerLinkEvent)==12?1:-1];
typedef char WordWidth[sizeof(void*)==4&&sizeof(s32)==4?1:-1];
typedef char HeaderSize[sizeof(struct260)==0x24?1:-1];
typedef void(*Callback)(struct260*,s32,u8);
static u8 *arena,expected[160];static OwnerLinkEvent packet;
static u8 references[6][256] __attribute__((aligned(256)));
static Callback ARRAY[COUNT];static u32 calls,last,mode;
/* Fresh brk storage has no declared aggregate type or undersized header object. */
static void *allocate(u32 size){u32 old,got,begin,end;
 __asm__ volatile("int $0x80":"=a"(old):"0"(45),"b"(0):"memory","cc");
 begin=(old+15)&~15u;end=begin+size;
 __asm__ volatile("int $0x80":"=a"(got):"0"(45),"b"(end):"memory","cc");
 return got<end?0:(void*)begin;}
void func_1516972C(struct102 *p){calls++;last=(u32)p;if(mode&1)((u8*)p)[0x31]^=0x55;
 if(mode&2)((EmbeddedOwnerLink*)((u8*)p+OFFSET))->owner=references[5];}
static void other(struct260*p,s32 event,u8 command){func_1516972C((struct102*)p);}
'''.replace('OFFSET',str(target['offset'])).replace('ARRAY',array).replace('COUNT',str(target['count']))+bodies+'\n'+parent+'''
static int variant(Callback target){
 u32 iface,cmd,relation,pattern,plan,j,selected,selector,want,count=0;
 u8 *a=arena,*b=expected,*owner=arena+16;
 EmbeddedOwnerLink *link=(EmbeddedOwnerLink*)(owner+OFFSET),expectedLink;
 u8 *first,*second,*current;
INIT
 for(iface=0;iface<=256;iface++)for(cmd=0;cmd<256;cmd++)for(relation=0;relation<5;relation++)
 for(pattern=0;pattern<4;pattern++)for(plan=0;plan<2;plan++){
  for(j=0;j<160;j++)a[j]=(u8)(j*13+37);
  selector=iface?iface-1:INDEX;selected=selector<COUNT?selector:0;
  first=pattern==0?0:references[pattern-1]+(plan?(selector^128):selector);second=pattern==1?0:references[pattern]+(plan?(selector^128):selector);
  if(relation==4)second=first;
  current=relation==0||relation==4?first:relation==1?second:references[5];
  packet.before=first;packet.after=second;packet.before_identity=0x12;packet.after_identity=0xE7;
  link->owner=current;link->identity=(u8)(((u8*)&packet)[4]^(relation==3?0:1));
  owner[SELECTOR]=(u8)selector;
  calls=last=0;mode=plan?3:0;for(j=0;j<160;j++)b[j]=a[j];want=0;expectedLink=*link;
  {
   if(selected==INDEX){
    if(cmd==45){if(current==first){expectedLink.owner=second;expectedLink.identity=packet.after_identity;}
     else if(current==second){expectedLink.owner=first;expectedLink.identity=packet.before_identity;}}
    else if(!cmd&&(first==current||expectedLink.identity==((u8*)&packet)[4]))want=1;
   }else if(ARRAY[selected])want=1;
  }
  for(j=0;j<want;j++){if(mode&1)b[16+0x31]^=0x55;if(mode&2)expectedLink.owner=references[5];}
  for(j=0;j<sizeof(expectedLink);j++)b[16+OFFSET+j]=((u8*)&expectedLink)[j];
  if(iface)PARENT((struct260*)owner,(s32)(u32)&packet,(u8)cmd);
  else target((struct260*)owner,(s32)(u32)&packet,(u8)cmd);
  if(calls!=want||(want&&last!=(u32)owner))return 23;
  for(j=0;j<160;j++)if(a[j]!=b[j])return 23;count++;
 }
 return count==EXPECTED?0:24;
}
static int run(void){arena=allocate(160);if(!arena)return 25;CHECKS return 0;}
__attribute__((force_align_arg_pointer)) void _start(void){int code=run();__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
'''.replace('INIT',init).replace('COUNT',str(target['count'])).replace('INDEX',str(target['index'])).replace('SELECTOR',str(target['selector'])).replace('OFFSET',str(target['offset'])).replace('ARRAY',array).replace('PARENT',parent_name).replace('EXPECTED',str(count)).replace('CHECKS',checks)


class PayloadOwnerLinkEventTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);cls.rom=cls.values['conker/conker.us.bin']
        cls.installed=all((ROOT/t['source']).read_text()==source.recovered_owner(name,cls.values[t['source']].decode())for name,t in source.TARGETS.items())
        if cls.installed:source.audit(ROOT,cls.out)
        else:source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        cls.images={};cls.objects={};cls.parents={};cls.tables={};cls.parent_sources={}
        for name,t in source.TARGETS.items():
            obj,diag=source.compile_owner(ROOT,cls.out,source.ISOLATED_HEADERS+source.DECLARATIONS+source.SELECTED[name],'fresh-'+name)
            if diag:raise ValueError(diag)
            data,fs=source.link_owner(ROOT,cls.out,obj,t['owner']);raw=list(struct.unpack_from('>43I',data,fs[name]['value']))
            fitted=list(raw)
            for i,word in source.RAW_ROLE_WORDS.items():fitted[i]=source.role_word(word,commute=i==20)
            cls.images[name]=(list(struct.unpack_from('>43I',cls.rom,t['rom'])),raw,fitted);cls.objects[name]=obj
            off=t['parent']-0x15000000+0x2D4B0
            cls.parents[name]=list(struct.unpack_from('>%dI'%(t['parent_size']//4),cls.rom,off))
            cls.tables[name]=list(struct.unpack_from('>%dI'%t['count'],cls.rom,t['table_rom']))
            text=cls.values[t['parent_source']].decode();lo,hi=source.function_span(text,'func_%08X'%t['parent'])
            cls.parent_sources[name]=text[lo:hi]
        cls.receipt=dict(installed=cls.installed)

    @classmethod
    def tearDownClass(cls):
        (cls.out/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n');print(cls.receipt)

    def compare(self,name,c,phase=0,images=None,entry=None,helper=HELPER):
        t=source.TARGETS[name];memory,event=fixture(t,c,phase)
        expected,calls,trace=reference(t,c,memory,event,phase);models=[]
        for code in images or self.images[name]:
            m=LinkOracle(code,memory,(OWNER,event,c.command),t,phase,c.mode,entry=entry,helper=helper).run()
            self.assertEqual(public(m.memory),public(expected),(name,c));self.assertEqual(m.calls,calls)
            self.assertEqual([x for x in m.trace if not STACK-0x100<=x[1]<STACK+0x88],
                [x for x in trace if not STACK-0x100<=x[1]<STACK+0x88]);models.append(m)
        self.assertEqual(complete(models[0]),complete(models[-1]));self.assertEqual(models[0].trace,models[-1].trace)
        return models

    def test_01_owners_real_Make_closed_roles_and_effective_stubs(self):
        q=json.loads((self.out/'qualification.json').read_text());m=json.loads((self.out/'make-shadow.json').read_text())
        self.assertEqual((q['total_words'],q['new_guards'],q['compiler_only'],m['actual_Make_commands']),(43,4,False,3))
        for name,t in source.TARGETS.items():
            truth,raw,fitted=self.images[name];self.assertEqual(truth,fitted)
            self.assertEqual({i for i in range(43)if truth[i]!=raw[i]},set(source.RAW_ROLE_WORDS))
            self.assertEqual(source.payload(source.original(ROOT,self.out,name),name),source.normalized(name,*source.payload(self.objects[name],name)))
            at=source.elf_slot_offset(self.values['conker/build/conker.us.elf'],t['entry'],172)
            old=list(struct.unpack_from('>43I',self.values['conker/build/conker.us.elf'],at));memory,event=fixture(t,Case())
            model=LinkOracle(old,memory,(OWNER,event,45),t).run()
            self.assertNotEqual(public(model.memory),public(self.compare(name,Case())[0].memory))
        self.receipt.update(words=43,frame_each=24,bindings_each=1,new_guards=4,closed_role_words_each=4,
            actual_Make_commands=3,neighbors=q['preserved_neighbors'],old_stub_rejected=True,
            raw_complete_state_claimed=False)

    def test_02_all_commands_widths_order_aliases_and_ignored_unmapped_payloads(self):
        phases=aliases=0
        for name,t in source.TARGETS.items():
            visits=set()
            cases=(Case(cmd,relation,pattern,mode=pattern%4)for cmd,relation,pattern in itertools.product(range(256),range(5),range(2)))
            for c,phase in itertools.product(cases,(0,8)):
                visits.update(self.compare(name,c,phase)[0].visits);phases+=1
            for cmd,relation,pattern,phase in itertools.product((0,45,255,0xAB000000,0xAB00002D),range(5),range(6),(0,8)):
                self.compare(name,Case(cmd,relation,pattern),phase);phases+=1
            for alias,cmd,relation,phase in itertools.product(range(1,7),(0,45,255,0xAB00002D),range(5),(0,8)):
                self.compare(name,Case(cmd,relation,3,alias),phase);aliases+=1
            self.assertEqual(visits,set(range(t['entry'],t['entry']+172,4))-{t['entry']+76})
            for cmd in(1,2,44,46,255,0xAB0000FF):
                memory,_=fixture(t,Case(cmd));models=[LinkOracle(w,memory,(0xDEADC000,0xBEEF0010,cmd),t).run()for w in self.images[name]]
                self.assertEqual(complete(models[0]),complete(models[-1]));self.assertFalse(models[0].calls)
        self.receipt.update(guest_phases=phases,guest_alias_phases=aliases,reachable_words_each=42,
            retained_unreachable_words_each=1,full_mask_home_and_order=True,unmapped_ignored_arguments=True,
            portable_native_alias_claimed=False)

    def test_03_native32_actual_C_callers_and_twelve_defined_wrong_C(self):
        for name,t in source.TARGETS.items():
            body=native_harness(name,t,self.parent_sources[name],self.tables[name])
            for opt in('-O0','-O2','-O3'):
                unit=self.out/(name+opt+'.c');exe=unit.with_suffix('.elf');unit.write_text(body)
                q=subprocess.run([*native_command(opt),'-mstackrealign',str(unit),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
                self.assertEqual(q.returncode,0,q.stdout+q.stderr)
                self.assertEqual(subprocess.run([str(exe)],capture_output=True,timeout=180).returncode,0,(name,opt))
        self.receipt.update(native_cases_per_optimization=257*256*5*4*2,
            native_optimizations=3,trap_UBSan=True,defined_wrong_C_controls_each=12,actual_C_callers=True,
            native_disjoint_allocated_owner_and_typed_packet=True,native_explicit_opaque_bytes_and_fences=True,
            undersized_declared_header_object_used=False,all_native_selector_bytes=True)

    def test_04_actual_registration_and_complete_dispatcher(self):
        count=0
        for name,t in source.TARGETS.items():
            table=self.tables[name];self.assertEqual(table[t['index']],t['entry'])
            ptr=struct.pack('>I',t['entry']);jal=struct.pack('>I',0x0C000000|(t['entry']>>2&0x3FFFFFF))
            self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==ptr],[t['table_rom']+4*t['index']])
            self.assertFalse(any(self.rom[i:i+4]==jal for i in range(0,len(self.rom),4)))
            old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,t['parent'],t['parent_size'])
            self.assertEqual(list(struct.unpack_from('>23I',old,at)),self.parents[name])
            at=source.elf_slot_offset(old,t['table'],4*t['count'])
            self.assertEqual(old[at:at+4*t['count']],self.rom[t['table_rom']:t['table_rom']+4*t['count']])
            visits=set()
            for selector,cmd,relation,phase in itertools.product(range(256),(0,34,36,37,45,255,0xAB000022,0xAB00002D),range(5),(0,8)):
                index=selector if selector<t['count']else 0
                c=Case(cmd,relation,3,mode=3);memory,event=fixture(t,c,phase)
                memory[OWNER+t['selector']]=selector
                for i,word in enumerate(table):put(memory,t['table']+4*i,word)
                expected=dict(memory);calls=[];command=cmd&255
                if table[index]:
                    calls.append((table[index],(OWNER,event,command)))
                    if index==t['index']:
                        expected,more,_=reference(t,Case(command,relation,3,mode=3),expected,event,phase);calls+=more
                    else:effect(expected,OWNER,t,3)
                models=[]
                for code in self.images[name]:
                    connected=dict(zip(range(t['entry'],t['entry']+172,4),code))
                    model=LinkOracle(self.parents[name],memory,(OWNER,event,cmd),t,phase,3,entry=t['parent'],
                        connected=connected,other_callbacks=table).run();models.append(model);visits.update(model.visits)
                    self.assertEqual(public(model.memory),public(expected));self.assertEqual(model.calls,calls)
                self.assertEqual(complete(models[0]),complete(models[-1]));count+=1
            self.assertTrue(set(range(t['parent'],t['parent']+92,4))<=visits)
        self.receipt.update(caller_phases=count,caller_words=23,reachable_caller_words=23,
            all_caller_words_visited=True,actual_registration_indices=[16],actual_table_lengths=[74],
            other_callbacks_bounded=True,unsigned_selector_and_out_of_range_slot_zero=True,
            broadcast_dispatcher_recovery_claimed=False)

    def test_05_original_current_release_scan_and_default_chain(self):
        old=self.values['conker/build/conker.us.elf'];connected={}
        for entry,size in((HELPER,112),(SCAN,80),(DEFAULT,32)):
            off=entry-0x15000000+0x2D4B0;raw=self.rom[off:off+size];at=source.elf_slot_offset(old,entry,size)
            self.assertEqual(old[at:at+size],raw);connected.update(zip(range(entry,entry+size,4),struct.unpack('>%dI'%(size//4),raw)))
        phases=0;visits=set()
        for name,t in source.TARGETS.items():
            for kind,n,provider,phase in itertools.product((0,1,2,7,255),(0,1,3,127,128,255),(0,1),(0,8)):
                c=Case(0,0,3);memory,event=fixture(t,c,phase);memory[OWNER]=kind;put(memory,OWNER+8,ALT)
                memory[COUNT]=n
                for i in range(127):put(memory,SLOTS+4*i,OWNER if i%2==0 else ALT)
                put(memory,DESTRUCTORS+52*kind,PROVIDER if provider else 0)
                expected=dict(memory)
                if 0<n<128:
                    for i in range(n):
                        if read(expected,SLOTS+4*i)==OWNER:put(expected,SLOTS+4*i,ALT)
                models=[]
                for words in(self.images[name][0],self.images[name][-1]):
                    model=LinkOracle(words,memory,(OWNER,event,0),t,phase,connected=connected).run()
                    models.append(model);visits.update(model.visits)
                    self.assertEqual(public(model.memory),public(expected))
                    wanted=[(HELPER,(OWNER,)),(SCAN,(OWNER,))]
                    if kind>=2:wanted+=[(PROVIDER,(OWNER,))]if provider else[(DEFAULT,(OWNER,)),(RELEASE,(OWNER,1))]
                    self.assertEqual(model.calls,wanted)
                self.assertEqual(complete(models[0]),complete(models[-1]));phases+=1
        self.assertTrue(set(connected)<=visits)
        self.receipt.update(actual_release_chain_words=56,release_chain_phases=phases,all_release_chain_words_visited=True,
            signed_count_and_cached_scan_bound=True,lower_release_and_type_callback_providers_bounded=True,
            hardware_or_full_heap_acceptance_claimed=False)

    def link_words(self,name,obj,entry,helper,label):
        text,fs,rs=source.parse_object(obj);asm,unknown=emit_function(text,fs[name],rs,name,dict(func_1516972C=helper));self.assertFalse(unknown)
        p=self.out/label;a=p.with_suffix('.s');o=p.with_suffix('.o');ld=p.with_suffix('.ld');elf=p.with_suffix('.elf')
        a.write_text(asm);ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(o),str(a)],capture_output=True,check=True)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',name,
            '--defsym=func_1516972C=0x%X'%helper,'-o',str(elf),str(o)],capture_output=True,check=True)
        return list(struct.unpack_from('>43I',sections(elf)['.text'][1]))

    def test_06_independent_GNU_rebases_and_fired_root_faults(self):
        phases=cuts=links=0
        for name,t in source.TARGETS.items():
            for i,(entry,helper)in enumerate(((t['entry'],HELPER),(0x18017FFC,0x18108000),(0x1A028000,0x1A30FFFC))):
                images=[]
                for j,obj in enumerate((source.original(ROOT,self.out,name),self.objects[name],self.out/('qualified-'+t['owner']+'.o'))):
                    code=self.link_words(name,obj,entry,helper,'rebase-'+name+'-%d-%d'%(i,j));links+=1
                    if j==1:
                        for pos,word in source.RAW_ROLE_WORDS.items():code[pos]=source.role_word(word,commute=pos==20)
                    images.append(code)
                self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
                for cmd,relation,phase in itertools.product((0,45,255,0xAB00002D),range(5),(0,8)):
                    self.compare(name,Case(cmd,relation,3),phase,images,entry,helper);phases+=1
            for cmd,relation,alias,phase in itertools.product((0,45,255),range(5),(0,1,3,5,6),(0,8)):
                c=Case(cmd,relation,3,alias);memory,event=fixture(t,c,phase)
                good=LinkOracle(self.images[name][0],memory,(OWNER,event,cmd),t,phase).run()
                for cut in range(good.root_accesses):
                    models=[LinkOracle(words,memory,(OWNER,event,cmd),t,phase)for words in(self.images[name][0],self.images[name][-1])]
                    for model in models:
                        model.root_fault=cut
                        with self.assertRaises(faults.AccessBoundary):model.run()
                    self.assertEqual(complete(models[0]),complete(models[-1]))
                    self.assertEqual((models[0].current_pc,models[0].delay_of),(models[-1].current_pc,models[-1].delay_of));cuts+=1
        self.receipt.update(independent_GNU_links=links,rebase_phases=phases,fired_root_fault_prefixes=cuts,
            guarded_complete_state_and_PC=True,portable_C_fault_claimed=False)

    def test_07_derived_guard_rows_role_and_strict_image_corruptions(self):
        old=self.values['conker/retail_word_patches.us.csv'];after=source.guard_bytes(old);self.assertTrue(after.startswith(old))
        fields=list(csv.DictReader(io.StringIO(old.decode())).fieldnames)
        rows=list(csv.DictReader(io.StringIO(after[len(old):].decode()),fieldnames=fields));self.assertEqual(len(rows),4)
        for name,t in source.TARGETS.items():
            own=[r for r in rows if r['function']==name]
            self.assertEqual({int(r['offset'],0)//4 for r in own},set(source.RAW_ROLE_WORDS))
            for row in own:
                i=int(row['offset'],0)//4;word=source.RAW_ROLE_WORDS[i]
                self.assertEqual((row['filename'],int(row['expected'],0),int(row['replacement'],0)),
                    (t['owner'],word,source.role_word(word,commute=i==20)))
                self.assertEqual((row['omit'],row['insert_after'],row['expected_relocations']),('false','','-'))
            raw,bindings=source.payload(self.objects[name],name)
            for pos in(0,40,44,48,80,88,148,168):
                wrong=bytearray(raw);wrong[pos]^=1
                with self.assertRaises(ValueError):source.normalized(name,bytes(wrong),bindings)
            with self.assertRaises(ValueError):source.normalized(name,raw,{})
        with self.assertRaises(ValueError):source.guard_bytes(old+b'\n')
        before=self.values['conker/build/conker.us.elf'];pred=source.predicted_image(before,self.rom)
        positions=[0,len(pred)-1,source.elf_slot_offset(before,HELPER,4),source.elf_slot_offset(before,0x80082B20,4)]
        for t in source.TARGETS.values():positions+=[source.elf_slot_offset(before,t['entry'],172),source.elf_slot_offset(before,t['parent'],4)]
        for pos in positions:
            wrong=bytearray(pred);wrong[pos]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(wrong),self.rom)
        with self.assertRaises(ValueError):source.check_image(before,pred[:-1],self.rom)
        self.receipt.update(guard_rows=4,guard_prefix_byte_identical=True,raw_role_negatives=9,
            strict_image_negatives=len(positions)+1,metadata_exclusions=0)

    def test_08_historical_inputs_and_installed_identity(self):
        sources={t['source']:name for name,t in source.TARGETS.items()}
        for name,old in self.values.items():
            self.assertEqual(source.digest(old),source.INPUTS[name])
            expected=old
            if self.installed:
                if name in sources:expected=source.recovered_owner(sources[name],old.decode()).encode()
                elif name=='conker/retail_word_patches.us.csv':expected=source.guard_bytes(old)
                elif name=='conker/build/conker.us.elf':expected=source.predicted_image(old,self.rom)
            self.assertEqual((ROOT/name).read_bytes(),expected,name)
        self.receipt.update(pinned_inputs=len(self.values),all_target_and_non_target_inputs_checked=True)
