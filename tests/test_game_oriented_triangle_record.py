"""Direct triangle builder, its two callers and bounded original geometry helpers."""
import itertools,json,struct,subprocess,unittest
from pathlib import Path
from tools.experiments import game_oriented_triangle_record as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_projected_packet_draw import native_command

ROOT=Path(__file__).resolve().parents[2]
ENTRY,SRC,OUT,ALT=0x1514F640,0x20000,0x22000,0x24000
BASIS,DOT,CROSS=0x15144E80,0x15144A74,0x151450B4
PARENTS=((0x1514FEFC,0x17D3AC,0x1514FF44),(0x15153C84,0x181134,0x15153CCC))
FLOATS=(0,0x80000000,0x3F800000,0xBF800000,1,0x80000001,0x7F800000,0xFF800000,0x7FC12345,0xFFC12345,0x7F812345)
NORMAL=(0x3FA00000,0xC0200000,0x80000000)
TRIANGLES=(
 ((0,0,0),(1,0,0),(0,1,0)),((0,0,0),(0,0,0),(0,1,0)),
 ((0,1,0),(0,0,0),(0,1,0)),((0,1,0),(0,0,0),(0,0,0)),
 ((0,0,0),(1,1,1),(2,2,2)),((-32768,32767,-1),(32767,-32768,1),(13,5,-8)),
 ((4,2,3),(4,7,3),(4,7,9)),((4,2,3),(4,2,9),(5,7,9)))


def fixture(phase=0,alias=0,triangle=0,vector=(1.0,-2.0,3.0),snapshot=0x7F812345):
    m={STACK+phase+i:(i*17+0xA5)&255 for i in range(-0x600,0x180)}
    for b in (SRC-16,OUT-16,ALT-16):m.update({b+i:0xA5 for i in range(160)})
    out={1:SRC,2:SRC+4,3:SRC-4,4:STACK+phase+0x10,5:STACK+phase+0x38}.get(alias,OUT)
    for b in (SRC,ALT):
        for i,v in enumerate(vector):put(m,b+i*4,bits(v))
        for i,v in enumerate(sum(TRIANGLES[triangle],())):put(m,b+12+i*2,v&65535,2)
        put(m,b+32,snapshot)
    return m,(SRC,out)


def public(m):
    return {a:v for a,v in m.items()if not STACK-0x600<=a<STACK+0x200}


class RecordOracle(TimingOracle):
    def __init__(self,words,memory,args,phase=0,status=1,dot=0xBF800000,mode=0,
                 entry=ENTRY,connected=None,bindings=(BASIS,DOT)):
        self.status,self.dot,self.effect_mode=status,dot,mode
        self.bindings=bindings;self.trace=[];self.packets=[]
        super().__init__(words,memory,phase=phase,entry=entry,arguments=args,connected=connected)
    def get(self,address,size):
        value=super().get(address,size)
        if self.own_instruction:self.trace.append(('R',address,size,value))
        return value
    def put(self,address,value,size):
        super().put(address,value,size)
        if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(8*size))-1)))
    def execute(self,word):
        if word>>26==17 and word>>21&31==16 and word&63==7:
            self.f[word>>6&31]=self.f[word>>11&31]^0x80000000
        else:super().execute(word)
    def record_call(self,target):
        canonical={self.bindings[0]:BASIS,self.bindings[1]:DOT}.get(target,target)
        n={ENTRY:2,BASIS:4,DOT:2,CROSS:3,0x1514FF44:5,0x15153CCC:5}[canonical]
        args=self.arguments(n);self.calls.append((canonical,args));self.events.append(('CALL',canonical,args))
        if canonical in (0x1514FF44,0x15153CCC):
            self.packets.append(bytes(self.memory[args[0]+i]for i in range(44)))
    def hook(self,target):
        canonical,args=self.calls[-1]
        if canonical==BASIS:
            if self.status:
                for at,values in ((args[1],(bits(4.),bits(5.),bits(6.))),
                                  (args[2],(bits(7.),bits(8.),bits(9.))),(args[3],NORMAL)):
                    for i,w in enumerate(values):put(self.memory,at+i*4,w)
            if self.effect_mode&1:
                put(self.memory,SRC+32,0x87654321);put(self.memory,SRC,0xC1100000)
            if self.effect_mode&2:put(self.memory,self.r[29]+40,ALT)
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo=0x12345678,0x87654321
        self.r[2]=self.status if canonical==BASIS else 0x87654321
        if canonical==DOT:self.f[0]=self.dot


