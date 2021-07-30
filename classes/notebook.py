import imp
import re
from prettytable.prettytable import NONE
from prompt_toolkit.filters.app import renderer_height_is_known
from whoosh.query.ranges import TermRange
from classes.argparser import CommandParser
import os
import datetime
import getpass
import inspect
from whoosh.fields import SchemaClass, TEXT, KEYWORD, ID, STORED
from whoosh.qparser import QueryParser
from whoosh.writing import IndexWriter
import classes.prompt
from distutils.util import strtobool


class currUser:
    def __init__(self) -> None:
        self.username = getpass.getuser()
        self.uid = os.getuid()

class Base:
    def __init__(self) -> None:
        self.ignore = dict()
    
    @property
    def properties(self):
        keys =  [i for i in self.__dict__.keys()]
        vals =  [i for i in self.__dict__.values()]

        return dict(zip(keys, vals))

    def __getstate__(self):
        """Return state values to be pickled."""
        props = self.properties
        for name in self.ignore.keys():
            try:
                del props[name]
            except KeyError:
                continue
        return props

    def __setstate__(self, props):
        for name, val in props["ignore"].items():
            try:
                if(val == "%pr"):
                    val = classes.prompt.InteractiveShell.currinst #im lazy lol  
                props[name] = val
            except KeyError:
                continue    
        self.__dict__.update(props)    

        

class UpdateHandler:
    def __init__(self, name) -> None:
        self.name = name

    def val_getter(self, instance):
        if(not self.inited(instance)):
            setattr(instance, "_{}".format(self.name), None)
            return None
        instance.access()
        return getattr(instance, "_{}".format(self.name))

    def inited(self, instance):
        return getattr(instance, "_{}".format(self.name), None) != None

    def val_setter(self, value, instance):
        if(self.inited(instance)):
            instance.mod(name=self.name)
        setattr(instance, "_{}".format(self.name), value)

    def __get__(self, instance, owner):
        return self.val_getter(instance)

    def __set__(self, instance, value):
        self.val_setter(value, instance)

class Arg(Base):
    def __init__(self) -> None:
        super().__init__()
        self._datemodified = datetime.datetime.now()
        self._datecreated = datetime.datetime.now()


    @property
    def datecreated(self):
        return self._datecreated.strftime("%m/%d/%Y, %H:%M:%S")


    @property
    def datemodified(self):
        return self._datemodified.strftime("%m/%d/%Y, %H:%M:%S")

    def mod(self, *args, **kwargs):

        self._datemodified = datetime.datetime.now()
        self._dateaccessed = datetime.datetime.now()
        
        if(not isinstance(self, File)):
            return
        promptinstance = classes.prompt.InteractiveShell.currinst
        promptinstance.filecache.add(self)

    def access(self, *args, **kwargs):
        pass

class Folder(Arg):
    childfolders = UpdateHandler("childfolders")
    childfiles = UpdateHandler("childfiles")
    childrefs = UpdateHandler("childrefs")
    level = UpdateHandler("level")
    name = UpdateHandler("name")
    parent = UpdateHandler("parent")
    def __init__(self, name, parent, level="USER", ntbk=None) -> None:
        super().__init__()
        self.parent = parent
        self.name = name 
        if(ntbk):
            self.ntbk = ntbk
        else:
            self.ntbk = self.parent.ntbk
        self.id = self.ntbk.nextid
        self.ntbk.nextid += 1
        self.childfolders = dict()
        self.childfiles = dict()
        self.childrefs = dict()
        self.parentrefs = dict()
        self.level = level
        self.childrefs["."] = Reference(".", self, self, level="SYS")

        if(parent):
            self.childrefs[".."] = Reference("..", parent, self, level="SYS")
            parent.childfolders[name] = self
            

    @property 
    def fullpath(self):
        curr = "{}/".format(self.name)
        if(self.parent == None):
            return "/" + curr
        return self.parent.fullpath + curr

    @property
    def all_children_as_str(self):
        refs = list(map(lambda x: x+"/", list(self.childrefs.keys())))
        folders = list(map(lambda x: x+"/", list(self.childfolders.keys()))) 
        files = list(self.childfiles.keys())
        return refs + folders + files

