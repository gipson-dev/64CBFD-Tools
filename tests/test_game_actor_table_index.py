"""Actor table lookup: pure reads, byte/full-word domains, real call delays and closed ELF."""
from dataclasses import dataclass
import csv,itertools,json,struct,subprocess,unittest
from pathlib import Path
from tools.experiments import game_actor_table_index as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_projected_packet_draw import native_command
from tools import match_progress as match

ROOT=Path(__file__).resolve().parents[2]
ENTRY,ACTOR,HEADER,ALT,DATA,ALT_DATA=0x1505E7CC,0x20000,0x22008,0x23008,0x30000,0x32000
TABLE=0x800D1588
SITES=(0x15056538,0x15056768,0x15059710,0x1505B67C,0x1505C01C,0x1505D318,0x1506EB68)
LENGTHS=(0,1,23,24,25,47,48,49,71,72,73,95,96,97,0x7FFFFFFF,0x80000000,0xFFFFFFE8,0xFFFFFFFF)


@dataclass(frozen=True)
class Case:
    id:int=7
    key:int=33
    length:int=96
    gate:int=0
    tag:int=33
    alias:int=0


def fixture(c,phase=0,table=TABLE):
    m={STACK+phase+i:(i*17+0xA5)&255 for i in range(-0x400,0x300)}
    for base,size in ((ACTOR,0x32C),(table,256*4),(HEADER-8,160),(ALT-8,160),(DATA,256),(ALT_DATA,256)):
        m.update({base+i:0xA5 for i in range(size)})
    header=ACTOR+8 if c.alias==3 else HEADER
    entries={1:ACTOR+0x10,2:table+128*4,4:header-8}.get(c.alias,DATA)
    for i in range(8):
        m[entries+i*24]=c.tag if i&1 else c.tag^1
        m[ALT_DATA+i*24]=c.tag if i==2 else c.tag^1
    for i in range(256):put(m,table+i*4,ALT)
    put(m,ALT-8,ALT_DATA);put(m,ALT-4,96)
    put(m,header-8,0 if c.gate==2 else entries);put(m,header-4,c.length)
    put(m,table+c.id*4,0 if c.gate==1 else header)
    m[ACTOR+4]=c.id
    return m


def reference(memory,key,actor=ACTOR,table=TABLE):
    trace=[]
    def get(a,n):
        value=read(memory,a,n);trace.append(('R',a,n,value));return value
    ident=get(actor+4,1)
    if ident==255:return 0,trace
    header=get(table+ident*4,4)
    if not header:return 0,trace
    length=get(header-4,4)
    if not length:return 0,trace
    count=length//24;entries=get(header-8,4)
    if not entries:return 0,trace
    for i in range(count):
        if key&0xFFFFFFFF==get(entries+i*24,1):return i,trace
    return 0,trace


class WindowBoundary(Exception):
    pass


class StopCode(dict):
    def __init__(self,wrapped,owner,stop):
        super().__init__(wrapped);self.wrapped,self.owner,self.stop=wrapped,owner,stop
    def __contains__(self,address):
        return address==self.stop or super().__contains__(address)
    def __getitem__(self,address):
        if address==self.stop:
            self.owner.current_pc=address;self.owner.delay_of=None;raise WindowBoundary
        return self.wrapped[address]


class IndexOracle(TimingOracle):
    def __init__(self,words,c=Case(),phase=0,table=TABLE,entry=ENTRY,connected=None,memory=None):
        self.trace=[]
        super().__init__(words,fixture(c,phase,table)if memory is None else memory,phase=phase,entry=entry,
            arguments=(c.key,ACTOR),connected=connected)
    def get(self,address,size):
        value=super().get(address,size)
        if self.own_instruction:self.trace.append(('R',address,size,value))
        return value
    def record_call(self,target):
        assert target==ENTRY,hex(target)
        args=self.arguments(2);self.calls.append((target,args));self.events.append(('CALL',target,args))


