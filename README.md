![Demo](https://github.com/Shriinivas/etc/blob/master/shapekeyimport/illustrations/intro.gif)
# Blender add-on to import paths as shape keys<br>
This add-on lets you import paths from an SVG file as paths as well as shape keys <br><br>
Supported Blender versions<br>
2.8+ and 3.x (Script File - shapekeyimport_2_8.py) <br>
2.79b (Script File - shapekeyimport.py) <br>

# Installation
For Blender 2.8+ and 3.x, download shapekeyimport_2_8.py; for 2.79b download svgimport.py<br><br>
In Blender select File->User Preferences <br>
Click install Add-ons tab and then Install Add-on from File<br>
Select the downloaded file <br>
Check the 'Import Paths and Shape Keys' option in the add-ons dialog <br>
  
You can invoke the add-on in 2.79 by pressing spacebar or in 2.8+ / 3.x by pressing F3 in the 3d view and selecting the <br>
'Import Paths & Shape Keys' option<br> The add-on is also accesible from Import menu under File<br>

'demo.blend' and 'demo ver 2.blend' illustrate the basic functionality and the new enhancements of version 2. You can import one of the SVGs (via import shape keys option) in a new blender file to verify the functionality. 


# Quick start
![Demo](https://github.com/Shriinivas/etc/blob/master/shapekeyimport/illustrations/git.gif)
(SVG Editor: Inkscape)<br>
Group the paths in the SVG editor, make sure the group is in some Layer and the target is the first node in the XML group node &lt;svg:g&gt;<br>
Invoke the add-on in Blender, select the svg file and click 'Import Paths & Shapekeys' button<br>
The target now has the shapekeys that correspond to the paths in the svg group  <br>

(SVG Editor: Inkscape and others)<br>
Alternatively, you can create target-shapekey relationship by adding an xml attribute 'shapekeys' in the <br>
target path and setting its value to the comma separated IDs of the shapekey paths<br>
In case you are using SVG Editor other than Inkscape, you may have to uncheck 'Import by Group' checkbox <br>
  
<a href=https://youtu.be/XMimQfQR_ss> The introductory video</a> and <a href=https://youtu.be/o6oCFZsM87M> the enhancements overview </a>  are a good starting point for exploring the add-on functionality

# Examples & Demos
You can find [here](https://github.com/Shriinivas/etc/tree/master/shapekeyimport/samples) the demo files used on this page as well as some samples demonstrating the add-on functionality 

# Limitations
Exercise caution when using this add-on in production as it's in beta stage<br>

As of now the Add-on is tested with Inkscape only. If you face issues with other SVG editors, try exporting the file as plain SVG <br> Please report such and other issues along with the sample files here and I will look into them as soon as I can <br>

Keep watching this space, as there will be updates to the code as and when bugs are discovered and fixed <br>

# Credits
The add-on file includes python converted <a href=https://github.com/fontello/svgpath>a2c</a> js function (Copyright (C) 2013-2015 by Vitaly Puzrin)
and some portion imported from <a href=https://github.com/mathandy/svgpathtools>svgpathtools</a> (Copyright (c) 2015 Andrew Allan Port, Copyright (c) 2013-2014 Lennart Regebro)<br>
A few of the bezier curve related algorithms were inspired by the answers on stackoverflow; their links can be found in the code.

# License
<a href=https://github.com/Shriinivas/shapekeyimport/blob/master/LICENSE>MIT</a>
