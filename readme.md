# Texture Locator

### Summary

Show a view of all files used by image nodes in the current material and allow the user to change the sources.

Under the list (tree) view of files, the currently selected file is previewed and images which use it can be renamed.

### Installation / Usage

Instructions for installing add-ons are [here](https://docs.blender.org/manual/en/latest/editors/preferences/addons.html#installing-add-ons)

- Install and enable the add-on (note you will need to enable the 'Testing' filter to see it in the preferences)
- Activate a Material which has some file based Image nodes in it
- Go to the Shader Editor
- Select the 'Tool' tab
- You should see a new panel called 'Texture Locator' in there

### Screenshot

![screenshot](screenshot.png)

### Buttons

Above the files there are some buttons, this is what they do:

|Button|Function|
|-|-|
|Refresh|Scans the node tree for all source images|
|Select|Selects all nodes which use an image or any image in a folder|
|Change File|Change the source for images which use the selected file|
|Change Folder|Change all sources in a folder (recursively), any missing images will be left unchanged|


### Notes / Issues / Limitations

I haven't managed to get `bpy.msgbus` to trigger a callback when the set of nodes in the active material changes, so you have to click 'Refresh' after adding or removing any Image nodes. If anyone knows how to make this work I'd be happy to hear about it.

The UIList view of files/folders is jerry-rigged to look like a tree view. It sort of works but is kind of janky. I couldn't find a proper tree view exposed in the Python API anywhere.

The tooltips for the items in the UIList are all wrong. I haven't figured out how to make them useful.

I can't see a way to set the filter in the file dialog so you are only shown image files when you click 'Change Image'. At the moment it shows files of all types which might lead to confusion.

Undo is somewhat broken. After making changes with 'Change File' or 'Change Folder' you have to press ctrl-z twice to get the action undone. Also the image preview gets corrupted after the undo until you press 'Refresh'. From what I can see on the forums, undo support for add-ons is a little shaky. I've tried with manually calling `bpy.ops.ed.undo_push()` as well as specifying `bl_options = {"REGISTER", "UNDO"}` in the operator, the result is the same in either case.

### bl_info

```
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
```