"""Category/frame gates, unused float homes, rectangle helper and real dispatch."""
import itertools,json,struct,subprocess,unittest
from pathlib import Path
from tools.experiments import game_category_frame_fill as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_command_stream_relocator import StopCode,WindowEnd
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT=Path(__file__).resolve().parents[2]
CURSOR,CONTEXT,CHILD,DESCRIPTOR=0x50000,0x30000,0x32000,0x34000
assert CURSOR-16>STACK+0x208 and CONTEXT+0x3E0<STACK-0x600
CALLEE,TABLE=0x15110544,0x800891D8
SYMBOLS=dict(D_800BE9F0=0x800BE9F0,D_800DBFF0=0x800DBFF0,D_800DBEA8=0x800DBEA8,
             D_800BE620=0x800BE620,D_800BE624=0x800BE624,func_15110544=CALLEE)
WIDTHS=(292,0,2,0x7FFFFFFF,0x80000000,0xFFFFFFFF)
HEIGHTS=(216,0,1,0xFFFFFFFF,0x80000000,0x12345678)
HOMES=(0,0x80000000,0x3F800001,0x7F800001,0xFFFFFFFF,0x87654321)


def fixture(category=0x31,child=3,pattern=0,phase=0,symbols=None):
    s=SYMBOLS if symbols is None else symbols
    m={STACK+phase+i:(i*17+0xA5)&255 for i in range(-0x600,0x200)}
    for base,size in ((CONTEXT,0x3E0),(CHILD,0x90),(CURSOR-16,0x120),(DESCRIPTOR,32)):
        for i in range(size):m[base+i]=(i*13+0xA5)&255
    for n in ('D_800BE9F0','D_800DBFF0','D_800DBEA8','D_800BE620','D_800BE624'):
        for i in range(8):m[s[n]+i]=0xA5
    put(m,s['D_800BE9F0'],category);put(m,s['D_800DBFF0'],CONTEXT)
    put(m,CONTEXT+0x3D4,CHILD);m[CHILD+0x78]=child
    put(m,s['D_800BE620'],WIDTHS[pattern%6]);put(m,s['D_800BE624'],HEIGHTS[pattern%6])
    for i in range(3):m[s['D_800DBEA8']+i]=(pattern*71+i*109+child)&255
    return m


def packet(memory,symbols=None,cursor=CURSOR):
    s=SYMBOLS if symbols is None else symbols;cat=read(memory,s['D_800BE9F0'])
    active=cat in (0x1B,0x1E)or(cat==0x31 and memory[read(memory,read(memory,s['D_800DBFF0'])+0x3D4)+0x78]==3)
    if not active:return None
    return (cursor,2,0,(read(memory,s['D_800BE620'])-2)&0xFFFFFFFF,read(memory,s['D_800BE624']),
            *(memory[s['D_800DBEA8']+i]for i in range(3)))


def effects(memory,symbols,mode,cursor=CURSOR):
    put(memory,cursor,0xAABBCCDD);put(memory,cursor+4,0x12345678)
    if mode:
        put(memory,symbols['D_800BE9F0'],0xFFFFFFFF);put(memory,symbols['D_800BE620'],0x87654321)
        put(memory,symbols['D_800BE624'],0);memory[CHILD+0x78]=255
        for i in range(3):memory[symbols['D_800DBEA8']+i]=0


def public(memory):
    return {a:v for a,v in memory.items()if not STACK-0x600<=a<STACK+0x208}


class FillOracle(TimingOracle):
    def __init__(self,words,memory,phase=0,pattern=0,mode=0,symbols=None,entry=source.ENTRY,connected=None):
        self.trace=[];homes=tuple(HOMES[(pattern+i)%6]for i in range(3))
        super().__init__(words,memory,phase=phase,entry=entry,arguments=(CURSOR,*homes),connected=connected)
        self.homes=homes;self.symbols=SYMBOLS if symbols is None else symbols;self.mode=mode
    def get(self,address,size):
        v=super().get(address,size)
        if self.own_instruction:self.trace.append(('R',address,size,v))
        return v
    def put(self,address,value,size):
        super().put(address,value,size)
        if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
    def record_call(self,target):
        if target==source.ENTRY:count=4
        elif target==self.symbols['func_15110544']:count=8
        else:
            assert target in (0x1501A680,0x1501A6CC),hex(target)
            count=1 if target==0x1501A680 else 5
        args=self.arguments(count);self.calls.append((target,args));self.events.append(('CALL',target,args))
    def hook(self,target):
        assert target==self.symbols['func_15110544'],hex(target)
        effects(self.memory,self.symbols,self.mode,self.r[4])
        for i in range(8):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo,self.condition=0x87654321,0x12345678,True
        self.r[2]=0 if self.mode else CURSOR+0x20


