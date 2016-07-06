import numpy
import scipy
import pylab
import numbers
from datetime import datetime
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.collections import PolyCollection

from matplotlib.mlab import dist
from matplotlib.patches import Circle, Rectangle
from matplotlib.lines import Line2D
from matplotlib.transforms import blended_transform_factory
from matplotlib.widgets import Cursor

class Plot():
    """
    Basic 'plot' class containing functions for various types of plots.
    """

    _plot_id_num = 0

    def __init__(self):
        self._time = datetime.now()
        self.id = 'plot_{}'.format(Plot._plot_id_num)
        Plot._plot_id_num += 1
        self.fig = None

    @property
    def id(self):
        return self.__id

    @id.setter
    def id(self, id):
        self.__id = id

    @property
    def fig(self):
        return self._fig

    @fig.setter
    def fig(self, fig):
        if fig is None or isinstance(fig, Figure):
            self._fig = fig
        else:
            raise TypeError('fig must be of type matplotlib.figure.Figure.')

    def _plot_ppm(self, data, params, 
            upper_ppm=None, 
            lower_ppm=None, 
            color='k', 
            lw=1,
            filename=None):
        if not Plot._is_flat_iter(data): 
            raise AttributeError('data must be flat iterable.')
        if upper_ppm is not None and lower_ppm is not None:
            if upper_ppm == lower_ppm or upper_ppm < lower_ppm:
                raise ValueError('ppm range specified is invalid.')
        sw_left = params['sw_left']
        sw = params['sw']

        if upper_ppm is None:
            upper_ppm = sw_left
        if lower_ppm is None:
            lower_ppm = sw_left-sw

        ppm = numpy.linspace(sw_left-sw, sw_left, len(data))[::-1]
        ppm_bool_index = (ppm < upper_ppm) * (ppm > lower_ppm)
        ppm = ppm[ppm_bool_index]
        data = data[ppm_bool_index]

        self.fig = pylab.figure(figsize=[10,5])
        ax = self.fig.add_subplot(111)
        ax.plot(ppm, data, color=color, lw=lw)
        ax.invert_xaxis()
        ax.set_xlim([upper_ppm, lower_ppm])
        ax.grid()
        ax.set_xlabel('PPM (%.2f MHz)'%(params['reffrq']))
        #self.fig.show()
        if filename is not None:
            self.fig.savefig(filename, format='pdf')

    def _deconv_generator(self, fid,
            upper_ppm=None, 
            lower_ppm=None, 
            ):

        data = fid.data
        params = fid._params

        if not Plot._is_flat_iter(data): 
            raise AttributeError('data must be flat iterable.')

        peakshapes = fid._f_pks_list(fid._deconvoluted_peaks, numpy.arange(len(data))) 

        if not Plot._is_iter_of_iters(peakshapes): 
            raise AttributeError('data must be flat iterable.')
        if upper_ppm is not None and lower_ppm is not None:
            if upper_ppm == lower_ppm or upper_ppm < lower_ppm:
                raise ValueError('ppm range specified is invalid.')
        sw_left = params['sw_left']
        sw = params['sw']

        if upper_ppm is None:
            upper_ppm = sw_left
        if lower_ppm is None:
            lower_ppm = sw_left-sw

        ppm = numpy.linspace(sw_left-sw, sw_left, len(data))[::-1]
        ppm_bool_index = (ppm <= upper_ppm) * (ppm >= lower_ppm)
        ppm = ppm[ppm_bool_index]
        data = data[ppm_bool_index]
        peakshapes = peakshapes[:, ppm_bool_index]
        summed_peaks = peakshapes.sum(0)
        residual = data-summed_peaks
        return ppm, data, peakshapes, summed_peaks, residual, upper_ppm, lower_ppm

    def _plot_deconv(self, fid,
            upper_ppm=None, 
            lower_ppm=None, 
            colour='k', 
            peak_colour='b', 
            summed_peak_colour='r', 
            residual_colour='g', 
            lw=1):

        #validation takes place in self._deconv_generator
        ppm, data, peakshapes, summed_peaks, residual, upper_ppm, lower_ppm = self._deconv_generator(fid,
                                                                                upper_ppm=upper_ppm,
                                                                                lower_ppm=lower_ppm)

        self.fig = pylab.figure(figsize=[10,5])
        ax = self.fig.add_subplot(111)
        ax.plot(ppm, residual, color=residual_colour, lw=lw)
        ax.plot(ppm, data, color=colour, lw=lw)
        ax.plot(ppm, summed_peaks, '--', color=summed_peak_colour, lw=lw)
        label_pad = 0.02*peakshapes.max()
        for n in range(len(peakshapes)):
            peak = peakshapes[n]
            ax.plot(ppm, peak, '-', color=peak_colour, lw=lw)
            ax.text(ppm[numpy.argmax(peak)], label_pad+peak.max(), str(n), ha='center')
        ax.invert_xaxis()
        ax.set_xlim([upper_ppm, lower_ppm])
        ax.grid()
        ax.set_xlabel('PPM (%.2f MHz)'%(fid._params['reffrq']))
        
    def _plot_deconv_array(self, fids,
            upper_index=None, 
            lower_index=None, 
            upper_ppm=None, 
            lower_ppm=None, 
            data_colour='k', 
            #peak_colour='b', 
            summed_peak_colour='r', 
            residual_colour='g', 
            data_filled=False,
            summed_peak_filled=True,
            residual_filled=False,
            figsize=[15, 7.5],
            lw=0.3, 
            azim=-90, 
            elev=20, 
            filename=None):

        if lower_index is None:
            lower_index = 0
        if upper_index is None:
            upper_index = len(fids)-1
        if lower_index >= upper_index:
            raise ValueError('upper_index must exceed lower_index')
        fids = fids[lower_index: upper_index]
        generated_deconvs = []
        for fid in fids:
            generated_deconvs.append(self._deconv_generator(fid, upper_ppm=upper_ppm, lower_ppm=lower_ppm))
      
        params = fids[0]._params 
        ppm = generated_deconvs[0][0]
        data = [i[1] for i in generated_deconvs]
        peakshapes = [i[2] for i in generated_deconvs]
        summed_peaks = [i[3] for i in generated_deconvs]
        residuals = [i[4] for i in generated_deconvs]
        upper_ppm = generated_deconvs[0][5]
        lower_ppm = generated_deconvs[0][6]

        plot_data = numpy.array([
                    residuals, 
                    data, 
                    summed_peaks,
                    ])
        colours_list = [
                    [residual_colour]*len(residuals),
                    [data_colour]*len(data), 
                    [summed_peak_colour]*len(summed_peaks), 
                    ]
        filled_list = [
                    residual_filled,
                    data_filled, 
                    summed_peak_filled, 
                    ] 

        xlabel = 'PPM (%.2f MHz)'%(params['reffrq'])
        ylabel = 'min.'
        acqtime = fids[0]._params['acqtime'][0]
        minutes = numpy.arange(len(data))*acqtime
        self.fig = self._generic_array_plot(ppm, minutes, plot_data, 
                                            colours_list=colours_list,
                                            filled_list=filled_list,
                                            figsize=figsize, 
                                            xlabel=xlabel,
                                            ylabel=ylabel,
                                            lw=lw, 
                                            azim=azim, 
                                            elev=elev, 
                                            )
        if filename is not None:
            self.fig.savefig(filename, format='pdf')
        self.fig.show()
          
        

    def _plot_array(self, data, params, 
                upper_index=None, 
                lower_index=None, 
                upper_ppm=None, 
                lower_ppm=None, 
                figsize=[15, 7.5],
                lw=0.3, 
                azim=-90, 
                elev=20, 
                filled=False, 
                show_zticks=False, 
                labels=None, 
                colour=True,
                filename=None,
                ):

        if not Plot._is_iter_of_iters(data): 
            raise AttributeError('data must be 2D.')
        if upper_ppm is not None and lower_ppm is not None:
            if upper_ppm == lower_ppm or upper_ppm < lower_ppm:
                raise ValueError('ppm range specified is invalid.')
        if upper_index is not None and lower_index is not None:
            if upper_index == lower_index or upper_index < lower_index:
                raise ValueError('index range specified is invalid.')


        sw_left = params['sw_left']
        sw = params['sw']

        if upper_index is None:
            upper_index = len(data)
        if lower_index is None:
            lower_index = 0
        
        if upper_ppm is None:
            upper_ppm = sw_left
        if lower_ppm is None:
            lower_ppm = sw_left-sw

        ppm = numpy.linspace(sw_left-sw, sw_left, data.shape[1])[::-1]
        ppm_bool_index = (ppm < upper_ppm) * (ppm > lower_ppm)
        ppm = ppm[ppm_bool_index]
        if len(data) > 1:
            data = data[lower_index:upper_index, ppm_bool_index]
        else:
            data = data[:, ppm_bool_index]

        if colour:
            colours_list = [pylab.cm.viridis(numpy.linspace(0, 1, len(data)))]
        else:
            colours_list = None

        acqtime = params['acqtime'][0]
        minutes = numpy.arange(len(data))*acqtime

        xlabel = 'PPM (%.2f MHz)'%(params['reffrq'])
        ylabel = 'min.'
        self.fig = self._generic_array_plot(ppm, minutes, [data], 
                                            colours_list=colours_list,
                                            filled_list=[filled],
                                            figsize=figsize, 
                                            xlabel=xlabel,
                                            ylabel=ylabel,
                                            lw=lw, 
                                            azim=azim, 
                                            elev=elev, 
                                            )
        if filename is not None:
            self.fig.savefig(filename, format='pdf')
        self.fig.show()

    @staticmethod
    def _interleave_datasets(data):
        """
        interleave a list of lists with equal dimensions
        """
        idata = []
        for y in range(len(data[0])):
            for x in range(len(data)):
                idata.append(data[x][y])
        return idata

    def _generic_array_plot(self, x, y, zlist, 
                colours_list=None, 
                filled_list=None, 
                upper_lim=None,
                lower_lim=None,
                lw=0.3, 
                azim=-90, 
                elev=20, 
                figsize=[5,5],
                show_zticks=False, 
                labels=None, 
                xlabel=None,
                ylabel=None,
                filename=None,
        ):
        """

        Generic function for plotting arrayed data on a set of 3D axes. x and y
        must be 1D arrays. zlist is a list of 2D data arrays, each of which will be
        plotted with the corresponding colours_list colours, and filled_lists filled
        state.

        """

        


        if colours_list is None:
            colours_list = [['k']*len(y)]*len(zlist)

        if filled_list is None:
            filled_list = [False]*len(zlist)


        fig = pylab.figure(figsize=figsize)
        ax = fig.add_subplot(111, projection='3d', azim=azim, elev=elev)

        for data_n in range(len(zlist)):
            data = zlist[data_n]
            bh = abs(data.min()) 
            filled = filled_list[data_n]
            cl = colours_list[data_n]
            if not filled:
                #spectra are plotted in reverse for zorder
                for n in range(len(data))[::-1]:
                    datum = data[n]
                    clr = cl[n]
                    ax.plot(x, len(datum)*[y[n]], datum, color=clr, lw=lw)
            if filled:
                verts = []
                plot_data = data+bh 
                for datum in plot_data:
                    datum[0], datum[-1] = 0, 0
                    verts.append(list(zip(x, datum)))
                 
                fclr, eclr = ['w']*len(data), ['k']*len(data)
                fclr = cl
                poly = PolyCollection(verts, 
                    facecolors=fclr,
                    edgecolors=eclr,
                    linewidths=[lw]*len(verts))
                ax.add_collection3d(poly, zs=y, zdir='y')
    
        ax.set_zlim([0, 1.1*max(numpy.array(zlist).flat)])
        ax.invert_xaxis()
        if upper_lim is None:
            upper_lim = x[0]
        if lower_lim is None:
            lower_lim = x[-1]
        ax.set_xlim([upper_lim, lower_lim])
        ax.set_ylim([y[0], y[-1]])
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        if not show_zticks:
            ax.set_zticklabels([])
        return fig
        

    @classmethod
    def _is_iter(cls, i):
        try:
            iter(i)
            return True
        except TypeError:
            return False

    @classmethod
    def _is_iter_of_iters(cls, i):
        if i == []:
            return False
        elif cls._is_iter(i) and all(cls._is_iter(j) for j in i):
            return True
        return False

    @classmethod
    def _is_flat_iter(cls, i):
        if i == []:
            return True
        elif cls._is_iter(i) and not any(cls._is_iter(j) for j in i):
            return True
        return False

