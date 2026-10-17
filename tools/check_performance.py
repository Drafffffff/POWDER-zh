#!/usr/bin/env python3
"""Compare deterministic completed-input responses and unchanged UI pixels."""
from pathlib import Path
import hashlib
import json
from PIL import Image, ImageChops

R = Path(__file__).resolve().parents[1]
A = R / 'analysis/runtime'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
before_sha = sha(R / 'output/powder118_zh_stable.gba')
after_sha = sha(R / 'build/gba_zh_src/powder.gba')
responses = []
for before_dir, after_dir in [('latency_before', 'smooth_final'),
                              ('latency_tutorial_before', 'smooth_tutorial')]:
    before = json.loads((A / before_dir / 'input_latency.json').read_text())
    after = json.loads((A / after_dir / 'input_latency.json').read_text())
    assert before['rom_sha256'] == before_sha
    assert after['rom_sha256'] == after_sha
    previous = {r['label']: r['completed_response_frames'] for r in before['responses']}
    for item in after['responses']:
        label = item['label']
        old, new = previous[label], item['completed_response_frames']
        assert new <= old, (label, old, new)
        if label.startswith(('menu_', 'reader_')) or label == 'open_menu':
            assert new < old, (label, old, new)
        responses.append({'label': label, 'before_frames': old, 'after_frames': new})

screens = ['command_menu', 'command_page_two', 'command_page_eight',
           'command_last_page', 'command_wrap_first', 'command_cancelled',
           'help_page', 'inventory', 'options', 'font_changed',
           'tileset_changed', 'save_loaded']
for name in screens:
    old = Image.open(A / 'latency_before' / (name + '.png'))
    new = Image.open(A / 'smooth_final' / (name + '.png'))
    assert ImageChops.difference(old, new).getbbox() is None, name

report = {'before_sha256': before_sha, 'rom_sha256': after_sha,
          'responses': responses, 'identical_screenshots': screens,
          'method': '4-frame input pulse; first video frame matching the settled screen after 80 frames',
          'limits': 'mGBA 0.10.5 deterministic UI/tutorial samples; not an FPS benchmark or real-hardware measurement'}
(R / 'analysis/performance_validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
