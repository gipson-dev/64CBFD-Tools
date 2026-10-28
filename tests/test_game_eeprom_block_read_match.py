"""EEPROM block reader: byte loops, provider lifetime, callers and literal image."""
from dataclasses import dataclass,replace
from pathlib import Path
import itertools,json,os,re,struct,subprocess,unittest
from tools.experiments import game_eeprom_block_read_match as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import signed
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2];QUEUE,BUFFER=0x22000,0x30000
@dataclass(frozen=True)
class Case:
    address:int=254
    length:int=17
    busy:int=2
    fail:int=-1
    status:int=0x81234567
    phase:int=0
    layout:int=0
    mutation:bool=False

def addresses(c,stack=None):
    sp=STACK+c.phase if stack is None else stack
    return QUEUE,(BUFFER,sp,sp-48,QUEUE+4)[c.layout],sp

def fixture(c,queue=None,buffer=None,stack=None):
    q,b,sp=addresses(c,stack);q=q if queue is None else queue;b=b if buffer is None else buffer
    m={STACK+i:(i*17+0xA5)&255 for i in range(-512,512)}
    for base,size in((q,32),(b,2112)):
        if not STACK-512<=base<STACK+512:m.update({base+i:(i*13+0x59)&255 for i in range(-16,size+16)})
    return m,(q,c.address&0xFFFFFFFF,b,c.length&0xFFFFFFFF),sp

def public(m):return{a:b for a,b in m.items()if not STACK-512<=a<STACK+512}
def provider_effect(m,c,q,b,index,address,status,sp):
    if index>=0:
        for j in range(3 if status else 8):m[(b+j)&0xFFFFFFFF]=(address*17+index*11+j)&255
    if c.mutation:
        put(m,q,(read(m,q)+1)&0xFFFFFFFF);put(m,sp+4,0xD00D00FF)

def reference(initial,c,args,sp):
    m=dict(initial);q,address,b,remaining=args;address&=255;remaining=signed(remaining);calls=[]
    for i in range(c.busy+1):
        calls.append((source.POLL,(1,)));provider_effect(m,c,q,b,-1,address,0,sp)
    index=0;result=0
    while remaining>0:
        calls.append((source.READ,(q,address,b)));result=c.status&0xFFFFFFFF if index==c.fail else 0
        provider_effect(m,c,q,b,index,address,result,sp)
        if result:break
        remaining-=8;address=(address+1)&255;b=(b+8)&0xFFFFFFFF;index+=1
        assert index<300
    return m,result,calls

class EepromOracle(RayOracle):
    def __init__(self,words,memory,c=Case(),entry=source.ENTRY,arguments=None,connected=None,poll=source.POLL,reader=source.READ):
        q,b,sp=addresses(c);args=arguments or(q,c.address&0xFFFFFFFF,b,c.length&0xFFFFFFFF)
        TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=args,connected=connected)
        self.case,self.trace,self.polls,self.block_reads=c,[],0,0;self.poll,self.reader=poll,reader
        self.target_sp=sp;self.target_arguments=args;self.provider_saved=[]
    def get(self,address,size):
        v=super().get(address,size)
        if self.own_instruction:self.trace.append(('R',address,size,v))
        return v
    def put(self,address,value,size):
        super().put(address,value,size)
        if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
    def record_call(self,target):
        assert target in(source.ENTRY,self.poll,self.reader),hex(target)
        if target==source.ENTRY:self.target_sp=self.r[29];self.target_arguments=self.arguments(4)
        a=self.arguments(4 if target==source.ENTRY else 1 if target==self.poll else 3);self.calls.append((target,a));self.events.append(('CALL',target,a))
    def hook(self,target):
        c=self.case;q,address,b,remaining=self.target_arguments;index=self.block_reads
        expected=(remaining&0xFFFFFFFF,address&255,b,0,q)
        if target==self.reader:
            expected=((remaining-index*8)&0xFFFFFFFF,(address+index)&255,(b+index*8)&0xFFFFFFFF,0,q)
            assert self.arguments(3)==(q,(address+index)&255,(b+index*8)&0xFFFFFFFF)
            result=c.status&0xFFFFFFFF if index==c.fail else 0
            provider_effect(self.memory,c,q,(b+index*8)&0xFFFFFFFF,index,(address+index)&255,result,self.target_sp);self.block_reads+=1
        else:
            assert target==self.poll and self.arguments(1)==(1,)
            result=(0xB0000000+self.polls)&0xFFFFFFFF if self.polls<c.busy else 0
            provider_effect(self.memory,c,q,b,-1,address&255,0,self.target_sp);self.polls+=1
        assert tuple(self.r[16:21])==expected,(self.r[16:21],expected)
        self.provider_saved.append(tuple(self.r[16:21]))
        assert self.block_reads<300 and self.polls<8
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=result;self.hi,self.lo=0xA5000010,0xA5000011

