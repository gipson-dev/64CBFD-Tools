"""SDK segment selection, fifth-argument lifetime, typed caller and real helper bounds."""
from dataclasses import dataclass,replace
import itertools,json,struct,subprocess,unittest
from pathlib import Path
from tools.experiments import game_segment_bank_pair as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_projected_packet_draw import native_command

ROOT=Path(__file__).resolve().parents[2]
NAME='func_151D710C'
ENTRY,CALLER,HELPER,FOLLOW,DECODE=0x151D710C,0x150FB1E8,0x15133EEC,0x15157F80,0x1510D0EC
BUFFER,OTHER,DESC,FLAG=0x30000,0x34000,0x28000,0x29000
SYMBOLS=dict(D_80083740=0x80083740,D_800838C0=0x800838C0,func_15133EEC=HELPER)


@dataclass(frozen=True)
class Case:
    alpha:int=255
    mode:int=0
    alias:int=0
    unused2:int=0xABCD1234
    unused3:int=0x87654321


def pointers(case,sp):
    descriptor=sp+8-0x43 if case.alias==6 else DESC
    flag=(FLAG,DESC+0x43,BUFFER+34,sp+8,sp+12,sp+16,FLAG)[case.alias]
    return descriptor,flag


def fixture(case,phase=0):
    sp=STACK+phase;m={sp+i:(i*17+0xA5)&255 for i in range(-0x400,0x200)}
    for base,size in ((BUFFER,512),(OTHER,256),(DESC,128),(FLAG,16)):
        m.update({base+i:0xA5 for i in range(size)})
    descriptor,flag=pointers(case,sp);m[descriptor+0x43]=case.alpha
    put(m,sp+16,flag)
    return m


def effect(case,m,args,sp,ordinal,descriptor):
    cursor,resource,segment,kind=args
    put(m,cursor,0xD0600000|segment);put(m,cursor+4,resource<<8|kind)
    if case.mode&1:m[descriptor+0x43]^=255
    for i in range(4):put(m,sp+i*4,0xB5000000+i)
    if case.mode&8 and ordinal==0:put(m,sp+40,FLAG+1)
    if case.mode&2:return OTHER+32+ordinal*16
    if case.mode&4:return cursor-8 if ordinal==0 else cursor+16
    return cursor+8


def reference(case,memory,phase=0,symbols=None):
    syms=symbols or SYMBOLS;sp=STACK+phase;descriptor,_=pointers(case,sp);m=dict(memory)
    put(m,sp-4,0xDEAD0000);put(m,sp+8,case.unused2);put(m,sp+12,case.unused3)
    bank=syms['D_80083740']if m[descriptor+0x43]<255 else syms['D_800838C0']
    put(m,BUFFER+32,0xDB060020);put(m,BUFFER+36,bank)
    cursor=BUFFER+40;calls=[]
    for n,segment in enumerate((6,7)):
        args=(cursor,0xC3,segment,3);calls.append((syms['func_15133EEC'],args))
        cursor=effect(case,m,args,sp-24,n,descriptor)
    m[read(m,sp+16)]=1
    return m,cursor,calls


