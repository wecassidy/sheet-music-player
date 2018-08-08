import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk, Poppler

FILE = "/home/wec/Dropbox/music/shes_always_a_woman.pdf"
REPEATS = [
    (4, 2),
    (3, 4)
]

def resolve_repeats(repeat_sequence, num_pages):
    nextRepeat = next(repeat_sequence)
    i = 0
    while i < num_pages:
        yield i
        if nextRepeat is not None and i == nextRepeat[0]:
            i = nextRepeat[1]
            try:
                nextRepeat = next(repeat_sequence)
            except StopIteration:
                nextRepeat = None
        else:
            i += 1

class SMPlayer(Gtk.Window):
    def __init__(self, file, repeats=None):
        # Load document
        self.document = Poppler.Document.new_from_file("file://{}".format(file), None)
        self.pages = [self.document.get_page(i) for i in range(self.document.get_n_pages())]

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

        self.layout = Gtk.Grid()
        self.add(self.layout)

        # Make sure the window catches keypresses
        self.props.events |= Gdk.EventMask.KEY_PRESS_MASK
        self.connect("key-press-event", self.keyboard_handler)

        # Place document in layout
        self.docBox = Gtk.Stack()
        self.docBox.set_hexpand(True)
        self.docBox.set_vexpand(True)
        # Iterate through pages and set up a child of the Stack for each
        for pageNum, page in enumerate(self.pages):
            pageArea = Gtk.DrawingArea()
            pageArea.set_size_request(*page.get_size()) # Make appropriately sized
            pageArea.connect("draw", self.draw)
            self.docBox.add_named(pageArea, str(pageNum))

        self.layout.attach(self.docBox, 0, 0, 2, 1)

        # Next and previous page buttons
        self.prevBtn = Gtk.Button(label="Previous page")
        self.nextBtn = Gtk.Button(label="Next page")

        self.prevBtn.connect("clicked", self.to_prev_page)
        self.nextBtn.connect("clicked", self.to_next_page)

        self.prevBtn.set_sensitive(False)

        self.layout.attach(self.prevBtn, 0, 1, 1, 1)
        self.layout.attach(self.nextBtn, 1, 1, 1, 1)

    def keyboard_handler(self, widget, key):
        if key.keyval == Gdk.KEY_Left:
            self.to_prev_page(_)
        else:
            self.to_next_page(_)

    def draw(self, widget, surface):
        self.pages[self.page_order[self.page_order_pos]].render(surface)

    def update_page(self):
        self.docBox.set_visible_child_name(str(self.page_order[self.page_order_pos]))

        if self.page_order_pos == 0:
            self.prevBtn.set_sensitive(False)
        else:
            self.prevBtn.set_sensitive(True)

        if self.page_order_pos == len(self.page_order) - 1:
            self.nextBtn.set_sensitive(False)
        else:
            self.nextBtn.set_sensitive(True)

    def to_prev_page(self, widget):
        if self.page_order_pos > 0:
            self.page_order_pos -= 1
            self.update_page()

    def to_next_page(self, widget):
        if self.page_order_pos < len(self.page_order) - 1:
            self.page_order_pos += 1
            self.update_page()

window = SMPlayer(FILE, iter(REPEATS))
window.show_all()
Gtk.main()
