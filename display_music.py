import enum, itertools, math
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk, Poppler

FILE = "/home/wec/Dropbox/music/shes_always_a_woman.pdf"
REPEATS = [
    (4, 2),
    (3, 4)
]

# View configuration constants
class Viewer(enum.Enum):
    NORMAL = enum.auto()
    INVERTED = enum.auto()
    LEFT = enum.auto()
    RIGHT = enum.auto()

ORIENTATION = itertools.cycle([Viewer.NORMAL, Viewer.RIGHT, Viewer.INVERTED, Viewer.LEFT])

def resolve_repeats(repeat_sequence, num_pages):
    next_repeat = next(repeat_sequence)
    i = 0
    while i < num_pages:
        yield i
        if next_repeat is not None and i == next_repeat[0]:
            i = next_repeat[1]
            try:
                next_repeat = next(repeat_sequence)
            except StopIteration:
                next_repeat = None
        else:
            i += 1

class SMPlayer(Gtk.Window):
    def __init__(self, file, repeats=None):
        # Load document
        self.document = Poppler.Document.new_from_file("file://{}".format(file), None)
        self.pages = [self.document.get_page(i) for i in range(self.document.get_n_pages())]
        self.orientation = next(ORIENTATION)

        # Resolve repeats, if any
        if repeats is not None:
            self.page_order = list(resolve_repeats(repeats, self.document.get_n_pages()))
        else:
            self.page_order = list(range(self.document.get_n_pages()))
        self.page_order_pos = 0

        # Set up window
        Gtk.Window.__init__(self, title=self.document.get_title())
        self.connect("destroy", Gtk.main_quit)
        self.maximize()

        layout = Gtk.Box()
        self.add(layout)

        # Make sure the window catches keypresses
        self.props.events |= Gdk.EventMask.KEY_PRESS_MASK
        self.connect("key-press-event", self.keyboard_handler)

        # Place document in layout
        self.doc_box = Gtk.Stack()
        self.doc_box.set_hexpand(True)
        self.doc_box.set_vexpand(True)
        # Iterate through pages and set up a child of the Stack for each
        for page_num, page in enumerate(self.pages):
            page_area = Gtk.DrawingArea()
            page_area.set_size_request(*page.get_size()) # Make appropriately sized
            page_area.connect("draw", self.draw)
            self.doc_box.add_named(page_area, str(page_num))

        layout.add(self.doc_box)

    def keyboard_handler(self, widget, key):
        if key.keyval == Gdk.KEY_Left:
            self.to_prev_page()
        elif key.keyval == Gdk.KEY_r:
            self.orientation = next(ORIENTATION)
        else:
            self.to_next_page()

    def draw(self, widget, surface):
        current_page = self.pages[self.page_order[self.page_order_pos]]
        page_size = current_page.get_size()
        widget_size = widget.get_allocated_size()[0]

        # Calculate scaling
        if self.orientation == Viewer.NORMAL or self.orientation == Viewer.INVERTED: # Upright or upside down
            horizontal_scale = widget_size.width / page_size[0]
            vertical_scale = widget_size.height / page_size[1]
        else: # On its side
            horizontal_scale = widget_size.width / page_size[1]
            vertical_scale = widget_size.height / page_size[0]

        scale = min(horizontal_scale, vertical_scale) # Use the lesser scale to avoid overflow
        surface.scale(scale, scale) # Apply scaling

        # Change orientation
        if self.orientation == Viewer.LEFT:
            surface.rotate(-math.pi/2)
            surface.translate(-page_size[0], 0)
        elif self.orientation == Viewer.RIGHT:
            surface.rotate(math.pi/2)
            surface.translate(0, -page_size[1])
        elif self.orientation == Viewer.INVERTED:
            surface.rotate(math.pi)
            surface.translate(-page_size[0], -page_size[1])

        current_page.render(surface)

    def update_page(self):
        self.doc_box.set_visible_child_name(str(self.page_order[self.page_order_pos]))

    def to_prev_page(self):
        if self.page_order_pos > 0:
            self.page_order_pos -= 1
            self.update_page()

    def to_next_page(self):
        if self.page_order_pos < len(self.page_order) - 1:
            self.page_order_pos += 1
            self.update_page()

window = SMPlayer(FILE, iter(REPEATS))
window.show_all()
Gtk.main()