def native_harness(body,boundaries=True):
    return source.DECLARATIONS+"""
typedef struct {u8 *entries;u32 length;}TableIndexHeader;
typedef char Width[(sizeof(void*)==4&&sizeof(u32)==4&&sizeof(s32)==4&&sizeof(TableIndexHeader)==8&&
 __builtin_offsetof(struct127,id)==4)?1:-1];
s32 D_800D1588[187];
static TableIndexHeader header,alternate;static struct127 actor;
static u8 records[65537*24],other[96];
static u32 currentId,currentKey,currentLength,currentGate,currentTag,cases;
"""+body+"""
static u32 expected(void){
 u32 i,count;
 if(currentId==255||currentGate==1||currentLength==0||currentGate==2)return 0;
 count=currentLength/24;
 for(i=0;i<count&&i<4;i++)if(currentKey==(i&1?currentTag:currentTag^1u))return i;
 return 0;
}
static int one(void){
 u32 i,want,got;
 for(i=0;i<187;i++)D_800D1588[i]=(s32)(u32)(&alternate+1);
 for(i=0;i<8;i++)records[i*24]=(u8)(i&1?currentTag:currentTag^1u);
 for(i=0;i<4;i++)other[i*24]=(u8)(i==2?currentTag:currentTag^1u);
 header.entries=currentGate==2?0:records;header.length=currentLength;
 alternate.entries=other;alternate.length=96;actor.id=(u8)currentId;
 if(currentId!=255)D_800D1588[currentId]=currentGate==1?0:(s32)(u32)(&header+1);
 want=expected();got=func_1505E7CC((s32)currentKey,&actor);cases++;
 if(got!=want||header.length!=currentLength||header.entries!=(currentGate==2?0:records)||actor.id!=(u8)currentId)return 23;
 for(i=0;i<8;i++)if(records[i*24]!=(u8)(i&1?currentTag:currentTag^1u))return 23;
 return 0;
}
static int run(void){
 static const u32 lengths[18]={0,1,23,24,25,47,48,49,71,72,73,95,96,97,0x7FFFFFFFu,0x80000000u,0xFFFFFFE8u,0xFFFFFFFFu};
 static const u32 upper[4]={0,0x100,0x80000000u,0xFFFFFF00u};
""" + (' static const u32 wide[4]={255,256,65535,65536};\n' if boundaries else '') + """
 u32 i,j,k;
 for(i=0;i<sizeof(records);i++)records[i]=0xA5;
 for(i=0;i<96;i++)other[i]=0xA5;
 currentLength=96;currentGate=0;currentTag=33;
 for(i=0;i<""" + ('188' if boundaries else '187') + """;i++)for(j=0;j<4;j++){
  currentId=i==187?255:i;currentKey=((u32[]){33,32,289,0xFFFFFFFFu})[j];if(one())return 23;
 }
 currentId=7;
 for(i=0;i<256;i++)for(j=0;j<4;j++){
  currentTag=i;currentKey=upper[j]|i;if(one())return 23;
 }
 currentTag=33;
 for(i=0;i<""" + ('18' if boundaries else '14') + """;i++)for(j=0;j<3;j++)for(k=0;k<2;k++){
  currentLength=lengths[i];currentGate=j;currentKey=33^k;if(one())return 23;
 }
 """ + ("""
 for(i=0;i<65537;i++)records[i*24]=0xA5;
 for(i=0;i<4;i++){
  u32 index=wide[i];records[index*24]=0xFE;header.entries=records;header.length=(index+1)*24;
  D_800D1588[7]=(s32)(u32)(&header+1);actor.id=7;
  if(func_1505E7CC(254,&actor)!=index)return 23;
  records[index*24]=0xA5;cases++;
 }
 """ if boundaries else '') + """
 return cases==""" + ('1888' if boundaries else '1856') + """?0:23;
}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
"""


class ActorTableIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.installed=source.digest((ROOT/source.SOURCE).read_bytes())!=source.INPUTS[source.SOURCE]
        if cls.installed:source.audit(ROOT,cls.out)
        else:source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        cls.values=source.snapshot(cls.out);cls.rom=cls.values['conker/conker.us.bin']
        cls.obj,diag=source.compile_owner(ROOT,cls.out,source.DECLARATIONS+source.SELECTED,'fresh-selected')
        if diag:raise ValueError(diag)
        text,fs=source.link_owner(ROOT,cls.out,cls.obj,source.OWNER)
        cls.words=list(struct.unpack_from('>42I',text,fs[source.FUNCTION]['value']))
        cls.truth=list(struct.unpack_from('>42I',cls.rom,source.ROM));cls.receipt=dict(installed=cls.installed)
    @classmethod
    def tearDownClass(cls):
        (cls.out/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n');print(cls.receipt)
    def compare(self,c,phase=0,images=None,table=TABLE,entry=ENTRY):
        memory=fixture(c,phase,table);wanted,trace=reference(memory,c.key,table=table);models=[]
        for code in images or (self.truth,self.words):
            model=IndexOracle(code,c,phase,table,entry,memory=memory);initial=dict(model.memory);model.run()
            self.assertEqual(model.r[2],wanted);self.assertEqual(model.trace,trace);self.assertEqual(model.memory,initial);models.append(model)
        self.assertEqual(complete(models[0]),complete(models[1]));return models

    def test_01_direct_GNU_owner_Make_and_overflow(self):
        self.assertEqual(self.words,self.truth);raw,bindings=source.payload(self.obj)
        self.assertEqual(bindings,source.BINDINGS);self.assertEqual(source.payload(source.original(ROOT,self.out)),(raw,bindings))
        q=json.loads((self.out/'qualification.json').read_text());self.assertEqual((q['words'],q['frame'],q['guards'],q['unchanged_raw_and_padded_neighbors']),(42,0,0,88))
        self.assertEqual(json.loads((self.out/'make-shadow.json').read_text())['actual_Make_commands'],5)
        report=json.loads((self.out/'first-link.json').read_text())
        self.assertEqual((report['removed_overflow_bytes'],report['moved_overflow_bodies'],report['overflow_ROM_end_shift']),(284,7,272))
        self.assertEqual(report['old_ELF_bytes']-report['new_ELF_bytes'],320)
        self.receipt.update(direct_words=42,frame=0,bindings=2,guards=0,neighbors=88,removed_overflow_bytes=284,moved_overflow_bodies=7,relocated_trampolines=4)

    def test_02_ID_key_length_gates_aliases_and_read_order(self):
        count=0;visits=set()
        for ident,phase in itertools.product(range(256),(0,8)):
            m=self.compare(Case(id=ident),phase)[0];visits.update(m.visits);count+=1
        for tag,upper,phase in itertools.product(range(256),(0,0x100,0x80000000,0xFFFFFF00),(0,8)):
            m=self.compare(Case(key=upper|tag,tag=tag),phase)[0];visits.update(m.visits);count+=1
        for length,gate,key,phase in itertools.product(LENGTHS,range(3),(32,33),(0,8)):
            m=self.compare(Case(key=key,length=length,gate=gate),phase)[0];visits.update(m.visits);count+=1
        aliases=0
        for alias,gate,key,phase in itertools.product(range(1,5),range(3),(32,33),(0,8)):
            self.compare(Case(key=key,gate=gate,alias=alias),phase);aliases+=1
        self.assertEqual(visits,set(range(ENTRY,ENTRY+168,4))-{0x1505E804,0x1505E858})
        self.receipt.update(guest_phases=count,guest_alias_phases=aliases,reachable_words=40,unreachable_duplicate_words=2,
            all_ID_bytes=True,native_ID_domain_separate=True,all_memory_unchanged=True,exact_read_order=True)

    def native(self,body,label,opt='-O2',boundaries=True):
        path=self.out/(label+opt+'.c');exe=path.with_suffix('.elf');path.write_text(native_harness(body,boundaries))
        p=subprocess.run(native_command(opt)+['-mstackrealign',str(path),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr);return subprocess.run([str(exe)],capture_output=True,timeout=20).returncode
    def test_03_native32_valid_arrays_unsigned_widths_and_wrong_C(self):
        for opt in ('-O0','-O2','-O3'):self.assertEqual(self.native(source.SELECTED,'native',opt),0)
        controls=[('disabled-id','id == 0xFF','id == 0'),('key-width','key == cursor[0]','(u8)key == cursor[0]'),
          ('stride','cursor += 0x18','cursor += 0x14'),('count','count /= 0x18','count /= 0x20'),
          ('field','key == cursor[0]','key == cursor[1]'),('one-based','return index;','return index + 1;'),
          ('always-zero','return index;','return 0;'),('signed-length','count /= 0x18','count = (s32)count / 0x18')]
        for label,a,b in controls:
            wrong=source.SELECTED.replace(a,b);self.assertNotEqual(wrong,source.SELECTED)
            # Signed length's discriminating -1/24 case is bounded by a guaranteed early match.
            bounds=label=='signed-length'
            self.assertNotEqual(self.native(wrong,'wrong-'+label,boundaries=bounds),0,label)
        self.receipt.update(native_cases_per_optimization=1888,native_optimizations=3,trap_UBSan=True,
            all_valid_187_native_IDs_and_disabled_FF=True,index_widths=(255,256,65535,65536),
            effective_defined_wrong_C_controls=8,native_no_guest_only_alias_or_out_of_bounds_ID=True)

    def test_04_all_retail_call_sites_and_literal_JAL_delay_windows(self):
        with (ROOT/'conker/progress.csv').open(newline='')as stream:rows=list(csv.DictReader(stream))
        syms=match.load_symbol_addrs(str(ROOT/'conker/symbol_addrs.us.txt'))
        match.add_retail_lengths(rows,'us',match.DEFAULT_SEGMENTS['us'],syms);found=[]
        for row in rows:
            if row['version']!='us' or row['section']not in match.DEFAULT_SEGMENTS['us']:continue
            entry=match.function_vram(row,syms);vram,off=match.DEFAULT_SEGMENTS['us'][row['section']];start=entry-vram+off
            for i,w in enumerate(struct.unpack_from('>%dI'%row['_retail_nwords'],self.rom,start)):
                if w==0x0D4179F3:found.append((entry+i*4,start+i*4))
        self.assertEqual(tuple(site for site,_ in found),SITES);count=0
        for site,offset in found:
            for key,phase in itertools.product((12,33,0x10000021),(0,8)):
                c=Case(key=key);models=[]
                for code in (self.truth,self.words):
                    connected=dict(zip(range(ENTRY,ENTRY+168,4),code));m=IndexOracle(list(struct.unpack_from('>2I',self.rom,offset)),c,phase,entry=site,connected=connected)
                    for reg in range(16,24):m.r[reg]=ACTOR
                    m.memory[STACK+phase+0x67]=key&255
                    m.code=StopCode(m.code,m,site+8)
                    with self.assertRaises(WindowBoundary):m.run()
                    args=m.calls[0][1];self.assertEqual(args[1],ACTOR)
                    want,_=reference(fixture(c,phase),args[0])
                    self.assertEqual(m.r[2],want);models.append(m)
                self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.receipt.update(all_direct_retail_sites=list(SITES),JAL_delay_window_phases=count,
            window_boundary_inputs_seeded=True,complete_parent_or_gameplay_claimed=False)

    def test_05_independent_GNU_symbol_rebases(self):
        from tools.experiments.alternative_source_draft_word_screen import emit_function
        original=source.original(ROOT,self.out);links=count=0
        for i,table in enumerate((0x80207FFC,0x80308000,0x8040FFFC)):
            entry=0x17007FFC+i*0x10000;images=[];syms=dict(D_800D1588=table)
            for label,obj in [('original',original),('C',self.obj)]:
                text,fs,rs=source.parse_object(obj);assembly,unknown=emit_function(text,fs[source.FUNCTION],rs,source.FUNCTION,syms);self.assertFalse(unknown)
                stem=self.out/('rebase-%d-%s'%(i,label));asm=stem.with_suffix('.s');out=stem.with_suffix('.o');ld=stem.with_suffix('.ld');elf=stem.with_suffix('.elf')
                asm.write_text(assembly);ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(out),str(asm)],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',source.FUNCTION,
                    '--defsym=D_800D1588=0x%X'%table,'-o',str(elf),str(out)],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>42I',sections(elf)['.text'][1])));links+=1
            self.assertEqual(images[0],images[1])
            for ident,key,phase in itertools.product((0,7,186,255),(32,33,0x10000021),(0,8)):
                self.compare(Case(id=ident,key=key),phase,images,table,entry);count+=1
        self.receipt.update(independent_GNU_links=links,rebase_phases=count,HI16_LO16_signed_low_carries=True)

    def test_06_fired_root_read_fault_prefixes(self):
        count=0
        for ident,length,gate,key,alias,phase in itertools.product((7,255),(0,23,48,96),(0,1,2),(32,33),(0,1),(0,8)):
            c=Case(id=ident,key=key,length=length,gate=gate,alias=alias);good=IndexOracle(self.truth,c,phase).run()
            for cut in range(good.root_accesses):
                models=[IndexOracle(code,c,phase)for code in (self.truth,self.words)]
                for m in models:m.root_fault=cut
                for m in models:
                    with self.assertRaises(faults.AccessBoundary):m.run()
                self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(models[0].trace,models[1].trace)
                self.assertEqual((models[0].current_pc,models[0].delay_of),(models[1].current_pc,models[1].delay_of));count+=1
        self.receipt.update(fired_root_fault_prefixes=count,portable_fault_or_MMU_claimed=False)

    def test_07_closed_image_corruptions(self):
        before=self.out/'before-conker_build_conker.us.elf';actual=(self.out/'first-linked.elf').read_bytes()
        truth=self.rom[source.ROM:source.ROM+168];predicted,report=source.image_prediction(before,truth)
        self.assertEqual(actual,predicted);header=source.ELF_HEADER.unpack_from(actual)
        positions=(0,len(actual)-1,source.elf_slot_offset(actual,ENTRY,168),
          source.elf_slot_offset(actual,0x150768DC,4),source.elf_slot_offset(actual,0x80082B20,4),
          source.elf_slot_offset(actual,0x15F00000,4),header[6],header[5]+6*header[9]+16)
        bad=self.out/'corrupt-image.elf'
        for pos in positions:
            data=bytearray(actual);data[pos]^=1;bad.write_bytes(data)
            with self.assertRaises(ValueError):source.inspect_image(before,bad,truth,ROOT/'conker')
        bad.write_bytes(actual[:-1])
        with self.assertRaises(ValueError):source.inspect_image(before,bad,truth,ROOT/'conker')
        self.receipt.update(strict_image_corruptions_rejected=9,metadata_exclusions=0,
            closed_strings_symbols_headers_and_trampolines=True)

    def test_08_all_27_inputs_and_installed_identity(self):
        self.assertEqual(len(self.values),27)
        for name,old in self.values.items():
            self.assertEqual(source.digest(old),source.INPUTS[name])
            expected=source.recovered_owner(old.decode()).encode()if self.installed and name==source.SOURCE else (
                (self.out/'first-linked.elf').read_bytes()if self.installed and name=='conker/build/conker.us.elf'else old)
            self.assertEqual((ROOT/name).read_bytes(),expected)
        self.assertEqual(source.digest((self.out/'before-padded.o').read_bytes()),source.BEFORE_OBJECT_SHA)
        if self.installed:self.assertEqual((ROOT/source.OBJECT).read_bytes(),(self.out/'padded/game_83300.c.o').read_bytes())
        self.receipt.update(historical_and_live_inputs=27,guard_manifest_unchanged=True,old_object_pinned=True)


if __name__=='__main__':
    unittest.main()
