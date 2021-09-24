# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

######################################################################
# Texture Locator
#
# Summary
#
#     Show a view of all files used by image nodes in the current
#     material and allow the user to change the sources
#
#     Under the list (tree) view of files, the currently selected file is
#     previewed and images which use it can be renamed
#
# Buttons
#
#    Refresh
#        scans the node tree for all source images
#
#    Select
#        selects all nodes which use an image or any image in a folder
#
#    Change File
#        change the source for images which use the selected file
#
#    Change Folder
#        change all sources in a folder (recursively), any missing images
#        will be left unchanged

import os
import bpy

import bpy.utils.previews

from bpy_extras.io_utils import ImportHelper

from bpy.props import (StringProperty,
                       IntProperty,
                       CollectionProperty,
                       BoolProperty,
                       PointerProperty)

from bpy.types import (PropertyGroup,
                       UIList,
                       Operator,
                       Image,
                       Panel,
                       Menu)

######################################################################

bl_info = {
    "name": "Texture Locator",
    "description": "For managing Image node sources",
    "blender": (2, 80, 0),
    "category": "Material",
    "location": "Material > Tool",
    "author": "Charlie Skilbeck",
    "version": (0, 0, 1),
    "support": "TESTING",
    "doc_url": "http://skilbeck.com",
    "wiki_url": "",
    "tracker_url": ""
}

######################################################################
# jumping through hoops to make UIList behave like a TreeView


class ImagePointer(PropertyGroup):

    img: PointerProperty(type=Image)


class ListItem(PropertyGroup):

    parent: IntProperty()
    path: StringProperty()
    is_folder: BoolProperty()
    expanded: BoolProperty(default=True)
    images: CollectionProperty(type=ImagePointer)

######################################################################
# one instance of MyStuff is stored in (of all places) context.window_manager

# don't want to put it in context.scene because it's not supposed to be
# persistent, just working storage that can be used to display a UIList

# if anyone has any better ideas about where to keep this and still make
# it accessible from a UIList I'm all ears


class MyStuff(PropertyGroup):

    # the items in the UIList
    list_items: CollectionProperty(type=ListItem)

    # the index of the selected item in the UIList
    list_index: IntProperty(default=-1, name=" ")

    # the last scanned material name - if current material name
    # is different from this, then rescan
    material_name: StringProperty()

    # node source(s) changed so refresh the UIList next time it's drawn
    refresh_required: BoolProperty()

######################################################################
# split a layout into columns based on list of ratios


def split_layout(layout, ratios, **kwargs):
    columns = []
    for i in range(len(ratios)):
        layout = layout.split(factor=ratios[i] / sum(ratios[i:]))
        columns.append(layout.column(**kwargs))
    return columns

######################################################################
# check if node at index i is a child of node at index p


def is_child(items, i, p):
    i = items[i].parent
    while(i != -1):
        if i == p:
            return True
        i = items[i].parent
    return False


######################################################################
# helper for poll() functions


def is_in_shader_node_editor(context):
    return (context.space_data
            and context.space_data.type == "NODE_EDITOR"
            and context.space_data.tree_type == "ShaderNodeTree")


######################################################################
# only show select/move buttons if a valid item is selected


def show_select_or_move(context):
    s = context.window_manager.tl_stuff
    index = s.list_index
    items = s.list_items
    return (is_in_shader_node_editor(context)
            and 0 <= index < len(items))

######################################################################
# get filepath for an image list_item (prepend parent path)


def image_path(items, index):
    path = items[index].path
    p = items[index].parent
    return None if p == -1 else os.path.join(items[p].path, path)

######################################################################
# change image filepath, maintaining relativity if possible


def replace_path(image, new_path):
    if image.filepath[:2] == '//':
        try:
            new_path = bpy.path.relpath(new_path)
        except ValueError:
            pass
    image.filepath = new_path


######################################################################


class TEXTURE_LOCATOR_OT_ChangeFolder(Operator):

    """ Select a new folder for all children of a path """

    bl_idname = "texture_locator.change_folder"
    bl_label = "Change folder"

    directory: StringProperty()

    @classmethod
    def poll(cls, context):
        return show_select_or_move(context)

    def execute(self, context):
        new_dir = self.properties.directory
        s = context.window_manager.tl_stuff
        index = s.list_index
        items = s.list_items
        item = items[index]
        missing = 0
        for n in range(index + 1, len(items)):
            if not is_child(items, n, index):
                break
            if not items[n].is_folder:
                local = image_path(items, n)
                if local:
                    relative = os.path.relpath(local, item.path)
                    newfile = os.path.join(new_dir, relative)
                    if os.path.exists(newfile):
                        for img in items[n].images:
                            replace_path(img.img, newfile)
                        s.refresh_required = True
                    else:
                        print(f"Warning: Can't find {newfile}")
                        missing += 1
        if missing != 0:
            self.report({'WARNING'}, f"{missing} files not found")
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

