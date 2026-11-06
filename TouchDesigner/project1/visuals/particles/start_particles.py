"""Start the particle simulation when the project opens (a Particle POP waits for Initialize, then Start)."""


def onStart():
	sim = op('geo/particle_sim')
	sim.par.initializepulse.pulse()
	run("args[0].par.startpulse.pulse()", sim, delayFrames=2)
