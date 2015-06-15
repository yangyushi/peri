import matplotlib as mpl
mpl.use('Agg')
import numpy as np
import acor
import pylab as pl
from cbamf.cu import nbl, fields
from cbamf import observers, samplers, models, engines, initializers, states
from time import sleep
import itertools
import sys
import pickle
import time

GS = 0.05
RADIUS = 12.0
PSF = (0.6, 2)
ORDER = (3,3,2)
PAD = 18

sweeps = 30
samples = 20
burn = sweeps - samples

def renorm(s, doprint=1):
    p, r = s.state[s.b_pos], s.state[s.b_rad]
    nbl.naive_renormalize_radii(p, r, 1)
    s.state[s.b_pos], s.state[s.b_rad] = p, r

#itrue = initializers.normalize(initializers.load_tiff("/media/scratch/bamf/brian-frozen.tif", do3d=True)[12:,:128,:128], False)
itrue = initializers.normalize(initializers.load_tiff("/media/scratch/bamf/neil-large-clean.tif", do3d=True)[12:,:128,:128], False)
xstart, proc = initializers.local_max_featuring(itrue, 10)
itrue = initializers.normalize(itrue, True)

rstart = 6*np.ones(xstart.shape[0])
pstart = np.array(PSF)
bstart = np.zeros(np.prod(ORDER))
astart = np.zeros(1)
GN = rstart.shape[0]
bstart[0] = 1

itrue = np.pad(itrue, PAD+2, mode='constant', constant_values=-10)
xstart += PAD+2

strue = np.hstack([xstart.flatten(), rstart, pstart, bstart, astart])
s = states.ConfocalImagePython(GN, itrue, pad=PAD, order=ORDER, state=strue, threads=1)

renorm(s)

def sample_state(st, blocks, slicing=True, N=1, doprint=False):
    m = models.PositionsRadiiPSF(imsig=GS)

    eng = engines.SequentialBlockEngine(m, st)
    opsay = observers.Printer()
    ohist = observers.HistogramObserver(block=blocks[0])
    eng.add_samplers([samplers.SliceSampler(RADIUS/1e1, block=b) for b in blocks])

    eng.add_likelihood_observers(opsay) if doprint else None
    eng.add_state_observers(ohist)

    eng.dosteps(N)
    return ohist

def sample_ll(st, element, size=0.1, N=1000):
    m = models.PositionsRadiiPSF(imsig=GS)
    start = st.state[element]

    ll = []
    vals = np.linspace(start-size, start+size, N)
    for val in vals:
        st.update(element, val)
        l = m.loglikelihood(st)
        ll.append(l)
    m.free()
    return vals, np.array(ll)

def scan_noise(image, st, element, size=0.01, N=1000):
    start = st.state[element]

    xs, ys = [], []
    for i in xrange(N):
        print i
        test = image + np.random.normal(0, GS, image.shape)
        x,y = sample_ll(test, st, element, size=size, N=300)
        st.update(element, start)
        xs.append(x)
        ys.append(y)

    return xs, ys

#"""
#raise IOError
if True:
    h = []
    for i in xrange(sweeps):
        print '{:=^79}'.format(' Sweep '+str(i)+' ')

        for particle in xrange(s.N):
            print particle
            sys.stdout.flush()

            renorm(s)

            if s.set_current_particle(particle):
                blocks = s.blocks_particle()
                sample_state(s, blocks)

        print '{:-^39}'.format(' PSF ')
        s.set_current_particle()
        blocks = s.explode(s.create_block('psf'))
        sample_state(s, blocks)

        print '{:-^39}'.format(' BKG ')
        s.set_current_particle()
        blocks = (s.create_block('bkg'),)
        sample_state(s, blocks)

        print '{:-^39}'.format(' AMP ')
        s.set_current_particle()
        blocks = s.explode(s.create_block('amp'))
        sample_state(s, blocks)

        if i > burn:
            h.append(s.state.copy())

    h = np.array(h)
    #return h

#h = cycle(itrue, xstart, rstart, pstart, sweeps, sweeps-samples, size=SIZE)
mu = h.mean(axis=0)
std = h.std(axis=0)
pl.figure(figsize=(20,4))
pl.errorbar(xrange(len(mu)), (mu-strue), yerr=5*std/np.sqrt(samples),
        fmt='.', lw=0.15, alpha=0.5)
pl.vlines([0,3*GN-0.5, 4*GN-0.5], -1, 1, linestyle='dashed', lw=4, alpha=0.5)
pl.hlines(0, 0, len(mu), linestyle='dashed', lw=5, alpha=0.5)
pl.xlim(0, len(mu))
pl.ylim(-0.02, 0.02)
pl.show()
#"""
