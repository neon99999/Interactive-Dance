"""Task 01 sync test: drives the transport through the brief's steps on a schedule.

Call op('test_t01/sync_test').module.Start(). Results land in test_t01/results;
note events land in transport/note_log.
"""
import time

STEPS = [  # (wall seconds after start, step name)
	(0.0, 'reset+play'),
	(8.0, 'pause'),
	(10.0, 'check_paused+resume'),
	(13.0, 'seek12'),
	(22.0, 'reset'),        # keeps playing from 0 (repeat performance)
	(28.0, 'seek20.2'),     # land inside held notes 65/67: must not fire
	(29.0, 'seek4.9'),      # note 60 must fire ~0.1 s later
	(30.0, 'stop'),
]


def Start():
	t = op('../transport')
	op('../transport/note_log').clear(keepFirstRow=True)
	op('results').clear(keepFirstRow=True)
	me.store('t0', time.perf_counter())
	for at, step in STEPS:
		run(_do, step, delayMilliSeconds=int(at * 1000))


def _do(step):
	t = op('../transport')
	if step == 'reset+play':
		t.par.Reset.pulse(); t.par.Play = 1
	elif step == 'pause':
		t.par.Play = 0
	elif step == 'check_paused+resume':
		_record('paused_still')
		t.par.Play = 1
	elif step.startswith('seek'):
		t.par.Seekto = float(step[4:]); t.par.Seek.pulse()
	elif step == 'reset':
		t.par.Reset.pulse()
	elif step == 'stop':
		t.par.Play = 0
	_record(step)


def _record(step):
	t = op('../transport')
	info = op('../transport/info_music')
	audio_s = float(info['sample']) / max(1.0, float(info['sample_rate']))
	wall = time.perf_counter() - me.fetch('t0')
	op('results').appendRow([round(wall, 3), step, round(t.time.seconds, 4), round(audio_s, 4), op('../transport/note_log').numRows - 1])
