import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk, Poppler

FILE = "/home/wec/Dropbox/music/shes_always_a_woman.pdf"
REPEATS = [
    (4, 2),
    (3, 4)
]

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

        layout = Gtk.Grid()
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

        layout.attach(self.doc_box, 0, 0, 2, 1)

        # Next and previous page buttons
        self.prev_btn = Gtk.Button(label="Previous page")
        self.next_btn = Gtk.Button(label="Next page")

        self.prev_btn.connect("clicked", self.to_prev_page)
        self.next_btn.connect("clicked", self.to_next_page)

        self.prev_btn.set_sensitive(False)

        layout.attach(self.prev_btn, 0, 1, 1, 1)
        layout.attach(self.next_btn, 1, 1, 1, 1)

    def keyboard_handler(self, widget, key):
        if key.keyval == Gdk.KEY_Left:
            self.to_prev_page(widget)
        else:
            self.to_next_page(widget)

    def draw(self, widget, surface):
        current_page = self.pages[self.page_order[self.page_order_pos]]

        # Calculate scaling
        page_size = current_page.get_size()
        widget_size = widget.get_allocated_size()[0]

        horizontal_scale = widget_size.width / page_size[0]
        vertical_scale = widget_size.height / page_size[1]

        scale = min(horizontal_scale, vertical_scale) # Use the lesser scale to avoid overflow

        surface.scale(scale, scale)
        current_page.render(surface)

    def update_page(self):
        self.doc_box.set_visible_child_name(str(self.page_order[self.page_order_pos]))

        if self.page_order_pos == 0:
            self.prev_btn.set_sensitive(False)
        else:
            self.prev_btn.set_sensitive(True)

        if self.page_order_pos == len(self.page_order) - 1:
            self.next_btn.set_sensitive(False)
        else:
            self.next_btn.set_sensitive(True)

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