class NotebookSchema(SchemaClass):
    id = ID(stored=False, unique=True)
    description = TEXT(stored=True)
    text = TEXT(stored=True)

class Ret:
    def __init__(self, val) -> None:
        self.val = val

class File(Arg):
    level = UpdateHandler("level")
    name = UpdateHandler("name")
    parent = UpdateHandler("parent")
    lexer = UpdateHandler("lexer")
    #text = UpdateHandler("text")
    #description = UpdateHandler("description")
    def __init__(self, name, parent, promptinstance, level="USER") -> None:
        super().__init__()
        self.promptinstance = promptinstance
        self.cached = False
        self.pending = dict()
        self.parent = parent
        self.name = name
        self.lexer = None
        self.level = level
        self.parentrefs = dict()
        if(parent):
            parent.childfiles[name] = self

        self.ntbk = self.parent.ntbk
        self.id = self.ntbk.nextid
        self.ntbk.nextid += 1

        promptinstance.writer.add_document(id=str(self.id), description="", text="")
        promptinstance.update = True

        self.ignore = {
            "promptinstance": "%pr",
            "pending": dict()
        }

    def query(self):
        q = QueryParser("", schema=self.promptinstance.writer.schema).parse(u"id:{}".format(str(self.id)))
        with self.promptinstance.writer.searcher() as s:
            results = s.search(q)[0].fields()
        return results

    def cache_file(self):
        #print("cached: {}".format(self.fullpath))
        if(self.cached):
            return
        self.cached = True

        results = self.query()
        self.c_description = results["description"]
        self.c_text = results["text"]

    def uncache_file(self):
        if(not self.cached):
            return
        self.cached = False
        for name, val in self.pending.items():
            self.promptinstance.writer.update_document(**val)
            self.promptinstance.update = True
        self.c_description = None
        self.c_text = None

    @property
    def description(self):
        if(self.cached):
            return self.c_description
        else:
            return self.query()["description"]

    @description.setter
    def description(self, val):
        self.mod()
        if(self.cached):
            self.c_description = val
            self.pending["description"] = {"id": str(self.id), "description": val, "text": self.text}
            return
        self.promptinstance.update = True
        self.promptinstance.writer.update_document(id=str(self.id), description=val, text=self.text)


    @property
    def text(self):
        if(self.cached):
            return self.c_text
        else:
            return self.query()["text"]

    @text.setter
    def text(self, val):
        self.mod()
        if(self.cached):
            self.c_text = val
            self.pending["text"] = {"id": str(self.id), "text": val, "description": self.description}
            return
        self.promptinstance.update = True
        self.promptinstance.writer.update_document(id=str(self.id), text=val, description=self.description)

    @property 
    def fullpath(self):
        curr = "{}".format(self.name)
        if(self.parent == None):
            return "/" + curr
        return self.parent.fullpath + curr

class Reference(Arg):
    level = UpdateHandler("level")
    name = UpdateHandler("name")
    parent = UpdateHandler("parent")
    references = UpdateHandler("references")
    def __init__(self, name ,references, parent, level="USER") -> None:
        super().__init__()
        if(isinstance(references, Reference)):
            raise ReferenceError("cannot reference a reference")
        self.parent = parent
        self.references = references
        references.parentrefs[name] = self
        self.refname = name
        self.level = level

        self.ntbk = self.parent.ntbk
        self.id = self.ntbk.nextid
        self.ntbk.nextid += 1
    
        
    @property
    def name(self):
        return "{} -> {}".format(self.refname, self.references.fullpath)

    @property 
    def fullpath(self):
        curr = "{}".format(self.refname)
        if(self.parent == None):
            return "/" + curr
        return self.parent.fullpath + curr

class EnviornmentVar:
    def __init__(self, name, help, val, checkfunc) -> None:
        self.name = name
        self.help = help
        self.checkfunc = checkfunc
        self.val = val

