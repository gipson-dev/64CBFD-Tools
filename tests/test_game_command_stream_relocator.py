"""Signed SDK stream relocation, cursor normalization and bounded retail call windows."""
import csv,io,itertools,json,struct,subprocess,unittest
from pathlib import Path
from tools.experiments import game_command_stream_relocator as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_projected_packet_draw import native_command

ROOT=Path(__file__).resolve().parents[2]
ENTRY,BASE,HEADER,CELL,BANK=0x150049A4,0x20000,0x30000,0x32000,0x34000
WORDS=(0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0x87654321)
OFFSETS=((0,0),(1,0xFFFFFFFF),(0xFFFFFFFF,1),(0x7FFFFFFF,0x80000000),(0x80000000,0x7FFFFFFF),(0x87654321,0x12345678))
SAVED=0x13579BDF


def signed_byte(value):
    return value if value<128 else value-256


def fixture(opcode=1,tag=14,payload=0xFFFFFFFF,count=1,phase=0,base=BASE):
    m={STACK+phase+i:(i*17+0xA5)&255 for i in range(-0x1200,0x300)}
    for i in range(-16,(count+5)*8+16):m[(base+i)&0xFFFFFFFF]=0xA5
    for i in range(count):
        at=(base+i*8)&0xFFFFFFFF
        m[at]=opcode if i==0 else (1,0xDC,0xDE,0xDC,0)[(i-1)%5]
        m[at+3]=tag if i==0 else (14 if i%2 else 255)
        put(m,at+4,(payload+i*0x1234567)&0xFFFFFFFF)
    for i,op in ((count,0xDF),(count+1,1),(count+2,0xDE),(count+3,0xDF)):
        at=(base+i*8)&0xFFFFFFFF;m[at]=op;m[at+3]=14;put(m,at+4,payload)
    return m


def reference(memory,args,sp=STACK,flip=None,saved=SAVED):
    m=dict(memory);base,data,matrix=args;trace=[];head_reads=0
    def rd(a,n=4):
        nonlocal head_reads
        v=read(m,a,n);trace.append(('R',a,n,v))
        if a==base and n==1:
            if head_reads==0 and flip is not None:m[a]=flip
            head_reads+=1
        return v
    def wr(a,v,n=4):
        put(m,a,v,n);trace.append(('W',a,n,v&((1<<(8*n))-1)))
    wr(sp-4,saved);count=0;cursor=base
    if signed_byte(rd(base,1))!=-33:
        opcode=signed_byte(rd(base,1))
        while True:
            count+=1
            if opcode==-36:
                if rd(cursor+3,1)==14:wr(cursor+4,(rd(cursor+4)+matrix)&0xFFFFFFFF)
            elif opcode in (1,0xDE):wr(cursor+4,(rd(cursor+4)+data)&0xFFFFFFFF)
            cursor=(base+count*8)&0xFFFFFFFF;opcode=signed_byte(rd(cursor,1))
            if opcode==-33:break
            if count>512:raise AssertionError('Unterminated reference fixture')
    rd(sp-4)
    return m,count,trace


class WindowEnd(Exception):
    pass


class StopCode(faults.TrackedCode):
    def __init__(self,values,owner,stop):
        super().__init__(values,owner);self.stop=stop
    def __getitem__(self,pc):
        if pc==self.stop:raise WindowEnd
        return super().__getitem__(pc)