######################################################################


class TEXTURE_LOCATOR_OT_ChangeFile(Operator):

    """ Select a new file source for an Image """

    bl_idname = "texture_locator.change_file"
    bl_label = "Change file"

    filepath: StringProperty()

    @classmethod
    def poll(cls, context):
        return show_select_or_move(context)

    def execute(self, context):
        newfile = self.properties.filepath
        if not os.path.exists(newfile):
            print(f"Warning: Can't find {newfile}")
            self.report({'ERROR'}, f"{newfile} not found")
        else:
            s = context.window_manager.tl_stuff
            index = s.list_index
            items = s.list_items
            item = items[index]
            for img in item.images:
                replace_path(img.img, newfile)
            s.refresh_required = True
        return {'FINISHED'}

    def invoke(self, context, event):
        self.use_filter_image = True
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

######################################################################


class TEXTURE_LOCATOR_OT_Select(Operator):

    """ Select the shader nodes which are using the selected texture(s) """

    bl_idname = "texture_locator.select"
    bl_label = "Select"

    @classmethod
    def poll(cls, context):
        return show_select_or_move(context)

    def select(self, context, item):
        for img in item.images:
            nodes = context.space_data.node_tree.nodes
            valid = ["GENERATED", "VIEWER"]
            for n in nodes:
                should_select = (n.bl_idname == "ShaderNodeTexImage"
                                 and n.image is not None
                                 and not n.image.source in valid
                                 and n.image.name == img.img.name)
                n.select |= should_select

    def execute(self, context):
        s = context.window_manager.tl_stuff
        index = s.list_index
        items = s.list_items
        item = items[index]

        bpy.ops.node.select_all(action='DESELECT')

        if not item.is_folder:
            self.select(context, item)
        else:
            for n in range(index + 1, len(items)):
                if is_child(items, n, index):
                    self.select(context, items[n])
                else:
                    break

        bpy.ops.node.view_selected()

        return {'FINISHED'}

######################################################################


class TEXTURE_LOCATOR_UL_List(UIList):

    """ UIList of folders and texture files - ghetto treeview mode """

    # filter based on tree nodes rather than... the filter

    def filter_items(self, context, data, propname):

        items = getattr(data, propname)

        # order never changes

        order = [n for n in range(0, len(items))]

        # apparently you:
        #     set bitflag_filter_item to SHOW it
        #     clear bitflag_filter_item to HIDE it

        # hide children of nodes which are not expanded

        flags = [0] * len(items)

        index = 0
        for i in items:

            show = self.bitflag_filter_item
            p = i.parent
            while p != -1:
                if not items[p].expanded:
                    show = 0
                    break
                p = items[p].parent

            flags[index] = show
            index += 1

        return flags, order

    # hide the filter UI

    def draw_filter(self, context, layout):
        pass

    # draw one

    def draw_item(self, context, layout, data, item,
                  icon, active_data, active_propname, index, flt_flag):

        s = context.window_manager.tl_stuff
        items = s.list_items

        row = layout.row(align=True)

        # indent with dummy props

        p = item.parent
        while p != -1:
            row.prop(item, "expanded", icon="NONE", text="", emboss=False)
            p = items[p].parent

        rel = item.path

        if item.is_folder:
            icon1 = 'TRIA_DOWN' if item.expanded else 'TRIA_RIGHT'
            icon2 = "COLLECTION_COLOR_05"
            if item.parent != -1:
                rel = os.path.relpath(item.path, items[item.parent].path)
        else:
            icon1 = "NONE"
            icon2 = "IMAGE_DATA"

        # icon1 toggles expansion which only matters for folders
        # but still use a prop so alignment is maintained

        row.prop(item, "expanded", text="", emboss=False, icon=icon1)

        # icon2 + text

        row.label(text=rel, icon=icon2)

######################################################################
# scan for unique images / paths


