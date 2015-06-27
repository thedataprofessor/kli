import numpy
import random
import time
import parameter
import matplotlib.pylab as plt
import scipy.stats
import ad
import repository

class Toy(object):
    def __init__(self, q):
        self.q = q
        self.preferred = parameter.preferredUnits()
        self.preferred.freq = 'kHz'

    def flatten(self, seed=None):
        parent = self  # for readability
        FT = FlatToy(parent, seed)
        return FT

    def getExperiment(self):  # For subclassing replace this code
        if len(self.q) == 1:
            toy2 = True
            q = parameter.mu(self.q[0], self.preferred.freq)
            q0 = None
            q1 = None
        elif len(self.q) == 2:
            toy2 = False
            q = None
            q0 = parameter.mu(self.q[0], self.preferred.freq)
            q1 = parameter.mu(self.q[1], self.preferred.freq)
        else:
            assert (False)  # Length of q should be 1 or 2
        return (toy2, q, q0, q1)


class SaveSeedRNG(random.Random):
    def __init__(self, seed=None):
        super(SaveSeedRNG, self).__init__()
        self.setSeedAndOffset(seed,0)
        self.setSeed(seed)

    def setSeedAndOffset(self, seed=None, offset=0):
        self.seedOffset = offset
        self.setSeed(seed)

    def setSeed(self, seed=None):
        if seed is None:
            self.usedSeed = long(time.time() * 256) + self.seedOffset
        else:
            self.usedSeed = seed + self.seedOffset  # can be changed with self.reseed()
        self.reset()

    def reset(self):  # Resets RNG to same seed as used before
        self.seed(self.usedSeed)


class MultipleRNGs(object):
    def __init__(self, numRNGs, seed=None, offset=1000000):
        self.RNGs = []  # Not yet implemented, if numRNGs is a list make it RNGs, set seeds and offsets
        for i in range(numRNGs):
            self.RNGs.append(SaveSeedRNG())
            self.RNGs[-1].setSeedAndOffset(seed,offset*i)

    def setSeedAndOffset(self, seed=None, offset=1000000):
        for i in range(len(self.RNGs)):
            self.RNGs[i].setSeedAndOffset(seed,offset*i)

    def setSeed(self, seed=None):
        for i in range(len(self.RNGs)):
            self.RNGs[i].setSeed(seed)

    def reset(self):
        for i in range(len(self.RNGs)):
            self.RNGs[i].reset()