def native_harness(bodies):
    return '#include <ultra64.h>\n'+source.DECLARATIONS+r'''
s32 D_800BE9F0,D_800BE620,D_800BE624;u8*D_800DBFF0;u8 D_800DBEA8[3];
static union{u32 align[256];u8 bytes[1024];}context;
static union{u32 align[36];u8 bytes[144];}child;
static Gfx commands[16],expected[16];static u32 called,error,shouldCall,expectedArgs[7],returnNull;
s32 func_15110544(Gfx*p,s32 x,s32 y,s32 w,s32 h,s32 r,s32 g,s32 b){
 u32 actual[7]={(u32)x,(u32)y,(u32)w,(u32)h,(u32)r,(u32)g,(u32)b},i;
 called++;if(p!=commands||!shouldCall||called!=1)error=1;
 for(i=0;i<7;i++)if(actual[i]!=expectedArgs[i])error=2;
 p[0].words.w0=0xAABBCCDD;p[0].words.w1=0x12345678;
 D_800BE9F0=-1;D_800BE620=0;D_800BE624=0;D_800DBEA8[0]=D_800DBEA8[1]=D_800DBEA8[2]=0;
 return returnNull?0:(s32)(u32)(p+5);
}
'''+bodies+r'''
static int runVariant(Gfx*(*target)(Gfx*,f32,f32,f32)){
 const u32 cats[]={0x1B,0x1E,0x31,0,0x1C,0x1000001B,0x80000000,0xFFFFFFFF};
 const u32 widths[]={292,0,2,0x80000000},heights[]={216,0,0xFFFFFFFF,0x80000000};
 u32 c,state,p,i,j,count=0;Gfx*answer;
 for(c=0;c<8;c++)for(state=0;state<256;state++)for(p=0;p<4;p++){
  for(i=0;i<16;i++)commands[i].words.w0=commands[i].words.w1=expected[i].words.w0=expected[i].words.w1=0xA5A5A5A5;
  for(i=0;i<144;i++)child.bytes[i]=0xA5;child.bytes[0x78]=(u8)state;
  *(u8**)(context.bytes+0x3D4)=child.bytes;D_800DBFF0=context.bytes;
  D_800BE9F0=(s32)cats[c];D_800BE620=(s32)widths[p];D_800BE624=(s32)heights[p];
  for(i=0;i<3;i++)D_800DBEA8[i]=(u8)(state+p*71+i*109);
  shouldCall=cats[c]==0x1B||cats[c]==0x1E||(cats[c]==0x31&&state==3);
  expectedArgs[0]=2;expectedArgs[1]=0;expectedArgs[2]=widths[p]-2;expectedArgs[3]=heights[p];
  for(i=0;i<3;i++)expectedArgs[4+i]=D_800DBEA8[i];
  called=error=0;returnNull=p&1;
  if(shouldCall){expected[0].words.w0=0xAABBCCDD;expected[0].words.w1=0x12345678;}
  answer=target(commands,.25f,-1.5f,2.0f);
  if(error||called!=shouldCall)return 20;
  if(answer!=(shouldCall?(returnNull?0:commands+5):commands))return 21;
  for(i=0;i<16;i++)for(j=0;j<2;j++)if(((u32*)commands)[i*2+j]!=((u32*)expected)[i*2+j])return 22;
  count++;
 }
 return count==8192?0:23;
}
static int run(void){
 if(runVariant(selected))return 30;
 if(!runVariant(wrongCategory))return 31;
 if(!runVariant(wrongState))return 32;
 if(!runVariant(wideState))return 33;
 if(!runVariant(signedColor))return 34;
 if(!runVariant(wrongWidth))return 35;
 if(!runVariant(swappedColor))return 36;
 if(!runVariant(discardedReturn))return 37;
 return 0;
}
__attribute__((force_align_arg_pointer)) void _start(void){int code=run();__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
'''


class CategoryFrameFillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.out.mkdir(parents=True,exist_ok=True);cls.values=source.snapshot(cls.out)
        cls.installed=(ROOT/source.SOURCE).read_text()==source.recovered_owner(cls.values[source.SOURCE].decode())
        if cls.installed:source.audit(ROOT,cls.out)
        else:source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>42I',cls.rom,source.ROM))
        cls.obj,diag=source.compile_owner(ROOT,cls.out,'#include <ultra64.h>\n'+source.DECLARATIONS+source.SELECTED,'fresh-selected')
        if diag:raise ValueError(diag)
        data,fs=source.link_owner(ROOT,cls.out,cls.obj,source.OWNER)
        cls.words=list(struct.unpack_from('>42I',data,fs[source.FUNCTION]['value']));cls.receipt=dict(installed=cls.installed)
    @classmethod
    def tearDownClass(cls):
        (cls.out/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n');print(cls.receipt)
    def compare(self,category=49,child=3,pattern=0,phase=0,mode=0,symbols=None,images=None,entry=source.ENTRY):
        s=SYMBOLS if symbols is None else symbols;m=fixture(category,child,pattern,phase,s);wanted=packet(m,s);expected=dict(m)
        if wanted:effects(expected,s,mode)
        models=[FillOracle(code,m,phase,pattern,mode,s,entry).run()for code in images or(self.truth,self.words)]
        for a in models:
            self.assertEqual(public(a.memory),public(expected));self.assertEqual(a.calls,[(s['func_15110544'],wanted)]if wanted else[])
            self.assertEqual(a.r[2],(0 if mode else CURSOR+0x20)if wanted else CURSOR)
            self.assertEqual(tuple(read(a.memory,STACK+phase+i*4)for i in(1,2,3)),a.homes)
            reads={t[1]for t in a.trace if t[0]=='R'}
            if category not in (27,30,49):self.assertTrue(reads.isdisjoint({s['D_800DBFF0'],CONTEXT+0x3D4,CHILD+0x78}))
            if not wanted:self.assertTrue(reads.isdisjoint({s['D_800BE620'],s['D_800BE624'],*(s['D_800DBEA8']+i for i in range(3))}))
        self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(models[0].trace,models[1].trace)
        return models
    def test_01_owner_actual_Make_and_effective_old_stub(self):
        self.assertEqual(self.truth,self.words);self.assertEqual(source.payload(self.obj),source.payload(source.original(ROOT,self.out)))
        q=json.loads((self.out/'qualification.json').read_text());self.assertEqual((q['words'],q['frame'],q['relocations'],q['new_guards'],q['preserved_neighbors']),(42,40,11,0,33))
        old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,source.ENTRY,168)
        stub=FillOracle(struct.unpack_from('>42I',old,at),fixture()).run()
        self.assertEqual(stub.r[2],0);self.assertFalse(stub.calls);self.assertNotEqual(stub.r[2],self.compare()[0].r[2])
        self.receipt.update(words=42,frame=40,bindings=11,new_guards=0,neighbors=33,old_stub_effectively_rejected=True)
    def test_02_categories_state_bytes_word_boundaries_homes_and_effects(self):
        count=0;seen=set()
        cases=itertools.chain(
            itertools.product(range(256),(0,3,255),(0,),(0,8),(0,1)),
            ((49,state,p,phase,0)for state,p,phase in itertools.product(range(256),(0,4),(0,8))),
            ((cat,3,p,phase,mode)for cat,p,phase,mode in itertools.product((0xFFFFFFFF,0x80000000,0x1000001B,0x7FFFFFFF,27,30,49,50),range(6),(0,8),(0,1))))
        for c in cases:
            a=self.compare(*c)[0];seen.update(a.visits);count+=1
        self.assertEqual(count,4288);self.assertEqual(seen,set(range(source.ENTRY,source.ENTRY+168,4)))
        self.receipt.update(guest_phases=count,all_words_visited=42,all_category_and_state_bytes=True,full_word_category_dimensions_and_unused_homes=True,effectful_callee_and_suppressed_reads=True)
    def test_03_native32_and_effective_defined_wrong_C(self):
        b=source.SELECTED
        variants={'selected':b,'wrongCategory':b.replace('== 0x1B','== 0x1C'),'wrongState':b.replace('== 3','!= 3'),
            'wideState':b.replace('(*(u8 **)(D_800DBFF0 + 0x3D4))[0x78]','*(u16 *)((*(u8 **)(D_800DBFF0 + 0x3D4)) + 0x78)'),
            'signedColor':b.replace('D_800DBEA8[0]','(s8)D_800DBEA8[0]'),
            'wrongWidth':b.replace('(u32)D_800BE620 - 2','(u32)D_800BE620 - 1'),
            'swappedColor':b.replace('D_800DBEA8[0], D_800DBEA8[1], D_800DBEA8[2]','D_800DBEA8[2], D_800DBEA8[1], D_800DBEA8[0]'),
            'discardedReturn':b.replace('commands = (Gfx *)func_15110544','(void)func_15110544')}
        bodies='\n'.join(v.replace(source.FUNCTION,n)for n,v in variants.items())
        for opt in('-O0','-O2','-O3'):
            p=self.out/('native'+opt);c=p.with_suffix('.c');c.write_text(native_harness(bodies))
            subprocess.run([*native_command(opt),'-fno-strict-aliasing',str(c),'-o',str(p)],cwd=ROOT,capture_output=True,check=True)
            subprocess.run([str(p)],capture_output=True,check=True)
        self.receipt.update(native32_selected_cases_per_optimization=8192,native_optimizations=['O0','O2','O3'],effective_defined_wrong_C_controls=7,trap_UBSan=True)
    def link_words(self,obj,entry,symbols,label):
        text,fs,rs=source.parse_object(obj);asm,unknown=emit_function(text,fs[source.FUNCTION],rs,source.FUNCTION,symbols);self.assertFalse(unknown)
        p=self.out/label;ap=p.with_suffix('.s');op=p.with_suffix('.o');ld=p.with_suffix('.ld');elf=p.with_suffix('.elf')
        ap.write_text(asm);ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+''.join('%s = 0x%X;\n'%x for x in symbols.items()))
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(op),str(ap)],capture_output=True,check=True)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',source.FUNCTION,'-o',str(elf),str(op)],capture_output=True,check=True)
        return list(struct.unpack_from('>42I',sections(elf)['.text'][1]))
    def test_04_independent_links_and_fired_fault_prefixes(self):
        original=source.original(ROOT,self.out);count=cuts=0
        for i,(entry,base)in enumerate(((0x17001000,0x81007FFC),(0x17108000,0x81108000),(0x1720FFFC,0x8120FFFC))):
            s={n:(base+j*0x1000)&0xFFFFFFFF for j,n in enumerate(SYMBOLS)};s['func_15110544']=0x17301000+i*0x100
            a=self.link_words(original,entry,s,'original-rebase'+str(i));b=self.link_words(self.obj,entry,s,'C-rebase'+str(i));self.assertEqual(a,b)
            for cat,state,phase in itertools.product((27,30,49,0),(2,3),(0,8)):
                self.compare(cat,state,4,phase,1,s,(a,b),entry);count+=1
        for cat,state,phase,mode in itertools.product((0,27,30,49),(2,3),(0,8),(0,1)):
            m=fixture(cat,state,4,phase);good=FillOracle(self.truth,m,phase,4,mode).run()
            for cut in range(good.root_accesses):
                models=[FillOracle(code,m,phase,4,mode)for code in(self.truth,self.words)]
                for a in models:
                    a.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):a.run()
                self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(models[0].trace,models[1].trace)
                self.assertEqual((models[0].current_pc,models[0].delay_of),(models[1].current_pc,models[1].delay_of));cuts+=1
        self.receipt.update(independent_GNU_links=6,rebase_phases=count,fired_root_fault_prefixes=cuts,portable_C_fault_or_MMU_claimed=False)
    def test_05_actual_float_callback_window(self):
        ptr=struct.pack('>I',source.ENTRY);jal=struct.pack('>I',0x0C000000|(source.ENTRY>>2&0x3FFFFFF))
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==ptr],[0x22DCA4])
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==jal],[])
        start,stop=0x15110244,0x15110288;window=list(struct.unpack_from('>18I',self.rom,0x13D6F4));count=0
        for cat,state,phase,mode in itertools.product((27,49,0),(2,3),(0,8),(0,1)):
            m=fixture(cat,state,2,phase);put(m,0x800B0DF0,DESCRIPTOR);m[DESCRIPTOR+8]=3;put(m,TABLE+12,source.ENTRY);models=[]
            for leaf in(self.truth,self.words):
                connected={source.ENTRY+i*4:w for i,w in enumerate(leaf)}
                a=FillOracle(window,m,phase,2,mode,entry=start,connected=connected)
                a.f[12],a.f[14],a.f[18]=a.homes;a.code=StopCode(a.code,a,stop)
                with self.assertRaises(WindowEnd):a.run()
                models.append(a)
            self.assertEqual(complete(models[0]),complete(models[1]));a=models[0]
            self.assertEqual(a.calls[0],(source.ENTRY,(CURSOR,*a.homes)))
            self.assertEqual(a.r[4],(0 if mode else CURSOR+0x20)if packet(m)else CURSOR)
            count+=1
        old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,0x1510FEA0,12)
        self.assertEqual(struct.unpack_from('>3I',old,at),(0x00001025,0x03E00008,0))
        self.receipt.update(actual_callback_slot=3,actual_caller_window_phases=count,actual_MFC1_float_transfers_and_return_copy=True,current_267_word_parent_still_stub=True,full_caller_or_gameplay_not_claimed=True)
    def test_06_original_fill_helper_and_current_exact_providers(self):
        elf=self.values['conker/build/conker.us.elf'];code={}
        for entry,size in((CALLEE,188),(0x1501A680,76),(0x1501A6CC,152)):
            raw=self.rom[entry-0x15000000+0x2D4B0:entry-0x15000000+0x2D4B0+size]
            if entry!=CALLEE:self.assertEqual(elf[source.elf_slot_offset(elf,entry,size):source.elf_slot_offset(elf,entry,size)+size],raw)
            code.update({entry+i*4:w for i,w in enumerate(struct.unpack('>%dI'%(size//4),raw))})
        count=0
        for cat,state,phase,page,p in itertools.product((27,49,0),(2,3),(0,8),(0,1),range(3)):
            m=fixture(cat,state,p,phase);width,height=((292,216),(640,480),(1024,1024))[p]
            put(m,SYMBOLS['D_800BE620'],width);put(m,SYMBOLS['D_800BE624'],height);m[0x800BE9C0]=page
            for i in range(2):put(m,0x8002AAE8+i*4,0x80200000+i*0x100000)
            wanted=packet(m);models=[FillOracle(w,m,phase,p,connected=code).run()for w in(self.truth,self.words)]
            self.assertEqual(complete(models[0]),complete(models[1]));a=models[0]
            if wanted:
                r,g,b=wanted[5:];color=((r<<8)&0xF800)|((g<<3)&0x7C0)|((b>>2)&0x3E)|1
                pairs=((0xE7000000,0),(0xEF302C0F,4),(0xFF100000|((width-1)&0xFFF),0x80200000+page*0x100000),
                       (0xF7000000,(color<<16)|color),(0xF6000000|(((width-2)&0x3FF)<<14)|((height&0x3FF)<<2),2<<14))
                expected=dict(m)
                for i,(x,y)in enumerate(pairs):put(expected,CURSOR+i*8,x);put(expected,CURSOR+i*8+4,y)
                self.assertEqual(public(a.memory),public(expected));self.assertEqual(a.r[2],CURSOR+40)
                self.assertEqual([x[0]for x in a.calls],[CALLEE,0x1501A680,0x1501A6CC])
            else:self.assertEqual(public(a.memory),public(m));self.assertEqual(a.r[2],CURSOR);self.assertFalse(a.calls)
            count+=1
        self.receipt.update(original_helper_words=47,current_exact_color_image_and_rectangle_providers=[19,38],actual_helper_chain_phases=count,actual_five_command_payload_verified=True,helper_C_stub_not_restored=True)
    def test_07_suppressed_pointer_and_color_reads(self):
        for cat in(0,26,28,29,31,48,50,0x1000001B):
            m=fixture(cat)
            for base,size in((CONTEXT,0x3E0),(CHILD,0x90),(SYMBOLS['D_800DBFF0'],4),(SYMBOLS['D_800DBEA8'],3),(SYMBOLS['D_800BE620'],4),(SYMBOLS['D_800BE624'],4)):
                for i in range(size):m.pop(base+i,None)
            for words in(self.truth,self.words):
                a=FillOracle(words,m).run();self.assertFalse(a.calls);self.assertEqual(a.r[2],CURSOR)
        self.receipt.update(unbacked_inactive_context_dimensions_and_colors_suppressed=True)
    def test_08_pins_installed_identity_and_whole_image_controls(self):
        for name,old in self.values.items():
            expected=source.recovered_owner(old.decode()).encode()if self.installed and name==source.SOURCE else source.predicted_image(old,self.rom[source.ROM:source.ROM+168])if self.installed and name=='conker/build/conker.us.elf'else old
            self.assertEqual((ROOT/name).read_bytes(),expected,name);self.assertEqual(source.digest(old),source.INPUTS[name])
        self.assertEqual(source.digest((self.out/'before-padded.o').read_bytes()),source.BEFORE_OBJECT_SHA)
        before=self.values['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+168];pred=source.predicted_image(before,truth)
        for at in(0,len(pred)-1,source.elf_slot_offset(pred,source.ENTRY,168),source.elf_slot_offset(pred,0x15110544,4),source.elf_slot_offset(pred,0x80082B20,4)):
            wrong=bytearray(pred);wrong[at]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(wrong),truth)
        self.receipt.update(pinned_inputs=len(self.values),whole_image_corruption_controls=5,guards_and_conversion_rows_unchanged=True,metadata_exclusions=0)


if __name__=='__main__':unittest.main()