def checkifbool(val):
    try:
        return bool(strtobool(val))
    except:
        return "Value is not a bool"

def checkifint(val):
    try:
        i = int(val)
        if(i < -1):
            return "Integer cannot be lower than -1"
        return int(val)
    except:
        return "Value is not a integer"

class Notebook:
    def __init__(self, name) -> None:
        self.name = name
        self.user = currUser()
        self.env_vars = dict()
        self.history = list()

        self.nextid = 0 

        self._datecreated = datetime.datetime.now()
        self._datemodified = datetime.datetime.now()

        self.create_env_vars()

        self.root = Folder("root", None, ntbk=self)


    def create_env_vars(self):

        self.env_vars["save_after_command"] = EnviornmentVar("save_after_command", "If True saves notebook after each command", True, checkifbool)
        self.env_vars["reset_history"] = EnviornmentVar("reset_history", "If True clears command history at exit", False, checkifbool)
        self.env_vars["file_cache_length"] = EnviornmentVar("file_cache_length", "number of files that can be cached at a single time, whenever you read or modify a file, it gets cached\nNote:if either this or folder_cache_length has a value of -1, all files will be cached and saved when exited meanwhile both 0s mean that nothing will be cached\nAlso these only take effect after restart to avoid having to cache hundreds of files after changing values", 10, checkifint)
        self.env_vars["folder_cache_length"] = EnviornmentVar("folder_cache_length", "number of folder that can be cached at a single time, whenever you ls into a folder, all files in it get cached\nNote:if either this or file_cache_length has a value of -1, all files will be cached and saved when exited meanwhile both 0s mean that nothing will be cached\nAlso these only take effect after restart to avoid having to cache hundreds of files after changing values", 3, checkifint)

    @property
    def datecreated(self):
        return self._datecreated.strftime("%m/%d/%Y, %H:%M:%S")
    
    @property
    def datemodified(self):
        return self._datecreated.strftime("%m/%d/%Y, %H:%M:%S")


#class used to interpret paths in current context
class PathInterpreter:
    def __init__(self, root, cdir, all_files = True, currentdir = True) -> None:
        self.root = root
        self.cdir = cdir
        self.all_files = all_files
        self.currentdir = currentdir

    def parsepath(self, path):
        if(path[:1] == "/"):
            wdir = self.root
        else:
            wdir = self.cdir

        path = CommandParser.splitargs(path, "/")
        return wdir, path

    def get_on_path(self, path, retref=False):
        wdir, path = self.parsepath(path)
        if(path == []):
            wdir: Folder
            return wdir.childrefs.get(".").references 
        def good_code(p, d):
            if(folder := d.childfolders.get(p[0], None)):
                if(len(p) == 1):
                    return folder
                else:
                    return good_code(p[1:], folder)
            elif(ref := d.childrefs.get(p[0], None)):
                if(len(p) == 1):
                    if(not retref):
                        return ref.references
                    else:
                        return ref
                else:
                    return good_code(p[1:], ref.references)
            elif((file := d.childfiles.get(p[0], None)) and len(p) == 1):
                return file

            return None

        exit = good_code(path, wdir)
        return exit 


    def completions_on_path(self, path):
        parentdir = os.path.dirname(path)
        autocomplete = os.path.basename(path) 
        if(parentdir[:1] == "/"):
            wdir = self.root
        else:
            wdir = self.cdir

        path = list(filter(None , parentdir.split("/")))
        #path = CommandParser.splitargs(parentdir, )

        if(path == []):
            wdir: Folder
            return wdir.all_children_as_str

        def good_code(p, d):
            if(folder := d.childfolders.get(p[0], None)):
                if(len(p) == 1):
                    return folder.all_children_as_str
                else:
                    return good_code(p[1:], d)
            elif((ref := d.childrefs.get(p[0], None)) and isinstance(ref.references, Folder)):
                if(len(p) == 1):
                    return ref.references.all_children_as_str
                else:
                    return good_code(p[1:], ref.references)
            else:
                return []

        return good_code(path, wdir)