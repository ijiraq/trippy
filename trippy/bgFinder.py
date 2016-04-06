# -*- coding: utf-8 -*-
"""
Copyright (C) 2016  Wesley Fraser

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

__author__ = ('Wesley Fraser (@wtfastro, github: fraserw <westhefras@gmail.com>), '
              'Academic email: wes.fraser@qub.ac.uk')

import numpy as num
import pylab as pyl
from scipy import stats
from astropy.io import fits as pyf
from scipy import optimize as opti


class bgFinder(object):
    """
    Get the background estimate of the inputted data. eg.

    bgf=trippy.bgFinder.bgFinder(dataNumpyArray)

    Best to call it as
    bgf(mode,n)
    where n is optional and not called for every mode

    where mode can be
    median - simple median of the values
    histMode [n] - uses a histogram to estimate the mode, n is the number of bins in the histogram
    mean - simple mean of the values
    fraserMode [n] - the background modal estimate described in Fraser et al. (2016) TRIPPy paper.
                     n=0.1 to 0.2 seems to work best. This is the method most robust to background
                     sources in the data. Also works well in pure background data. This is probably
                     the most robust method.
    gaussFit - perform a approximate gaussian fit to the data, returning the mean fit value
    smart [n] - this first does a gaussFit. If the condition standard Deviation/mean**0.5 > n
                (where n is the # of standard deviations, ~3) is satisfied, it means you have
                contamination, in which case it reverts to fraserMode. Otherwise, the gaussian
                mean is returned.
    """
    def __init__(self, data):
        self.data = num.ravel(data)

    def __call__(self, method='median', inp=None):
        if method == 'median':
            return num.median(self.data)
        elif method == 'mean':
            return num.mean(self.data)
        elif method == 'histMode':
            bins = 50.0 if inp is None else inp
            return self._stats(bins)[0]
        elif method == 'fraserMode':
            n = 0.1 if inp is None else inp
            return self._fraserMode(n)
        elif method == 'gaussFit':
            return self._gaussFit()
        elif method == 'smart':
            return self.smartBackground()
        else:
            raise ValueError('Unknown method {}'.format(method))

    def histMode(self, nbins=50):
        return self._stats(nbins)[0]

    def median(self):
        return num.median(self.data)
    def mean(self):
        return num.mean(self.data)
    def fraserMode(self,multi=0.1):
        return self._fraserMode(multi)
    def gaussFit(self):
        return self._gaussFit()

    #ahist and stats generously donated by JJ Kavelaars from jjkmode.py
    def _ahist(self,nbins=50):
        b = num.sort(self.data)
        ## use the top and bottom octile to set the histogram bounds
        mx = b[len(b)-max(1,len(b)/100)]
        mn = b[len(b)-99*len(b)/100]
        w = ((mx-mn)/nbins)

        n = num.searchsorted(b,num.arange(mn,mx,w))
        n = num.concatenate([n, [len(b)]])
        return n[1:]-n[:-1],w,mn

    def _stats(self,nbins=50.):
        #returns mode, std of mode
        (b, w, l)=self._ahist(nbins)
        b[len(b)-1]=0
        b[0]=0
        am = num.argmax(b)
        c=b[b>(b[am]/2)]
        return am*w+l,(len(c)*w/2.0)/1.41

    def _fraserMode(self,multi=0.1):
        y=num.array(self.data*multi).astype(int)
        mode=stats.mode(y)[0]
        w=num.where(y==mode)
        return num.median(self.data[w[0]])

    def _gaussFit(self):
        med=num.median(self.data)
        std=num.std(self.data)

        res=opti.fmin(self._gaussLike,[med,std],disp=False)
        self.gauss=res
        return res[0]

    def _gaussLike(self,x):
        [m,s]=x[:]

        X=-num.sum((self.data-m)**2)/(2*s*s)
        X-=len(self.data)*num.log((2*num.pi*s*s)**0.5)
        #print X,m,s
        return -X


    def smartBackground(self,gaussStdLimit=1.1,backupMode='fraserMode',inp=None,verbose=False,display=False):
        """
        guassStdLimit=1.1 seemed the best compromise in my experience
        """
        self._gaussFit()
        (g,s)=self.gauss
        #print s,g**0.5,'&&'
        #print
        if (s/g**0.5)>gaussStdLimit:
            if inp<>None:
                if verbose: print '\nUsing backup mode %s with parameter %s.\n'%(backupMode,inp)
                g=self(backupMode,inp)
            if verbose: print '\nUsing backup mode %s.\n'%(backupMode)
            g=self(backupMode)

        if display:
            figHist=pyl.figure('backgroundHistogram')
            ax=figHist.add_subplot(111)
            pyl.hist(self.data,bins=min(100,len(self.data)/10))
            (y0,y1)=ax.get_ylim()
            pyl.plot([g,g],[y0,y1],'r-',lw=2)
            pyl.title('Background %s'%(g))
            pyl.show()
        return g
    """
    def midBackground(self):
        x=num.array([self._gaussFit(),self.median(),self.mean(),self.fraserMode(),self.histMode()])
        args=num.argsort(x)
        if args[2]==0:
            print 'Adopting the Gaussian Fit.'
        elif args[2]==1:
            print 'Adopting the median.'
        elif args[2]==2:
            print 'Adopting the mean.'
        elif args[2]==3:
            print 'Adopting the Fraser mode.'
        else:
            print 'Adopting the JJK mode.'
        return x[args[2]]
    """

if __name__=="__main__":

    with pyf.open('junk.fits') as han:
        data=han[1].data

    #near source
    x,y=3275,2266
    #cosmic ray
    x,y=3179,2314
    #out of source
    x,y=3205,2260
    #funny place
    x,y= 3093,2422

    w=15

    data=data[y-w:y+w+1,x-w:x+w+1].reshape((2*w+1)**2)

    bg=bgFinder(data)
    mean=bg.mean()
    median=bg.median()
    histo=bg.histMode()
    fmode=bg.fraserMode(0.1)
    gauss=bg.gaussFit()
    smart=bg.smartBackground(inp=0.1)


    print 'Mean',mean
    print 'Median',median
    print 'JJKMode',histo
    print 'FraserMode',fmode
    print 'Gauss Fit',gauss
    print 'Smart Background',smart


    fig=pyl.figure(1)
    ax=fig.add_subplot(111)
    pyl.hist(data,bins=w*20)
    (y0,y1)=ax.get_ylim()
    pyl.plot([mean,mean],[0,y1],label='mean',lw=2)
    pyl.plot([median,median],[0,y1],label='median',lw=2)
    pyl.plot([histo,histo],[0,y1],label='JJKMode',lw=2)
    pyl.plot([fmode,fmode],[0,y1],label='Fraser Mode',lw=2)
    pyl.plot([gauss,gauss],[0,y1],label='Gauss Fit',lw=2)
    pyl.legend()
    pyl.show()
