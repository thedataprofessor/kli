__author__ = 'sean'
import numpy
import toy
import scipy

class Repetitions(toy.FlatToy):
    def __init__(self, base, rReps):
        self.base = base
        self.rReps= rReps
        self.stack = []
        super(Repetitions, self).__init__(base)

    def defineRepetitions(self):
        pass

    def initRNG(self, seed=None):
        pass

    def setUpExperiment(self, base):
        pass
        # self.base = base # moved to __init__() to avoid errors in debug

    def _reseed(self, seed=None):
        self.base._reseed(seed)

    def _restart(self):
        self.data = []
        self.likes = []
        self.base._restart()

    def push_mReps(self, reps=None):
        if reps is None:
            reps = self.mReps * self.rReps
        self.stack.append(self.base.mReps)
        self.base.sim(reps)

    def pop_mReps(self):
        assert len(self.stack) > 0
        reps = self.stack.pop(-1)
        self.base.sim(reps)

    def extendBaseData(self, reps):
        self.push_mReps(reps)
        self.pop_mReps()

    def extendBaseLikes(self, trueModel=None, reps=None):
        if trueModel is None:
            trueModel = self
        trueModel.push_mReps(reps)
        self.base.likelihoods(trueModel.base)
        trueModel.pop_mReps()

    def sim(self, mReps=None):
        if mReps is None:
            mReps = int(len(self.base.data) / self.rReps)
        self.extendBaseData(self.rReps*mReps)
        for r in range(len(self.data),mReps):
            datum = [self.base.data[r*self.rReps + d] for d in range(self.rReps)]
            self.data.append(datum)
        self.mReps = mReps

    def likelihoods(self, trueModel=None):
        if trueModel is None:
            trueModel = self
        assert trueModel.rReps == self.rReps
        likes = trueModel.likes.getOrMakeEntry(self)
        baseLikes = trueModel.base.likes.getOrMakeEntry(self.base)
        self.extendBaseLikes(trueModel)
        nFirst = len(likes)
        nLast = trueModel.mReps
        for n in range(nFirst, nLast):
            likeum = [baseLikes[n*trueModel.rReps + d] for d in range(trueModel.rReps)]
            likes.append(sum(likeum))
        return likes[0:nLast]

    def _debug(self, flag=None):
        return self.base._debug(flag)

    def simulateOnce(self, RNG=None):
        return [self.base.simulateOnce(RNG) for d in range(self.rReps)]

    # Bad because recomputes likes rather than using base.likes
    def likeOnce(self, datum):
        assert self.datumWellFormed(datum)
        logLike = 0
        for datumComponent in datum:
            logLike += self.base.likeOnce(datumComponent)  # These are numbers
        return logLike

    def datumWellFormed(self, datum):
        mustBeTrue = (len(datum) == self.rReps)
        for d in datum:
            mustBeTrue = (mustBeTrue and self.base.datumWellFormed(d))
        return mustBeTrue

    def PFalsify_function_of_rReps(self, alt, trueModel=None, rReps=None, mReps=1):
        if trueModel is None:
            trueModel = self
        if rReps is None:
            rReps = [trueModel.rReps]  # Can pass longer list of rReps: [1, 2, 3, 4, 5, 6, etc.]
        probabilities = []
        for reps in rReps:
            repeated_self, repeated_alt, repeated_true = self.repeated_models(alt, trueModel, reps, mReps)
            Pr = repeated_self.PFalsify(repeated_alt, repeated_true)
            probabilities.append(Pr)
        return probabilities

    def PFalsifyNormal(self, alt, trueModel=None):
        if trueModel is None:
            trueModel = self
        trueModel.push_mReps()
        mu, sig = self.base.likeRatioMuSigma(alt.base, trueModel.base)
        trueModel.pop_mReps()
        return scipy.stats.norm.cdf(numpy.sqrt(self.rReps)*mu/sig)

    def rInfinity(self, alt, trueModel=None, C=0.95):
        if trueModel is None:
            trueModel = self
        trueModel.push_mReps()
        mu, sig = self.base.likeRatioMuSigma(alt.base, trueModel.base)
        trueModel.pop_mReps()
        return (scipy.stats.norm.ppf(C)*sig/mu)**2

    def repeated_models(self, alt, trueModel=None, rReps=1, mReps=1):
        if trueModel is None:
            trueModel = self
        repeated_self = Repetitions(self.base, rReps)
        repeated_alt = Repetitions(alt.base, rReps)
        if trueModel is self:
            repeated_true = repeated_self
        elif trueModel is alt:
            repeated_true = repeated_alt
        else:
            repeated_true = Repetitions(trueModel.base, rReps)
        repeated_true.sim(mReps)  # if reps is None then use available data in trueModel.base
        return repeated_self, repeated_alt, repeated_true

    def rPlus(self, alt, trueModel=None, rMinus=None, PrMinus=None, C=0.95, mReps=None):
        if trueModel is None:
            trueModel = self
        if rMinus is None:
            rMinus = self.rInfinity(alt, trueModel, C)
        rMinus = max(1, int(rMinus))  # Make a positive integer
        if PrMinus is None:
            repeated_self, repeated_alt, repeated_true = self.repeated_models(alt, trueModel, rMinus, mReps)
            PrMinus = repeated_self.PFalsify(repeated_alt, repeated_true)
        cv = numpy.sqrt(rMinus)/scipy.stats.norm.ppf(PrMinus)
        return (scipy.stats.norm.ppf(C)*cv)**2

    def rMinus2Plus_plot(self, alt, trueModel, rMinus, rPlus, C):
        pass

    def rStar(self, alt, trueModel=None, rMinus=None, C=0.95, reps=None, iter=10, plot=False):
        for i in range(iter):
            rMinus = rPlus if i > 0 else rMinus
            rPlus = self.rPlus(alt, trueModel, rMinus, None, C, reps)
            print "Iteration: ", i, "| Value of R:", rMinus
        if plot:
            self.rMinus2Plus_plot(alt, trueModel, rMinus, rPlus, C)
        return rMinus

    def lrN(self, alt, N, M):
        print "Don't call lrN from Reps class"
        assert False

    def aicN(self, alt, N, M):
        print "Don't call aicN from Reps class"
        assert False