class RelocateOracle(TimingOracle):
    def __init__(self,words,memory,args,phase=0,entry=ENTRY,connected=None,base=None,flip=None,leaf_entry=None):
        self.trace=[];self.base=args[0]if base is None else base;self.flip=flip;self.header_reads=0
        self.leaf_entry=entry if leaf_entry is None else leaf_entry
        super().__init__(words,memory,phase=phase,entry=entry,arguments=args,connected=connected)
        self.r[16]=self.before[16]=SAVED
    def in_leaf(self):
        return self.own_instruction and self.leaf_entry<=self.current_pc<self.leaf_entry+168
    def get(self,address,size):
        v=super().get(address,size)
        if self.in_leaf():
            self.trace.append(('R',address,size,v))
            if address==self.base and size==1:
                if self.header_reads==0 and self.flip is not None:
                    self.memory[address]=self.flip;self.events.append(('HEADER_FLIP',address,self.flip))
                self.header_reads+=1
        return v
    def put(self,address,value,size):
        super().put(address,value,size)
        if self.recording and self.in_leaf():self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
    def execute(self,word):
        if word>>26==32:
            self.dispatched_word=word;self.own_instruction=True
            try:
                rs,rt,imm=word>>21&31,word>>16&31,word&65535
                address=(self.r[rs]+(imm if imm<32768 else imm-65536))&0xFFFFFFFF
                self.r[rt]=signed_byte(self.get(address,1))&0xFFFFFFFF;self.r[0]=0
            finally:self.own_instruction=False
        else:super().execute(word)
    def record_call(self,target):
        assert target==ENTRY,hex(target)
        args=self.arguments(3);self.calls.append((target,args));self.events.append(('CALL',target,args))
    def hook(self,target):
        raise AssertionError(('Unexpected external provider',hex(target)))


def native_harness(bodies,runner):
    return '#include <ultra64.h>\n'+r'''
typedef union{u32 words[2];u8 bytes[8];}Packet;
typedef struct{u32 before[4];Packet list[36];u32 after[4];}Arena;
typedef char Width[(sizeof(void*)==4&&sizeof(s32)==4&&sizeof(Packet)==8)?1:-1];
static Arena arena,expected;
'''+bodies+r'''
static int runVariant(void(*target)(s8*,u32,u32)){
 const u32 words[]={0,1,0x7FFFFFFFu,0xFFFFFFFFu};
 const u32 offsets[][2]={{0,0},{1,0xFFFFFFFFu},{0xFFFFFFFFu,1},{0x7FFFFFFFu,0x80000000u},{0x80000000u,0x7FFFFFFFu},{0x87654321u,0x12345678u}};
 const u8 tags[]={0,13,14,255};const u32 lengths[]={0,1,7};
 u32 op,t,p,k,n,i,j,code,count=0;u8*a=(u8*)&arena,*b=(u8*)&expected;
 for(op=0;op<256;op++)for(t=0;t<4;t++)for(p=0;p<4;p++)for(k=0;k<6;k++)for(n=0;n<3;n++){
  for(i=0;i<sizeof(Arena);i++)a[i]=(u8)(i*13+0xA5);
  for(i=0;i<lengths[n];i++){
   arena.list[i].bytes[0]=i?((i%3)==0?0xDC:(i%3)==1?1:0xDE):(u8)op;
   arena.list[i].bytes[3]=i?(i%2?14:255):tags[t];
   arena.list[i].words[1]=words[p]+i*0x1234567u;
  }
  arena.list[lengths[n]].bytes[0]=0xDF;
  arena.list[lengths[n]+1].bytes[0]=1;arena.list[lengths[n]+1].words[1]=words[p];
  arena.list[lengths[n]+2].bytes[0]=0xDE;
  arena.list[lengths[n]+3].bytes[0]=0xDF;
  for(i=0;i<sizeof(Arena);i++)b[i]=a[i];
  for(i=0;i<36;i++){
   code=expected.list[i].bytes[0];if(code==0xDF)break;
   if(code==1)expected.list[i].words[1]+=offsets[k][0];
   else if(code==0xDC&&expected.list[i].bytes[3]==14)expected.list[i].words[1]+=offsets[k][1];
  }
  target((s8*)arena.list,offsets[k][0],offsets[k][1]);
  for(j=0;j<sizeof(Arena);j++)if(a[j]!=b[j])return 23;count++;
 }
 return count==73728u?0:24;
}
'''+runner+r'''
void _start(void){int code=run();__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
'''


class CommandStreamRelocatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.out.mkdir(parents=True,exist_ok=True);cls.values=source.snapshot(cls.out)
        cls.installed=(ROOT/source.SOURCE).read_text()==source.recovered_owner(cls.values[source.SOURCE].decode())
        if cls.installed:source.audit(ROOT,cls.out)
        else:source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>42I',cls.rom,0x31E54))
        cls.obj,diag=source.compile_owner(ROOT,cls.out,'#include <ultra64.h>\n'+source.SELECTED[source.FUNCTIONS[0]],'fresh-selected')
        if diag:raise ValueError(diag)
        raw,bindings=source.payload(cls.obj,source.FUNCTIONS[0]);fitted,_=source.normalized(raw,bindings)
        cls.raw=list(struct.unpack('>42I',raw));cls.fitted=list(struct.unpack('>42I',fitted));cls.receipt=dict(installed=cls.installed)
    @classmethod
    def tearDownClass(cls):
        (cls.out/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n');print(cls.receipt)
    def relation(self,original,raw,entry=ENTRY):
        self.assertEqual(original.memory,raw.memory);self.assertEqual(original.trace,raw.trace)
        self.assertEqual(original.f,raw.f);self.assertEqual((original.hi,original.lo,original.condition),(raw.hi,raw.lo,raw.condition))
        for reg in range(32):
            if reg not in (3,5):self.assertEqual(original.r[reg],raw.r[reg],reg)
        if original.current_pc>=entry+28:
            self.assertEqual(original.r[5],raw.r[3]);self.assertEqual(original.r[3],original.before[3]);self.assertEqual(raw.r[5],raw.before[5])
        else:self.assertEqual(original.r,raw.r)
    def compare(self,op=1,tag=14,payload=0xFFFFFFFF,count=1,offsets=OFFSETS[-1],phase=0,base=BASE,flip=None,images=None,entry=ENTRY):
        memory=fixture(op,tag,payload,count,phase,base);args=(base,*offsets)
        expected,n,trace=reference(memory,args,STACK+phase,flip)
        models=[RelocateOracle(code,memory,args,phase,entry,base=base,flip=flip).run()for code in images or (self.truth,self.raw,self.fitted)]
        for model in models:
            self.assertEqual(model.memory,expected);self.assertEqual(model.trace,trace);self.assertEqual(model.r[2],n)
            self.assertEqual(model.r[16],SAVED);self.assertFalse(model.calls)
        self.relation(models[0],models[1],entry);self.assertEqual(complete(models[0]),complete(models[2]))
        return models
    def test_01_owner_Make_guard_lifetime_and_old_stub(self):
        self.assertEqual(self.fitted,self.truth);self.assertEqual(sum(a!=b for a,b in zip(self.raw,self.truth)),11)
        self.assertEqual(source.payload(source.original(ROOT,self.out,source.FUNCTIONS[0]),source.FUNCTIONS[0]),source.normalized(*source.payload(self.obj,source.FUNCTIONS[0])))
        q=json.loads((self.out/'qualification.json').read_text());self.assertEqual((q['total_words'],q['new_guards'],q['preserved_neighbors']),(42,11,8))
        old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,ENTRY,168)
        memory=fixture();args=(BASE,*OFFSETS[-1]);stub=RelocateOracle(struct.unpack_from('>42I',old,at),memory,args).run()
        self.assertNotEqual(stub.memory,reference(memory,args)[0])
        self.receipt.update(words=42,frame=8,bindings=0,new_guards=11,closed_cursor_lifetime_only=True,neighbors=8,old_stub_effectively_rejected=True)
    def test_02_signed_bytes_full_offsets_and_fences(self):
        seen=set();count=0
        for op,tag,k,phase in itertools.product(range(256),(0,13,14,255),range(6),(0,8)):
            m=self.compare(op,tag,WORDS[(op+tag+k)%6],1,OFFSETS[k],phase)[0];seen.update(m.visits);count+=1
        for n,phase in itertools.product((0,2,7,31,257),(0,8)):
            m=self.compare(0xDC,14,0xFFFFFFFF,n,OFFSETS[3],phase)[0];seen.update(m.visits);count+=1
        unreachable={ENTRY+i*4 for i in (20,21,22,23,24)}
        self.assertEqual(seen,set(range(ENTRY,ENTRY+168,4))-unreachable)
        self.receipt.update(guest_phases=count,reachable_words=37,unreachable_original_words=5,signed_DL_case_intentionally_unreachable=True,wrapping_payloads_and_full_fences=True,max_guest_commands=257)
    def test_03_native32_SDK_source_and_defined_wrong_C(self):
        body=source.SELECTED[source.FUNCTIONS[0]]
        changes=(('data-offset','+= dataOffset;','+= matrixOffset;'),('matrix-offset','+= matrixOffset;','+= dataOffset;'),
            ('vertex-opcode','case G_VTX:','case G_VTX + 1:'),('matrix-index','== G_MV_MATRIX','== G_MV_MATRIX + 1'),
            ('move-mem-signedness','case (s8)G_MOVEMEM:','case G_MOVEMEM:'),('fix-dead-DL','case G_DL:','case (s8)G_DL:'),
            ('payload-width','*(u32 *)(command + 4)','*(u16 *)(command + 4)'),('terminator','!= (s8)G_ENDDL','!= (s8)(G_ENDDL - 1)'))
        bodies=[body];names=[source.FUNCTIONS[0]]
        for i,(label,a,b)in enumerate(changes):
            self.assertIn(a,body);name=source.FUNCTIONS[0]+'_control'+str(i)
            bodies.append(body.replace(a,b).replace(source.FUNCTIONS[0],name));names.append(name)
        runner='static int run(void){int r;'+''.join('r=runVariant(%s);if(r!=%d)return %d;'%(name,0 if i==0 else 23,80+i)for i,name in enumerate(names))+'return 0;}'
        for opt in ('-O0','-O2','-O3'):
            p=self.out/('native-batch'+opt+'.c');exe=p.with_suffix('.elf');p.write_text(native_harness('\n'.join(bodies),runner))
            q=subprocess.run(native_command(opt)+['-mstackrealign','-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(q.returncode,0,q.stderr);self.assertEqual(subprocess.run([str(exe)],capture_output=True,timeout=30).returncode,0)
        self.receipt.update(native_cases_per_optimization=73728,native_optimizations=3,trap_UBSan=True,effective_defined_wrong_C_controls=8,native_compile_invocations=3,negative_controls_each_optimization=True,wrong_terminator_fixture_has_backed_fallback=True,native_generic_memory_view_alias_flag=True)
    def test_04_two_actual_caller_windows_and_static_references(self):
        jal=struct.pack('>I',0x0C000000|(ENTRY>>2&0x3FFFFFF))
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==jal],[0x3088C,0x308B8])
        self.assertFalse(any(self.rom[i:i+4]==struct.pack('>I',ENTRY)for i in range(0,len(self.rom),4)))
        count=0
        for start,rom,n in ((0x150033CC,0x3087C,6),(0x15003404,0x308B4,3)):
            words=list(struct.unpack_from('>%dI'%n,self.rom,rom));stop=start+n*4;continuation=struct.unpack_from('>I',self.rom,rom+n*4)[0]
            for value,phase in itertools.product(WORDS,(0,8)):
                memory=fixture(0xDC,14,0xFFFFFFFF,3,phase)
                for address,word in ((HEADER,BASE),(CELL,BASE),(BANK,value)):put(memory,address,word)
                models=[]
                for code in (self.truth,self.fitted):
                    connected=dict(zip(range(ENTRY,ENTRY+168,4),code));connected[stop]=continuation
                    m=RelocateOracle(words,memory,(BASE,value,HEADER),phase,start,connected,BASE,leaf_entry=ENTRY)
                    m.r[16]=m.before[16]=HEADER;m.r[17]=CELL;m.r[7]=BANK
                    m.code=StopCode(m.code,m,stop)
                    with self.assertRaises(WindowEnd):m.run()
                    models.append(m)
                self.assertEqual(complete(models[0]),complete(models[1]))
                expected_data=(value+0xFF000000)&0xFFFFFFFF if start==0x150033CC else value
                self.assertEqual(models[0].calls,[(ENTRY,(BASE,expected_data,HEADER))])
                expected,nprocessed,_=reference(memory,(BASE,expected_data,HEADER),STACK+phase,saved=HEADER)
                self.assertEqual(models[0].memory,expected);self.assertEqual(models[0].r[2],nprocessed);self.assertEqual(models[0].r[16],HEADER)
                count+=1
        old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,0x150031EC,12)
        self.assertEqual(struct.unpack_from('>3I',old,at),(0x00001025,0x03E00008,0))
        self.receipt.update(actual_caller_windows=2,caller_window_words=[6,3],caller_window_phases=count,second_window_A1_is_explicit_precondition=True,current_full_caller_still_stub=True,full_178_word_caller_not_executed=True,continuations_not_executed=True)
    def test_05_opening_double_read_and_effective_cached_C_control(self):
        phases=0
        for before,after,phase in itertools.product((1,0xDC,0xDF),(1,0xDC,0xDF),(0,8)):
            self.compare(before,14,0xFFFFFFFF,2,OFFSETS[-1],phase,flip=after);phases+=1
        body=source.SELECTED[source.FUNCTIONS[0]].replace('commands[index << 3] !=','(opcode = commands[index << 3]) !=').replace('        opcode = command[0];\n','')
        obj,diag=source.compile_owner(ROOT,self.out,'#include <ultra64.h>\n'+body,'cached-opening-control');self.assertFalse(diag)
        text,fs,_=source.parse_object(obj);f=fs[source.FUNCTIONS[0]];words=list(struct.unpack_from('>%dI'%(f['size']//4),text,f['value']));end=max(i for i,w in enumerate(words)if w==0x03E00008)+2;words=words[:end]
        memory=fixture(1,14,0xFFFFFFFF,2);args=(BASE,*OFFSETS[-1]);expected,_,_=reference(memory,args,flip=0xDC)
        wrong=RelocateOracle(words,memory,args,flip=0xDC).run()
        self.assertEqual(wrong.header_reads,1)
        self.assertNotEqual({a:v for a,v in wrong.memory.items()if BASE<=a<BASE+64},{a:v for a,v in expected.items()if BASE<=a<BASE+64})
        self.receipt.update(opening_header_mutation_phases=phases,effective_cached_opening_wrong_C=1,guest_read_mutations_not_portable_C_concurrency=True)
    @classmethod
    def link_words(cls,obj,entry,label):
        from tools.experiments.alternative_source_draft_word_screen import emit_function
        text,fs,rs=source.parse_object(obj);asm,unknown=emit_function(text,fs[source.FUNCTIONS[0]],rs,source.FUNCTIONS[0],{});assert not unknown
        p=cls.out/label;ap=p.with_suffix('.s');op=p.with_suffix('.o');ld=p.with_suffix('.ld');elf=p.with_suffix('.elf')
        ap.write_text(asm);ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(op),str(ap)],capture_output=True,check=True)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',source.FUNCTIONS[0],'-o',str(elf),str(op)],capture_output=True,check=True)
        return list(struct.unpack_from('>42I',sections(elf)['.text'][1]))
    def test_06_independent_links_wrap_addresses_and_fired_faults(self):
        original=source.original(ROOT,self.out,source.FUNCTIONS[0]);phases=cuts=0
        for i,entry in enumerate((0x17001000,0x17108000,0x1720FFFC)):
            a=self.link_words(original,entry,'rebase-original'+str(i));b=self.link_words(self.obj,entry,'rebase-C'+str(i))
            fitted=list(struct.unpack('>42I',source.normalized(struct.pack('>42I',*b),{})[0]));self.assertEqual(a,fitted)
            for op,base,phase in itertools.product((1,0xDC,0xDE,0xDF),(BASE,0x7FFFFFF8,0xFFFFFFF8),(0,8)):
                self.compare(op,14,0xFFFFFFFF,1,OFFSETS[-1],phase,base,images=(a,b,fitted),entry=entry);phases+=1
        for op,tag,count,phase in itertools.product((1,0xDC,0xDE,0xDF),(14,255),(0,3),(0,8)):
            memory=fixture(op,tag,count=count,phase=phase);args=(BASE,*OFFSETS[-1]);good=RelocateOracle(self.truth,memory,args,phase).run()
            for cut in range(good.root_accesses):
                models=[RelocateOracle(code,memory,args,phase)for code in (self.truth,self.raw,self.fitted)]
                for m in models:
                    m.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                self.assertEqual(complete(models[0]),complete(models[2]));self.relation(models[0],models[1])
                self.assertEqual((models[0].current_pc,models[0].delay_of),(models[2].current_pc,models[2].delay_of));cuts+=1
        self.receipt.update(independent_GNU_links=6,rebase_and_wrap_phases=phases,fired_root_fault_prefixes=cuts,raw_cursor_state_relation_qualified=True,portable_C_wrap_fault_MMU_claimed=False)
    def test_07_guard_and_complete_image_corruptions(self):
        raw,bindings=source.payload(self.obj,source.FUNCTIONS[0]);old=self.values['conker/retail_word_patches.us.csv'];new=source.guard_bytes(old)
        self.assertTrue(new.startswith(old));reader=csv.DictReader(io.StringIO(old.decode()))
        rows=list(csv.DictReader(io.StringIO(new[len(old):].decode()),fieldnames=reader.fieldnames));self.assertEqual(len(rows),11)
        self.assertEqual([int(r['offset'],0)for r in rows],list(source.CURSOR_FIELDS))
        for at in (0,*source.CURSOR_FIELDS,164):
            wrong=bytearray(raw);wrong[at]^=1
            with self.assertRaises(ValueError):source.normalized(bytes(wrong),bindings)
        with self.assertRaises(ValueError):source.normalized(raw,{0:[('R_MIPS_26','wrong')]})
        with self.assertRaises(ValueError):source.guard_bytes(old+b'\n')
        before=self.values['conker/build/conker.us.elf'];pred=source.predicted_image(before,self.rom)
        for at in (0,len(pred)-1,source.elf_slot_offset(pred,ENTRY,168),source.elf_slot_offset(pred,0x15004CE0,112),source.elf_slot_offset(pred,0x80082B20,4)):
            wrong=bytearray(pred);wrong[at]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(wrong),self.rom)
        self.receipt.update(strict_guard_corruption_controls=15,strict_image_corruption_controls=5,only_eleven_cursor_guards_appended=True,existing_neighbor_guards_untouched=True,metadata_exclusions=0)
    def test_08_pinned_inputs_and_installed_identity(self):
        for name,old in self.values.items():
            self.assertEqual(source.digest(old),source.INPUTS[name])
            expected=source.recovered_owner(old.decode()).encode()if self.installed and name==source.SOURCE else source.guard_bytes(old)if self.installed and name=='conker/retail_word_patches.us.csv'else source.predicted_image(old,self.rom)if self.installed and name=='conker/build/conker.us.elf'else old
            self.assertEqual((ROOT/name).read_bytes(),expected,name)
        self.assertEqual(source.digest((self.out/'before-padded.o').read_bytes()),source.BEFORE_OBJECT_SHA)
        self.receipt.update(pinned_inputs=len(self.values),old_object_pinned=True,guard_prefix_byte_identical=True)


if __name__=='__main__':unittest.main()
