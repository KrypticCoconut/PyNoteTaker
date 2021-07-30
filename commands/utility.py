
from prettytable import PrettyTable
from prompt_toolkit import history
from prompt_toolkit.shortcuts.prompt import confirm
from classes.prompt import *
from classes.command import *
from classes.argparser import *


helpoutline = """
each command is assigned to a subcategory
each of them also has a help page that can be accessed by "{{commandname}} [-help, -h]"

{}
"""

class Utility(Cog):

    def __init__(self) -> None:
        super().__init__()
        self.description = "Utility commands"

    #------------------------------------------------------------------
    #                               HELP
    #------------------------------------------------------------------
    @Command("help", 
    "Prints all commands and thier corrosponding categories",
    """
help # prints help page
    """)
    def help(self, promptinstance, parsedata):
        ret = str()
        for category, commands in promptinstance.commands.items():
            ret += "\n{}: {}\n".format(category.name, category.description)
            for command in commands:
                ret += "    {}: {}\n".format(command.name, command.desc)
        ret = ret.rstrip("\n").lstrip("\n")
        global helpoutline
        promptinstance.printl(helpoutline.format(ret).lstrip("\n"))
        

    @help.set_completionargs
    def help_completionargs(self, promptinstance, parser: CommandParser):
        return parser


    @help.set_validation
    def mkdir_validate(self, promptinstance, parsedata):
        pass


    #------------------------------------------------------------------
    #                               EXIT
    #------------------------------------------------------------------
    @Command("exit", 
    "saves current notebook and exits pynotetaker",
    """
exit #exits program
    """)
    def exit(self, promptinstance, parsedata):
        promptinstance.exit = True
        

    @exit.set_completionargs
    def exit_completionargs(self, promptinstance, parser):
        return parser


    @exit.set_validation
    def exit_validate(self, promptinstance, parsedata):
        pass

    #------------------------------------------------------------------
    #                               HISTORY
    #------------------------------------------------------------------
    @Command("history", 
    "print command history",
    """
history #pritns command history
histor -less #shows history in a scrollable view
    """)
    def history(self, promptinstance, parsedata):
        if(parsedata.clear):
            promptinstance.history._storage = []
            promptinstance.notebook.history = []
            return
        ret = str()
        history = promptinstance.notebook.history
        for i, word in enumerate(history):
            ret += "{}: {}\n".format(i, word)
        promptinstance.printl(ret.rstrip("\n"))
        

    @history.set_completionargs
    def history_completionargs(self, promptinstance, parser: CommandParser):
        arg = parser.add_arg("clear", "c", "clear history", False, True, True, False)
        return parser


    @history.set_validation
    def history_validate(self, promptinstance, parsedata):
        pass


    #------------------------------------------------------------------
    #                               SET
    #------------------------------------------------------------------
    @Command("set", 
    "set enviornment variables",
    """
set -print #prints all curr vars
set reset_history True # sets reset_history to true
set -print reset_history #shows more info about reset_history
    """)
    def set(self, promptinstance, parsedata):
        name = parsedata.varname
        val = parsedata.value
        if(parsedata.print):
            ret = str()
            if(name):
                name = promptinstance.notebook.env_vars.get(name)
                ret += "Current Value: {}\n{}".format(name.val, name.help)
                promptinstance.printl(ret)
                return
            for name, val in promptinstance.env_vars.items():
                ret += "{}: {}\n".format(name, val.val)
            promptinstance.printl(ret.rstrip("\n"))
            return
        promptinstance.notebook.env_vars[name].val = promptinstance.notebook.env_vars.get(name).checkfunc(val)

    @set.set_completionargs
    def set_completionargs(self, promptinstance, parser: CommandParser):
        arg = parser.add_arg("print", "p", "print all enviorment variables", False, False, True, True)
        arg = parser.add_arg("varname", None, "varname of env variable", True, True, False, False)
        arg.vals = list(promptinstance.notebook.env_vars.keys())
        arg = parser.add_arg("value", None, "value to assign to the env variable", True, True, False, False)
        

        return parser


    @set.set_validation
    def set_validate(self, promptinstance, parsedata):
        if(parsedata.print):
            name = parsedata.varname
            if(not name):
                return
            if(not (t := promptinstance.notebook.env_vars.get(name, None))):
                return "Invalid env var: {}".format(name)
            return
        name = parsedata.varname
        val = parsedata.value
        if(not (t := promptinstance.notebook.env_vars.get(name, None))):
            return "Invalid env var: {}".format(name)
        r = t.checkfunc(val)
        if(isinstance(r, str)):
            return r
        pass


    #------------------------------------------------------------------
    #                             SHOWCACHE
    #------------------------------------------------------------------
    @Command("showcache", 
    "print file/directory cache",
    """
showcache dir #prints directory cache
showcache file #prints file cache
    """)
    def showcache(self, promptinstance, parsedata):
        if(parsedata.dir):
            dircache = promptinstance.dircache
            for dir in dircache.cachelist():
                print(dir.fullpath)
        if(parsedata.file):
            filecache = promptinstance.filecache
            for file in filecache.cachelist():
                print(file.fullpath)
        

    @showcache.set_completionargs
    def showcache_completionargs(self, promptinstance, parser):
        parser.add_arg("dir", "d", "switch to show dir cache", False, False, True, False)
        parser.add_arg("file", "f", "switch to show file cache", False, False, True, False)
        return parser


    @showcache.set_validation
    def showcache_validate(self, promptinstance, parsedata):

        dir = parsedata.dir
        file = parsedata.file
        if(not dir and not file):
            return "cache to print not specified"
        if(dir and file):
            return "Both caches specified"

def setup(shell):
    instance = Utility.load(shell)
    return instance