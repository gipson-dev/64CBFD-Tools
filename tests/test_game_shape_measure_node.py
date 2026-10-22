"""Shape-node constructor: allocation gates, live helper effects and complete caller."""
from dataclasses import dataclass,replace
from pathlib import Path
import itertools,json,re,struct,subprocess,unittest
from tools.experiments import game_shape_measure_node as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests import test_game_shape_volume_match as volume
from tools.tests.game_view_render_pass_oracle import STACK

ROOT=Path(__file__).resolve().parents[2]
DESC,ALT,NODE=0x24000,0x25000,0x30000
HEAP,VOLUME,AREA,INSERT,CALLER=0x10003C6C,0x1514462C,0x15144598,0x1515F25C,0x150150A4
HEAD,TOTAL=0x800DCDC4,0x800DCD90
SYMBOLS=dict(func_10003C6C=HEAP,func_1514462C=VOLUME,func_15144598=AREA)
WORDS=(0,0x80000000,0x3F800000,0xBF800000,1,0x7F7FFFFF,0x7F800000,0xFF800000,0x7FC12345,0x7FA54321)

@dataclass(frozen=True)
class Case:
    descriptor:int=DESC
    result:int=NODE
    volume:int=0x3FA00000
    area:int=0xC0200000
    mode:int=0

def fixture(c,phase=0):
    m={STACK+phase+i:(i*17+0xA5)&255 for i in range(-0x600,0x300)}
    for p,n in((DESC-16,112),(ALT-16,112),(NODE-16,112),(HEAD-8,24),(TOTAL-8,24),
                (c.descriptor-16,112)if c.descriptor else(DESC-16,112),
                (c.result-16,112)if c.result else(NODE-16,112)):
        for i in range(n):m.setdefault(p+i,(i*13+37)&255)
    put(m,HEAD,ALT);put(m,TOTAL,bits(3.5))
    return m

def public(m):return {a:v for a,v in m.items()if not STACK-0x600<=a<STACK+0x308}

def effect(m,c,ordinal,phase=0):
    if ordinal==0:
        if c.descriptor and c.mode&1:m[c.descriptor+21]^=0x80
        if c.mode&64:put(m,STACK+phase,ALT)
    elif ordinal==1:
        if c.mode&2:
            put(m,c.result,ALT);put(m,c.result+8,0x41200000);put(m,c.result+12,ALT)
        if c.mode&4:m[c.descriptor+21]^=3
    else:
        if c.mode&16:put(m,c.result+4,read(m,c.result+4)^0x80000000)
        if c.mode&32:put(m,c.result+12,ALT)

def result_word(m,c,ordinal):
    return bits(float(m[c.descriptor+21]+ordinal))if c.mode&8 else c.volume if ordinal==1 else c.area

def observation(m,c):return tuple(read(m,(c.result or NODE)+i*4)for i in range(4))

def measurements(m,p,coefficients):
    w,h,d=(read(m,p+i,2)for i in(6,8,10));w,h,d=(v-65536 if v&32768 else v for v in(w,h,d))
    flags=m[p+21];v,_=volume.reference(w,h,d,flags,coefficients[1:])
    a=bits(float(w*d)*4.0)if flags&3==2 else bits(floating(bits(float(w*w)))*floating(coefficients[0]))if flags&3 in(0,1)else bits(1.0)
    return v,a

def reference(c,phase=0,symbols=None,memory=None,real=None):
    s=symbols or SYMBOLS;m=dict(fixture(c,phase)if memory is None else memory);calls=[];observations=[]
    calls.append((s['func_10003C6C'],(16,1,2,0,1)));observations.append(observation(m,c));effect(m,c,0,phase)
    if not c.result:return m,calls,observations,0
    put(m,c.result,c.descriptor)
    for ordinal,name,off in((1,'func_1514462C',4),(2,'func_15144598',8)):
        value=0
        if c.descriptor:
            calls.append((s[name],(c.descriptor,)));observations.append(observation(m,c))
            if real is None:effect(m,c,ordinal,phase);value=result_word(m,c,ordinal)
            else:value=measurements(m,c.descriptor,real)[ordinal-1]
        put(m,c.result+off,value)
    put(m,c.result+12,0)
    return m,calls,observations,c.result

