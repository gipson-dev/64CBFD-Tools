"""Circular byte transfers, cached o32 count, five caller sites and real memcpy."""
from dataclasses import dataclass,replace
from pathlib import Path
import itertools,json,struct,subprocess,unittest
from tools.experiments import game_ring_buffer_transfers as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.match_progress import DEFAULT_SEGMENTS
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_command_stream_relocator import StopCode,WindowEnd
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT=Path(__file__).resolve().parents[2]
NAMES=tuple(source.TARGETS);COPY=0x10022EC0
RING,LINEAR,OBJECT=0x28010,0x30010,0x34000
CAPACITIES=(1,2,3,4,7,16,32)
WORDS=(0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0x87654321,0xFFFFFFFE,256)
def signed(x):return (x&0xFFFFFFFF)-0x100000000 if x&0x80000000 else x&0xFFFFFFFF


@dataclass(frozen=True)
class Case:
    capacity:int=7
    cursor:int=6
    count:int=2
    align:int=0
    homes:bool=False
    empty_unbacked:bool=False
    prefix:bool=False


def pointers(c):return (0,0)if c.empty_unbacked else(RING+c.align,LINEAR+(c.align^1))
def public(m):return {a:v for a,v in m.items()if not STACK-0x600<=a<STACK+0x408}


def fixture(c,phase=0):
    m={STACK+phase+i:(i*17+0xA5)&255 for i in range(-0x600,0x400)}
    if not c.empty_unbacked:
        m.update({RING+i:(i*13+c.capacity*7+c.align*31)&255 for i in range(-16,256)})
        m.update({LINEAR+i:(i*29+c.cursor*11+c.capacity)&255 for i in range(-16,256)})
    m.update({OBJECT+i:0xA5 for i in range(32)})
    put(m,STACK+phase+16,c.count);return m


def reference(m,name,c):
    m=dict(m);ring,linear=pointers(c);calls=[];cursor=c.cursor;remaining=c.count
    if remaining:
        assert c.capacity>0 and 0<=cursor<=c.capacity
        for i in range(remaining):
            at=ring+(cursor+i)%c.capacity
            if name==NAMES[0]:m[at]=m[linear+i]
            else:m[linear+i]=m[at]
        while remaining:
            chunk=min(remaining,c.capacity-cursor)
            args=(ring+cursor,linear,chunk)if name==NAMES[0]else(linear,ring+cursor,chunk)
            calls.append((COPY,args));cursor+=chunk;linear+=chunk;remaining-=chunk
            if cursor>=c.capacity:cursor=0
    return m,calls,cursor


class CopyBoundary(Exception):pass


class RingOracle(TimingOracle):
    def __init__(self,words,memory,name=NAMES[0],case=Case(),phase=0,entry=None,copy=COPY,connected=None,limit=None):
        self.ring_name=name;self.ring_case=case;self.copy_address=copy;self.copy_limit=limit;self.copy_calls=0;self.trace=[]
        ring,linear=pointers(case);entry=source.TARGETS[name][0]if entry is None else entry
        super().__init__(words,memory,phase=phase,entry=entry,arguments=(ring,case.capacity,case.cursor,linear),connected=connected)
    def get(self,address,size):
        v=super().get(address,size)
        if self.own_instruction:self.trace.append(('R',address,size,v))
        return v
    def put(self,address,value,size):
        super().put(address,value,size)
        if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
    def record_call(self,target):
        count=3 if target==self.copy_address else 5
        assert target in(self.copy_address,*(v[0]for v in source.TARGETS.values())),hex(target)
        args=self.arguments(count);self.calls.append((target,args));self.events.append(('CALL',target,args))
        if target==self.copy_address:
            self.copy_calls+=1
            if self.copy_calls==self.copy_limit:raise CopyBoundary
    def hook(self,target):
        assert target==self.copy_address;dst,src,n=self.arguments(3)
        if not self.ring_case.prefix:
            assert n<=256,('unbounded copy fixture',n)
            for i in range(n):self.put(dst+i,self.get(src+i,1),1)
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        if self.ring_case.homes:self.put(self.r[29]+64,0x87654321,4)
        for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo,self.condition=0x87654321,0x12345678,True;self.r[2]=dst


