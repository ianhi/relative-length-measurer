from numbers import Real
from pathlib import Path
from typing import List, Tuple

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backend_bases import MouseEvent
from matplotlib.cbook import CallbackRegistry
from matplotlib.lines import Line2D
from matplotlib.widgets import AxesWidget, TextBox
from mpl_interactions import panhandler, zoom_factory
from PIL import Image


class DraggableLine(AxesWidget):
    def __init__(self, ax, x, y, grab_range=10, useblit=False, **kwargs) -> None:
        """
        ax : Axes
        x, y : (2,) Array of float
            The initial positions of the handles.
        grab_range : Number, default: 10
            Grab range for the handles in pixels (I think it's pixels)
        useblit : bool, default False
            Whether to use blitting for faster drawing (if supported by the
            backend). See the tutorial :doc:`/tutorials/advanced/blitting`
            for details.
        **kwargs :
            Passed on to Line2D for styling
        """
        super().__init__(ax)
        self._useblit = useblit
        center_x = (x[0] + x[1]) / 2
        center_y = (y[0] + y[1]) / 2

        marker = kwargs.pop("marker", "o")
        color = kwargs.pop("color", "k")
        self._handles = Line2D(
            [x[0], center_x, x[1]],
            [y[0], center_y, y[1]],
            marker=marker,
            color=color,
            **kwargs,
        )
        self.ax.add_artist(self._handles)
        self.connect_event("button_press_event", self._on_press)
        self.connect_event("motion_notify_event", self._on_move)
        self.connect_event("button_release_event", self._on_release)
        self._handle_idx = None  # none implies not moving
        self._grab_range = grab_range
        self._observers = CallbackRegistry()

    @property
    def grab_range(self) -> Real:
        """
        Grab range in pixels (I think in pixels)
        """
        return self._grab_range

    @grab_range.setter
    def grab_range(self, val: Real):
        if not isinstance(val, Real):
            raise TypeError(f"Val must be a number but got type {type(val)}")
        self._grab_range = val

    def _on_press(self, event: MouseEvent):
        if self.ax != event.inaxes:
            return
        if not self.canvas.widgetlock.available(self):
            return
        x, y = self._handles.get_data()
        # figure out if any handles are being grabbed
        # maybe possibel to do this with a pick event?

        x, y = self._handles.get_data()
        # this is taken pretty much directly from the implementation
        # in matplotlib.widget.ToolHandles.closest
        pts = self.ax.transData.transform(np.column_stack([x, y]))
        diff = pts - [event.x, event.y]
        dist = np.hypot(*diff.T)
        idx = np.argmin(dist)
        if dist[idx] < self._grab_range:
            self._handle_idx = idx
        else:
            self._handle_idx = None

    def _on_move(self, event: MouseEvent):
        if self.ax != event.inaxes:
            return
        if self._handle_idx is None:
            # not dragging one of out handles
            return
        x, y = self._handles.get_data()
        if self._handle_idx == 1:
            x += event.xdata - x[1]
            y += event.ydata - y[1]
        else:
            x[self._handle_idx] = event.xdata
            y[self._handle_idx] = event.ydata
            x[1] = (x[0] + x[2]) / 2
            y[1] = (y[0] + y[2]) / 2
        self._handles.set_data(x, y)
        self._observers.process("line-changed", (x[0], x[2]), (y[0], y[2]))
        if self.drawon:
            self.ax.figure.canvas.draw_idle()

    def _on_release(self, event: MouseEvent):
        self._handle_idx = None

    def on_line_changed(self, func):
        """
        Connect *func* as a callback function whenever the line is moved.
        *func* will receive the end points of the line as (x, y) with each of x and y
        having shape (2,)

        Parameters
        ----------
        func : callable
            Function to call when a point is added.

        Returns
        -------
        int
            Connection id (which can be used to disconnect *func*).
        """
        return self._observers.connect("line-changed", lambda *args: func(*args))

    def get_length(self) -> Tuple[Real, Real]:
        x, y = self._handles.get_data()
        return ((x[2] - x[0]) ** 2 + (y[2] - y[0]) ** 2) ** (1 / 2)

    def get_endpoints(self) -> Tuple[List[float], List[float]]:
        x, y = self._handles.get_data()
        return [x[0], x[2]], [y[0], y[2]]


im = Image.open(Path(__file__).parent / "pic.jpg")
fig, ax = plt.subplots()
ax.imshow(im)
zoom_factory(ax)
ph = panhandler(fig, button=2)

# manually chosen initial values
refx = [390.21691176470574, 388.0611631016043]
refy = [592.6617647058823, 927.7553475935829]

reference_length = 26  # in inches - this was in craiglist post
ref_line = DraggableLine(ax, refx, refy)
plt.subplots_adjust(bottom=0.2)
axbox1 = plt.axes([0.2, 0.05, 0.1, 0.075])
ref_text = TextBox(axbox1, "Reference\nLength", initial=f"{reference_length}")
ref_line.drawon = True


test_line_color = "tab:red"
test_line = DraggableLine(ax, [5, 500], [5, 500], color=test_line_color)
test_line.drawon = False
axbox2 = plt.axes([0.5, 0.05, 0.2, 0.075])
# # ideally this textbox wouldn't be allowed to be typed in.
# # but that doesn't seem to be possible
measured_box = TextBox(axbox2, "Test\nLength", initial="???")
measured_box.label.set_color(test_line_color)
measured_box.drawon = False


def update_test_readout(test_length=None):
    if test_length is None:
        test_length = test_line.get_length()
    length = float(ref_text.text) * test_length / ref_line.get_length()
    measured_box.set_val(f"{length:.2f}")
    fig.canvas.draw_idle()


def test_moved(x, y):
    update_test_readout(((x[1] - x[0]) ** 2 + (y[1] - y[0]) ** 2) ** (1 / 2))


test_line.on_line_changed(test_moved)

ref_text.on_text_change(lambda text: update_test_readout())
fig.canvas.draw()
plt.show()

print(ref_line.get_endpoints())