class Phaser:
    """Interactive phase-correction widget"""
    def __init__(self, fid):
        if not Plot._is_flat_iter(fid.data): 
            raise ValueError('data must be flat iterable.')
        if fid.data == [] or fid.data == None:
            raise ValueError('data must exist.')
        self.fid = fid
        self.fig = pylab.figure(figsize=[15, 7.5])
        self.phases = numpy.array([0.0, 0.0])
        self.y = 0.0
        self.ax = self.fig.add_subplot(111)
        self.ax.plot(self.fid.data, color='k', linewidth=1.0)
        self.ax.hlines(0, 0, len(self.fid.data)-1)
        self.ax.set_xlim([0, len(self.fid.data)])
        xtcks = numpy.linspace(0,1,10)*len(self.fid.data)
        xtcks[-1] = xtcks[-1]-1
        self.ax.set_xticks(xtcks)
        self.ax.set_xlabel('PPM (%.2f MHz)'%(self.fid._params['reffrq']))
        self.ax.set_xticklabels([numpy.round(self.fid._ppm[int(i)], 1) for i in xtcks])
        ylims = numpy.array([-6, 6])*numpy.array([max(self.ax.get_ylim())]*2)
        self.ax.set_ylim(ylims)
        self.ax.grid()
        self.visible = True
        self.canvas = self.ax.figure.canvas
        self.canvas.mpl_connect('motion_notify_event', self.onmove)
        self.canvas.mpl_connect('button_press_event', self.press)
        self.canvas.mpl_connect('button_release_event', self.release)
        self.pressv = None
        self.buttonDown = False
        self.prev = (0, 0)
        self.ax.text(0.05 *self.ax.get_xlim()[1],0.7 *self.ax.get_ylim()[1],'phasing\nleft - zero-order\nright - first order')
        cursor = Cursor(self.ax, useblit=True, color='k', linewidth=0.5)
        cursor.horizOn = False
        self.fig.show()

    def press(self, event):
        tb = pylab.get_current_fig_manager().toolbar
        if tb.mode == '':
            x, y = event.xdata, event.ydata
            if event.inaxes is not None:
                self.buttonDown = True
                self.button = event.button
                self.y = y

    def release(self, event):
        self.buttonDown = False
        print('p0: {} p1: {}'.format(*self.phases))
        return False

    def onmove(self, event):
        if self.buttonDown is False or event.inaxes is None:
                return
        x = event.xdata
        y = event.ydata
        dy = y-self.y
        self.y = y
        if self.button == 1:
                self.phases[0] = 100*dy/self.ax.get_ylim()[1]
        if self.button == 3:
                self.phases[1] = 100*dy/self.ax.get_ylim()[1]
        self.fid.ps(p0=self.phases[0], p1=self.phases[1])
        self.ax.lines[0].set_data(numpy.array([numpy.arange(len(self.fid.data)), self.fid.data]))
        self.canvas.draw()  # _idle()
        return False