class WindowBoundary(Exception):pass
class WindowCode(faults.TrackedCode):
    def __getitem__(self,pc):
        if pc==self.owner.window_end:raise WindowBoundary
        return super().__getitem__(pc)

def controls():
    b=source.SELECTED
    return dict(skip_empty_poll=b.replace('    while (func_151DCFD8(1) != 0)', '    if (remaining <= 0) return 0;\n    while (func_151DCFD8(1) != 0)'),
        wrong_poll_flag=b.replace('func_151DCFD8(1)','func_151DCFD8(0)'),poll_once=b.replace('    while (func_151DCFD8(1) != 0) {\n    }','    func_151DCFD8(1);'),
        normalized_error=b.replace('            return result;','            return -1;'),ignored_error=b.replace('            return result;','            result = 0;'),
        wrong_address=b.replace('address++;','address += 2;'),wrong_buffer=b.replace('buffer += 8;','buffer += 4;'),
        wrong_length=b.replace('remaining -= 8;','remaining -= 4;'),round_down=b.replace('while (remaining > 0)','while (remaining >= 8)'),
        false_result=b.replace('    return result;\n}','    return 7;\n}'))

def native_harness():
    t=source.HEADERS+source.DECLARATIONS+r'''
typedef char ABI[(sizeof(void*)==4&&sizeof(s32)==4&&sizeof(u8)==1)?1:-1];
static OSMesgQueue queue;static u8 storage[2144],expected[2144];static u8*base;static u32 pcalls,rcalls,wrong,seedAddress;static s32 busy,failAt,errorStatus;
s32 func_151DCFD8(s32 flag){u32 n=pcalls++;if(flag!=1)wrong=1;queue.validCount++;return n<(u32)busy?7:0;}
s32 func_151DD140(OSMesgQueue*q,u8 address,u8*buffer){u32 n=rcalls++,j;s32 status=(s32)n==failAt?errorStatus:0;if(q!=&queue||address!=(u8)(seedAddress+n)||buffer!=base+n*8)wrong=1;queue.validCount++;if(rcalls>520){wrong=1;return 99;}for(j=0;j<(status?3u:8u);j++)buffer[j]=(u8)(address*17+n*11+j);return status;}
'''
    for name,b in dict(selected=source.SELECTED,**controls()).items():t+=b.replace('s32 '+source.FUNCTION,'static s32 '+name)+'\n'
    t+=r'''
typedef s32(*Read)(OSMesgQueue*,u8,u8*,s32);
static int check(Read fn){const s32 lengths[]={(-2147483647-1),-1,0,1,7,8,9,15,16,17,63,64,65,112,128,2057};const s32 statuses[]={8,-1,0x12345678};u32 a,l,b,f,offset,i,j,n,wantPoll,wantReads;s32 want,result;
 for(a=0;a<256;a++)for(l=0;l<16;l++)for(b=0;b<2;b++)for(f=0;f<3;f++)for(offset=0;offset<2;offset++){
  for(i=0;i<2144;i++)storage[i]=expected[i]=(u8)(i*13+0x59);
  base=storage+16+offset;seedAddress=a;busy=(s32)(b*3);failAt=f==0?-1:f==1?0:1;errorStatus=statuses[(a+l)%3];pcalls=rcalls=wrong=0;queue.validCount=0;
  n=lengths[l]>0?((u32)lengths[l]+7)/8:0;wantReads=failAt>=0&&(u32)failAt<n?(u32)failAt+1:n;want=failAt>=0&&(u32)failAt<n?errorStatus:0;wantPoll=(u32)busy+1;
  for(i=0;i<wantReads;i++)for(j=0;j<(failAt==(s32)i?3u:8u);j++)expected[16+offset+i*8+j]=(u8)((u8)(a+i)*17+i*11+j);
  result=fn(&queue,(u8)a,base,lengths[l]);if(wrong||result!=want||pcalls!=wantPoll||rcalls!=wantReads||queue.validCount!=(s32)(wantPoll+wantReads))return 1;
  for(i=0;i<2144;i++)if(storage[i]!=expected[i])return 1;
 }return 0;}
static int run(void){if(check(selected))return 10;
'''
    for i,name in enumerate(controls()):t+='if(!check('+name+'))return '+str(20+i)+';\n'
    return t+'return 0;}\n'+START