def do_scan(context):

    s = context.window_manager.tl_stuff

    paths = {}

    # this check _should_ be unnecessary but...

    if context.space_data and context.space_data.node_tree:

        # scan all the nodes

        for n in context.space_data.node_tree.nodes:

            # if node has an Image which is based on a source file

            img = getattr(n, "image", None)

            if img is not None and img.filepath:

                # get path and filename

                path, name = os.path.split(bpy.path.abspath(img.filepath))
                if path and name:

                    # add new path if haven't seen it yet

                    if path not in paths:
                        paths[path] = []

                    # and any new image(s) which reference the file

                    exists = False
                    for e in paths[path]:
                        if e['filename'] == name:
                            if not img in e['images']:
                                e['images'].append(img)
                            exists = True
                            break
                    if not exists:
                        paths[path].append({
                            "filename": name,
                            "images": [img]})

    # sorted list of paths so parents come before children

    sorted_paths = sorted(paths.keys())

    # now make the List Items

    items = s.list_items

    # try to keep the selection on the thing it was on before...

    index = s.list_index

    old_path = ""
    old_parent = ""
    if index != -1:
        item = items[index]
        old_path = item.path
        if not item.is_folder:
            old_parent = items[item.parent].path

    new_index = -1

    items.clear()

    index = 0
    for p in sorted_paths:

        # find most recent parent folder (or -1 if it's a root path)

        parent = -1
        for i in range(index - 1, -1, -1):
            if items[i].is_folder and bpy.path.is_subdir(p, items[i].path):
                parent = i
                break

        # add folder to the list

        x = items.add()
        x.is_folder = True
        x.path = p
        x.index = index
        x.parent = parent
        x.expanded = True

        # was this one (or a child of this one) selected before?

        if p == old_path or p == old_parent:
            old_parent = ""
            new_index = index

        parent = index
        index += 1

        # add the files in that folder to the list

        for t in paths[p]:

            y = items.add()
            y.is_folder = False
            y.path = t["filename"]
            y.index = index
            y.parent = parent
            for i in t['images']:
                img_ptr = y.images.add()
                img_ptr.img = i

            # refresh the preview from image 0, should be the same for all
            # the images in the list

            t['images'][0].preview.reload()

            # was this the one they had selected before?

            if new_index == parent and old_path == y.path:
                new_index = index
                old_path = ""
                old_parent = ""

            index += 1

    # selection index hopefully pointing at same old one or none

    s.list_index = new_index

######################################################################


class TEXTURE_LOCATOR_OT_Refresh(Operator):

    """ Refresh list of textures """

    bl_idname = "texture_locator.refresh"
    bl_label = "Refresh"

    @classmethod
    def poll(cls, context):
        return is_in_shader_node_editor(context)

    def execute(self, context):
        do_scan(context)
        return {'FINISHED'}

######################################################################


class TEXTURE_LOCATOR_PT_TextureLocatorPanel(Panel):

    """ Texture Locator Panel """

    bl_label = "Texture Locator"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_context = "node"
    bl_category = "Tool"
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 10000

    @classmethod
    def poll(cls, context):
        return is_in_shader_node_editor(context)

    def draw(self, context):

        s = context.window_manager.tl_stuff

        active = context.active_object

        # rescan the tree when active material changes or changes
        # have been made via the Change File/Folder button

        # would be nice to track node new/delete but msgbus doesn't
        # seem to want to play ball there so if you add/remove any
        # nodes you have to manually refresh it

        if (active.active_material.name != s.material_name
                or s.refresh_required):
            s.refresh_required = False
            s.material_name = active.active_material.name
            do_scan(context)

        # first the buttons

        items = s.list_items
        index = s.list_index

        layout = self.layout

        cols = split_layout(layout, [1, 1])
        row = cols[0].row(align=True)
        row.operator("texture_locator.refresh")
        row.operator("texture_locator.select")

        if 0 > index or index >= len(items):
            cols[1].label(text="")
        elif items[index].is_folder:
            cols[1].operator("texture_locator.change_folder")
        else:
            cols[1].operator("texture_locator.change_file")

        # then the UIList (treeview)

        row = layout.row()
        row.template_list("TEXTURE_LOCATOR_UL_List", "Items",
                          s, "list_items", s, "list_index")

        # then details and image preview if selected item is an image

        if 0 <= index < len(items):
            item = items[index]
            if not item.is_folder:
                for img in item.images:
                    row = layout.row()
                    row.prop(img.img, "name", icon="IMAGE_DATA", text="")

                image = item.images[0].img
                row = layout.row()
                row.label(text=f"{image.size[0]} x {image.size[1]}")
                row = layout.row()
                row.template_icon(icon_value=image.preview.icon_id, scale=8)

######################################################################


classes = [
    ImagePointer,
    ListItem,
    MyStuff,
    TEXTURE_LOCATOR_OT_ChangeFile,
    TEXTURE_LOCATOR_OT_ChangeFolder,
    TEXTURE_LOCATOR_UL_List,
    TEXTURE_LOCATOR_OT_Refresh,
    TEXTURE_LOCATOR_OT_Select,
    TEXTURE_LOCATOR_PT_TextureLocatorPanel
]

######################################################################


def register():

    for c in classes:
        bpy.utils.register_class(c)

    bpy.types.WindowManager.tl_stuff = bpy.props.PointerProperty(type=MyStuff)

######################################################################


def unregister():

    del bpy.types.WindowManager.tl_stuff

    for c in classes:
        bpy.utils.unregister_class(c)

    # not sure this is doing anything...
    # was getting some shirty messages about dangling something

    bpy.utils.previews.clear()

######################################################################


if __name__ == "__main__":
    register()
