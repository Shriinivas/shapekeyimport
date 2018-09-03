# Blender add-on to import paths as shape keys<br>
This add-on lets you import paths from an SVG file as paths as well as shape keys
Supported Blender version: 2.79b

# Installation
Download the svgimport.py file and in Blender select File->User Preferences <br>
Click install Add-ons tab and then Install Add-on from File<br>
Select the downloaded file <br>
Check the option 'Import Shapekeys and Paths' option in the add-ons dialog <br>
Click 'Save User Settings'<br>
  
You can invoke the add-on by pressing spacebar in the 3d view and selecting the <br>
'Import Paths & Shapekeys' option<br>

The demo.svg and demo.blend illustrate the functionality. You can import the demo.svg in a new blender file to see the shapekeys of the main object in action. Uncheck the Relative option to apply all shape keys one by one in turn.


# Quick start
Group the paths in the SVG editor, make sure the target is the first node in the XML group node &lt;svg:g&gt;<br>
Invoke the add-on in Blender, select the svg file and click 'Import Paths & Shapekeys' button<br>
The target now has the shapekeys that correspond to the paths in the svg group  <br>

Alternatively, you can create target-shapekey relationship by adding an xml attribute 'shapekeys' in the <br>
target path and setting its value to the comma separated IDs of the shapekey paths<br>
  
<a href=https://youtu.be/XMimQfQR_ss> This video</a> provides a more detailed overview of the add-on and the various options available

# Limitations
Exercise caution when using this add-on in production as it's in alpha stage<br>

# Credits
The add-on file includes python converted <a href=https://github.com/fontello/svgpath>a2c</a> js function (Copyright (C) 2013-2015 by Vitaly Puzrin)
and some portion imported from <a href=https://github.com/mathandy/svgpathtools>svgpathtools</a> (Copyright (c) 2015 Andrew Allan Port, Copyright (c) 2013-2014 Lennart Regebro)

# License
<a href=https://github.com/Shriinivas/shapekeyimport/blob/master/LICENSE>MIT</a>
