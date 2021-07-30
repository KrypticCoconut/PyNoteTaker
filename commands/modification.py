from os import lseek, name
from prettytable import PrettyTable
from prompt_toolkit.shortcuts.prompt import confirm
from classes.prompt import *
from classes.command import *
from classes.argparser import *

class Modification(Cog):

    def __init__(self) -> None:
        super().__init__()
        self.description = "Commands for modifying the filesystem"

    #------------------------------------------------------------------
    #                               MKDIR
    #------------------------------------------------------------------
    @Command("mkdir", 
    "Make a directory on specified path",
    """
mkdir ./testdir1 # makes directory named testdir1 in current directory 
mkdir ./testdir2 # makes directory named testdir2 in root
    """)
    def mkdir(self, promptinstance, parsedata):
        opath = parsedata.path
        fullpath = CommandParser.splitargs(opath, "/")
        existpath = '/'.join(fullpath[:-1])
        if(opath.startswith("/")):
            existpath = "/" + existpath
        newpath = CommandParser.remove_quotes(fullpath[-1])
        wdir = promptinstance.path.get_on_path(existpath)

        wdir.childfolders[newpath] = Folder(newpath, wdir)
        

    @mkdir.set_completionargs
    def mkdir_completionargs(self, promptinstance, parser: CommandParser):
        arg = parser.add_arg("path", None, "path on which new directory should be created", True, True, False, False)
        arg.vals = [promptinstance.path]
        return parser


    @mkdir.set_validation
    def mkdir_validate(self, promptinstance, parsedata):
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



    #------------------------------------------------------------------
    #                               MKREF
    #------------------------------------------------------------------
    @Command("mkref", 
    "Makes a new reference",
    """
mkref ./newref ./folder1 # make a reference names "newref" that references folder1 
mkref ./newref /  # make a reference names "newref" that references root
    """)
    def mkref(self, promptinstance, parsedata):
        references = promptinstance.path.get_on_path(parsedata.referencespath)

        refpath = parsedata.refpath
        fullpath = CommandParser.splitargs(refpath, "/")
        existpath = '/'.join(fullpath[:-1])
        if(refpath.startswith("/")):
            existpath = "/" + existpath
        newpath = fullpath[-1]
        wdir = promptinstance.path.get_on_path(existpath)

        obj = Reference(newpath, references, wdir)
        wdir.childrefs[newpath] = obj


    @mkref.set_completionargs
    def mkref_completionargs(self, promptinstance, parser: CommandParser):
        arg = parser.add_arg("refpath", None, "path to new reference", True, True, False, False)
        arg.vals = [promptinstance.path]
        arg = parser.add_arg("referencespath", None, "path to file/folder that the new reference with lead to", True, True, False, False)
        arg.vals = [promptinstance.path]
        return parser


    @mkref.set_validation
    def mkref_validate(self, promptinstance, parsedata):
        references = promptinstance.path.get_on_path(parsedata.referencespath)
        if(not references):
            return "Invalid reference path \"{}\"".format(parsedata.referencespath)

        refpath = parsedata.refpath
        fullpath = CommandParser.splitargs(refpath, "/")
        existpath = '/'.join(fullpath[:-1])
        if(refpath.startswith("/")):
            existpath = "/" + existpath
        newpath = fullpath[-1]
        wdir = promptinstance.path.get_on_path(existpath)
        if(not wdir):
            return "Invalid new path \"{}\"".format(existpath)

        if(isinstance(wdir, File)):
            return "New reference path cannot lead to a file"

        if(x := wdir.childfiles.get(CommandParser.remove_quotes(newpath), None)):
            return "{}: File already exists in {}".format(x.name, wdir.fullpath)

        if(x := wdir.childfolders.get(CommandParser.remove_quotes(newpath), None)):
            return "{}: Folder already exists in {}".format(x.name, wdir.fullpath)

        if x :=(wdir.childrefs.get(CommandParser.remove_quotes(newpath), None)):
            return "{}: Reference already exists in {}".format(x.name, wdir.fullpath)


    #------------------------------------------------------------------
    #                               RM
    #------------------------------------------------------------------

    @Command("rm", 
    "remove object in filesystem",
    """
rm ./folder #removes folder
rm ./reference # removes reference, NOTE: this will not remove the object the reference points to
    """)
    def rm(self, promptinstance, parsedata):
        obj = promptinstance.path.get_on_path(parsedata.path, retref=True)
        if(isinstance(obj, File)):
            self.delrefs(obj)
            del obj.parent.childfiles[obj.name]
        if(isinstance(obj, Folder)):
            self.delrefs(obj)
            del obj.parent.childfolders[obj.name]
        if(isinstance(obj, Reference)):
            del obj.parent.childrefs[obj.refname]

    def delrefs(self, obj):
        for refname, ref in obj.parentrefs.items():
            del ref.parent.childrefs[ref.refname] 

    @rm.set_completionargs
    def rm_completionargs(self, promptinstance, parser):
        arg = parser.add_arg("path", None, "path to navigate into", True, True, False)
        arg.vals = [promptinstance.path]

        return parser


    @rm.set_validation
    def rm_validate(self, promptinstance, parsedata):
        path = parsedata.path

        if(not (r := promptinstance.path.get_on_path(path, retref=True))):
            return "Invalid Path"
        if(r.level == "SYS"):
            return "Cannot delete system level objects"


    #------------------------------------------------------------------
    #                               MV
    #------------------------------------------------------------------
    @Command("mv", 
    "moves a file/ref/folder toa  folder",
    """
mkref ./file ./folder1/ # moves file1 into folder1 
    """)
    def mv(self, promptinstance, parsedata):
        mvobject = promptinstance.path.get_on_path(parsedata.mvpath, retref=True)
        newpath = promptinstance.path.get_on_path(parsedata.newpath)
        if(isinstance(mvobject, File)):
            del mvobject.parent.childfiles[mvobject.name]
            mvobject.parent = newpath
            newpath.childfiles[mvobject.name] = mvobject
        if(isinstance(mvobject, Folder)):
            del mvobject.parent.childfolders[mvobject.name]
            mvobject.parent = newpath
            newpath.childfolders[mvobject.name] = mvobject
        if(isinstance(mvobject, Reference)):
            del mvobject.parent.childfolders[mvobject.name]
            mvobject.parent = newpath
            newpath.childrefs[mvobject.refname] = mvobject
        


    @mv.set_completionargs
    def mv_completionargs(self, promptinstance, parser: CommandParser):
        arg = parser.add_arg("mvpath", None, "path to object to move", True, True, False, False)
        arg.vals = [promptinstance.path]
        arg = parser.add_arg("newpath", None, "path directory to put the file in", True, True, False, False)
        arg.vals = [promptinstance.path]
        return parser


    @mv.set_validation
    def mv_validate(self, promptinstance, parsedata):
        mvpath = promptinstance.path.get_on_path(parsedata.mvpath, retref=True)
        if(not mvpath):
            return "Invalid path \"{}\"".format(mvpath)

        newpath = promptinstance.path.get_on_path(parsedata.newpath)
        if(not newpath):
            return "Invalid path \"{}\"".format(newpath)

        if(isinstance(newpath, File)):
            return "path cannot lead to a file: {}".format(newpath)

        if(mvpath.level == "SYS"):
            return "Cannot move system level objects"

    #------------------------------------------------------------------
    #                              RENAME
    #------------------------------------------------------------------
    @Command("rename", 
    "rename file/ref/folder",
    """
rename ./file ./newfilename # changes file name for "file" to "newfilename" 
    """)
    def rename(self, promptinstance, parsedata):
        path = promptinstance.path.get_on_path(parsedata.path, retref=True) 
        name = parsedata.newname
        if(isinstance(path, File)):
            del path.parent.childfiles[path.name]
            path.name = name
            path.parent.childfiles[path.name] = path
        if(isinstance(path, Folder)):
            del path.parent.childfolders[path.name]
            path.name = name
            path.parent.childfiles[path.name] = path
        if(isinstance(path, Reference)):
            del path.parent.childrefs[path.refname]
            del path.references.parentrefs[path.refname]
            path.refname = name
            path.references.parentrefs[path.refname] = path
            path.parent.childrefs[path.refname] = path
        


    @rename.set_completionargs
    def rename_completionargs(self, promptinstance, parser: CommandParser):
        arg = parser.add_arg("path", None, "path to file", True, True, False, False)
        arg.vals = [promptinstance.path]
        parser.add_arg("newname", None, "new name for file", True, True, False, False)
        return parser


    @rename.set_validation
    def rename_validate(self, promptinstance, parsedata):
        path = promptinstance.path.get_on_path(parsedata.path, retref=True)
        if(not path):
            return "Invalid path \"{}\"".format(path)


def setup(shell):
    instance = Modification.load(shell)
    return instance