class NodeOracle(TimingOracle):
    def __init__(self,words,c=Case(),phase=0,symbols=None,entry=source.ENTRY,connected=None,memory=None,argument=None):
        self.node_case=c;self.node_phase=phase;self.node_symbols=symbols or SYMBOLS;self.condition=False;self.visits=set()
        super().__init__(words,fixture(c,phase)if memory is None else memory,phase=phase,entry=entry,
            arguments=(c.descriptor if argument is None else argument,),connected=connected)
    def record_call(self,target):
        n=5 if target==self.node_symbols['func_10003C6C']else 2 if target==INSERT else 1
        assert target in(*self.node_symbols.values(),source.ENTRY,INSERT),hex(target)
        args=tuple(self.arguments(n));self.calls.append((target,args));self.events.append(('CALL',target,args))
        if target in self.node_symbols.values():self.observations.append(observation(self.memory,self.node_case))
    def hook(self,target):
        ordinal=0 if target==self.node_symbols['func_10003C6C']else 1 if target==self.node_symbols['func_1514462C']else 2
        effect(self.memory,self.node_case,ordinal,self.node_phase)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
        if ordinal==0:self.r[2]=self.node_case.result
        else:self.f[0]=result_word(self.memory,self.node_case,ordinal)
    def execute(self,word):
        self.visits.add(self.current_pc)
        if word>>26==17 and word>>21&31==20 and word&63==32:
            self.f[word>>6&31]=bits(float(signed(self.f[word>>11&31])));return
        super().execute(word)

def corpus():
    for fail,present,mode,k in itertools.product((0,1),(0,1),range(64),range(8)):
        yield Case(DESC if present else 0,0 if fail else NODE,WORDS[k],WORDS[(k+3)%10],mode)
    for offset,mode in itertools.product(range(0,32,4),range(64)):
        yield Case(DESC,DESC+offset,WORDS[mode%10],WORDS[(mode+4)%10],mode)
    for high,mode in itertools.product((0x80000000,0xA0000000),range(4)):
        yield Case(DESC+high,NODE+high,WORDS[8],WORDS[9],mode)

def controls():
    b=source.SELECTED
    return dict(selected=b,wrongSize=b.replace('(0x10, 1, 2, 0, 1)','(0xC, 1, 2, 0, 1)'),
        wrongPool=b.replace('(0x10, 1, 2, 0, 1)','(0x10, 1, 2, 0, 2)'),
        wrongDescriptor=b.replace('node->descriptor = descriptor;','node->descriptor = NULL;'),
        wrongVolume=b.replace('func_1514462C((struct134 *)descriptor)','func_15144598((struct134 *)descriptor)'),
        wrongArea=b.replace('func_15144598((struct134 *)descriptor)','func_1514462C((struct134 *)descriptor)'),
        omitVolume=b.replace('func_1514462C((struct134 *)descriptor)','0.0f'),
        omitArea=b.replace('func_15144598((struct134 *)descriptor)','0.0f'),
        wrongNext=b.replace('node->next = NULL;','node->next = node;'),
        rereadDescriptor=b.replace('func_15144598((struct134 *)descriptor)','func_15144598((struct134 *)node->descriptor)'),
        wrongReturn=b.replace('return (u8 *)node;','return NULL;'),
        earlyClear=b.replace('    node->next = NULL;\n','').replace('    node->descriptor = descriptor;','    node->next = NULL;\n    node->descriptor = descriptor;'),
        collapseNull=b.replace('    if (descriptor != NULL) {','    if (0) {'))