class FlatToy(object):
    def __init__(self, parent, seed=None):
        self.debug(False)  # To save hidden states, call sellf.debug(True)
        self.R = self.initRNG(seed)  # Afterwards, must call restart()
        self.setUpExperiment(parent)
        self.defineRepetitions()
        self.restart()

    def defineRepetitions(self):
        self.base = self  # Used in functions below; Defined differently for Repetitions subclass
        self.rReps = 1  # Used in functions below; Defined differently by Repetitions subclass

    def initRNG(self, seed=None):  # Maybe overloaded if using a different RNG, eg rpy2
        return SaveSeedRNG(seed)

    def reseed(self, seed=None):
        self.R.setSeed(seed)
        self.restart()

    def restart(self):  # Clears data and resets RNG with same seed
        self.R.reset()
        self.data = []  # Data used for fitting model. (Each datum may be a tuple)
        self.hiddenStates = []  # These are the Markov states, including hidden ones.  This model isn't Markovian, though.
        self.likes = []  # Likelihood (single number) of each datum. (Each datum may be a tuple) 
        self.likeInfo = []
        self.changedSinceLastSim = False

    def setUpExperiment(self, parent):
        self.experiment = parent.getExperiment()
        self.toy2, self.q, self.q0, self.q1 = self.experiment
        self.changedSinceLastSim = True

    def changeModel(self, parent):
        self.setUpExperiment(self, parent)

    def sim(self, mReps=1, clear=False):  # Only does new reps; keeps old; if (nReps < # Trajs) then does nothing
        if clear:
            self.restart()  # Resets random number generator
        elif self.changedSinceLastSim:
            self.restart()
        numNewReps = mReps - len(self.data)  # Negative if decreasing nReps; if so, nReps updated data unchanged
        for n in range(numNewReps):
            self.data.append(self.simulateOnce(self.R))  # Don't want to use self.R elsewhere
            if self.debugFlag:
                self.hiddenStates.append(self.hiddenStateTrajectory)
        self.mReps = mReps  # Might be decreasing nReps, but code still saves the old results
        self.changedSinceLastSim = False

    def resim(self, mReps=1):
        self.sim(mReps, clear=True)

    def debug(self, flag=None):
        if flag == True:
            self.debugFlag = True
            self.restart()  # Restart because you need to rerun to save hidden states
        elif flag == False:
            self.debugFlag = False
        return self.debugFlag

    def simulateOnce(self, RNG=None):  # Overload
        if RNG is None:
            RNG = self.initRNG(None)
        if self.toy2:
            self.hiddenStateTrajectory = (RNG.expovariate(self.q),)  # Though not Markovian, we can save the hidden transition times
        else:
            self.hiddenStateTrajectory = (RNG.expovariate(self.q1), RNG.expovariate(self.q0))
        return sum(self.hiddenStateTrajectory)

    def likelihoods(self, trueModel=None):
        if trueModel is None:  # Data not passed
            trueModel = self
        likes = repository.Repo.likes.getOrMake(self, trueModel)
        # likeInfo?
        nFirst = len(likes)
        nLast = trueModel.mReps  # Restricts return to self.mReps
        for datum in trueModel.data[nFirst:nLast]:
            likes.append(self.likeOnce(datum))
            #if self.debugFlag and self.recentLikeInfo is not None:
            #    likeInfo.append(self.recentLikeInfo)
        return likes[0:nLast]  # Restrict what you return to stopping point

    def likeOnce(self, datum):  # Overload when subclassing
        #if self.debugFlag:
        #    self.recentLikeInfo = None
        if not self.datumIntegrity(datum):
            return -numpy.infty
        elif self.toy2:
            return numpy.log(self.q) - self.q * datum
        elif self.q0 == self.q1:
            return numpy.log(self.q1) + numpy.log(self.q0) - self.q0 * datum + numpy.log(datum)
        else:
            return numpy.log(self.q1) + numpy.log(self.q0) + numpy.log(
                (numpy.exp(-self.q0 * datum) - numpy.exp(-self.q1 * datum)) / (self.q1 - self.q0))

    def datumWellFormed(self, datum):
        return isinstance(datum, float) or isinstance(datum, int)

    def datumIntegrity(self, datum):
        if not self.datumWellFormed(datum):
            return False
        elif datum < 0.:
            return False
        elif (not self.toy2) and datum == 0:
            return False
        else:
            return True

    def minuslike(self, trueModel=None):
        L = self.likelihoods(trueModel)
        return -sum(L)

    def like(self, trueModel=None):
        L = self.likelihoods(trueModel)
        return sum(L)

    def pdf(self, datum):
        assert False  # Needs Fixing
        # return numpy.exp(self.likelihoods([datum])[0])

    def mle(self):
        assert self.toy2  # Not yet implemented for toy 3
        return 1. / numpy.mean(self.data[0:self.mReps])

    def logf(self, trueModel=None):
        return numpy.matrix(self.likelihoods(trueModel))
        #  M = numpy.matrix(self.likelihoods(data))
        #  print M.mean()
        #  return M

    def mRepsRestrictedData(self):
        return self.data[0:self.mReps]

    def likeRatios(self, alt, trueModel=None):  # likelihood ratio; self is true model
        if trueModel is None:
            trueModel = self
        return self.logf(trueModel) - alt.logf(trueModel)

    def PFalsify(self, alt, trueModel=None):
        ratios = self.likeRatios(alt, trueModel)
        return float(numpy.sum(ratios > 0))/float(ratios.shape[1])

    def PFalsifyNormal(self, alt, trueModel=None):
        mu, sig = self.base.likeRatioMuSigma(alt.base, trueModel.base)
        print "Using rReps ="+str(self.rReps)
        return scipy.stats.norm.cdf(numpy.sqrt(self.rReps)*mu/sig)

    def likeRatioMuSigma(self, alt, trueModel=None):  # self is true model
        lrs = self.likeRatios(alt, trueModel)
        mu = numpy.mean(lrs)
        sig = numpy.std(lrs)
        return mu, sig

    def lrN(self, alt, N, M, trueModel=None):  # add N of them, return M
        self.sim(mReps=N * M)
        lrNM = self.likeRatios(alt, trueModel)
        L = numpy.reshape(lrNM, (M, N))
        return L.sum(axis=0)

    def aic(self, alt, trueModel=None):  # self is true model
        if trueModel is None:
            trueModel = self
        data = self.mRepsRestrictedData()
        return 2 * (self.logf(trueModel) - alt.logf(trueModel))

    def a_mn_sd(self, alt, trueModel=None):  # self is true model
        aics = self.aic(alt)
        mn = numpy.mean(aics)
        sd = numpy.std(aics)
        return (mn, sd)

    def aicN(self, alt, N, M, trueModel=None):  # add N of them, return M
        self.sim(mReps=N * M)
        aicNM = self.aic(alt)
        A = numpy.reshape(aicNM, (M, N))
        return A.sum(axis=0)

    def Ehlogf(self, data_h=None, trueModel=None):
        return (self.logf(trueModel).mean())

    def KL(self, other, trueModel=None):
        if trueModel is None:
            trueModel = self
        data = self.mRepsRestrictedData()
        return self.Ehlogf(data) - other.Ehlogf(data)

    # def pdfplot(self):
        #    assert(len(self.data)>99)
        #    m = min(self.data)
        #    M = max(self.data)
        #    X = numpy.arange(m,M,(M-m)/100)
        #    Y = []
        #    for x in X:
        #        Y.append(self.pdf(x))
        #    plt.plot(X,Y)
        #    plt.hist(self.data,50,normed=1)
        #    plt.show()


