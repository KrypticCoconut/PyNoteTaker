from os import lseek, read
from prettytable import PrettyTable
from prompt_toolkit.shortcuts.prompt import confirm
from pygments import lexer
from classes.prompt import *
from classes.command import *
from classes.argparser import *
from prompt_toolkit import application
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, VSplit, HSplit, Window, Float
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.styles import Style
from prompt_toolkit.layout.dimension import LayoutDimension as D
from prompt_toolkit.widgets import MenuContainer, MenuItem, Frame
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from pygments.lexers import get_all_lexers, get_lexer_by_name
from pygments.util import ClassNotFound

class splitnote:
    def __init__(self, file, readonly=False) -> None:
        self.readonly = readonly
        self.file = file
        self.description = self.textarea(file.description, "description", None)
        if(self.file.lexer):
            self.value = self.textarea(file.text, 'value', PygmentsLexer(self.file.lexer.__class__))
        else:
            self.value = self.textarea(file.text, 'value', None)
        self.currenttextarea = self.description
        self.build_container()
        self.build_keybinds()
        self.startapp()

    def get_status(self):
        return [
            ("class:status", self.file.fullpath + " - "),
            (
                "class:status.position",
                "{}:{}".format(
                    self.currenttextarea.body.document.cursor_position_row + 1,
                    self.currenttextarea.body.document.cursor_position_col + 1,
                ),
            )
        ]

    def textarea(self, text, name, lexer):
        if(lexer):
            input_text_area = Frame(TextArea(
                text=text,
                scrollbar=True,
                line_numbers=True,
                read_only=self.readonly,
                lexer=lexer
            ), name)  
        else:
            input_text_area = Frame(TextArea(
                text=text,
                scrollbar=True,
                line_numbers=True,
                read_only=self.readonly
            ), name)  
        input_text_area.body.buffer.name = name
        return input_text_area
    
    def build_container(self):
        def exit_handler():
            self.application.exit(result=self.file)
        
        def exitandsave_handler():
            self.file.description = self.description.body.text
            self.file.text = self.value.body.text
            self.application.exit(result=self.file)

        def save_handler():
            self.file.description = self.description.body.text
            self.file.text = self.value.body.text  
        root_container = HSplit(
            [
                Window(
                    content=FormattedTextControl(self.get_status),
                    height=D.exact(1),
                    style="class:status",
                ),
                VSplit([ self.description, self.value])
            ]
        ) 

        menu = [MenuItem("File", children=[MenuItem("Save", handler=save_handler), MenuItem("Save and Exit", handler=exitandsave_handler), MenuItem("-", disabled=True),MenuItem("Exit", handler=exit_handler)])]
        self.root_container = MenuContainer(root_container, menu, [Float(xcursor=True,ycursor=True,content=CompletionsMenu(max_height=16, scroll_offset=1))])
    


    def build_keybinds(self):
        def focus_next(event):
            windows = self.application.layout.get_visible_focusable_windows()

            if len(windows) > 0:
                try:
                    index = windows.index(self.application.layout.current_window)
                except ValueError:
                    index = 0
                else:
                    index = (index + 1) % len(windows)
                window = windows[index]
                try:
                    buffer = window.content.buffer
                    name = buffer.name
                    if(name == "description"):
                        self.currenttextarea = self.description
                    elif(name == "value"):
                        self.currenttextarea = self.value
                except Exception as err:
                    pass
                self.application.layout.focus(window)

        def focus_previous(event):
            windows = self.application.layout.get_visible_focusable_windows()

            if len(windows) > 0:
                try:
                    index = windows.index(self.application.layout.current_window)
                except ValueError:
                    index = 0
                else:
                    index = (index - 1) % len(windows)
                self.application.layout.focus(windows[index])

        kb = KeyBindings()
        kb.add("tab")(focus_next)
        kb.add("s-tab")(focus_previous)
        self.kb = kb

    def startapp(self):
        style = Style.from_dict( #took from examples lol
            {
                "status": "reverse",
                "status.position": "#aaaa00",
                "status.key": "#ffaa00",
                "not-searching": "#888888",
            }
        )

        self.application = Application(
            layout=Layout(self.root_container, focused_element=self.description),
            key_bindings=self.kb,
            enable_page_navigation_bindings=True,
            mouse_support=True,
            style=style,
            full_screen=True,
        )
        self.application.layout.focus_previous()
        self.application.run()

