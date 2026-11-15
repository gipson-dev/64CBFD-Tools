"""Qualified radial-effect source and eleven bounded retail word normalizations."""
import csv,hashlib,io,json,os,struct,subprocess
from pathlib import Path
from tools.experiments import game_radial_effect_150c29f0_recovery as old
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve()
BUILD='conker/build/game-radial-effect-150c29f0-match';OUT=ROOT/BUILD
SOURCE,NAME,ENTRY,ROM,SIZE=old.SOURCE,old.NAME,old.ENTRY,old.ROM,old.SIZE
PREAMBLE=old.PREAMBLE
BODY='''/* Submit a randomized radial effect and refresh the owner's timer. */
void func_150C29F0(u8 *volatile owner) {
    u8 *position;
    RadialEffectPacket150C29F0 packet;
    f32 firstScale, secondScale;
    u8 angle;
    f32 directionX, directionZ, radius;

    angle = func_150ADA20();
    directionX = func_151423D8((u8)(angle - 64));
    directionZ = func_151423D8(angle);
    radius = func_150ADA68();
    position = owner;
    radius = radius * *(f32 *)(position + 0x30);
    packet.code0 = 0x6231;
    packet.code1 = 0x1A4D;
    packet.firstColor[0] = 0;
    packet.firstColor[1] = 0;
    packet.firstColor[2] = 0;
    packet.alpha = 255;
    packet.secondColor[0] = 255;
    packet.secondColor[1] = 255;
    packet.zero30 = 0;
    packet.flags2A = 1;
    packet.secondColor[2] = 0;
    packet.enabled = 1;
    position += 0x28;
    packet.duration = (u32)func_150ADA20() % 201U + 100;
    packet.kind34 = 15;
    packet.zero38 = 0.0f;
    packet.value40 = D_800A02A0;
    packet.value44 = D_800A02A4;
    packet.x = *(f32 *)position + radius * directionX;
    packet.y = *(f32 *)(position + 12);
    packet.z = *(f32 *)(position + 4) + radius * directionZ;
    packet.value3C = D_800A02A8;
    firstScale = func_150ADA68();
    firstScale = firstScale * 0.5f + 1.0f;
    secondScale = func_150ADA68();
    secondScale = secondScale * 0.5f + 1.0f;
    packet.size0 = D_800A02AC * firstScale;
    packet.size1 = D_800A02B0 * firstScale;
    packet.delta0 = D_800A02B4 * secondScale;
    packet.delta1 = D_800A02B8 * secondScale;
    packet.delta2 = D_800A02BC * secondScale;
    position = owner;
    func_15149550(&packet, 10, 1, 0, position[0xC], position[1]);
    *(s16 *)(owner + 0xE) = (u32)func_150ADA20() % 51U + 25;
}'''
RAW_SHA256='c97d541c809848d9175d2f9c9445826a81acefcb4352973fbaa0a5dcf59c0566'
# Word index: (compiler word, retail word, independently justified group).
PATCHES={6:(0x2484ffc0,0xa3a40033,'byte-home schedule'),7:(0x308e00ff,0x2484ffc0,'byte-home schedule'),8:(0xa3a20033,0x308e00ff,'byte-home schedule'),22:(0x46002082,0x46040082,'source-ordered radius multiply'),27:(0xa7af005c,0xa7b8005e,'disjoint halfword-store schedule'),28:(0xa7b8005e,0xa7af005c,'disjoint halfword-store schedule'),39:(0xafa30084,0xafa30020,'isolated private pointer home'),52:(0x8fa30084,0x8fa30020,'isolated private pointer home'),104:(0x8fa30088,0x8fa20088,'closed owner temporary'),115:(0x906f000c,0x904f000c,'closed owner temporary'),117:(0x90780001,0x90580001,'closed owner temporary')}
symbols=old.symbols

def proposed(source):
 stub=body(source,NAME);assert stub=='s32 func_150C29F0() {\n    return 0;\n}'
 result=source.replace(stub,BODY).replace('s32 func_150C29F0();\n','')
 result=result.replace('/* Generated placeholder declarations. */',PREAMBLE+'\n/* Generated placeholder declarations. */',1)
 result=result.replace('/* Non-matching C placeholders for asm/nonmatchings/game_EF410/func_150C29F0.s. */\n','')
 return result.rstrip()+'\n'

def normalize(raw,refs):
 assert len(raw)==SIZE and hashlib.sha256(raw).hexdigest()==RAW_SHA256,'Compiler radial body changed'
 pinned=json.loads(Path(__file__).with_name('game_radial_effect_150c29f0_manifest.json').read_text())['raw_relocations']
 assert {str(k):[list(x) for x in v] for k,v in refs.items()}==pinned,'Radial relocation set changed'
 words=list(struct.unpack('>132I',raw))
 for i,(want,replacement,_) in PATCHES.items():
  assert words[i]==want and i*4 not in refs,(i,words[i],refs.get(i*4))
  words[i]=replacement
 return struct.pack('>132I',*words),refs

def programs():
 truth=list(struct.unpack_from('>132I',(ROOT/'conker/conker.us.bin').read_bytes(),ROM));raw,refs=payload(OUT/'recovered.o',NAME);fixed,fr=normalize(raw,refs)
 return [truth,bound_blob(raw,refs,symbols()),bound_blob(fixed,fr,symbols())]

def main():
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();frozen=OUT/'production-baseline';record=json.loads((frozen/'fingerprints.json').read_text());before=(frozen/SOURCE).read_text();source=proposed(before);installed=(ROOT/SOURCE).read_text()==source
 plan=json.loads((OUT/'adoption-plan.json').read_text()) if (OUT/'adoption-plan.json').exists() else {}
 for name,want in record['inputs'].items():assert sha(ROOT/name)==(plan.get(name,want) if installed else want),name
 base,d1=compile_owner(ROOT,OUT,before,'baseline');obj,d2=compile_owner(ROOT,OUT,source,'recovered');assert d1==d2 and same_functions(base,obj,(NAME,))==17
 assert normalized_pools(base)==normalized_pools(obj)
 raw,refs=payload(obj,NAME);fixed,fr=normalize(raw,refs);truth,_,words=programs();assert words==truth and words[0]==0x27bdff78
 original=(ROOT/'conker/asm/nonmatchings/game_EF410'/f'{NAME}.s').read_text();asm=OUT/'retail.s';asm.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+original+'\n.size '+NAME+',.-'+NAME+'\n')
 q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(OUT/'retail.o'),str(asm)],cwd=ROOT/'conker',capture_output=True,text=True);assert q.returncode==0 and not q.stderr,q.stderr
 assert payload(OUT/'retail.o',NAME)==(fixed,fr)
 guards=(frozen/'conker/retail_word_patches.us.csv').read_bytes();fields=next(csv.reader(io.StringIO(guards.decode())));stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n')
 for i,(expected,replacement,group) in PATCHES.items():writer.writerow(dict(filename='game_EF410',function=NAME,offset='0x%03X'%(i*4),expected='0x%08X'%expected,replacement='0x%08X'%replacement,expected_relocations='-',replacement_relocations='-',note='Normalize radial effect '+group,insert_after='',insert_after_relocations='',omit='false'))
 (OUT/'proposed-guards.csv').write_bytes(guards+stream.getvalue().encode())
 for name,want in record['inputs'].items():assert sha(ROOT/name)==(plan.get(name,want) if installed else want),name
 report=dict(installed=installed,body_words=132,frame=136,guards=11,bindings=len(refs),neighbors=17,raw_word_differences=11,c_match_credit=int(installed))
 (OUT/'match-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