class DataSelector:
    """Interactive selector widget"""
    def __init__(self, data, params, 
                peaks=None, 
                ranges=None, 
                title=None, 
                voff=0.3, 
                label=None):
        if not Plot._is_iter(data):
            raise AttributeError('data must be iterable.')
        self.fig = pylab.figure(figsize=[15, 7.5])
        self.data = numpy.array(data)
        self.peaklines = {}
        self.rangespans = []
        self.ax = self.fig.add_subplot(111)
        if len(self.data.shape)==1:
            ppm = numpy.mgrid[params['sw_left']-params['sw']:params['sw_left']:complex(data.shape[0])]
            self.ax.plot(ppm[::-1], data, color='k', lw=1)
        elif len(self.data.shape)==2:
            cl = dict(zip(range(len(data)), pylab.cm.viridis(numpy.linspace(0,1,len(data)))))
            ppm = numpy.mgrid[params['sw_left']-params['sw']:params['sw_left']:complex(data.shape[1])]
            inc_orig = voff*data.max()
            inc = inc_orig.copy()
            #this is reversed for zorder
            for i,j in zip(range(len(data))[::-1], data[::-1]):
                self.ax.plot(ppm[::-1], j+inc, color=cl[i], lw=1)
                inc -= inc_orig/len(data)
        self.ax.set_xlabel('ppm')
        self.rectprops = dict(facecolor='0.5', alpha=0.2)
        self.visible = True
        self.canvas = self.ax.figure.canvas
        self.canvas.mpl_connect('motion_notify_event', self.onmove)
        self.canvas.mpl_connect('button_press_event', self.press)
        self.canvas.mpl_connect('button_release_event', self.release)
        self.minspan = 0
        self.rect = None
        self.pressv = None
        self.buttonDown = False
        self.prev = (0, 0)
        trans = blended_transform_factory(
            self.ax.transData,
            self.ax.transAxes)
        w, h = 0, 1
        self.rect = Rectangle([0, 0], w, h,
                              transform=trans,
                              visible=False,
                              **self.rectprops
                              )
        self.ax.add_patch(self.rect)
        self.ranges = []
        self.peaks = []
        if peaks is not None:
            self.peaks = list(peaks)
        if ranges is not None:
            self.ranges = list(ranges)
        self.ylims = numpy.array([self.ax.get_ylim()[0], self.data.max() + abs(self.ax.get_ylim()[0])])
        self.ax.set_ylim(self.ylims)#self.ax.get_ylim()[0], self.data.max()*1.1])
        self.ax_lims = self.ax.get_ylim()
        self.xlims = [ppm[-1], ppm[0]]
        self.ax.set_xlim(self.xlims)
        for x in self.peaks:
            self.peaklines[x] = self.makeline(x)
        for rng in self.ranges:
            self.rangespans.append(self.makespan(rng[1], rng[0]-rng[1]))
        cursor = Cursor(self.ax, useblit=True, color='k', linewidth=0.5)
        cursor.horizOn = False
        self.fig.suptitle(title, size=20)
        self.ax.text(
            0.95 *
            self.ax.get_xlim()[0],
            0.7 *
            self.ax.get_ylim()[1],
            label),
        self.ax.set_ylim(self.ylims)
        pylab.show()

    def makespan(self, left, width):
        return self.ax.bar(left=left,
                        height=sum(abs(self.ylims)),
                        width=width,
                        bottom=self.ylims[0],
                        alpha=0.2,
                        color='0.5',
                        edgecolor='k')
    def makeline(self, x):
        return self.ax.vlines(x, self.ax_lims[0], self.ax_lims[1], color='#CC0000', lw=1)

    def press(self, event):
        tb = pylab.get_current_fig_manager().toolbar
        if tb.mode == '':
            x = numpy.round(event.xdata, 2)
            if event.button == 2:
                if event.key == None:
                    #find and delete nearest peakline
                    if len(self.peaks) > 0:
                        x = event.xdata
                        delete_peak = numpy.argmin([abs(i-x) for i in self.peaks])
                        old_peak = self.peaks.pop(delete_peak)
                        peakline = self.peaklines.pop(old_peak)
                        peakline.remove()
                elif event.key == 'control':
                    #find and delete range
                    if len(self.ranges) > 0:
                        x = event.xdata
                        rng = 0
                        while rng < len(self.ranges):
                            if x >= (self.ranges[rng])[1] and x <= (self.ranges[rng])[0]:
                                self.ranges.pop(rng) 
                                rangespan = self.rangespans.pop(rng)
                                rangespan.remove()
                                break
                            rng += 1
            if event.button == 3:
                self.buttonDown = True
                self.pressv = event.xdata
            if event.button == 1 and (x >= self.xlims[1]) and (x <= self.xlims[0]):
                self.peaks.append(x)
                self.peaklines[x] = self.makeline(x)
                print(x)
                self.peaks = sorted(self.peaks)[::-1]
            self.canvas.draw()

    def release(self, event):
        if self.pressv is None or not self.buttonDown:
            return
        self.buttonDown = False
        self.rect.set_visible(False)
        vmin = numpy.round(self.pressv, 2)
        vmax = numpy.round(event.xdata or self.prev[0], 2)
        if vmin > vmax:
            vmin, vmax = vmax, vmin
        span = vmax - vmin
        self.pressv = None
        spantest = False
        if len(self.ranges) > 0:
            for i in self.ranges:
                print(i, vmin, vmax)
                if (vmin >= i[1]) and (vmin <= i[0]):
                    spantest = True
                if (vmax >= i[1]) and (vmax <= i[0]):
                    spantest = True
        if span > self.minspan and spantest is False:
            self.ranges.append([numpy.round(vmin, 2), numpy.round(vmax, 2)])
            self.rangespans.append(self.makespan(vmin, span))
        #self.ax.set_ylim(self.ylims)
        self.canvas.draw()
        self.ranges = [numpy.sort(i)[::-1] for i in self.ranges]
        return False

    def onmove(self, event):
        if self.pressv is None or self.buttonDown is False or event.inaxes is None:
                return
        self.rect.set_visible(self.visible)
        x, y = event.xdata, event.ydata
        self.prev = x, y
        v = x
        minv, maxv = v, self.pressv
        if minv > maxv:
                minv, maxv = maxv, minv
        self.rect.set_xy([minv, self.rect.xy[1]])
        self.rect.set_width(maxv-minv)
        vmin = self.pressv
        vmax = event.xdata  # or self.prev[0]
        if vmin > vmax:
                vmin, vmax = vmax, vmin
        self.canvas.draw_idle()
        return False