class SegmentOracle(TimingOracle):
    def __init__(self,words,case,phase=0,entry=ENTRY,symbols=None,connected=None,memory=None):
        self.case,self.anchors=case,symbols or SYMBOLS;self.trace=[];self.ordinals=0
        descriptor,_=pointers(case,STACK+phase)
        super().__init__(words,fixture(case,phase)if memory is None else memory,phase=phase,entry=entry,
            arguments=(BUFFER+32,descriptor,case.unused2,case.unused3),connected=connected)

    def get(self,address,size):
        value=super().get(address,size)
        if self.own_instruction:self.trace.append(('R',address,size,value))
        return value

    def put(self,address,value,size):
        if self.recording and self.own_instruction:assert all(address+i in self.memory for i in range(size)),(address,size)
        super().put(address,value,size)
        if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))

    def record_call(self,target):
        if target in (ENTRY,FOLLOW):args=tuple(self.r[4:8])+(read(self.memory,self.r[29]+16),)
        else:args=tuple(self.r[4:8])
        self.calls.append((target,args));self.events.append(('CALL',target,args))

    def hook(self,target):
        args=self.calls[-1][1]
        if target==self.anchors['func_15133EEC']:
            descriptor=pointers(self.case,STACK+self.phase_value)[0]
            value=effect(self.case,self.memory,args,self.r[29],self.ordinals,descriptor);self.ordinals+=1
        elif target==FOLLOW:value=0x76543210
        else:raise AssertionError(('Unexpected provider',target))
        for register in (1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0x87654321,0x12345678
        self.r[2]=value


def native_harness(body,parent):
    return '#include <ultra64.h>\n'+source.DECLARATIONS+"""
typedef struct{u32 pre[4];Gfx commands[64],other[32];u8 descriptor[96],flag[16];u32 post[4];}State;
typedef char Width[(sizeof(void*)==4&&sizeof(Gfx)==8)?1:-1];
Gfx D_80083740[48],D_800838C0[48];
static State actual,expected,*active;
static u32 mode,number,logs[3][5],wanted[3][5],want_count;static u8 *description;
static u32 location(State *s,void *p){u32 v=(u32)p,b=(u32)s;
 if(v>=b&&v<b+sizeof(*s))return v-b+0x10000u;return v;}
static void call(State *s,u32 out[3][5],u32 n,void *p,u32 a,u32 b,u32 c,u32 d){
 out[n][0]=location(s,p);out[n][1]=a;out[n][2]=b;out[n][3]=c;out[n][4]=d;
}
static Gfx *change(State *s,Gfx *p,u16 resource,u8 segment,s32 kind,u32 n,u8 *desc){
 p->words.w0=0xD0600000u|segment;p->words.w1=(u32)resource<<8|(u32)kind;
 if(mode&1)*desc^=255;
 if(mode&2)return s->other+4+n*2;
 return p+1;
}
Gfx *func_15133EEC(Gfx *p,u16 resource,u8 segment,s32 kind){
 call(active,logs,number,p,resource,segment,(u32)kind,0);
 p=change(active,p,resource,segment,kind,number,description);number++;return p;
}
s32 func_15157F80(s32 p,s32 d,s32 a,s32 b,s32 f){
 call(active,logs,number,(void*)p,location(active,(void*)d),(u32)a,(u32)b,location(active,(void*)f));number++;return 0x76543210;
}
""" + body+'\n'+parent+"""
static int run(void){u32 alpha,m,f,alias,parent_mode,i,j;u8 *a=(u8*)&actual,*e=(u8*)&expected,*da,*de,*fa,*fe;Gfx *p,*want,*result;
 for(alpha=0;alpha<256;alpha++)for(m=0;m<4;m++)for(f=0;f<4;f++)for(alias=0;alias<2;alias++)for(parent_mode=0;parent_mode<2;parent_mode++){
  for(i=0;i<sizeof(actual);i++)a[i]=e[i]=0xA5;
  mode=m;number=0;want_count=0;active=&actual;
  da=alias?(u8*)&actual+__builtin_offsetof(State,commands)-9:actual.descriptor;
  de=alias?(u8*)&expected+__builtin_offsetof(State,commands)-9:expected.descriptor;
  da[0x43]=de[0x43]=(u8)alpha;description=da+0x43;
  fa=f==0?actual.flag:f==1?da+0x43:f==2?(u8*)(actual.commands+4)+2:actual.flag+1;
  fe=f==0?expected.flag:f==1?de+0x43:f==2?(u8*)(expected.commands+4)+2:expected.flag+1;
  for(i=0;i<3;i++)for(j=0;j<5;j++)logs[i][j]=wanted[i][j]=0;
  p=expected.commands+4;p->words.w0=0xDB060020u;p->words.w1=(u32)(alpha<255?D_80083740:D_800838C0);p++;
  for(i=0;i<2;i++){call(&expected,wanted,want_count,p,0xC3,6+i,3,0);p=change(&expected,p,0xC3,(u8)(6+i),3,want_count,de+0x43);want_count++;}
  *fe=1;want=p;
  if(parent_mode){call(&expected,wanted,want_count,p,location(&expected,de),0x80000000u|alpha,~alpha,location(&expected,fe));want_count++;}
  if(parent_mode){func_150FB1E8((s32)(actual.commands+4),(s32)da,(s32)(0x80000000u|alpha),(s32)~alpha,(s32)fa);result=0;}
  else result=func_151D710C(actual.commands+4,da,(s32)(0x80000000u|alpha),(s32)~alpha,fa);
  if((!parent_mode&&location(&actual,result)!=location(&expected,want))||number!=want_count)return 23;
  for(i=0;i<sizeof(actual);i++)if(a[i]!=e[i])return 23;
  for(i=0;i<3;i++)for(j=0;j<5;j++)if(logs[i][j]!=wanted[i][j])return 23;
 }return 0;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
"""


class SegmentBankPairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.installed=source.digest((ROOT/source.SOURCE).read_bytes())!=source.INPUTS[source.SOURCE]
        if cls.installed:source.audit(ROOT,cls.out)
        else:source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        cls.values=source.snapshot(cls.out);cls.rom=cls.values['conker/conker.us.bin']
        cls.obj,diag=source.compile_owner(ROOT,cls.out,'#include <ultra64.h>\n'+source.DECLARATIONS+source.SELECTED[NAME],'fresh-selected')
        if diag:raise ValueError(diag)
        text,fs=source.link_owner(ROOT,cls.out,cls.obj,source.OWNER);cls.words=list(struct.unpack_from('>40I',text,fs[NAME]['value']))
        cls.truth=list(struct.unpack_from('>40I',cls.rom,0x2045BC))
        caller=source.recovered_caller(cls.values[source.CALLER_SOURCE].decode());lo,hi=source.function_span(caller,'func_150FB1E8');cls.parent=caller[lo:hi]
        cls.receipt=dict(installed=cls.installed)

    @classmethod
    def tearDownClass(cls):
        (cls.out/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n');print(cls.receipt)

    def machine(self,code,case,phase=0,entry=ENTRY,symbols=None,connected=None,memory=None):
        model=SegmentOracle(code,case,phase,entry,symbols,connected,memory);model.phase_value=phase;return model

    def compare(self,case,phase=0,images=None,symbols=None,entry=ENTRY):
        m=fixture(case,phase);expected,result,calls=reference(case,m,phase,symbols)
        models=[self.machine(code,case,phase,entry,symbols).run()for code in images or (self.truth,self.words)]
        for model in models:self.assertEqual(model.memory,expected);self.assertEqual(model.r[2],result);self.assertEqual(model.calls,calls)
        self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(models[0].trace,models[1].trace)
        return models

    def test_01_direct_SDK_body_GNU_bindings_two_owners_and_alignment(self):
        self.assertEqual(self.words,self.truth)
        raw,bindings=source.payload(self.obj,NAME);self.assertEqual(source.payload(source.original(ROOT,self.out,NAME),NAME),(raw,bindings))
        self.assertEqual(bindings,{48:[('R_MIPS_HI16','D_80083740')],52:[('R_MIPS_LO16','D_80083740')],84:[('R_MIPS_HI16','D_800838C0')],88:[('R_MIPS_LO16','D_800838C0')],108:[('R_MIPS_26','func_15133EEC')],128:[('R_MIPS_26','func_15133EEC')]})
        q=json.loads((self.out/'qualification.json').read_text());self.assertEqual((q['total_words'],q['preserved_neighbors'],q['preserved_caller_functions']),(40,6,18))
        self.assertEqual(json.loads((self.out/'make-shadow.json').read_text())['actual_Make_commands'],6)
        old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,ENTRY,164)
        self.assertEqual(old[at+160:at+164],b'\0'*4)
        observed=self.machine(list(struct.unpack_from('>40I',old,at)),Case()).run()
        self.assertNotEqual(observed.memory,reference(Case(),fixture(Case()))[0])
        self.receipt.update(body_words=40,slot_words=41,frame=24,bindings=6,new_guards=0,neighbors=6,caller_functions=18,caller_object_identical=True)

    def test_02_all_alpha_bytes_returns_store_order_and_guest_homes(self):
        visits=set();count=0
        for alpha,mode,phase in itertools.product(range(256),(0,1,2,3,4,8),(0,8)):
            case=Case(alpha,mode);models=self.compare(case,phase);visits.update(models[0].visits);count+=1
            trace=models[0].trace
            self.assertEqual([x[:3]for x in trace[:4]],[('W',STACK+phase-4,4),('W',STACK+phase+8,4),('W',STACK+phase+12,4),('R',DESC+0x43,1)])
        self.assertEqual(visits,set(range(ENTRY,ENTRY+160,4)))
        aliases=0
        for alpha,mode,alias,phase in itertools.product((0,255),(0,1,2,4,8),range(1,7),(0,8)):
            self.compare(Case(alpha,mode,alias),phase);aliases+=1
        self.receipt.update(guest_phases=count,alias_phases=aliases,all40_body_words_visited=True,descriptor_read_before_commands=True,
                            full_unused_homes_and_late_fifth_pointer=True,guest_stack_aliases_not_portable_C_claim=True)

    def native(self,body,label,opt='-O2'):
        path=self.out/(label+opt+'.c');exe=path.with_suffix('.elf');path.write_text(native_harness(body,self.parent))
        p=subprocess.run(native_command(opt)+[str(path),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr);return subprocess.run([str(exe)],capture_output=True).returncode

    def test_03_native_actual_SDK_caller_legal_aliases_and_wrong_C(self):
        body=source.SELECTED[NAME]
        for opt in ('-O0','-O2','-O3'):self.assertEqual(self.native(body,'native',opt),0)
        controls=[('gate','< 0xFF','< 0xFE'),('bank','gSPSegment(commands++, 8, D_800838C0)','gSPSegment(commands++, 8, D_80083740)'),
            ('segment','commands++, 8','commands++, 9'),('resource','0xC3','0xC2'),('first','0xC3, 6','0xC3, 5'),
            ('second','0xC3, 7','0xC3, 8'),('mode','6, 3','6, 2'),('flag','*changed = 1','*changed = 0')]
        for label,a,b in controls:self.assertNotEqual(body.replace(a,b),body);self.assertEqual(self.native(body.replace(a,b),'wrong-'+label),23,label)
        self.receipt.update(native_cases_per_optimization=256*4*4*2*2,native_optimizations=3,trap_UBSan=True,
                            actual_SDK_and_C_caller=True,typed_arrays_and_character_aliases=True,effective_wrong_C_controls=8)

    def test_04_complete_current_and_original_caller_five_arguments(self):
        parent=list(struct.unpack_from('>22I',self.rom,0x128698));before=self.values['conker/build/conker.us.elf']
        at=source.elf_slot_offset(before,CALLER,88);self.assertEqual(list(struct.unpack_from('>22I',before,at)),parent)
        visits=set();count=0
        for alpha,mode,phase in itertools.product((0,254,255),(0,1,2,4),(0,8)):
            case=Case(alpha,mode);models=[]
            for code in (self.truth,self.words):
                m=fixture(case,phase);connected=dict(zip(range(ENTRY,ENTRY+160,4),code))
                model=self.machine(parent,case,phase,CALLER,connected=connected,memory=m).run()
                self.assertEqual(model.calls[0],(ENTRY,(BUFFER+32,DESC,case.unused2,case.unused3,FLAG)))
                self.assertEqual(model.calls[-1],(FOLLOW,(model.calls[-2][1][0]+(16 if mode&4 else 8)if not mode&2 else OTHER+48,DESC,case.unused2,case.unused3,FLAG)))
                self.assertEqual(model.memory[FLAG],1);models.append(model);visits.update(model.visits)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.assertTrue(set(range(CALLER,CALLER+88,4))<=visits)
        self.receipt.update(complete_caller_words=22,caller_phases=count,all_five_arguments_and_forwarded_cursor=True,opaque_follow_provider_only=True)

    def test_05_independent_GNU_symbol_rebases(self):
        from tools.experiments.alternative_source_draft_word_screen import emit_function
        original=source.original(ROOT,self.out,NAME);links=count=0
        for i in range(3):
            entry=0x17007FFC+i*0x10000;syms=dict(D_80083740=0x80208000+i*0x10000,D_800838C0=0x8030FFFC+i*0x20000,func_15133EEC=0x17203000+i*0x1000);images=[]
            for label,obj in [('original',original),('C',self.obj)]:
                text,fs,rs=source.parse_object(obj);assembly,unknown=emit_function(text,fs[NAME],rs,NAME,syms);self.assertFalse(unknown)
                stem=self.out/('rebase-%d-%s'%(i,label));asm=stem.with_suffix('.s');out=stem.with_suffix('.o');ld=stem.with_suffix('.ld');elf=stem.with_suffix('.elf')
                asm.write_text(assembly);ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(out),str(asm)],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',NAME,*['--defsym=%s=0x%X'%p for p in syms.items()],'-o',str(elf),str(out)],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>40I',sections(elf)['.text'][1])));links+=1
            self.assertEqual(images[0],images[1])
            for alpha,mode,phase in itertools.product((0,254,255),(0,1,2,4),(0,8)):self.compare(Case(alpha,mode),phase,images,syms,entry);count+=1
        self.receipt.update(independent_GNU_links=links,rebase_phases=count,all6_bindings_and_signed_low_carries=True)

    def test_06_original59word_helper_with_bounded_decoder(self):
        helper=list(struct.unpack_from('>59I',self.rom,0x16139C));visits=set();count=0
        for alpha,flag,second,length,phase in itertools.product((0,255),(0,2),(0,1),(0,0x20,0x200,0xFFFFFFFF),(0,8)):
            models=[]
            for code in (self.truth,self.words):
                case=Case(alpha);m=fixture(case,phase);table=0x80090B60+0xC3*12
                put(m,table,0x60000);m[table+10]=flag;m[table+11]=second;put(m,0x60000,0x70000)
                connected=dict(zip(range(HELPER,HELPER+236,4),helper));connected.update(zip(range(ENTRY,ENTRY+160,4),code))
                model=self.machine(code,case,phase,connected=connected,memory=m)
                decoded=[]
                def decoder(target):
                    self.assertEqual(target,DECODE);args=model.calls[-1][1];self.assertEqual((args[0],args[2],args[3]),(0x70000,3,0))
                    put(model.memory,args[1],length);decoded.append(args)
                    for reg in (1,2,3,*range(4,16),24,25):model.r[reg]=0xA5000000+reg
                    model.f[:20]=[0xA5000000+i for i in range(20)];model.r[2]=0x12340000
                model.hook=decoder;model.run();self.assertEqual(len(decoded),2)
                cursor=BUFFER+40
                for seg in (6,7):
                    self.assertEqual((read(model.memory,cursor),read(model.memory,cursor+4)),(0xDB060000|seg*4,0x12340000));cursor+=8
                    if flag==2:
                        self.assertEqual((read(model.memory,cursor),read(model.memory,cursor+4)),(0xDB060000|(seg*4+4),(0x12340000+length-(0x200 if second==1 else 0x20))&0xFFFFFFFF));cursor+=8
                self.assertEqual(model.r[2],cursor);self.assertEqual(model.memory[FLAG],1);visits.update(model.visits);models.append(model)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.assertTrue(set(range(HELPER,HELPER+236,4))<=visits)
        self.receipt.update(original_helper_words=59,connected_helper_phases=count,all59_words_visited=True,decoder_implementation_or_gameplay_claimed=False)

    def test_07_fired_root_fault_prefixes(self):
        count=0
        for alpha,mode,phase in itertools.product((0,255),(0,1,2,4,8),(0,8)):
            case=Case(alpha,mode);good=self.machine(self.truth,case,phase).run()
            for cut in range(good.root_accesses):
                models=[self.machine(code,case,phase)for code in (self.truth,self.words)]
                for model in models:model.root_fault=cut
                for model in models:
                    with self.assertRaises(faults.AccessBoundary):model.run()
                self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(models[0].trace,models[1].trace)
                self.assertEqual((models[0].current_pc,models[0].delay_of),(models[1].current_pc,models[1].delay_of));count+=1
        self.assertGreater(count,100)
        self.receipt.update(fired_root_fault_prefixes=count,portable_fault_or_MMU_claimed=False)

    def test_08_strict_image_29_inputs_old_objects_and_corruptions(self):
        before=self.values['conker/build/conker.us.elf'];expected=source.predicted_image(before,self.rom)
        self.assertEqual(expected,(self.out/'first-linked.elf').read_bytes());at=source.elf_slot_offset(before,ENTRY,164)
        sym=next(pos for pos,n,f,_ in source.symbol_rows(before)if n==NAME and f[1:3]==(ENTRY,12))
        for pos in (0,len(expected)-1,at,at+159,at+160,sym+8):
            bad=bytearray(expected);bad[pos]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),self.rom)
        with self.assertRaises(ValueError):source.check_image(before,expected[:-1],self.rom)
        for name,old in self.values.items():
            self.assertEqual(source.digest(old),source.INPUTS[name])
            current=source.recovered_owner(old.decode()).encode()if self.installed and name==source.SOURCE else source.recovered_caller(old.decode()).encode()if self.installed and name==source.CALLER_SOURCE else expected if self.installed and name=='conker/build/conker.us.elf'else old
            self.assertEqual((ROOT/name).read_bytes(),current)
        self.assertEqual(source.digest((self.out/'before-padded.o').read_bytes()),source.BEFORE_OBJECT_SHA)
        self.assertEqual(source.digest((self.out/'before-caller-padded.o').read_bytes()),source.BEFORE_CALLER_OBJECT_SHA)
        self.receipt.update(strict_image_corruptions_rejected=7,live_and_historical_inputs=29,both_old_objects_pinned=True,alignment_bytes_preserved=4,guard_manifest_unchanged=True)


if __name__=='__main__':
    unittest.main()