def reference(memory,args,status,dot,mode=0):
    m=dict(memory);src,out=args;m[out]=2;put(m,out+40,read(m,src+32))
    calls=[(BASIS,(src+12,out+16,out+28,out+4))]
    if status:
        for at,values in ((out+16,(bits(4.),bits(5.),bits(6.))),(out+28,(bits(7.),bits(8.),bits(9.))),(out+4,NORMAL)):
            for i,w in enumerate(values):put(m,at+i*4,w)
    if mode&1:put(m,SRC+32,0x87654321);put(m,SRC,0xC1100000)
    if status:
        calls.append((DOT,(out+4,ALT if mode&2 else src)))
        if floating(dot)<0.:
            for at in (4,8,12):put(m,out+at,read(m,out+at)^0x80000000)
    return m,calls


def finite_reference(memory,args,triangle):
    m=dict(memory);src,out=args;m[out]=2;put(m,out+40,read(m,src+32))
    p=TRIANGLES[triangle]
    if len(set(p))!=3:return m,False
    edge=tuple(floating(bits(float(a-b)))for a,b in zip(p[0],p[1]))
    other=tuple(floating(bits(float(a-b)))for a,b in zip(p[2],p[1]))
    def cross(a,b):
        return tuple(floating(bits(floating(bits(a[j]*b[k]))-floating(bits(a[k]*b[j]))))
                     for j,k in ((1,2),(2,0),(0,1)))
    normal=cross(edge,other);second=cross(edge,normal)
    vector=tuple(floating(read(m,src+i*4))for i in range(3))
    value=floating(bits(floating(bits(floating(bits(normal[0]*vector[0]))+
                       floating(bits(normal[1]*vector[1]))))+floating(bits(vector[2]*normal[2]))))
    for offset,values in ((4,normal),(16,second),(28,edge)):
        for i,v in enumerate(values):put(m,out+offset+i*4,bits(v)^(0x80000000 if offset==4 and value<0 else 0))
    return m,True


def native_harness(body,parents):
    return '#include <ultra64.h>\n'+source.DECLARATIONS+r'''
typedef union{u32 w[32];u8 b[128];f32 f[32];}Block;
static Block input,output;static u32 status,dotword,basisCalls,dotCalls,bad,consumerCalls;
static f32 real(u32 w){union{u32 w;f32 f;}v;v.w=w;return v.f;}
s32 func_15144E80(s16*p,f32*a,f32*b,f32*n){
 if((u8*)p!=input.b+12||a!=(f32*)(output.b+16)||b!=(f32*)(output.b+28)||n!=(f32*)(output.b+4))bad=1;
 basisCalls++;if(status){a[0]=4.;a[1]=5.;a[2]=6.;b[0]=7.;b[1]=8.;b[2]=9.;n[0]=1.25f;n[1]=-2.5f;n[2]=-0.0f;}
 return (s32)status;}
f32 func_15144A74(f32*a,f32*b){dotCalls++;if(a!=(f32*)(output.b+4)||b!=(f32*)input.b)bad=1;return real(dotword);}
static s32 consume(u8*p,s32 a,s32 b,u8 c,s32 d){
 u32 i;consumerCalls++;if(a!=(s32)0x87654321u||b!=0x12345678||c!=0xE7||d!=(s32)0xFEDCBA98u)bad=1;
 for(i=0;i<44;i++){if(i>=1&&i<=3)continue;if(!status&&i>=4&&i<40)continue;if(p[i]!=output.b[i])bad=1;}
 return 0;}
s32 func_1514FF44(u8*p,s32 a,s32 b,u8 c,s32 d){return consume(p,a,b,c,d);}
s32 func_15153CCC(u8*p,s32 a,s32 b,u8 c,s32 d){return consume(p,a,b,c,d);}
'''+body+'\n'+parents+r'''
static int run(void){
 const u32 dots[]={0,0x80000000u,0x3F800000u,0xBF800000u,1,0x80000001u,0x7F800000u,0xFF800000u,0x7FC12345u};
 const u32 statuses[]={0,1,0x80000000u,0xFFFFFFFFu};u32 s,k,i,flip,cases=0;
 for(s=0;s<4;s++)for(k=0;k<9;k++){
  for(i=0;i<32;i++){input.w[i]=0x12345678u;output.w[i]=0xA5A5A5A5u;}
  input.w[8]=0x80000000u;status=statuses[s];dotword=dots[k];basisCalls=dotCalls=bad=consumerCalls=0;
  func_1514F640(input.b,output.b);
  if(bad||basisCalls!=1||dotCalls!=(status!=0)||output.b[0]!=2||output.b[1]!=0xA5||output.b[2]!=0xA5||output.b[3]!=0xA5||output.w[10]!=input.w[8])return 23;
  flip=real(dotword)<0.0f?0x80000000u:0;
  if(status){if(output.w[1]!=(0x3FA00000u^flip)||output.w[2]!=(0xC0200000u^flip)||output.w[3]!=(0x80000000u^flip))return 23;
   if(output.f[4]!=4.f||output.f[6]!=6.f||output.f[7]!=7.f||output.f[9]!=9.f)return 23;}
  else for(i=1;i<10;i++)if(output.w[i]!=0xA5A5A5A5u)return 23;
  for(i=11;i<32;i++)if(output.w[i]!=0xA5A5A5A5u)return 23;
  cases++;
 }
 return cases==36?0:24;}
void _start(void){int code=run();__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
'''


class OrientedTriangleRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.out.mkdir(parents=True,exist_ok=True)
        cls.values=source.snapshot(cls.out);cls.rom=cls.values['conker/conker.us.bin']
        cls.installed=(ROOT/source.SOURCE).read_text()==source.recovered_owner(cls.values[source.SOURCE].decode())
        if cls.installed:source.audit(ROOT,cls.out)
        else:source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        cls.obj,diag=source.compile_owner(ROOT,cls.out,'#include <ultra64.h>\n'+source.DECLARATIONS+source.SELECTED[source.FUNCTIONS[0]],'fresh-selected')
        if diag:raise ValueError(diag)
        cls.raw=cls.link_words(cls.obj,ENTRY,(BASIS,DOT),'fresh-link')
        cls.truth=list(struct.unpack_from('>42I',cls.rom,0x17CAF0))
        cls.parents=[list(struct.unpack_from('>18I',cls.rom,rom))for _,rom,_ in PARENTS]
        cls.helpers={entry:list(struct.unpack_from('>%dI'%n,cls.rom,rom))for entry,rom,n in ((BASIS,0x172330,141),(CROSS,0x172564,29),(DOT,0x171F24,13))}
        cls.receipt=dict(installed=cls.installed)
    @classmethod
    def link_words(cls,obj,entry,helpers,label):
        from tools.experiments.alternative_source_draft_word_screen import emit_function
        text,fs,rs=source.parse_object(obj);symbols=dict(zip(('func_15144E80','func_15144A74'),helpers))
        asm,unknown=emit_function(text,fs[source.FUNCTIONS[0]],rs,source.FUNCTIONS[0],symbols);assert not unknown
        stem=cls.out/label;ap=stem.with_suffix('.s');op=stem.with_suffix('.o');lp=stem.with_suffix('.ld');ep=stem.with_suffix('.elf')
        ap.write_text(asm);lp.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(op),str(ap)],capture_output=True,check=True)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(lp),*['--defsym=%s=0x%X'%(k,v)for k,v in symbols.items()],'-e',source.FUNCTIONS[0],'-o',str(ep),str(op)],capture_output=True,check=True)
        return list(struct.unpack_from('>42I',sections(ep)['.text'][1]))
    @classmethod
    def tearDownClass(cls):
        (cls.out/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n');print(cls.receipt)
    def pair(self,memory,args,**kw):
        models=[RecordOracle(code,memory,args,**kw).run()for code in (self.truth,self.raw)]
        self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(models[0].trace,models[1].trace)
        return models[0]
    def test_01_direct_owner_Make_GNU_and_stub_rejection(self):
        self.assertEqual(self.raw,self.truth)
        self.assertEqual(source.payload(self.obj,source.FUNCTIONS[0]),source.payload(source.original(ROOT,self.out,source.FUNCTIONS[0]),source.FUNCTIONS[0]))
        q=json.loads((self.out/'qualification.json').read_text())
        self.assertEqual((q['total_words'],q['new_guards'],q['compiler_only']),(42,0,True))
        old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,ENTRY,168)
        m,args=fixture();old_model=RecordOracle(struct.unpack_from('>42I',old,at),m,args).run()
        self.assertNotEqual(public(old_model.memory),public(reference(m,args,1,0xBF800000)[0]))
        self.receipt.update(words=42,frame=40,new_guards=0,bindings=2,old_stub_effectively_rejected=True,neighbors=q['preserved_neighbors'])
    def test_02_guest_float_gates_source_homes_and_aliases(self):
        visits=set();count=aliases=0
        for status,dot,mode,phase,snapshot in itertools.product((0,1,0x80000000,0xFFFFFFFF),FLOATS,range(4),(0,8),(0x80000000,0x7F812345)):
            m,args=fixture(phase,snapshot=snapshot);model=self.pair(m,args,phase=phase,status=status,dot=dot,mode=mode)
            expected,calls=reference(m,args,status,dot,mode)
            self.assertEqual(public(model.memory),public(expected));self.assertEqual(model.calls,calls)
            self.assertEqual(model.memory[OUT+1],0xA5);self.assertEqual(read(model.memory,OUT+40),snapshot)
            visits.update(model.visits);count+=1
        for alias,status,dot,phase in itertools.product(range(1,6),(0,1),(0,0xBF800000,0x7FC12345),(0,8)):
            m,args=fixture(phase,alias);self.pair(m,args,phase=phase,status=status,dot=dot);aliases+=1
        self.assertEqual(visits,set(range(ENTRY,ENTRY+168,4)))
        self.receipt.update(guest_phases=count,guest_alias_phases=aliases,reachable_words=len(visits),physical_stack_home_mutations=True,ordered_NaN_and_signed_zero_gate=True,FCSR_or_exception_equivalence_claimed=False)
    def test_03_native32_and_effective_wrong_C(self):
        body=source.SELECTED[source.FUNCTIONS[0]]
        def run(body,label,opt):
            p=self.out/(label+opt+'.c');exe=p.with_suffix('.elf');p.write_text(native_harness(body,''))
            q=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(q.returncode,0,q.stderr);return subprocess.run([str(exe)],capture_output=True,timeout=30).returncode
        for opt in ('-O0','-O2','-O3'):self.assertEqual(run(body,'native',opt),0)
        changes=(('tag','output[0] = 2','output[0] = 3'),('snapshot','source + 0x20','source + 0x1C'),
                 ('negative-gate','< 0.0f','> 0.0f'),('zero-gate','< 0.0f','<= 0.0f'),
                 ('normal-y','output + 8) = -','output + 8) = +'),
                 ('status','if (func_15144E80','if (!func_15144E80'))
        for label,a,b in changes:
            self.assertIn(a,body);self.assertEqual(run(body.replace(a,b),'wrong-'+label,'-O2'),23,label)
        self.receipt.update(native_cases_per_optimization=36,native_optimizations=3,trap_UBSan=True,effective_wrong_C_controls=len(changes),native_private_padding_not_asserted=True)
    def test_04_two_complete_wrappers_and_packet_forwarding(self):
        jal=struct.pack('>I',0x0C000000|(ENTRY>>2&0x3FFFFFF))
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==jal],[0x17D3C0,0x181148])
        self.assertFalse(any(self.rom[i:i+4]==struct.pack('>I',ENTRY)for i in range(0,len(self.rom),4)))
        count=0;seen=set()
        for index,status,dot,phase,byte in itertools.product(range(2),(0,1),(0,0xBF800000,0x7FC12345),(0,8),(0,255,0xAB0000E7)):
            entry,_,consumer=PARENTS[index];m,_=fixture(phase);args=(SRC,0x87654321,0x12345678,byte,0xFEDCBA98);models=[]
            for code in (self.truth,self.raw):
                connected=dict(zip(range(ENTRY,ENTRY+168,4),code))
                model=RecordOracle(self.parents[index],m,args,phase,status,dot,entry=entry,connected=connected).run();models.append(model);seen.update(model.visits)
            self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(models[0].packets,models[1].packets)
            out=STACK+phase-80+36;calls=models[0].calls
            self.assertEqual(calls[0],(ENTRY,(SRC,out)))
            self.assertEqual(calls[-1],(consumer,(out,*args[1:3],byte&255,args[4])))
            packet=models[0].packets[0];self.assertEqual((packet[0],int.from_bytes(packet[40:44],'big')),(2,0x7F812345));count+=1
        for entry,_,_ in PARENTS:self.assertTrue(set(range(entry,entry+72,4))<=seen)
        before=self.values['conker/build/conker.us.elf']
        for code,(entry,_,_)in zip(self.parents,PARENTS):
            at=source.elf_slot_offset(before,entry,72);self.assertEqual(code,list(struct.unpack_from('>18I',before,at)))
        self.receipt.update(original_current_callers=2,caller_words_each=18,caller_phases=count,all_caller_words_visited=True,full_44_byte_guest_packet_compared=True,consumer_providers_bounded=True)
    def test_05_connected_original_geometry_helpers(self):
        connected={pc:w for entry,code in self.helpers.items()for pc,w in zip(range(entry,entry+len(code)*4,4),code)}
        count=0;seen=set()
        for triangle,vector,phase in itertools.product(range(len(TRIANGLES)),((1.,-2.,3.),(-1.,2.,-3.),(0.,0.,0.)),(0,8)):
            m,args=fixture(phase,triangle=triangle,vector=vector);expected,valid=finite_reference(m,args,triangle)
            model=self.pair(m,args,phase=phase,connected=connected);self.assertEqual(public(model.memory),public(expected))
            self.assertEqual([x[0]for x in model.calls],[BASIS,CROSS,CROSS,DOT]if valid else [BASIS])
            seen.update(model.visits);count+=1
        old=self.values['conker/build/conker.us.elf']
        for entry,code in self.helpers.items():
            at=source.elf_slot_offset(old,entry,len(code)*4);self.assertEqual(code,list(struct.unpack_from('>%dI'%len(code),old,at)))
        coverage={hex(e):sum(pc in seen for pc in range(e,e+len(c)*4,4))for e,c in self.helpers.items()}
        self.assertEqual(coverage[hex(CROSS)],29);self.assertEqual(coverage[hex(DOT)],13)
        self.receipt.update(original_helper_words=[141,29,13],connected_finite_phases=count,helper_visited_words=coverage,signed_short_vertices=True,collinear_not_rejected=True,NULL_normal_helper_path_not_claimed=True)
    def test_06_independent_links_and_fired_fault_prefixes(self):
        original=source.original(ROOT,self.out,source.FUNCTIONS[0]);count=cuts=0
        for i,helpers in enumerate(((0x17107FFC,0x17208000),(0x1720FFFC,0x17300000),(0x17308000,0x17407FFC))):
            entry=0x17001000+i*0x10000
            images=[self.link_words(obj,entry,helpers,'rebase-%s-%d'%(label,i))for label,obj in (('original',original),('C',self.obj))]
            self.assertEqual(*images);count+=2
            for status,dot in itertools.product((0,1),(0,0xBF800000,0x7FC12345)):
                m,args=fixture();models=[RecordOracle(code,m,args,status=status,dot=dot,entry=entry,bindings=helpers).run()for code in images]
                self.assertEqual(complete(models[0]),complete(models[1]))
                self.assertEqual(public(models[0].memory),public(reference(m,args,status,dot)[0]))
        for status,dot,alias,phase in itertools.product((0,1),(0,0xBF800000,0x7FC12345),(0,1,4),(0,8)):
            m,args=fixture(phase,alias);good=RecordOracle(self.truth,m,args,phase,status,dot).run()
            for cut in range(good.root_accesses):
                models=[RecordOracle(code,m,args,phase,status,dot)for code in (self.truth,self.raw)]
                for model in models:
                    model.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):model.run()
                self.assertEqual(complete(models[0]),complete(models[1]))
                self.assertEqual((models[0].current_pc,models[0].delay_of),(models[1].current_pc,models[1].delay_of));cuts+=1
        self.receipt.update(independent_GNU_links=count,fired_root_fault_prefixes=cuts,portable_C_fault_MMU_or_hardware_FPU_claimed=False)
    def test_07_strict_image_corruptions(self):
        before=self.values['conker/build/conker.us.elf'];predicted=source.predicted_image(before,self.rom)
        for at in (0,len(predicted)-1,source.elf_slot_offset(predicted,ENTRY,168),source.elf_slot_offset(predicted,PARENTS[0][0],72),source.elf_slot_offset(predicted,0x80082B20,4)):
            wrong=bytearray(predicted);wrong[at]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(wrong),self.rom)
        self.receipt.update(strict_image_corruption_controls=5,metadata_exclusions=0,guard_manifest_unchanged=True)
    def test_08_all_pins_and_installed_identity(self):
        for name,old in self.values.items():
            self.assertEqual(source.digest(old),source.INPUTS[name])
            expected=source.recovered_owner(old.decode()).encode()if self.installed and name==source.SOURCE else source.predicted_image(old,self.rom)if self.installed and name=='conker/build/conker.us.elf'else old
            self.assertEqual((ROOT/name).read_bytes(),expected,name)
        self.assertEqual(source.digest((self.out/'before-padded.o').read_bytes()),source.BEFORE_OBJECT_SHA)
        self.receipt.update(pinned_inputs=len(self.values),old_object_pinned=True)


if __name__=='__main__':unittest.main()
