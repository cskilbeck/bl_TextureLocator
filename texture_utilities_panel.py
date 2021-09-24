import os
import bpy
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, IntProperty, CollectionProperty, BoolProperty, PointerProperty
from bpy.types import PropertyGroup, UIList, Operator, Panel
import bpy.utils.previews

######################################################################

class TreeItem(PropertyGroup):

    index: IntProperty(name="index")
    parent: IntProperty(name="parent")

######################################################################

class ListItem(TreeItem):

    """ a folder containing some texture files or a texture file """

    # jumping through hoops to make UIList behave like a TreeView

    path: StringProperty(name="path")
    is_folder: BoolProperty(name="is_folder")
    relative_path: StringProperty(name="relative_path")
    expanded: BoolProperty(name="expanded", description="Expanderooo")
    image_name: StringProperty(name="image_name")

######################################################################

class MyStuff(PropertyGroup):
    
    """ Stuff we need to access all over the place """
    
    list_items: CollectionProperty(type=ListItem, name = "list_items")
    list_index: IntProperty(name = "list_index", default = -1)

######################################################################

class RemapFolder(bpy.types.Operator, ImportHelper):
    
    """ remap files in current folder to a new one """

    bl_idname = "texture_utilities.remap_folder"
    bl_label = "Relocate"

    @classmethod
    def poll(cls, context):
        
        stuff = context.window_manager.stuff
        index = stuff.list_index
        folders = stuff.list_items
        return (context.space_data.type == "NODE_EDITOR"
                and 0 <= index < len(folders)
                and folders[index].is_folder)
                
    def execute(self, context):

        path = os.path.dirname(os.path.abspath(self.properties.filepath))
        self.report({'INFO'}, f"Remap to {path}")
        return {'FINISHED'}

######################################################################

class FILES_UL_List(UIList):

    """ UIList of folders and texture files - ghetto treeview mode """

    def filter_items(self, context, data, propname):

        items = getattr(data, propname)

        order = [n for n in range(0, len(items))]

        # set bitflag_filter_item to SHOW it
        # clear bitflag_filter_item to HIDE it

        flags = [self.bitflag_filter_item] * len(items)

        index = 0
        for i in items:

            # show if all parents are expanded

            show = True
            p = i.parent
            while p != -1:
                show &= items[p].expanded
                p = items[p].parent

            flags[index] &= ~(0 if show else self.bitflag_filter_item)
            index += 1

        return flags, order
    
    def draw_filter(self, context, layout):
        pass

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index, flt_flag):

        stuff = context.window_manager.stuff
        folders = stuff.list_items

        indent = 0
        p = item.parent
        while p != -1:
            indent += 1
            p = folders[p].parent

        row = layout.row(align = True)
        
        for n in range(indent):
            row.prop(item, "expanded", icon = "NONE", text = "", emboss = False)

        if item.is_folder:
            item_icon = "COLLECTION_COLOR_05"
            icn = 'TRIA_DOWN' if item.expanded else 'TRIA_RIGHT'
        else:
            item_icon = "IMAGE_DATA"
            icn = "NONE"

        row.prop(item, "expanded", text = "", emboss = False, icon = icn)
        row.label(text=item.relative_path, icon = item_icon)

######################################################################

class ScanForFolders(bpy.types.Operator):

    """Find all the folders where textures are stored"""

    bl_idname = "texture_utilities.scan_files"
    bl_label = "Scan"
    
    @classmethod
    def poll(cls, context):
        space = context.space_data
        return space.type == 'NODE_EDITOR'

    def execute(self, context):

        # get a dictionary of paths containing lists of files

        stuff = context.window_manager.stuff

        paths = {}

        for n in context.space_data.node_tree.nodes:
            if n.bl_idname == "ShaderNodeTexImage" and not n.image.source in ["GENERATED", "VIEWER"]:
                path, name = os.path.split(bpy.path.abspath(n.image.filepath))
                if path and name:
                    if path not in paths:
                        paths[path] = []
                    found = False
                    if not [e for e in paths[path] if e['filename'] == name]:
                        paths[path].append({"filename": name, "image_name": n.image.name})

        # sorted list of paths so parents come before children

        sorted_paths = sorted(paths.keys())

        folders = stuff.list_items
        
        folders.clear()

        index = 0
        for p in sorted_paths:

            # find most recent parent folder

            relative = p
            parent = -1
            for i in range(index - 1, -1, -1):
                if folders[i].is_folder and bpy.path.is_subdir(p, folders[i].path):
                    relative = os.path.relpath(p, folders[i].path)
                    parent = i
                    break

            # add folder to the list

            x = folders.add()
            x.is_folder = True
            x.path = p
            x.relative_path = relative
            x.index = index
            x.parent = parent
            index += 1;
            
            # add the files in that folder to the list

            for t in paths[p]:
                f = t["filename"]
                y = folders.add()
                y.is_folder = False
                y.path = f
                y.relative_path = f
                y.index = index
                y.parent = x.index
                y.image_name = t['image_name']

                index += 1;

        stuff.list_index = -1

        return {'FINISHED'}

######################################################################

class ResetFolders(bpy.types.Operator):

    """ Clear the list of files and folders """

    bl_idname = "texture_utilities.clear_folders"
    bl_label = "Clear"

    def execute(self, context):

        context.window_manager.stuff.list_items.clear()
        return {'FINISHED'}

######################################################################

def padded_row(layout, padding):
    """ make a row with some padding on either side """
    row = layout.row()
    split = row.split(factor = padding)
    split.column()
    padding = (1 - padding * 2) / (1 - padding)
    return split.column().row().split(factor = padding).column().row()

######################################################################

class NODE_PT_TextureRemapPanel(bpy.types.Panel):

    """ Texture Utilities """

    bl_label = "Texture Locator"
    bl_idname = "NODE_PT_TextureRemapPanel"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_context = "node"
    bl_category = "Tool"
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 1000
    
    def draw(self, context):
        
        layout = self.layout

        row = padded_row(layout, 0.1)
        row.operator("texture_utilities.scan_files")
        row.operator("texture_utilities.clear_folders")
        row.operator("texture_utilities.remap_folder")

        row = layout.row()
        row.template_list("FILES_UL_List", "Folders", context.window_manager.stuff, "list_items", context.window_manager.stuff, "list_index")
        
        folders = context.window_manager.stuff.list_items
        index = context.window_manager.stuff.list_index
            
        if 0 <= index < len(folders) and folders[index].image_name:
            name = folders[index].image_name
            if name in bpy.data.images:
                image = bpy.data.images[name]
                size = image.size
                row = layout.row()
                split = row.split()
                col1 = split.column()
                col2 = split.column()
                col1.row().label(text = f"{image.name_full}")
                col1.row().label(text = f"{size[0]} x {size[1]}")
                col2.row().template_icon(icon_value=image.preview.icon_id, scale=6)


######################################################################

classes = [
    RemapFolder,
    ScanForFolders,
    NODE_PT_TextureRemapPanel,
    TreeItem,
    ListItem,
    MyStuff,
    FILES_UL_List,
    ResetFolders]

######################################################################

def register():

    global classes
    for c in classes:
        bpy.utils.register_class(c)

    bpy.types.window_manager.stuff = bpy.props.PointerProperty(type=MyStuff)
    
######################################################################

def unregister():

    del bpy.types.WindowManager.stuff

    global classes
    for c in classes:
        bpy.utils.unregister_class(c)

    # not sure this is doing anything... was getting some shirty messages saying to call it

    bpy.utils.previews.remove()
    
######################################################################

if __name__ == "__main__":
    register()