def native_harness(descriptor):
    node='typedef struct ShapeMeasureNode'+source.EXTRA_DECLARATIONS.split('typedef struct ShapeMeasureNode',1)[1]
    bodies='\n'.join(b.replace(source.FUNCTION,n)for n,b in controls().items())
    checks='\n'.join(('if(variant(%s)!=0)return 30;'if n=='selected'else'if(variant(%s)!=23)return 31;')%n for n in controls())
    return '''typedef unsigned char u8;typedef unsigned short u16;typedef short s16;typedef unsigned int u32;typedef int s32;typedef float f32;
#define NULL ((void*)0)
'''+descriptor+'\n'+node+'''
typedef char node_size[sizeof(ShapeMeasureNode)==16?1:-1];
typedef char node_area[__builtin_offsetof(ShapeMeasureNode,area)==8?1:-1];
typedef char node_next[__builtin_offsetof(ShapeMeasureNode,next)==12?1:-1];
static struct{u32 l[4];ShapeMeasureNode node;u32 r[4];}arena;
static struct{u32 l[4];struct134 d;u32 r[4];}descriptors[2];
static u8 before[sizeof(struct134)],*arg;static u32 failed,mode,vword,aword,stage,bad;
static u32 word(f32 x){union{f32 f;u32 u;}v;v.f=x;return v.u;}
static f32 number(u32 x){union{f32 f;u32 u;}v;v.u=x;return v.f;}
static u32 output(u32 which){return mode&8?word((f32)(arg[21]+which)):which==1?vword:aword;}
__attribute__((noinline,noclone)) s32 func_10003C6C(s32 a,s32 b,s32 c,s32 d,s32 e){
 if(stage++||a!=16||b!=1||c!=2||d||e!=1)bad=1;
 if(arg&&(mode&1))arg[21]^=0x80;
 return failed?0:(s32)(u32)&arena.node;
}
__attribute__((noinline,noclone)) f32 func_1514462C(struct134*p){
 if(stage!=1||(u8*)p!=arg||arena.node.descriptor!=arg||word(arena.node.volume)!=0x3FC00000
  ||word(arena.node.area)!=0xC0200000||arena.node.next)bad=1;
 stage++;
 if(mode&2){arena.node.descriptor=(u8*)&descriptors[1].d;arena.node.area=10.0f;arena.node.next=(ShapeMeasureNode*)&descriptors[1].d;}
 if(mode&4)arg[21]^=3;
 return number(output(1));
}
__attribute__((noinline,noclone)) f32 func_15144598(struct134*p){
 if(stage!=2||(u8*)p!=arg||arena.node.descriptor!=(mode&2?(u8*)&descriptors[1].d:arg)
  ||word(arena.node.volume)!=output(1)||word(arena.node.area)!=(mode&2?0x41200000:0xC0200000)
  ||arena.node.next!=(mode&2?(ShapeMeasureNode*)&descriptors[1].d:NULL))bad=1;
 stage++;
 if(mode&16)arena.node.volume=number(word(arena.node.volume)^0x80000000);
 if(mode&32)arena.node.next=(ShapeMeasureNode*)&descriptors[1].d;
 return number(output(2));
}
'''+bodies+'''
typedef u8*(*Factory)(u8*);
static int one(Factory fn,u32 fail,u32 present,u32 effects,u32 v,u32 a){
 u32 i,j,expectedV,expectedA;u8*out;failed=fail;mode=effects;vword=v;aword=a;stage=bad=0;
 for(j=0;j<2;j++){
  for(i=0;i<sizeof(struct134);i++)((u8*)&descriptors[j].d)[i]=(u8)(i*13+37+j*29);
  for(i=0;i<4;i++){descriptors[j].l[i]=0xA5A50000+j*16+i;descriptors[j].r[i]=0x5A5A0000+j*16+i;}
 }
 for(i=0;i<4;i++){arena.l[i]=0xA5A50000+i;arena.r[i]=0x5A5A0000+i;}
 arg=present?(u8*)&descriptors[0].d:NULL;
 for(i=0;i<sizeof(struct134);i++)before[i]=((u8*)&descriptors[0].d)[i];
 arena.node.descriptor=NULL;arena.node.volume=1.5f;arena.node.area=-2.5f;arena.node.next=NULL;
 out=fn(arg);
 if(arg&&(mode&1))before[21]^=0x80;
 if(!fail&&arg&&(mode&4))before[21]^=3;
 if(bad||stage!=(fail||!arg?1:3)||out!=(fail?NULL:(u8*)&arena.node))return 23;
 expectedV=fail?0x3FC00000:!arg?0:output(1)^(mode&16?0x80000000:0);
 expectedA=fail?0xC0200000:!arg?0:output(2);
 if(word(arena.node.volume)!=expectedV||word(arena.node.area)!=expectedA||arena.node.next
  ||arena.node.descriptor!=(fail||!arg?NULL:mode&2?(u8*)&descriptors[1].d:arg))return 23;
 for(i=0;i<sizeof(struct134);i++)if(((u8*)&descriptors[0].d)[i]!=before[i]
  ||((u8*)&descriptors[1].d)[i]!=(u8)(i*13+66))return 23;
 for(i=0;i<4;i++){
  if(arena.l[i]!=0xA5A50000+i||arena.r[i]!=0x5A5A0000+i)return 23;
  for(j=0;j<2;j++)if(descriptors[j].l[i]!=0xA5A50000+j*16+i||descriptors[j].r[i]!=0x5A5A0000+j*16+i)return 23;
 }return 0;
}
static int variant(Factory fn){
 const u32 values[]={0,0x80000000,0x3F800000,0xBF800000,1,0x7F7FFFFF,0x7F800000,0xFF800000};
 u32 f,p,m,v,a,n=0;
 for(f=0;f<2;f++)for(p=0;p<2;p++)for(m=0;m<64;m++)for(v=0;v<8;v++)for(a=0;a<8;a++){
  if(one(fn,f,p,m,values[v],values[a]))return 23;n++;
 }return n==16384?0:24;
}
static int run(void){
'''+checks+'''
 return 0;
}
__attribute__((force_align_arg_pointer)) void _start(void){int c=run();__asm__ volatile("int $0x80"::"a"(1),"b"(c):"memory");__builtin_unreachable();}
'''

class ShapeMeasureNodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out)
        cls.installed=(ROOT/source.SOURCE).read_text()==source.recovered_owner(cls.values[source.SOURCE].decode())
        if cls.installed:source.audit(ROOT,cls.out)
        else:source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        cls.obj,diag=source.compile_owner(ROOT,cls.out,'#include <ultra64.h>\n'+source.EXTRA_DECLARATIONS+source.SELECTED,'fresh-selected')
        if diag:raise ValueError(diag)
        data,fs=source.link_owner(ROOT,cls.out,cls.obj,source.OWNER);cls.rom=cls.values['conker/conker.us.bin']
        cls.words=list(struct.unpack_from('>43I',data,fs[source.FUNCTION]['value']));cls.truth=list(struct.unpack_from('>43I',cls.rom,source.ROM));cls.receipt=dict(installed=cls.installed)
    @classmethod
    def tearDownClass(cls):
        (cls.out/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n');print(cls.receipt)
    def compare(self,c,phase=0,images=None,symbols=None,entry=source.ENTRY,connected=None,memory=None,real=None):
        expected,calls,observations,result=reference(c,phase,symbols,memory,real);models=[]
        for words in images or(self.truth,self.words):
            m=NodeOracle(words,c,phase,symbols,entry,connected,memory).run()
            self.assertEqual((public(m.memory),m.calls,m.observations,m.r[2]),(public(expected),calls,observations,result));models.append(m)
        self.assertEqual(complete(models[0]),complete(models[1]));return models
    def test_01_direct_C_owner_caller_Make_and_effective_stub(self):
        q=json.loads((self.out/'qualification.json').read_text());m=json.loads((self.out/'make-shadow.json').read_text())
        self.assertEqual(self.words,self.truth);self.assertEqual((q['words'],q['frame'],q['relocations'],q['preserved_neighbors'],q['preserved_caller_functions']),(43,48,3,34,32))
        self.assertEqual(m['actual_Make_commands'],10);self.assertTrue(m['entire_caller_object_identical'])
        old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,source.ENTRY,172)
        stale=NodeOracle(struct.unpack_from('>43I',old,at)).run();self.assertFalse(stale.calls);self.assertEqual(stale.r[2],0)
        self.assertNotEqual(public(stale.memory),public(self.compare(Case())[0].memory))
        self.receipt.update(words=43,frame=48,bindings=3,neighbors=34,caller_functions=32,new_guards=0,actual_Make_commands=10,old_stub_rejected=True)
    def test_02_all_gates_helper_effects_aliases_and_float_words(self):
        count=0;visits=set()
        for c,phase in itertools.product(corpus(),(0,8)):
            m=self.compare(c,phase)[0];visits.update(m.visits);count+=1
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+172,4)))
        self.receipt.update(guest_phases=count,all43_words_visited=True,allocation_and_null_descriptor_gates=True,captured_input_and_live_helper_effects=True,guest_descriptor_node_aliases=True)
    def test_03_native32_three_optimizations_and_twelve_defined_controls(self):
        descriptor=re.search(r'typedef struct \{[^{}]*\} struct134;',self.values['conker/include/structs.h'].decode()).group()
        for opt in('-O0','-O2','-O3'):
            p=self.out/('native'+opt);c=p.with_suffix('.c');c.write_text(native_harness(descriptor))
            q=subprocess.run([*native_command(opt),str(c),'-o',str(p)],cwd=ROOT,capture_output=True,text=True)
            (self.out/('native'+opt+'-diagnostics.txt')).write_text(q.stdout+q.stderr);self.assertEqual(q.returncode,0,q.stdout+q.stderr)
            q=subprocess.run([str(p)],capture_output=True);self.assertEqual(q.returncode,0,q.stderr)
        self.receipt.update(native_cases_per_optimization=16384,native_optimizations=['O0','O2','O3'],defined_wrong_C_controls=12,trap_UBSan=True,native_size_offsets_and_fences=True,native_signaling_NaN_or_alias_claimed=False)
    def linked(self,obj,entry,symbols,label):
        data,fs,rs=source.parse_object(obj);asm,unknown=emit_function(data,fs[source.FUNCTION],rs,source.FUNCTION,symbols);self.assertFalse(unknown)
        p=self.out/label;a=p.with_suffix('.s');o=p.with_suffix('.o');ld=p.with_suffix('.ld');elf=p.with_suffix('.elf')
        a.write_text(asm);ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(o),str(a)],capture_output=True,check=True)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',source.FUNCTION,*['--defsym=%s=0x%X'%x for x in symbols.items()],'-o',str(elf),str(o)],capture_output=True,check=True)
        return struct.unpack_from('>43I',sections(elf)['.text'][1])
    def test_04_independent_rebases_and_fired_access_prefixes(self):
        phases=cuts=0
        for i,entry in enumerate((source.ENTRY,0x18017FFC,0x1A028000)):
            s={k:v+i*0x10004 for k,v in SYMBOLS.items()}
            images=[self.linked(obj,entry,s,'rebase-%d-%d'%(i,j))for j,obj in enumerate((source.original(ROOT,self.out),self.obj,self.out/'qualified-padded.o'))]
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            for fail,present,phase in itertools.product((0,1),(0,1),(0,8)):
                self.compare(Case(DESC if present else 0,0 if fail else NODE,mode=63),phase,images[:2],s,entry);phases+=1
        for c,phase in itertools.product((Case(0),Case(result=0),Case(mode=63),Case(DESC,DESC+8,mode=63)),(0,8)):
            good=NodeOracle(self.truth,c,phase).run()
            for cut in range(good.root_accesses):
                models=[NodeOracle(w,c,phase)for w in(self.truth,self.words)]
                for m in models:
                    m.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual((models[0].current_pc,models[0].delay_of),(models[1].current_pc,models[1].delay_of));cuts+=1
        self.receipt.update(independent_GNU_links=9,rebase_phases=phases,fired_root_access_prefixes=cuts,portable_C_fault_claimed=False)
    def test_05_complete_original_caller_and_actual_list_insert(self):
        jal=struct.pack('>I',0x0C000000|(source.ENTRY>>2&0x3FFFFFF));ptr=struct.pack('>I',source.ENTRY)
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==jal],[0x4255C]);self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==ptr],[])
        caller=self.rom[0x42554:0x42554+96];insert=self.rom[0x18C70C:0x18C70C+20];old=self.values['conker/build/conker.us.elf']
        for entry,raw in((CALLER,caller),(INSERT,insert)):
            at=source.elf_slot_offset(old,entry,len(raw));self.assertEqual(old[at:at+len(raw)],raw)
        count=0
        for fail,present,mode,phase in itertools.product((0,1),(0,1),(0,2,16,63),(0,8)):
            c=Case(DESC if present else 0,0 if fail else NODE,mode=mode);expected,calls,observations,result=reference(c,phase)
            if result:
                calls.append((INSERT,(HEAD,result)));put(expected,result+12,read(expected,HEAD));put(expected,HEAD,result)
                put(expected,TOTAL,bits(floating(read(expected,TOTAL))+floating(read(expected,result+8))))
            models=[]
            for words in(self.truth,self.words):
                connected={source.ENTRY+i*4:w for i,w in enumerate(words)};connected.update({INSERT+i*4:w for i,w in enumerate(struct.unpack('>5I',insert))})
                m=NodeOracle(struct.unpack('>24I',caller),c,phase,entry=CALLER,connected=connected).run()
                self.assertEqual((public(m.memory),m.calls,m.observations,m.r[2]),(public(expected),[(source.ENTRY,(c.descriptor,))]+calls,observations,1));models.append(m)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.receipt.update(complete_caller_phases=count,complete_caller_words=24,actual_insert_words=5,all_caller_paths_qualified=True,real_heap_execution_claimed=False)
    def test_06_actual_volume_and_area_helpers(self):
        old=self.values['conker/build/conker.us.elf'];connected={}
        for entry,rom,n in((VOLUME,0x171ADC,56),(AREA,0x171A48,37)):
            raw=self.rom[rom:rom+n*4];at=source.elf_slot_offset(old,entry,n*4);self.assertEqual(old[at:at+n*4],raw)
            connected.update({entry+i*4:w for i,w in enumerate(struct.unpack('>%dI'%n,raw))})
        coefficients=struct.unpack_from('>3I',self.rom,0x2275E0+0x800A5694-0x80082B20);count=0;visits=set()
        for flag,w,h,d,alias,phase in itertools.product((0,1,2,3,252,253,254,255),(-32768,1,32767),(-1,2),(0,32767),(False,True),(0,8)):
            c=Case(result=DESC+8 if alias else NODE);memory=fixture(c,phase)
            for off,value in((6,w),(8,h),(10,d)):put(memory,DESC+off,value&65535,2)
            memory[DESC+21]=flag
            for i,word in enumerate(coefficients):put(memory,0x800A5694+i*4,word)
            m=self.compare(c,phase,connected=connected,memory=memory,real=coefficients)[0];visits.update(m.visits);count+=1
        self.assertEqual(set(connected)-visits,{0x1514468C})
        self.receipt.update(actual_measurement_phases=count,current_original_helper_words=93,executed_helper_words=92,retained_unreachable_volume_load='1514468C',real_heap_execution_claimed=False,portable_native_alias_claimed=False)
    def test_07_captured_argument_and_true_record_layout(self):
        for c,phase in itertools.product((Case(mode=127),Case(DESC,DESC,mode=127)),(0,8)):
            self.compare(c,phase)
        self.assertIn('struct ShapeMeasureNode *next;',source.EXTRA_DECLARATIONS)
        caller=source.recovered_caller(self.values[source.CALLER_SOURCE].decode())
        self.assertIn('u8 *func_1515F1B0(u8 *arg0);',caller);self.assertNotIn('struct17 *temp_v0 = func_1515F1B0',caller)
        self.receipt.update(guest_incoming_home_mutation_phases=4,private_16byte_node_and_opaque_caller=True,shared_struct17_unchanged=True)
    def test_08_history_strict_image_and_guard_identity(self):
        before=self.values['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+172];pred=source.predicted_image(before,truth)
        source.check_image(before,pred,truth);at=source.elf_slot_offset(before,source.ENTRY,172)
        for pos in(0,at-1,at,at+168,at+172,len(before)-1):
            wrong=bytearray(pred);wrong[pos]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(wrong),truth)
        with self.assertRaises(ValueError):source.check_image(before,pred[:-1],truth)
        for name,wanted in source.INPUTS.items():
            old=self.values[name];self.assertEqual(source.digest(old),wanted)
            expected=source.recovered_owner(old.decode()).encode()if self.installed and name==source.SOURCE else source.recovered_caller(old.decode()).encode()if self.installed and name==source.CALLER_SOURCE else pred if self.installed and name=='conker/build/conker.us.elf'else old
            self.assertEqual((ROOT/name).read_bytes(),expected,name)
        self.assertEqual((ROOT/source.CALLER_OBJECT).read_bytes(),(self.out/'before-caller-padded.o').read_bytes())
        self.receipt.update(pinned_inputs=len(source.INPUTS),strict_image_negatives=7,guard_manifest_unchanged=True,entire_caller_object_identical=True)
