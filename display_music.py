import argparse, enum, itertools, math, os, os.path, time, sys
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("Poppler", "0.18")
from gi.repository import Gdk, Gtk, Poppler

REPEATS = None
# iter([
#     (5, 3)
# ])

class Viewer(enum.Enum):
    """
    Configuration constants for the sheet music viewer.
    """

    NORMAL = enum.auto()
    INVERTED = enum.auto()
    LEFT = enum.auto()
    RIGHT = enum.auto()

    ONE_PAGE = enum.auto()
    TWO_PATE = enum.auto()

# An infinite iterator for cycling clockwise through the four possible
# orientations of the sheet music page.
ORIENTATION = itertools.cycle([
    Viewer.NORMAL,
    Viewer.RIGHT,
    Viewer.INVERTED,
    Viewer.LEFT]
)

def resolve_repeats(repeat_sequence, num_pages):
    """
    Determine the order to display pages given jumps the flow.
    """

    next_repeat = next(repeat_sequence)
    i = 0
    while i < num_pages:
        yield i
        if next_repeat is not None and i == next_repeat[0] - 1:
            i = next_repeat[1] - 1
            try:
                next_repeat = next(repeat_sequence)
            except StopIteration:
                next_repeat = None
        else:
            i += 1

class SMPlayer(Gtk.Window):
    """
    The sheet music player application.
    """

    # If more than one keypress is detected within KEY_DEBOUNCE
    # seconds, they will be ignored. This prevents multiple keys or
    # accidental double-presses incorrectly advancing the sheet music.
    KEY_DEBOUNCE = 0.1 # seconds

    def __init__(self, file, repeats=None):
        """
        Set up the window: load documents, etc.
        """

        # Load document
        self.document = Poppler.Document.new_from_file("file://{}".format(file), None)
        self.pages = [self.document.get_page(i) for i in range(self.document.get_n_pages())]
        self.orientation = next(ORIENTATION)
        self.pages_displayed = Viewer.ONE_PAGE

        # Set up key debounce
        self.last_key_time = time.time()

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
        self.doc_box = Gtk.DrawingArea()
        self.doc_box.set_hexpand(True)
        self.doc_box.set_vexpand(True)
        self.doc_box.connect("draw", self.draw)

        layout.add(self.doc_box)

    def keyboard_handler(self, widget, key):
        """
        Determine the action to take based on keypresses.
        """

        if time.time() - self.last_key_time > SMPlayer.KEY_DEBOUNCE:
            self.last_key_time = time.time()

            if key.keyval == Gdk.KEY_Left:
                self.to_prev_page()
            elif key.keyval == Gdk.KEY_r:
                self.orientation = next(ORIENTATION)
                self.doc_box.queue_draw()
            elif key.keyval == Gdk.KEY_1:
                if self.pages_displayed == Viewer.ONE_PAGE:
                    self.pages_displayed = Viewer.TWO_PAGE
                else:
                    self.pages_displayed = Viewer.ONE_PAGE
            else:
                self.to_next_page()

    def draw(self, widget, surface):
        """
        Draw the current page onto the window.
        """

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

    def to_prev_page(self):
        """
        Move to the previous page in the sheet music, updating the
        window.
        """
        if self.page_order_pos > 0:
            self.page_order_pos -= 1
            self.doc_box.queue_draw()

    def to_next_page(self):
        """
        Move to the next page in the sheet music, updating the window.
        """

        if self.page_order_pos < len(self.page_order) - 1:
            self.page_order_pos += 1
            self.doc_box.queue_draw()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file", nargs="?", default=None, help="a PDF containing sheet music")

    args = parser.parse_args()

    if args.file is not None: # If a file was provided on the command line
        # Clean up any filename weirdness (e.g. ~user constructs,
        # variables, symlinks)
        music_file = os.path.realpath(
            os.path.expanduser(
                os.path.expandvars(
                    os.path.normpath(args.file))))
    else: # Use a file chooser dialogue if no command line argument
        file_chooser = Gtk.FileChooserDialog("Please choose a file", None,
            Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OPEN, Gtk.ResponseType.OK))

        # Set up a filter to only take PDFs
        pdf_filter = Gtk.FileFilter()
        pdf_filter.set_name("PDF files")
        pdf_filter.add_mime_type("application/pdf")
        file_chooser.add_filter(pdf_filter)

        # Fallback filter for any file
        all_filter = Gtk.FileFilter()
        all_filter.set_name("Any files")
        all_filter.add_pattern("*")
        file_chooser.add_filter(all_filter)

        # Run the dialogue to get a file
        response = file_chooser.run()
        if response == Gtk.ResponseType.OK:
            music_file = file_chooser.get_filename()
        else:
            sys.quit()

        file_chooser.destroy()

    window = SMPlayer(music_file, REPEATS)
    window.show_all()
    Gtk.main()
