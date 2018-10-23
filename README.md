# Blender add-on to import paths as shape keys<br>
This add-on lets you import paths from an SVG file as paths as well as shape keys
Supported Blender version: 2.79b

# Installation
Download the svgimport.py file and in Blender select File->User Preferences <br>
Click install Add-ons tab and then Install Add-on from File<br>
Select the downloaded file <br>
Check the 'Import Paths and Shape Keys' option in the add-ons dialog <br>
  
You can invoke the add-on by pressing spacebar in the 3d view and selecting the <br>
'Import Paths & Shape Keys' option<br> The add-on is also accesible from Import menu under File

'demo.blend' and 'demo ver 2.blend' illustrate the basic functionality and the new enhancements of version 2. You can import one of the SVGs (via import shape keys option) in a new blender file to verify the functionality. Even though the import function currently works only with 2.79b, the imported shapes can be accessed from 2.8 alpha as well. So the blend files here can be opened with Blender 2.8


# Quick start
Group the paths in the SVG editor, make sure the target is the first node in the XML group node &lt;svg:g&gt;<br>
Invoke the add-on in Blender, select the svg file and click 'Import Paths & Shapekeys' button<br>
The target now has the shapekeys that correspond to the paths in the svg group  <br>

Alternatively, you can create target-shapekey relationship by adding an xml attribute 'shapekeys' in the <br>
target path and setting its value to the comma separated IDs of the shapekey paths<br>
  
<a href=https://youtu.be/XMimQfQR_ss> The introductory video</a> and <a href=https://youtu.be/o6oCFZsM87M> the enhancements overview </a>  are a good starting point for exploring the add-on functionality

# Limitations
Transform attribute in the SVG is not currently supported<br>
Exercise caution when using this add-on in production as it's in alpha stage<br>

# Credits
The add-on file includes python converted <a href=https://github.com/fontello/svgpath>a2c</a> js function (Copyright (C) 2013-2015 by Vitaly Puzrin)
and some portion imported from <a href=https://github.com/mathandy/svgpathtools>svgpathtools</a> (Copyright (c) 2015 Andrew Allan Port, Copyright (c) 2013-2014 Lennart Regebro)

# License
<a href=https://github.com/Shriinivas/shapekeyimport/blob/master/LICENSE>MIT</a>


