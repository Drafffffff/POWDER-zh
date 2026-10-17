#!/usr/bin/env python3
"""Run a ROM with a caller-provided mGBA libretro core and save menu frames.

No access to OpenEmu's saves/configuration. Each run starts with blank SRAM.
Dependencies: Python Pillow, compiled mGBA libretro shared library.
"""
import argparse
import ctypes as C
import json,hashlib,zlib
from pathlib import Path

from PIL import Image


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom", type=Path)
    ap.add_argument("--core", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--scenario",choices=["menu","game","tutorial","world"],default="menu")
    ap.add_argument("--trace",action="store_true",help="Capture every unique transition frame, including intermediate frames")
    ap.add_argument("--grouped-actions",action="store_true",help="Verify all 29 actions and wrapping in the grouped menu")
    ap.add_argument("--action-pages",type=int,default=5,help="Expected number of Start action menu pages")
    ap.add_argument("--inventory-checks",action="store_true",help="Check enlarged item action menu paging and restoration")
    ap.add_argument("--latency",action="store_true",help="Measure completed UI response in emulated frames; requires --trace")
    ap.add_argument("--stress",type=int,default=0,help="Repeat menu and reader switching")
    ap.add_argument("--world-frames",type=int,default=0,help="Exercise built-in AI world regeneration in emulator RAM only")
    args = ap.parse_args()
    core = C.CDLL(str(args.core.resolve()))
    args.out.mkdir(parents=True, exist_ok=True)
    state = {"keys": set(), "image": None, "format": 2}
    ENV = C.CFUNCTYPE(C.c_bool, C.c_uint, C.c_void_p)
    VIDEO = C.CFUNCTYPE(None, C.c_void_p, C.c_uint, C.c_uint, C.c_size_t)
    AUDIO = C.CFUNCTYPE(None, C.c_int16, C.c_int16)
    BATCH = C.CFUNCTYPE(C.c_size_t, C.c_void_p, C.c_size_t)
    POLL = C.CFUNCTYPE(None)
    INPUT = C.CFUNCTYPE(C.c_int16, C.c_uint, C.c_uint, C.c_uint, C.c_uint)

    class MemoryDescriptor(C.Structure):
        _fields_=[("flags",C.c_uint64),("ptr",C.c_void_p),("offset",C.c_size_t),("start",C.c_size_t),
                  ("select",C.c_size_t),("disconnect",C.c_size_t),("len",C.c_size_t),("addrspace",C.c_char_p)]
    class MemoryMap(C.Structure):
        _fields_=[("descriptors",C.POINTER(MemoryDescriptor)),("num_descriptors",C.c_uint)]

    @ENV
    def env(cmd, data):
        if cmd==0x10024:
            maps=C.cast(data,C.POINTER(MemoryMap)).contents
            state["memory_maps"]=[(m.ptr,m.offset,m.start,m.len) for m in maps.descriptors[:maps.num_descriptors]]
            return True
        if cmd == 10:  # SET_PIXEL_FORMAT
            state["format"] = C.cast(data, C.POINTER(C.c_int)).contents.value
            return state["format"] == 2
        if cmd == 17:  # GET_VARIABLE_UPDATE
            C.cast(data, C.POINTER(C.c_bool)).contents.value = False
            return True
        return False

    trace=[];seen=set();frame=0
    @VIDEO
    def video(ptr,width,height,pitch):
        nonlocal frame
        frame+=1
        if not ptr or (not args.trace and not state.get("capture",False)):return
        raw=C.string_at(ptr,pitch*height)
        # Decode RGB565 in native Pillow code, including the core's padded stride.
        im=Image.frombytes("RGB",(width,height),raw,"raw","BGR;16",pitch)
        if state.get("capture",False):state["image"]=im
        if args.trace:
            crc=f"{zlib.crc32(im.tobytes()):08x}"
            box=im.getextrema();blank=all(a==b for a,b in box)
            trace.append({"frame":frame,"hash":crc,"uniform":blank,"uniform_rgb":im.getpixel((0,0)) if blank else None,"keys":sorted(state["keys"])})
            if crc not in seen:
                seen.add(crc)
                if len(seen)<=1000 or blank:
                    d=args.out/"frames";d.mkdir(exist_ok=True);im.save(d/(crc+".png"))

    audio = AUDIO(lambda left, right: None)
    batch = BATCH(lambda ptr, frames: frames)
    poll = POLL(lambda: None)
    input_cb = INPUT(lambda port, device, index, key: int(key in state["keys"]))
    for name, callback in [("environment", env), ("video_refresh", video),
                           ("audio_sample", audio), ("audio_sample_batch", batch),
                           ("input_poll", poll), ("input_state", input_cb)]:
        getattr(core, "retro_set_" + name).argtypes = [type(callback)]
        getattr(core, "retro_set_" + name)(callback)
    core.retro_init()

    class Game(C.Structure):
        _fields_ = [("path", C.c_char_p), ("data", C.c_void_p),
                    ("size", C.c_size_t), ("meta", C.c_char_p)]

    rom_bytes = args.rom.read_bytes()
    rom_data = C.create_string_buffer(rom_bytes)
    game = Game(str(args.rom.resolve()).encode(), C.cast(rom_data, C.c_void_p), len(rom_bytes), None)
    core.retro_load_game.argtypes = [C.POINTER(Game)]
    core.retro_load_game.restype = C.c_bool
    if not core.retro_load_game(C.byref(game)):
        raise SystemExit("Could not load ROM")

    measurements=[]
    def measure_renderer(label="final",strict=True):
        symbols=args.rom.parent/"renderer_symbols.json"
        if not symbols.exists():return
        values={}
        for name,address in json.loads(symbols.read_text()).items():
            for ptr,offset,start,size in state.get("memory_maps",[]):
                if ptr and start<=address<=start+size-4:
                    values[name]=int.from_bytes(C.string_at(ptr+offset+address-start,4),'little');break
            assert name in values,"Core does not expose diagnostic memory mapping"
        if values:
            values["label"]=label;measurements.append(values)
            (args.out/"renderer_timing.json").write_text(json.dumps(measurements,indent=2)+"\n")
            if strict:assert values["zh_present_overruns"]==0,values

    def run(frames, keys=()):
        state["keys"] = set(keys)
        for i in range(frames):
            state["capture"]=i==frames-1
            core.retro_run()

    responses=[]
    def probe(label,key):
        assert args.trace,"Latency probes require --trace"
        before=trace[-1]["hash"];begin=frame
        run(4,[key]);run(76)
        events=[t for t in trace if begin<t["frame"]<=frame]
        final=events[-1]["hash"]
        assert final!=before,(label,"Input produced no response")
        completed=next(t["frame"]-begin for t in events if t["hash"]==final)
        responses.append({"label":label,"completed_response_frames":completed})
        measure_renderer("response_"+label,False)
        (args.out/"input_latency.json").write_text(json.dumps({"rom_sha256":hashlib.sha256(rom_bytes).hexdigest(),"responses":responses},indent=2)+"\n")

    markers={}
    def save(name):
        markers[name]=frame
        measure_renderer(name,False)
        if state["image"] is None:
            raise RuntimeError("No video output")
        state["image"].save(args.out / (name + ".png"))
        state["image"].resize((720, 480), Image.Resampling.NEAREST).save(args.out / (name + "_3x.png"))

    if args.scenario=="world":
        run(args.world_frames or 60000);save("world_stress")
        measure_renderer("world_stress_final")
        assert measurements[-1]["zh_world_rebuilds"]>=3,"Too few world rebuilds exercised"
        if args.trace:(args.out/"frame_trace.json").write_text(json.dumps(trace,indent=2)+"\n")
        core.retro_unload_game();core.retro_deinit();print("World-regeneration stress passed");return

    run(300)
    save("boot")
    # Move away and back; the glyph lock/cache path must redraw the selection.
    run(4, [5])  # libretro DOWN
    run(30)
    run(4, [4])  # UP
    run(30)
    save("menu_redraw")
    if args.scenario == "tutorial":
        run(4,[5]);run(30)
    # Confirm New Game using GBA A (libretro key 8).
    run(4, [8])
    run(300)
    save("after_new_game")
    if args.scenario=="game":
        run(4,[8]);run(120);save("name_entry")
        run(4,[3]);run(300);save("intro_help")
        run(4,[0]);run(180);save("entered_game")
    if args.scenario=="tutorial":
        save("tutorial_welcome")
        run(4,[0]);run(180);save("tutorial_map")
        if args.latency:
            probe("world_step_right",7);probe("world_step_left",6)
    def press(key,frames=90):
        run(4,[key]);run(frames)
    if args.scenario=="tutorial":
        press(7);press(7);save("tutorial_signpost")
        run(40,[5]);run(40);save("tutorial_signpost_scrolled")
        press(0)
    if args.scenario=="game":
        press(2);save("inventory")
        press(8);save("item_action_menu")
        if args.inventory_checks:
            first=state["image"].tobytes()
            press(7);save("item_action_page_two")
            assert first!=state["image"].tobytes(),"Item action right navigation produced no change"
            press(6);save("item_action_page_restored")
            assert first==state["image"].tobytes(),"Item action left navigation did not restore"
            press(5);save("item_action_selected");press(4)
            assert first==state["image"].tobytes(),"Item selection repaint damaged glyphs"
        press(0)
        if args.inventory_checks:
            from PIL import ImageChops
            assert ImageChops.difference(Image.open(args.out/"inventory.png"),state["image"]).getbbox() is None,"Item menu damaged inventory"
        press(0)
        save("before_command")
        if args.latency:
            probe("open_menu",3);probe("close_menu",0)
        press(3);save("command_menu")
        if args.latency:
            probe("menu_down",5);probe("menu_up",4)
            probe("menu_next_page",7);probe("menu_previous_page",6)
        if args.grouped_actions:
            first_menu=state["image"].tobytes();selections=[]
            for index in range(29):
                selections.append(state["image"].tobytes())
                if index in (11,20):save("group_page_"+str(2 if index==11 else 3))
                press(5,12)
            assert len(set(selections))==29,"Not all grouped actions are reachable"
            assert state["image"].tobytes()==first_menu,"Grouped actions did not wrap or repaint correctly"
        pages=[state["image"].tobytes()]
        press(7);save("command_page_two");pages.append(state["image"].tobytes())
        for _ in range(args.action_pages-2):
            press(7,15);pages.append(state["image"].tobytes())
        assert len(set(pages))==args.action_pages,"Paging did not visit every action page"
        save("command_page_eight")
        for _ in range(args.action_pages-1):press(6,15)
        press(4);save("command_last_page");press(5);save("command_wrap_first")
        press(0);save("command_cancelled")
        from PIL import ImageChops
        before=Image.open(args.out/"before_command.png")
        after=Image.open(args.out/"command_cancelled.png")
        # The modal overlay must restore the complete underlying screen.
        assert ImageChops.difference(before,after).getbbox() is None, "Menu did not restore its underlay"
        for _ in range(args.stress):
            press(3,30);press(7,30);press(6,30);press(0,30)
            assert ImageChops.difference(before,state["image"]).getbbox() is None,"Repeated action menu damaged screen"
        press(3);press(4);press(8);save("options")
        press(8);save("help_menu")
        press(5);press(8);save("help_page")
        if args.latency:
            probe("reader_down",5);probe("reader_up",4)
        run(40,[5]);run(50);save("help_scrolled")
        press(0);press(0)
        for _ in range(args.stress):
            press(3);press(8);press(8);press(8);press(5);press(4);press(0);press(0)
        press(3);press(8)
        for _ in range(4):press(5,10)
        press(8);save("font_menu")
        press(5);press(8);save("font_changed")
        press(3);press(8)
        for _ in range(2):press(4,10)
        press(8);save("tileset_menu")
        press(5);press(8);save("tileset_changed")
        press(3);save("command_lomaka");press(0)
        press(3);press(8);press(4)
        press(8,500);save("after_save")
        core.retro_get_memory_data.argtypes=[C.c_uint];core.retro_get_memory_data.restype=C.c_void_p
        core.retro_get_memory_size.argtypes=[C.c_uint];core.retro_get_memory_size.restype=C.c_size_t
        ptr=core.retro_get_memory_data(0);size=core.retro_get_memory_size(0)
        if ptr and size:(args.out/"test_save.sav").write_bytes(C.string_at(ptr,size))
        measure_renderer()
        core.retro_reset();run(400);save("save_reboot")
        press(8,400);save("save_loaded")
        a=Image.open(args.out/"tileset_changed.png").crop((32,32,224,144))
        b=Image.open(args.out/"save_loaded.png").crop((32,32,224,144))
        assert ImageChops.difference(a,b).getbbox() is None,"Saved map changed after reload"
        assert (args.out/"test_save.sav").stat().st_size>0
        (args.out/"checks.json").write_text(json.dumps({
            "rom_sha256":hashlib.sha256(rom_bytes).hexdigest(),
            "inventory_action_checks":args.inventory_checks, "all_action_pages":args.action_pages, "grouped_actions_reachable":29 if args.grouped_actions else None, "repeat_switch_cycles":args.stress, "cancel_restores_entire_screen":"pass",
            "saved_map_roundtrip":"pass", "screenshots":"inventory, help, fonts, tilesets, command menu, save/load"
        },indent=2)+"\n")
    measure_renderer()
    if measurements:(args.out/"renderer_timing.json").write_text(json.dumps(measurements,indent=2)+"\n")
    if args.trace:(args.out/"frame_trace.json").write_text(json.dumps(trace,indent=2)+"\n")
    (args.out/"frame_markers.json").write_text(json.dumps(markers,indent=2)+"\n")
    core.retro_unload_game()
    core.retro_deinit()
    print(f"Saved runtime screenshots to {args.out}")


if __name__ == "__main__":
    main()
