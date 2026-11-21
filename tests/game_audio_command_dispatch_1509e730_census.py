from pathlib import Path
import hashlib,json,struct,sys
from tools.experiments import game_audio_command_dispatch_1509e730_recovery as recovery
root=recovery.ROOT;out=recovery.OUT

from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_actor_state_tick_integration import symbol_rows
def run():
    entry=0x1509E730;elf=out/'baseline/conker/build/conker.us.elf';rom=(root/'conker/conker.us.bin').read_bytes()
    fp=json.loads((out/'baseline/fingerprints.json').read_text())['inputs']
    assert hashlib.sha256(rom).hexdigest()==fp['conker/conker.us.bin']
    direct=[]
    for address,word in enumerate(struct.unpack_from('>%dI'%(len(rom)//4),rom)):
        if word>>26 in(2,3)and(word&0x3ffffff)<<2==entry&0xfffffff:
            direct.append(dict(rom=4*address,word=f'{word:08x}',kind='JAL'if word>>26==3 else'J'))
    rows=symbol_rows(elf.read_bytes());objects=[]
    for section,(base,data)in sections(elf).items():
        if not base or not section.startswith(('.game','.data','.rodata')):continue
        for offset in range(0,len(data)-3,4):
            if struct.unpack_from('>I',data,offset)[0]!=entry:continue
            address=base+offset
            neighbors=sorted((r[2][1],r[1],r[2][2])for r in rows if r[2][1]<=address and r[2][1]>=base)
            lo=max(0,offset-16);hi=min(len(data),offset+20)
            objects.append(dict(section=section,address=f'0x{address:08x}',nearest_symbols=neighbors[-4:],
                 surrounding_words=[f'{x:08x}'for x in struct.unpack('>%dI'%((hi-lo)//4),data[lo:hi])]))
    r=dict(function='func_1509E730',direct_original_code_references=direct,loaded_pointer_references=objects,
          source_installed=recovery.installed(),matching_credit=0,scope='Original decompressed ROM word census and frozen ELF loaded-section pointer census; indirect callers still need qualification.')
    (out/'caller-census.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
    return r