class DataTraceSelector:
    """Interactive integral-selection widget"""
    def __init__(self, fid_array):
        if fid_array.data == [] or fid_array.data == None:
            raise ValueError('data must exist.')
        data = fid_array.data
        params = fid_array._params
        sw_left = params['sw_left']
        sw = params['sw']

        ppm = numpy.linspace(sw_left-sw, sw_left, data.shape[1])[::-1]
        self.linebuilder = LineBuilder(
            x=ppm, 
            y=fid_array.data, 
            invert_x=True,
            xlabel='ppm',
            )
        self.traces = self.linebuilder.data_lines
        

class LineBuilder:
    def __init__(self, 
        x=None,
        y=None,
        invert_x=False,
        figsize=[15,7.5],
        lw=1,
        voff=0.1,
        xlabel=None,
        ylabel=None,
        ):
        self.x = x
        self.y = y
        self.lw = lw
        self.voff = 0.1
        self.y_indices = numpy.arange(0, self.voff*len(self.y), self.voff)
        self.xs = []
        self.ys = []
        self._x = None
        self._y = None
        self.datax = None
        self.datay = None
        self.lines = []
        self.data_lines = []
        self._visual_lines = []
        self.fig = pylab.figure(figsize=figsize)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_title('click to build line segments\nright-click to finish line\nctrl-click deletes nearest line')
        for i in range(len(y)):
            self.ax.plot(x, y[i]+self.y_indices[i], '-k')
        if invert_x:
            self.ax.invert_xaxis()
        self.ax.set_xlim([x[0], x[-1]])
        self.ax.set_xlabel(xlabel)
        self.ax.set_ylabel(ylabel)
        self.line = None
        self.data_line = None
        self.canvas = self.fig.canvas
        self.cid_press = self.canvas.mpl_connect('button_press_event', self.on_press)
        self.cid_release = self.canvas.mpl_connect('button_release_event', self.on_release)
        self.cid_move = self.canvas.mpl_connect('motion_notify_event', self.on_move)
        self.fig.show()
        self.background = self.canvas.copy_from_bbox(self.ax.bbox)
        self._drawing = False

    def check_mode(self):
        tb = pylab.get_current_fig_manager().toolbar
        return tb.mode
        
    def on_press(self, event):
        if self.check_mode() != '':
            return
        if event.xdata is None or event.ydata is None:
            return
        if event.button == 1:
            if event.key == 'control':
                if len(self._visual_lines) > 0:
                    x = event.xdata
                    y = event.ydata
                    trace_dist = [[i[0]-x, i[1]-y] for i in self.lines]
                    delete_trace = numpy.argmin([min(numpy.sqrt(i[0]**2+i[1]**2)) for i in trace_dist])
                    self.lines.pop(delete_trace)
                    trace = self._visual_lines.pop(delete_trace)
                    trace.remove()
                    self.canvas.draw()
                    self.background = self.canvas.copy_from_bbox(self.ax.bbox)
            else:
                self.xs.append(event.xdata)
                self.ys.append(event.ydata)
                if self.line is None:
                    self.line, = self.ax.plot(self.xs, self.ys, '-+', color='r', lw=self.lw, animated=True)
                self.line.set_data(self.xs, self.ys)
                self.background = self.canvas.copy_from_bbox(self.ax.bbox)
                self.ax.draw_artist(self.line)
                self.canvas.blit(self.ax.bbox) 
                self.data_line = None

        if event.button == 3 and self.line is not None:
            if len(self.xs) > 1:
                self._visual_lines.append(self.ax.plot(self.xs, self.ys, '-+', color='b', lw=self.lw)[0])
                self.canvas.draw()
                self.background = self.canvas.copy_from_bbox(self.ax.bbox)
                self.lines.append(numpy.array([self.xs, self.ys]))
                self.xs, self.ys = [], []
                self.line = None
                line_x = []
                line_y = []
                for i in range(len(self.lines[-1][0])-1):
                    line = self.lines[-1]
                    x1, y1, x2, y2 = line[0][i], line[1][i], line[0][i+1], line[1][i+1]
                    x, y = self.get_neighbours([x1, x2], [y1, y2])
                    if x is not None and y is not None:
                        line_x = line_x+list(x)
                        line_y = line_y+list(y)
                self.data_lines.append([line_x, line_y])
            else:
                self.canvas.draw()
                self.background = self.canvas.copy_from_bbox(self.ax.bbox)
                self.xs, self.ys = [], []
                self.line = None
            

    def on_release(self, event):
        if self.check_mode() != '':
            redraw_line = False
            if self.line is not None:
                redraw_line = True
                self.line = None
            self.canvas.draw()
            self.background = self.canvas.copy_from_bbox(self.ax.bbox)
            if redraw_line:
                self.line, = self.ax.plot(self.xs, self.ys, '-+', color='r', lw=self.lw, animated=True)
            return

    def on_move(self, event):
        if self.check_mode() == 'pan/zoom':
            return
        if self.line is None:
            return
        self.canvas.restore_region(self.background)
        self._x, self._y = event.xdata, event.ydata
        if self._x is None or self._y is None:
            return
        self.line.set_data(self.xs+[self._x], self.ys+[self._y])
        self.ax.draw_artist(self.line)
        self.datax, self.datay = self.get_neighbours([self.xs[-1], self._x], [self.ys[-1], self._y]) 
        if self.data_line is None and self.datax is not None and self.datay is not None:
            self.data_line, = self.ax.plot(self.datax, self.datay, 'o', color='r', animated=True)
        if self.data_line is not None and self.datax is not None and self.datay is not None:
            self.data_line.set_data(self.datax, self.datay)
        if self.data_line is not None:
            self.ax.draw_artist(self.data_line)
        self.canvas.blit(self.ax.bbox) 

    def get_neighbours(self, xs, ys):
        """
        For a pair of coordinates (xs = [x1, x2], ys = [y1, y2]), return the
        nearest datum in each spectrum for a line subtended between the two coordinate
        points which intersects the baseline of each spectrum.
        Returns two arrays, one of x-coordinates, one of y-coordinates.
        """
        ymask = list((self.y_indices <= max(ys)) * (self.y_indices >= min(ys)))
        if True not in ymask:
            return None, None
        y_lo = ymask.index(True)
        y_hi = len(ymask)-ymask[::-1].index(True)
        x_neighbours = []
        y_neighbours = []
        for i in range(y_lo, y_hi):
            x = [self.x[0], self.x[-1], xs[0], xs[1]]    
            y = [self.y_indices[i], self.y_indices[i], ys[0], ys[1]]    
            x, y = self.get_intersection(x, y)
            x = numpy.argmin(abs(self.x-x))
            x_neighbours.append(self.x[x])
            y_neighbours.append(self.y[i][x]+self.y_indices[i])
        return x_neighbours, y_neighbours

    @staticmethod
    def get_intersection(x, y):
        """
        This function take a set of two pairs of x/y coordinates, defining a
        pair of crossing lines, and returns the intersection. x = [x1, x2, x3, x4], y =
        [y1, y2, y3, y4], where [x1, y1] and [x2, y2] represent one line, and [x3, y3]
        and [x4, y4] represent the other. See
        https://en.wikipedia.org/wiki/Line%E2%80%93line_intersection#Given_two_points_on_each_line
        """
        px = (((x[0]*y[1]-y[0]*x[1])*(x[2]-x[3])-(x[0]-x[1])*(x[2]*y[3]-y[2]*x[3]))/((x[0]-x[1])*(y[2]-y[3])-(y[0]-y[1])*(x[2]-x[3])))
        py = (((x[0]*y[1]-y[0]*x[1])*(y[2]-y[3])-(y[0]-y[1])*(x[2]*y[3]-y[2]*x[3]))/((x[0]-x[1])*(y[2]-y[3])-(y[0]-y[1])*(x[2]-x[3])))
        return px, py







        
if __name__ == '__main__':
    pass