def toy3mlike4opt(q, data):
    mll = 0
    for datum in data:
        mll -= ad.admath.log(q[1]) + ad.admath.log(q[0])
        mll -= ad.admath.log((ad.admath.exp(-q[0] * datum) - ad.admath.exp(-q[1] * datum)) / (q[1] - q[0]))
    return mll


class likefun(object):
    def __init__(self, parent, paramTuple):
        self.parent = parent
        self.paramTuple = paramTuple
        self.F = self.parent.flatten()

    def set(self, valueTuple):
        for i, P in enumerate(self.paramTuple):
            P.assign(valueTuple[i])
        # Ex = self.parent.getExperiment()
        self.F.changeModel(self.parent)
        # self.F.changeModel(self.parent)

    def setLog(self, valueTuple):
        for i, P in enumerate(self.paramTuple):
            P.assignLog(valueTuple[i])  # AssignLog so that assigned values can vary from -infty to infty
        # Ex = self.parent.getExperiment()
        self.F.changeModel(self.parent)
        # self.F.changeModel(self.parent)

    def sim(self, XTrue, nReps=100, seed=None, log=True):
        self.XTrue = XTrue
        if log == True:
            self.setLog(XTrue)
        else:
            self.set(XTrue)
        self.F.reseed(seed)
        self.F.sim(nReps, clear=True)  # clear=True should now be redundant, but kept here for readability

    def minuslike(self, x):
        self.setLog(x)
        # if x[0] < 0. or x[1]<0:
        #    print "x is negative"
        #print "x[0], q[0]", x[0], q0.value
        #print "x[1], q[1]", x[1], q1.value
        return self.F.minuslike()

    def like(self, x, log=True):
        if log == True:
            self.setLog(x)
        else:
            self.set(x)
        return self.F.like()


class likefun1(object):  # One dimensional likelihood grid
    def __init__(self, parent, XParam, seed=None):
        self.parent = parent
        self.XParam = XParam
        self.F = self.parent.flatten(seed=seed)

    def setRange(self, XRange):
        self.XRange = XRange

    def set(self, X):
        self.XParam.assign(X)
        # Ex = self.parent.getExperiment()
        self.F.changeModel(self.parent)

    def sim(self, XTrue=15, nReps=100, seed=None):
        self.XTrue = XTrue
        self.set(XTrue)
        self.F.reseed(seed)
        self.F.sim(nReps, clear=True)  # clear=True should now be redundant, but kept here for readability

    def compute(self):
        self.llikes = []
        for x in self.XRange:
            self.set(x)
            self.llikes.append(self.F.like())

    def plot(self):
        plt.plot(self.XRange, self.llikes)
        plt.show()

    def addVLines(self):
        pass

    def replot(self, XTrue=15, nReps=100, seed=None):
        self.sim(XTrue=XTrue, nReps=nReps, seed=seed)
        self.compute()
        self.plot()


class likefun2(object):  # Two dimensional likelihood grid
    def __init__(self, parent, XParam, YParam):
        self.parent = parent
        self.XParam = XParam
        self.YParam = YParam


q0 = parameter.Parameter("q0", 0.5, "kHz", log=True)
q1 = parameter.Parameter("q1", 0.25, "kHz", log=True)
q = parameter.Parameter("q", 1. / 6., "kHz", log=True)
T3 = Toy([q0, q1])
T2 = Toy([q])
FT3 = T3.flatten(seed=3)
FT2 = T2.flatten(seed=3)
XRange = numpy.arange(0.1, 30.1, 1)
YRange = numpy.arange(0.11, 30.11, 1)  # Different values so rate constants remain unequal

# One dimensional likelihood plot with toy2 model
#plt.figure()
#LF2 = likefun1(T2,q)
#LF2.setRange(XRange)
#LF2.replot(XTrue=15.,seed=10,nReps=100)

#One-dimensional likelihood plot with toy3 modle
#plt.figure()
#LF3 = likefun1(T3,q0)
#LF3.setRange(XRange)
#LF3.replot(XTrue=15,seed=11,nReps=1000)
# LF = likefun(T3, [q0, q1])
# LF.sim((1., 2.), nReps=1000, seed=0, log=True)

#Histogram and PDFs
#plt.figure()
#FT3.sim(nReps=1000,clear=True)
#FT3.pdfplot()
#plt.figure()
#FT2.sim(nReps=1000,clear=True)
#FT2.pdfplot()
#plt.figure()
#q0.assign(2.)
#q1.assign(2.)
#FTE = T3.flatten(seed=4)
#FTE.sim(nReps=1000,clear=True)
#FTE.pdfplot()
