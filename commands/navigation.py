from os import lseek
from typing import Text
from prettytable import PrettyTable
from prompt_toolkit.shortcuts.prompt import confirm
from classes.prompt import *
from classes.command import *
from classes.argparser import *

class Navigation(Cog):

    def __init__(self) -> None:
        super().__init__()
        self.description = "Commands for navigating around the notebook"
        
    #------------------------------------------------------------------
    #                               LS
    #------------------------------------------------------------------

    @Command("ls", 
    "list current notebook folder",
    """
ls ./ # lists current directory 
ls /  # lists root
    """)
    def ls(self, promptinstance, parsedata):
        path = parsedata.path
        wdir = promptinstance.path.cdir
        if(path):
            wdir = promptinstance.path.get_on_path(path)

        headers = ["Name", "Type", "Level", "Date created", "Date modified"]
        all = list()

        for folder in wdir.childfolders.values():
            folder: Folder
            all.append([folder.name, "folder", folder.level, folder.datecreated, folder.datemodified])
        
        for file in wdir.childfiles.values():
            file: File
            all.append([file.name, "file", file.level, file.datecreated, file.datemodified])

        for ref in wdir.childrefs.values():
            ref: Reference
            all.append([ref.name, "reference", ref.level, ref.datecreated, ref.datemodified])

        t = PrettyTable(headers)
        t.align["Name"] = "l"
        t.add_rows(all)
        promptinstance.printl(t)

    @ls.set_completionargs
    def ls_completionargs(self, promptinstance, parser):
        arg = parser.add_arg("path", None, "path to directory to list", True, False, False)
        arg.vals = [promptinstance.path]

        return parser

    @ls.set_validation
    def ls_validate(self, promptinstance, parsedata):
        path = parsedata.path
        if(not path):
            return

        if(not (r := promptinstance.path.get_on_path(path))):
            return "Invalid Path \"{}\"".format(path)

        if(isinstance(r, File)):
            return "Path cannot lead to a file"


    #------------------------------------------------------------------
    #                               CD
    #------------------------------------------------------------------
    @Command("cd", 
    "navigate into specified folder",
    """
cd ./folder # sets current working directory as folder in current directory 
cd /        # sets current working directory as root
    """)
    def cd(self, promptinstance, parsedata):
        path = parsedata.path
        path = promptinstance.path.get_on_path(path)
        promptinstance.path.cdir = path
        promptinstance.dircache.add(path)

    @cd.set_completionargs
    def cd_completionargs(self, promptinstance, parser):
        arg = parser.add_arg("path", None, "path to navigate into", True, True, False)
        arg.vals = [promptinstance.path]

        return parser


    @cd.set_validation
    def cd_validate(self, promptinstance, parsedata):
        path = parsedata.path
    
        if(not (r := promptinstance.path.get_on_path(path))):
            return "Invalid Path"

        if(isinstance(r, File)):
            return "Path cannot lead to a file"

    #------------------------------------------------------------------
    #                               PWD
    #------------------------------------------------------------------
    @Command("pwd", 
    "print current working directory",
    """
pwd #prints current working directory
    """)
    def pwd(self, promptinstance, parsedata):
        promptinstance.printl(promptinstance.path.cdir.fullpath)
        

    @pwd.set_completionargs
    def pwd_completionargs(self, promptinstance, parser):
        return parser


    @pwd.set_validation
    def pwd_validate(self, promptinstance, parsedata):
        pass

    #------------------------------------------------------------------
    #                               INFO
    #------------------------------------------------------------------
    @Command("info", 
    "print info for a file/folder/ref",
    """
info ./file #prints info for file
    """)
    def info(self, promptinstance, parsedata):
        path = parsedata.path
        object = promptinstance.path.get_on_path(path, retref=True)

        if(isinstance(object, File)):
            object: File
            lexer = None
            if(object.lexer):
                lexer = object.lexer.__class__.name
            promptinstance.printl("-------INFO-------\nType: File\nName: {}\nFullpath: {}\nLevel: {}\nCreated: {}\nLast modified: {}\nLexer: {}\n-------ENDL-------".format(
                object.name, object.fullpath, object.level, object.datecreated, object.datemodified, lexer
            ))

        if(isinstance(object, Folder)):
            object: Folder
            promptinstance.printl("-------INFO-------\nType: Folder\nName: {}\nFullpath: {}\nLevel: {}\nCreated: {}\nLast modified: {}\n-------ENDL-------".format(
                object.name, object.fullpath, object.level, object.datecreated, object.datemodified
            ))
        if(isinstance(object, Reference)):
            object: Reference
            promptinstance.printl("-------INFO-------\nType: Folder\nName: {}\nFullpath: {}\nRefpath: {}\nLevel: {}\nCreated: {}\nLast modified: {}\n-------ENDL-------".format(
                object.refname, object.fullpath, object.name, object.level, object.datecreated, object.datemodified
            ))

        

    @info.set_completionargs
    def info_completionargs(self, promptinstance, parser):
        arg = parser.add_arg("path", None, "path to object", True, True, False)
        arg.vals = [promptinstance.path]

        return parser


    @info.set_validation
    def info_validate(self, promptinstance, parsedata):
        path = parsedata.path
    
        if(not (r := promptinstance.path.get_on_path(path, retref=True))):
            return "Invalid Path"


def setup(shell):
    instance = Navigation.load(shell)
    return instance