def controls(name):
    b=source.SELECTED[name]
    call='memcpy(ring + cursor, linear, chunk)'if name==NAMES[0]else'memcpy(linear, ring + cursor, chunk)'
    opposite='memcpy(linear, ring + cursor, chunk)'if name==NAMES[0]else'memcpy(ring + cursor, linear, chunk)'
    return {'selected':b,'wrongDirection':b.replace(call,opposite),'noLinearAdvance':b.replace('linear += chunk;','linear += 0;'),
        'ringShift':b.replace(call,call.replace('ring + cursor','ring + cursor + 1')),
        'linearShift':b.replace(call,call.replace('linear,','linear + 1,')),
        'shortCopy':b.replace(call,call.replace('chunk)','chunk > 0 ? chunk - 1 : 0)')),
        'longCopy':b.replace(call,call.replace('chunk)','chunk + 1)')),
        'zeroReturn':b.replace('return cursor;','return 0;'),
        'skipCapacityOne':b.replace('while (count != 0)','while (count != 0 && capacity != 1)')}


def native_harness():
    bodies=[];checks=[]
    for index,name in enumerate(NAMES):
        for label,b in controls(name).items():
            ident=label+str(index);bodies.append(b.replace(name,ident))
            checks.append(('if(variant(%s,%d))return 30;'if label=='selected'else'if(!variant(%s,%d))return 31;')%(ident,index))
    return '#include <ultra64.h>\n'+r'''
static union{u32 align[128];u8 bytes[512];}ringBlock,linearBlock;
static u8 expectedRing[512],expectedLinear[512];static u32 calls;
__attribute__((noinline,noclone)) void *memcpy(void *dst,const void *src,size_t n){
 u32 i;u8 *d=dst;const u8*s=src;calls++;
 if(n>256){__asm__ volatile("int $0x80"::"a"(1),"b"(99):"memory");__builtin_unreachable();}
 for(i=0;i<n;i++)d[i]=s[i];return dst;
}
'''+ '\n'.join(bodies)+r'''
static int variant(s32(*fn)(u8*,s32,s32,u8*,s32),u32 direction){
 const u32 caps[]={1,2,3,4,7,16,32},words[]={0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0x87654321,0xFFFFFFFE,256};
 u32 k,cap,cursor,n,a,i,j,count=0,counts[6],answer,expected;
 for(k=0;k<7;k++)for(cursor=0;cursor<=caps[k];cursor++)for(j=0;j<6;j++)for(a=0;a<2;a++){
  cap=caps[k];counts[0]=0;counts[1]=1;counts[2]=cap-1;counts[3]=cap;counts[4]=cap+1;counts[5]=2*cap+3;n=counts[j];
  for(i=0;i<512;i++){ringBlock.bytes[i]=expectedRing[i]=(u8)(i*13+cap*7+a*31);linearBlock.bytes[i]=expectedLinear[i]=(u8)(i*29+cursor*11+cap);}
  for(i=0;i<n;i++){
   u32 r=16+a+(cursor+i)%cap,l=16+(a^1)+i;
   if(direction)expectedLinear[l]=expectedRing[r];else expectedRing[r]=expectedLinear[l];
  }
  calls=0;answer=(u32)fn(ringBlock.bytes+16+a,(s32)cap,(s32)cursor,linearBlock.bytes+16+(a^1),(s32)n);
  expected=n?(cursor+n)%cap:cursor;
  if(answer!=expected||(!n&&calls))return 20;
  for(i=0;i<512;i++)if(ringBlock.bytes[i]!=expectedRing[i]||linearBlock.bytes[i]!=expectedLinear[i])return 21;
  count++;
 }
 for(i=0;i<8;i++){
  calls=0;answer=(u32)fn(NULL,(s32)words[(i+3)%8],(s32)words[i],NULL,0);
  if(calls||answer!=words[i])return 22;count++;
 }
 return count==872?0:23;
}
static int run(void){
'''+ '\n'.join(checks)+r'''
 return 0;
}
__attribute__((force_align_arg_pointer)) void _start(void){int code=run();__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
'''


class RingBufferTransfersTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.out.mkdir(parents=True,exist_ok=True);cls.values=source.snapshot(cls.out)
        cls.installed=(ROOT/source.SOURCE).read_text()==source.recovered_owner(cls.values[source.SOURCE].decode())
        if cls.installed:source.audit(ROOT,cls.out)
        else:source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        cls.rom=cls.values['conker/conker.us.bin'];cls.truth={n:list(struct.unpack_from('>42I',cls.rom,v[1]))for n,v in source.TARGETS.items()}
        cls.obj,diag=source.compile_owner(ROOT,cls.out,'#include <ultra64.h>\n'+'\n'.join(source.SELECTED.values()),'fresh-selected')
        if diag:raise ValueError(diag)
        data,fs=source.link_owner(ROOT,cls.out,cls.obj,source.OWNER)
        cls.words={n:list(struct.unpack_from('>42I',data,fs[n]['value']))for n in NAMES};cls.receipt=dict(installed=cls.installed)
    @classmethod
    def tearDownClass(cls):
        (cls.out/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n');print(cls.receipt)
    def compare(self,name,case=Case(),phase=0,images=None,entry=None,copy=COPY,connected=None):
        m=fixture(case,phase);expected,calls,result=reference(m,name,case)
        if copy!=COPY:calls=[(copy,args)for _,args in calls]
        models=[RingOracle(w,m,name,case,phase,entry,copy,connected).run()for w in images or(self.truth[name],self.words[name])]
        for a in models:self.assertEqual(public(a.memory),public(expected));self.assertEqual(a.calls,calls);self.assertEqual(a.r[2],result&0xFFFFFFFF)
        self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(models[0].trace,models[1].trace)
        return models
    def test_01_two_direct_slots_actual_Make_and_effective_stubs(self):
        q=json.loads((self.out/'qualification.json').read_text())
        self.assertEqual((q['words'],q['frame_each'],q['relocations'],q['new_guards'],q['preserved_neighbors'],q['compiler_only']),(84,48,2,0,14,True))
        old=self.values['conker/build/conker.us.elf']
        for n,(entry,_,_)in source.TARGETS.items():
            self.assertEqual(self.truth[n],self.words[n]);self.assertEqual(source.payload(self.obj,n),source.payload(source.original(ROOT,self.out,n),n))
            at=source.elf_slot_offset(old,entry,168);stub=RingOracle(struct.unpack_from('>42I',old,at),fixture(Case()),n).run()
            self.assertFalse(stub.calls);self.assertEqual(stub.r[2],0);self.assertEqual(self.compare(n)[0].r[2],1)
        self.receipt.update(functions=2,words=84,frame_each=48,bindings=2,new_guards=0,neighbors=14,both_old_stubs_effectively_rejected=True)
    def test_02_chunk_boundaries_multiwrap_fences_homes_and_empty_words(self):
        count=0;visits={n:set()for n in NAMES}
        for n,cap,a,phase in itertools.product(NAMES,CAPACITIES,(0,1),(0,8)):
            for cursor in range(cap+1):
                for length in(0,1,cap-1,cap,cap+1,2*cap+3):
                    c=Case(cap,cursor,length,a,homes=bool((length+cursor)&1));model=self.compare(n,c,phase)[0]
                    visits[n].update(model.visits);count+=1
        for n,cap,cursor,phase in itertools.product(NAMES,WORDS,WORDS,(0,8)):
            self.compare(n,Case(cap,cursor,0,empty_unbacked=True),phase);count+=1
        for n,v in visits.items():self.assertEqual(v,set(range(source.TARGETS[n][0],source.TARGETS[n][0]+168,4)))
        self.receipt.update(guest_phases=count,all_84_words_visited=True,zero_count_unbacked_pointers_and_full_word_return=True,
            cached_fifth_argument_mutation_probes=True,byte_alignment_and_whole_buffer_fences=True,zero_length_chunk_and_repeated_wraps=True)
    def test_03_native32_and_sixteen_effective_defined_wrong_C(self):
        for opt in('-O0','-O2','-O3'):
            p=self.out/('native'+opt);c=p.with_suffix('.c');c.write_text(native_harness())
            q=subprocess.run([*native_command(opt),'-fno-strict-aliasing',str(c),'-o',str(p)],cwd=ROOT,capture_output=True,text=True)
            (self.out/('native'+opt+'-diagnostics.txt')).write_text(q.stdout+q.stderr);self.assertEqual(q.returncode,0,q.stdout+q.stderr)
            subprocess.run([str(p)],capture_output=True,check=True)
        self.receipt.update(native32_selected_cases_per_optimization=1744,native_optimizations=['O0','O2','O3'],
            effective_defined_wrong_C_controls=16,trap_UBSan=True,ordinary_backed_nonoverlapping_domain=True)
    def link_words(self,obj,name,entry,copy,label):
        text,fs,rs=source.parse_object(obj);asm,unknown=emit_function(text,fs[name],rs,name,{'memcpy':copy});self.assertFalse(unknown)
        p=self.out/label;ap=p.with_suffix('.s');op=p.with_suffix('.o');ld=p.with_suffix('.ld');elf=p.with_suffix('.elf')
        ap.write_text(asm);ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\nmemcpy = 0x%X;\n'%(entry,copy))
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(op),str(ap)],capture_output=True,check=True)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',name,'-o',str(elf),str(op)],capture_output=True,check=True)
        return list(struct.unpack_from('>42I',sections(elf)['.text'][1]))
    def test_04_independent_links_and_fired_root_fault_prefixes(self):
        count=cuts=0
        for ni,n in enumerate(NAMES):
            original=source.original(ROOT,self.out,n)
            for i,base in enumerate((0x17001000,0x17108000,0x1720FFFC)):
                entry=base+ni*0x1000;copy=0x17300000+i*0x100
                a=self.link_words(original,n,entry,copy,'original-rebase-%d-%d'%(ni,i));b=self.link_words(self.obj,n,entry,copy,'C-rebase-%d-%d'%(ni,i));self.assertEqual(a,b)
                for phase,length,align in itertools.product((0,8),(0,17),(0,1)):
                    self.compare(n,Case(7,6,length,align,homes=True),phase,(a,b),entry,copy);count+=1
            for phase,c in itertools.product((0,8),(Case(4,1,0),Case(4,1,1),Case(4,1,3),Case(4,3,5),Case(4,0,11),Case(4,4,5))):
                m=fixture(c,phase);good=RingOracle(self.truth[n],m,n,c,phase).run()
                for cut in range(good.root_accesses):
                    models=[RingOracle(w,m,n,c,phase)for w in(self.truth[n],self.words[n])]
                    for a in models:
                        a.root_fault=cut
                        with self.assertRaises(faults.AccessBoundary):a.run()
                    self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(models[0].trace,models[1].trace)
                    self.assertEqual((models[0].current_pc,models[0].delay_of),(models[1].current_pc,models[1].delay_of));cuts+=1
        self.receipt.update(independent_GNU_links=12,rebase_phases=count,fired_root_fault_prefixes=cuts,portable_C_fault_MMU_claimed=False)
    def window(self,start,stop,m,n,c,phase,registers):
        rom=start-0x15000000+0x2D4B0;window=list(struct.unpack_from('>%dI'%((stop-start)//4+1),self.rom,rom));models=[]
        for leaf in(self.truth,self.words):
            connected={source.TARGETS[name][0]+i*4:w for name,words in leaf.items()for i,w in enumerate(words)}
            a=RingOracle(window,m,n,c,phase,entry=start,connected=connected)
            for reg,value in registers.items():a.r[reg]=value
            a.code=StopCode(a.code,a,stop)
            with self.assertRaises(WindowEnd):a.run()
            models.append(a)
        self.assertEqual(complete(models[0]),complete(models[1]));return models[0]
    def test_05_all_five_actual_caller_sites_and_partial_state_updates(self):
        for n,expected in((NAMES[0],[0x71114,0x71130]),(NAMES[1],[0x711A4,0x711CC,0x71214])):
            entry=source.TARGETS[n][0];jal=struct.pack('>I',0x0C000000|(entry>>2&0x3FFFFFF));ptr=struct.pack('>I',entry)
            self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==jal],expected)
            self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==ptr],[])
        counts=[0,0,0,0]
        for cap,pos,phase,homes in itertools.product((8,16),(0,1,2),(0,8),(False,True)):
            cursor=(0,cap-1,cap)[pos];base=Case(cap,cursor,0,homes=homes);ring,linear=pointers(base)
            for length in(4,12):
                m=fixture(base,phase);put(m,OBJECT,ring);put(m,OBJECT+4,cap);put(m,STACK+phase+0x30,length+4);put(m,STACK+phase+0x2C,linear)
                wanted=dict(m);stream=struct.pack('>I',length)+bytes(m[linear+i]for i in range(length))
                for i,b in enumerate(stream):wanted[ring+(cursor+i)%cap]=b
                final=(cursor+len(stream))%cap;put(wanted,OBJECT+12,final)
                a=self.window(0x15043C48,0x15043C90,m,NAMES[0],base,phase,{16:OBJECT,6:cursor})
                self.assertEqual(public(a.memory),public(wanted));self.assertEqual(a.r[2],0)
                calls=[x for x in a.calls if x[0]==source.TARGETS[NAMES[0]][0]]
                self.assertEqual(calls,[(source.TARGETS[NAMES[0]][0],(ring,cap,cursor,STACK+phase+0x30,4)),(source.TARGETS[NAMES[0]][0],(ring,cap,(cursor+4)%cap,linear,length))]);counts[0]+=1
            for length in(0,4,12):
                m=fixture(base,phase);put(m,OBJECT,ring);put(m,OBJECT+4,cap);put(m,STACK+phase+0x3C,linear)
                for i,b in enumerate(struct.pack('>I',length)):m[ring+(cursor+i)%cap]=b
                a=self.window(0x15043CF0,0x15043D08,m,NAMES[1],base,phase,{17:OBJECT,4:ring,6:cursor,7:STACK+phase+0x30,25:4})
                self.assertEqual(a.r[3],length);self.assertEqual(a.r[6],(cursor+4)%cap);self.assertEqual(a.r[7],linear);counts[1]+=1
            for length in(0,1,7,19):
                m=fixture(base,phase);put(m,OBJECT,ring);put(m,OBJECT+4,cap);put(m,STACK+phase+0x3C,linear)
                wanted=dict(m)
                for i in range(length):wanted[linear+i]=m[ring+(cursor+i)%cap]
                wanted[linear+length]=0
                a=self.window(0x15043D14,0x15043D34,m,NAMES[1],base,phase,{17:OBJECT,16:length,6:cursor,7:linear})
                self.assertEqual(public(a.memory),public(wanted));self.assertEqual(a.r[6],(cursor+length)%cap if length else cursor);counts[2]+=1
                m=fixture(base,phase);put(m,OBJECT,ring);put(m,OBJECT+4,cap);put(m,STACK+phase+0x30,length);wanted=dict(m)
                for i in range(length):wanted[linear+i]=m[ring+(cursor+i)%cap]
                put(wanted,OBJECT+8,(cursor+length)%cap if length else cursor)
                a=self.window(0x15043D58,0x15043D78,m,NAMES[1],base,phase,{17:OBJECT,6:cursor,7:linear})
                self.assertEqual(public(a.memory),public(wanted));self.assertEqual(a.r[2],length);counts[3]+=1
        old=self.values['conker/build/conker.us.elf']
        for entry,size,words in((0x15043BB8,20,(0xAFA40000,0xAFA50004,0xAFA60008,0x03E00008,0)),(0x15043CA4,12,(0x00001025,0x03E00008,0))):
            self.assertEqual(struct.unpack_from('>%dI'%(size//4),old,source.elf_slot_offset(old,entry,size)),words)
        self.receipt.update(actual_caller_window_phases=counts,all_five_JAL_sites=True,writer_header_and_payload_chaining=True,
            reader_header_truncation_terminator_and_full_publication=True,parent_stubs_and_unexecuted_eligibility_and_skip_paths_explicit=True)
    def test_06_signed_word_prefixes_degenerate_loop_and_compiled_negative_controls(self):
        phases=0
        cases=(Case(0,0,1,prefix=True),Case(7,0,0xFFFFFFFF,prefix=True),Case(0x7FFFFFFF,0x7FFFFFFE,8,prefix=True),Case(0x80000000,0xFFFFFFFF,2,prefix=True))
        for n,c,phase in itertools.product(NAMES,cases,(0,8)):
            models=[RingOracle(w,fixture(c,phase),n,c,phase,limit=1).run for w in(self.truth[n],self.words[n])]
            executed=[]
            for run in models:
                with self.assertRaises(CopyBoundary):run()
                executed.append(run.__self__)
            self.assertEqual(complete(executed[0]),complete(executed[1]))
            chunk=(c.capacity-c.cursor)&0xFFFFFFFF if signed(c.capacity)<signed((c.cursor+c.count)&0xFFFFFFFF)else c.count
            ring,linear=pointers(c);address=(ring+c.cursor)&0xFFFFFFFF;expected=(address,linear,chunk)if n==NAMES[0]else(linear,address,chunk)
            self.assertEqual(executed[0].calls,[(COPY,expected)]);phases+=1
        for n in NAMES:
            c=Case(0,0,1,prefix=True);models=[RingOracle(w,fixture(c),n,c,limit=3)for w in(self.truth[n],self.words[n])]
            for a in models:
                with self.assertRaises(CopyBoundary):a.run()
                self.assertEqual(a.calls,[(COPY,(RING,LINEAR+1,0)if n==NAMES[0]else(LINEAR+1,RING,0))]*3)
            self.assertEqual(complete(models[0]),complete(models[1]))
            for label,body,c in(('positive-only',source.SELECTED[n].replace('while (count != 0)','while (count > 0)'),Case(7,0,0xFFFFFFFF,prefix=True)),
                ('unsigned-boundary',source.SELECTED[n].replace('capacity < (s32)((u32)cursor + (u32)count)','(u32)capacity < ((u32)cursor + (u32)count)'),Case(0x7FFFFFFF,0x7FFFFFFE,8,prefix=True))):
                obj,diag=source.compile_owner(ROOT,self.out,'#include <ultra64.h>\n'+body,label+n);self.assertFalse(diag)
                data,fs=source.link_owner(ROOT,self.out,obj,source.OWNER);raw,_=source.payload(obj,n);words=struct.unpack_from('>%dI'%(len(raw)//4),data,fs[n]['value'])
                a=RingOracle(words,fixture(c),n,c,limit=1)
                if label=='positive-only':a.run();self.assertFalse(a.calls)
                else:
                    with self.assertRaises(CopyBoundary):a.run()
                    self.assertEqual(a.calls[0][1][2],1)
        self.receipt.update(signed_word_prefix_phases=phases,zero_capacity_nontermination_bounded_to_three_calls=True,
            effective_compiled_guest_prefix_controls=4,invalid_huge_copy_or_pointer_native_execution_claimed=False)
    def test_07_original_current_exact_memcpy_provider(self):
        old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,COPY,44);vram,off=DEFAULT_SEGMENTS['us']['init']
        raw=self.rom[COPY-vram+off:COPY-vram+off+44];self.assertEqual(old[at:at+44],raw)
        connected={COPY+i*4:w for i,w in enumerate(struct.unpack('>11I',raw))};count=0
        for n,cap,a,phase in itertools.product(NAMES,(1,3,8,32),(0,1),(0,8)):
            for cursor,length in itertools.product((0,cap-1,cap),(0,1,2*cap+3)):
                self.compare(n,Case(cap,cursor,length,a),phase,connected=connected);count+=1
        self.receipt.update(original_memcpy_words=11,current_memcpy_byte_exact=True,actual_memcpy_phases=count,ordinary_nonoverlapping_contract_only=True)
    def test_08_pins_installed_identity_and_two_slot_image_controls(self):
        truth=source.truths(self.values)
        for name,old in self.values.items():
            expected=source.recovered_owner(old.decode()).encode()if self.installed and name==source.SOURCE else source.predicted_image(old,truth)if self.installed and name=='conker/build/conker.us.elf'else old
            self.assertEqual((ROOT/name).read_bytes(),expected,name);self.assertEqual(source.digest(old),source.INPUTS[name])
        before=self.values['conker/build/conker.us.elf'];pred=source.predicted_image(before,truth)
        offsets=[0,len(pred)-1,source.elf_slot_offset(pred,0x80082B20,4),source.elf_slot_offset(pred,0x15043B70,4)]
        offsets +=[source.elf_slot_offset(pred,v[0],168)for v in source.TARGETS.values()]
        for at in offsets:
            wrong=bytearray(pred);wrong[at]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(wrong),truth)
        self.receipt.update(pinned_inputs=len(self.values),whole_image_corruption_controls=len(offsets),guard_manifest_and_conversion_rows_unchanged=True,metadata_exclusions=0)


if __name__=='__main__':unittest.main()
