import channel
import numpy as np
import random
import parameter

def equilQ(Q):
    (V,D) = np.linalg.eig(Q.T)   # eigenspace
    imin = np.argmin(np.absolute(V))  # index of 0 eigenvalue
    eigvect0 = D[:,imin]  # corresponding eigenvector
    return eigvect0.T/sum(eigvect0) # normalize and return (fixes sign)
class Patch(object):
    def __init__(self, channels):
        self.channels = channels
        self.assertOneChannel()
        self.Q = self.ch.makeQ()
        self.R = random.Random()
        self.Mean = self.ch.makeMean()
        self.Std = self.ch.makeStd()
    def assertOneChannel(self):
        assert(len(self.channels) == 1)
        assert(self.channels[0][0] == 1)
        self.ch = self.channels[0][1]
        assert(isinstance(self.ch,channel.Channel))
    def equilibrium(self):
        self.Q = self.ch.makeQ()
        return equilQ(self.Q)
    def select(self,mat,row=0):  # select from matrix[row,:]
        p = self.R.random()
        rowsum = 0
        for col in range(mat.shape[1]):  # iterate over columns of mat
            rowsum += mat[row, col]  # row constant passed into select
            if p < rowsum:
                return col
        assert(False)
    def sim(self,seed=None,firstState=None,dt=None,tstop=None):
        if not seed == None:  # if seed not passed, don't initialize R
            self.R.seed(seed)
        self.simStates = []
        if firstState == None: # if firstState not passed draw from equilibrium
            s = self.select(self.equilibrium())
            self.simStates.append(s)
        else:
            self.simStates.append(firstState)
        if tstop == None:  # use tstop from parameter module if not passed
            tstop = parameter.tstop
        if dt == None:  # use tstop from parameter module if not passed
            dt = parameter.dt
        return self.simStates
            
P = Patch([(1, channel.khh)])