class EepromBlockReadTests(unittest.TestCase):
    receipt={}
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>45I',cls.rom,source.ROM));local=cls.fresh/'qualified-padded.o';local.write_bytes((cls.out/'qualified-padded.o').read_bytes());data,functions=source.link_owner(ROOT,cls.fresh,local,source.OWNER);cls.words=list(struct.unpack_from('>45I',data,functions[source.FUNCTION]['value']))
    @classmethod
    def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
    def compare(self,c=Case(),images=None,entry=source.ENTRY,poll=source.POLL,reader=source.READ):
        initial,args,sp=fixture(c);want,result,calls=reference(initial,c,args,sp);pair=[]
        translated=[(poll if t==source.POLL else reader,a)for t,a in calls]
        for words in images or(self.truth,self.words):
            m=EepromOracle(words,initial,c,entry,args,poll=poll,reader=reader).run();self.assertEqual((public(m.memory),m.r[2],m.calls),(public(want),result,translated),c);self.assertEqual(m.r[29],sp);pair.append(m)
        self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);return pair[0]
    def linked(self,entry,poll,reader):
        if not hasattr(self,'links'):self.links={}
        key=(entry,poll,reader)
        if key in self.links:return self.links[key]
        pair=[];number=len(self.links)
        for j,obj in enumerate((self.out/('original-'+source.FUNCTION+'.o'),self.out/'selected.o')):
            p=self.fresh/('layout-%d-%d.ld'%(number,j));elf=p.with_suffix('.elf');p.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p),'-e',source.FUNCTION,'--defsym=func_151DCFD8=0x%X'%poll,'--defsym=func_151DD140=0x%X'%reader,'-o',str(elf),str(obj)],capture_output=True,check=True);pair.append(list(struct.unpack_from('>45I',sections(elf)['.text'][1])))
        self.assertEqual(*pair);self.links[key]=pair;return pair
    def test_01_owner_Make_bindings_types_and_original_caller_census(self):
        self.assertEqual(self.words,self.truth);source.checked_payload(*source.payload(self.out/'selected.o'));self.assertEqual(self.rom[source.ROM+source.BODY:source.ROM+source.SIZE],bytes(12))
        for label in('before','after'):
            obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),1)
        self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),0);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'));self.assertEqual(source.same_functions(self.out/'after-owner.o',self.out/'make-shadow/src/game/generated_20A850.c.o.compact'),1)
        self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()),(self.out/'proposed-owner.c').read_text());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3)
        ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);jal=0x0C000000|(source.ENTRY>>2&0x3FFFFFF);self.assertEqual([i*4 for i,w in enumerate(ws)if w==jal],[0x33B04,0x34748,0x3490C]);self.assertFalse(any(w==source.ENTRY for w in ws))
        callers=self.values['conker/src/game_33990.c'].decode()
        for n in('func_15006590','func_1500727C','func_15007440'):self.assertIn('s32 '+n+'() {\n    return 0;\n}',callers)
        self.assertIn('s32 func_151DCFD8() {\n    return 0;\n}',self.values['conker/src/game/generated_20A3A0.c'].decode());self.assertIn('osEepromLongRead(OSMesgQueue *',self.values['conker/include/2.0L/PR/os_eeprom.h'].decode())
        if self.installed:source.audit(ROOT,self.out)
        self.receipt['owner']=dict(words=45,slot_words=48,alignment_words=3,frame=48,bindings=3,guards=0,neighbors=0,compact_functions=1,GLOBAL_ASM_routines=0,Make_commands=3,diagnostics=0,three_original_JALs_not_current_caller_recovery=True,queue_pointer_u8_address_buffer_pointer_signed32_length=True)
    def test_02_guest_lengths_bytes_errors_capture_and_wrap(self):
        count=0;visits=set()
        for address,length,busy in itertools.product(range(256),(-1,0,1,7,8,9,16,17,65),(0,3)):
            m=self.compare(Case(address=address|0xA5A50000,length=length,busy=busy,phase=(address&1)*8,mutation=True));visits.update(m.visits);count+=1
        for length,busy,fail,status in itertools.product((-2147483648,2147483647,1,9,17,2057),(0,2),(0,1),(8,0xFFFFFFFF,0x81234567)):
            m=self.compare(Case(length=length,busy=busy,fail=fail if length!=2147483647 or fail==0 else 0,status=status,mutation=True));visits.update(m.visits);count+=1
        for layout,length,phase,mutation in itertools.product((1,2,3),(1,9),(0,8),(False,True)):
            self.compare(Case(layout=layout,length=length,phase=phase,mutation=mutation));count+=1
        self.compare(Case(length=2057,address=255));count+=1
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+source.BODY,4)))
        self.receipt['guest']=dict(cases=count,all256_addresses_and_wrap=True,signed_min_max_and_positive_partial_blocks=True,busy_poll_even_empty=True,exact_early_error_status=True,all45_words_visited=True,provider_clobbers_and_saved_lifetime=True,incoming_home_capture=True,guest_stack_and_queue_aliases=True,full_private_state_trace=True,bounded_providers_not_EEPROM_hardware=True)
    def test_03_three_actual_original_call_windows(self):
        specs=((0x15006634,0x33AE4,12,0x15006664,4,0x800BE358,128),(0x1500727C,0x3472C,11,0x150072A8,0x44,0x800BE2F0,112),(0x15007440,0x348F0,12,0x15007470,0,0x800BE358,32));count=0
        for va,rom,n,end,address,buffer,length in specs:
            parent=list(struct.unpack_from('>%dI'%n,self.rom,rom));name='func_15006590'if va==0x15006634 else'func_%08X'%va;asm=self.values['conker/asm/nonmatchings/game_33990/'+name+'.s'].decode();literal={int(a,16):int(w,16)for a,w in re.findall(r'/\*\s*[0-9A-F]+\s+([0-9A-F]+)\s+([0-9A-F]{8})\s*\*/',asm)};self.assertEqual(parent,[literal[va+i*4]for i in range(n)])
            for busy,fail in itertools.product((0,2),(-1,0,1)):
                c=Case(address=address,length=length,busy=busy,fail=fail,mutation=True);sp=STACK if va==0x15006634 else STACK-24;initial,args,_=fixture(c,0x800BE900,buffer,sp);put(initial,STACK+0xB0,0);models=[]
                want,result,calls=reference(initial,c,(0x800BE900,address,buffer,length),sp)
                for words in(self.truth,self.words):
                    m=EepromOracle(parent,initial,c,va,connected={source.ENTRY+4*i:w for i,w in enumerate(words)});m.r[16]=buffer;m.window_end=end;m.code=WindowCode(dict(m.code),m)
                    with self.assertRaises(WindowBoundary):m.run()
                    self.assertEqual(m.calls,[(source.ENTRY,(0x800BE900,address,buffer,length))]+calls);self.assertEqual(public(m.memory),public(want));self.assertEqual(m.r[2],m.memory[buffer+2]if va==0x1500727C else 0xCC);models.append(m)
                self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(models[0].trace,models[1].trace);count+=1
        self.receipt['callers']=dict(original_windows=3,mapped_words=[12,11,12],cases=count,queue_address_buffer_and_lengths_128_112_32=True,all_ignore_provider_status=True,current_three_callers_still_placeholders=True,no_full_checksum_or_save_device_acceptance=True)
    def test_04_native32_actual_C_complete_blocks_fences_and_controls(self):
        for opt in('-O0','-O2','-O3'):
            p=self.fresh/('native-'+opt[1:]+'.c');p.write_text(native_harness());binary=p.with_suffix('');q=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);p.with_suffix('.diagnostics.txt').write_text(q.stdout+q.stderr);self.assertEqual(q.returncode,0,q.stdout+q.stderr);self.assertEqual(subprocess.run([str(binary)],timeout=45).returncode,0,opt)
        self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_each_profile=256*16*2*3*2,effective_controls=len(controls()),trapping_UBSan=True,valid_storage_and_two_offsets=True,complete_storage_fences=True,address_wrap_and_signed_length_and_partial_blocks=True,no_guest_wrapping_pointer_or_hardware_claim=True)
    def test_05_fired_access_prefixes_and_sparse_empty_inputs(self):
        cuts=0
        for length,busy,fail,phase in itertools.product((0,1,9,17),(0,2),(-1,0),(0,8)):
            c=Case(length=length,busy=busy,fail=fail,phase=phase,mutation=True);initial,_,_=fixture(c);good=self.compare(c)
            for cut in range(good.root_accesses):
                pair=[]
                for words in(self.truth,self.words):
                    m=EepromOracle(words,initial,c);m.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    self.assertEqual(m.root_accesses,cut);pair.append(m)
                self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));cuts+=1
        for length in(0,-1,-2147483648):
            c=Case(length=length);initial,args,_=fixture(c);initial={a:b for a,b in initial.items()if STACK-512<=a<STACK+512}
            for words in(self.truth,self.words):m=EepromOracle(words,initial,c).run();self.assertEqual((m.r[2],m.polls,m.block_reads),(0,3,0))
        self.receipt['faults']=dict(fired_prefix_pairs=cuts,full_private_state_trace_PC_delay=True,empty_inputs_need_no_buffer_or_queue_mapping_but_still_poll=True,not_hardware_EPC_acceptance=True)
    def test_06_actual_padder_and_three_independent_GNU_layouts(self):
        raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'));bad=bytearray(raw);bad[100]^=1
        for b,bindings in((raw[:-4],rs),(bytes(bad),rs),(raw,{52:[('R_MIPS_26','wrong')],68:rs[68],96:rs[96]})):
            with self.assertRaises(ValueError):source.checked_payload(b,bindings)
        p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=ROOT/'conker/retail_word_patches.us.csv',filename=source.OWNER));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes());cases=0
        for entry,poll,reader in((source.ENTRY,source.POLL,source.READ),(0x17007FFC,0x1701FFFC,0x17020004),(0x2500FFFC,0x25F08000,0x25120000)):
            images=self.linked(entry,poll,reader)
            for length,fail in itertools.product((0,1,9,65),(-1,0)):
                self.compare(Case(length=length,fail=fail),images,entry,poll,reader);cases+=1
        self.receipt['rebases']=dict(layouts=3,guest_cases=cases,three_J26_bindings=True,GNU_original_and_compiled_objects=True,raw_corruption_controls=3,alignment_nops=3,guards=0)
    def test_07_actually_compiled_wrong_C_rejected_by_call_sequence(self):
        obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+controls()['skip_empty_poll'],'negative-skip-empty');self.assertFalse(diag);p=self.fresh/'negative.ld';elf=p.with_suffix('.elf');p.write_text('SECTIONS { .text 0x151DD3A0 : SUBALIGN(4) { *(.text) } }\n');subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p),'-e',source.FUNCTION,'--defsym=func_151DCFD8=0x151DCFD8','--defsym=func_151DD140=0x151DD140','-o',str(elf),str(obj)],capture_output=True,check=True);raw=sections(elf)['.text'][1];words=list(struct.unpack('>%dI'%(len(raw)//4),raw));c=Case(length=0);m=EepromOracle(words,fixture(c)[0],c).run();self.assertEqual(m.calls,[]);self.assertEqual(self.compare(c).polls,3);self.receipt['compiled_control']=dict(actually_compiled_skip_empty_rejected=True,call_sequence_failure_not_unmapped_read=True)
    def test_08_strict_entire_image_metadata_and_corruptions(self):
        v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=v['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,source.SIZE);symbol=next(p for p,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8
        for offset in(20,at,at+180,at+192,source.elf_slot_offset(before,0x80082B20,4),symbol):
            bad=bytearray(expected);bad[offset]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        self.assertEqual(sum(x!=y for x,y in zip(before,expected)),137);self.receipt['image']=dict(changed_bytes=137,code_bytes=136,metadata_bytes=1,body_extent_180_separate_from_slot192=True,other6055_bodies_and6056_addresses_fixed=True,protected_owners=720,protected_bytes=189088,exclusions=0,effective_corruptions=6,guards_shared_headers_helpers_and_callers_unchanged=True)
