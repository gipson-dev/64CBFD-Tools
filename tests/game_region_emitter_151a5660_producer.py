"""Pin the actual region-payload producer and its factory/copy interface."""
from tools.experiments import game_region_emitter_151a5660_recovery as source
from pathlib import Path
import hashlib,json,struct
from tools.tests.test_game_record_constructor_match import elf_slot_offset
def main():
 R=source.ROOT;O=source.OUT;elf=(R/'conker/build/conker.us.elf').read_bytes();rom=(R/'conker/conker.us.bin').read_bytes()
 entry,end=0x150139AC,0x15013C38;raw=rom[entry-0x14FD2B50:end-0x14FD2B50];assert len(raw)==652 and raw==rom[entry-0x14FD2B50:end-0x14FD2B50]
 def word(address,expected):assert struct.unpack_from('>I',raw,address-entry)[0]==expected,(hex(address),hex(expected))
 for address,expected in((0x150139C4,0x8E050018),(0x150139D0,0xAFB00050),(0x15013BE0,0x240A0070),(0x15013BEC,0xAFAA0014),(0x15013BF4,0x2404012C),(0x15013BF8,0x2405FFFF),(0x15013BFC,0x24060006),(0x15013C00,0x00003825),(0x15013C04,0x0D45247D),(0x15013C10,0x24440028),(0x15013C14,0x27A50050),(0x15013C18,0x0C008BB0),(0x15013C1C,0x24060070)):word(address,expected)
 items=[]
 for name,begin,finish in [('producer',entry,end),('record_factory',0x15149130,0x151491F4),('factory_wrapper',0x151491F4,0x15149264)]:
  original=rom[begin-0x14FD2B50:finish-0x14FD2B50];at=elf_slot_offset(elf,begin,len(original));current=elf[at:at+len(original)]
  items.append(dict(name=name,entry=hex(begin),words=len(original)//4,retail_sha256=hashlib.sha256(original).hexdigest(),production_sha256=hashlib.sha256(current).hexdigest(),production_literal=current==original))
 assert items[1]['production_literal']and items[2]['production_literal']and not items[0]['production_literal']
 report=dict(producer='func_150139AC',source='conker/src/game_40490.c',producer_audit='complete original body and static typed interface; producer not restored',functions=items,original_factory_call=hex(0x15013C04),factory_arguments=[300,-1,6,0,10,112,255,0],update_selector_index=2,record_update_offset=17,callback_table='D_8008A4E8[6]',payload_copy_bytes=112,payload_destination='returned_record+0x28',payload_source='producer SP+0x50',source_descriptor_minimum_bytes=28,target_source_view_bytes=24,source_index_offset=24,coefficient_table='0x80095FA0 + source.index * 56',height_cache_initializes_height_and_flags=True,view_mask_lookup='optional func_1510FD20(source.x,source.z)',target_read_contract='All callback fields fit the producer 112-byte payload; view is not a 24-byte source-object stride',source_installed=source.installed(),c_match_credit=0)
 p=O/'producer-audit.json';assert not p.exists();p.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