class Notes(Cog):

    def __init__(self) -> None:
        super().__init__()
        self.description = "Commands for taking notes"

        vals = []
        for lexer in get_all_lexers():
            vals += list(lexer[1])
        self.vals = vals
    
    #------------------------------------------------------------------
    #                               MKNOTE
    #------------------------------------------------------------------
    @Command("mknote", 
    "make a note",
    """
mknote ./note # makes a note in current directory 
mkdir /note # makes a note in root
    """)
    def mknote(self, promptinstance, parsedata):
        opath = parsedata.path
        fullpath = CommandParser.splitargs(opath, "/")
        existpath = '/'.join(fullpath[:-1])
        if(opath.startswith("/")):
            existpath = "/" + existpath
        newpath = CommandParser.remove_quotes(fullpath[-1])
        wdir = promptinstance.path.get_on_path(existpath)

        file = File(newpath, wdir, promptinstance)  
        if(lexer := parsedata.lexer):
            file.lexer = get_lexer_by_name(lexer)
        splitnote(file)
        wdir.childfiles[newpath] = file

        

    @mknote.set_completionargs
    def mknote_completionargs(self, promptinstance, parser: CommandParser):
        arg = parser.add_arg("path", None, "path to new note", True, True, False, False)
        arg.vals = [promptinstance.path]
        arg = parser.add_arg("lexer", "l", "lexer (text highlighter)", False, False, False, False)
        arg.vals = self.vals
        return parser


    @mknote.set_validation
    def mknote_validate(self, promptinstance, parsedata):
        opath = parsedata.path
        fullpath = CommandParser.splitargs(opath, "/")
        existpath = '/'.join(fullpath[:-1])
        if(opath.startswith("/")):
            existpath = "/" + existpath
        newpath = fullpath[-1]
        wdir = promptinstance.path.get_on_path(existpath)
        if(not wdir):
            return "Invalid existing path \"{}\"".format(existpath)

        if(isinstance(wdir, File)):
            return "Existing path cannot lead to a file"

        if(x := wdir.childfiles.get(CommandParser.remove_quotes(newpath), None)):
            return "{}: File already exists in {}".format(x.name, wdir.fullpath)

        if(x := wdir.childfolders.get(CommandParser.remove_quotes(newpath), None)):
            return "{}: Folder already exists in {}".format(x.name, wdir.fullpath)

        if x :=(wdir.childrefs.get(CommandParser.remove_quotes(newpath), None)):
            return "{}: Reference already exists in {}".format(x.name, wdir.fullpath)

        if(lexer := parsedata.lexer):
            try:
                x = get_lexer_by_name(lexer)
            except:
                return "invalid lexer: {}".format(lexer)

    #------------------------------------------------------------------
    #                              READNOTE
    #------------------------------------------------------------------

    @Command("readnote", 
    "read note/file",
    """
modnote -r ./note # read note in current directory 
modnote -m /note # modify note in current directory
    """)
    def readnote(self, promptinstance, parsedata):
        path = parsedata.path
        note = promptinstance.path.get_on_path(path)

        if(parsedata.read):
            splitnote(note, readonly=True)
        else:
            splitnote(note)

    @readnote.set_completionargs
    def readnote_completionargs(self, promptinstance, parser: CommandParser):
        arg = parser.add_arg("path", None, "path to note/file", True, True, False)
        arg.vals = [promptinstance.path]

        parser.add_arg("read", "r", "switch to read note", False, False, True, False)
        parser.add_arg("modify", "m", "switch to modify note", False, False, True, False)
        return parser

    @readnote.set_validation
    def readnote_validate(self, promptinstance, parsedata):
        path = parsedata.path

        if(not (r := promptinstance.path.get_on_path(path))):
            return "Invalid Path \"{}\"".format(path)

        if(not isinstance(r, File)):
            return "Path does not lead to a file"

        modify = parsedata.modify
        read = parsedata.read
        if(not read and not modify):
            return "Mode to open note in not specified"
        if(read and modify):
            return "Both modes specified"

    #------------------------------------------------------------------
    #                               chlexer
    #------------------------------------------------------------------
    @Command("chlexer", 
    "change lexer for notebook",
    """
chlexer ./file python #changes lexer to python (so now your note/file text will be highlighted in that lexer format)
chlexer ./file #changes lexer to none
    """)
    def chlexer(self, promptinstance, parsedata):
        lexer = parsedata.lexer
        path = parsedata.path
        file = promptinstance.path.get_on_path(path)
        if(not lexer):
            file.lexer = None
        else:
            file.lexer = get_lexer_by_name(lexer)
        

    @chlexer.set_completionargs
    def chlexer_completionargs(self, promptinstance, parser: CommandParser):
        arg = parser.add_arg("path", None, "path to note/file", True, True, False, False)
        arg.vals = [promptinstance.path]
        arg = parser.add_arg("lexer", None, "lexer to change to", True, False, False, False)
        arg.vals = self.vals
        return parser
        


    @chlexer.set_validation
    def chlexer_validate(self, promptinstance, parsedata):
        path = parsedata.path
        
        if(not (r := promptinstance.path.get_on_path(path))):
            return "Invalid Path \"{}\"".format(path)

        if(not isinstance(r, File)):
            return "Path does not lead to a file"


        if(lexer := parsedata.lexer):
            try:
                x = get_lexer_by_name(lexer)
            except:
                return "invalid lexer: {}".format(lexer)



def setup(shell):
    instance = Notes.load(shell)
    return instance