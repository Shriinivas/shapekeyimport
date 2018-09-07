#
#
# This Blender add-on imports paths and shapekeys from an  SVG file
# Supported Blender Version: 2.79b
#
# License: MIT (https://github.com/Shriinivas/shapekeyimport/blob/master/LICENSE)
#

#Not yet pep8 compliant

import bpy, copy, math
from bpy.props import FloatProperty, BoolProperty, StringProperty, CollectionProperty, EnumProperty
from xml.dom import minidom
from collections import OrderedDict
from mathutils import Vector
from math import sqrt, cos, sin, acos, degrees, radians
from cmath import exp, sqrt as csqrt, phase
from collections import MutableSequence
import re

bl_info = {
    "name": "Import Paths and Shapekeys from SVG",
    "category": "Import-Export",
}

noneStr = "-None-"

def getCurveNames(scene, context):
    return [(noneStr, noneStr, '-1')] + [(obj.name, obj.name, str(i)) for i, obj in enumerate(context.scene.objects) if obj.type == 'CURVE']

def getAlignmentList(scene, context):
    alignListStrs = [*getAlignOrderFns().keys()]
    return [(noneStr, noneStr, '-1')] + [(str(align), str(align), str(i)) for i, align in enumerate(alignListStrs)]

class ObjectImportShapekeys(bpy.types.Operator):
    bl_idname = "object.import_shapekeys" 
    bl_label = "Import Paths & Shapekeys"
    bl_options = {'REGISTER', 'UNDO'}

    filter_glob = StringProperty(default="*.svg")    
    filepath = StringProperty(subtype='FILE_PATH')

    #User input 
    shapekeyAttribName = StringProperty(name="Attribute")
    byGroup = BoolProperty(name="Import By Group")
    byAttrib = BoolProperty(name="Import By Attribute")
    addShapekeyPaths = BoolProperty(name="Retain Shape Key Paths")
    addNontargetPaths = BoolProperty(name="Import Non-target Paths")
    xScale = FloatProperty(name="X")
    yScale = FloatProperty(name="Y")
    zLocation = FloatProperty(name="Z Location")
    objList = EnumProperty(name='Copy Properties From', items=getCurveNames)
    alignList = EnumProperty(name='Node Alignment Order', items=getAlignmentList)
    addPathsFromHiddenLayer = BoolProperty(name="Import Hidden Layer Paths")
    originToGeometry = BoolProperty(name="Origin To Geometry")
    
    def execute(self, context):
        createdObjsMap = main(infilePath = self.filepath, shapekeyAttribName = self.shapekeyAttribName, byGroup = self.byGroup, 
                              byAttrib = self.byAttrib, addShapekeyPaths = self.addShapekeyPaths, addNontargetPaths = self.addNontargetPaths, 
                              scale = [self.xScale, -self.yScale, 1], zVal = self.zLocation, copyObjName = self.objList, 
                              alignOrder = self.alignList, pathsFromHiddenLayer = self.addPathsFromHiddenLayer, 
                              originToGeometry = self.originToGeometry)
        #Create demo video
        # ~ try:
            # ~ demoModule = [obj.data.body for obj in bpy.data.objects if obj.type == 'FONT'][0]
            # ~ print(demoModule)
            # ~ mod = __import__(demoModule, globals(), locals(), ['object'], 0)
            # ~ mod.postproc(createdObjsMap)
        # ~ except Exception as e:
            # ~ import traceback
            # ~ print(traceback.format_exc())
            # ~ pass
        return {'FINISHED'}
        
    def draw(self, context):
        layout = self.layout
        col = layout.column()
        row = col.row()
        row.prop(self, "byGroup")
        row = col.row()
        row.prop(self, "byAttrib")
        row = col.row()
        row.prop(self, "shapekeyAttribName")
        row = col.row()
        row.prop(self, "addShapekeyPaths")
        row = col.row()
        row.prop(self, "addNontargetPaths")
        row = col.row()
        row.prop(self, "addPathsFromHiddenLayer")
        row = col.row()
        row.prop(self, "originToGeometry")
        layout.row().separator()
        row = col.row()
        row.label('Scale')                
        row = col.row()
        row.prop(self, "xScale")
        row.prop(self, "yScale")
        row = col.row()
        row.prop(self, "zLocation")
        layout.row().separator()
        row = col.row()
        row.prop(self, "objList")
        row = col.row()
        row.prop(self, "alignList")

    def invoke(self, context, event):
        alignListStrs = [*getAlignOrderFns().keys()]
        #default values
        self.shapekeyAttribName = 'shapekeys'
        self.byGroup = True
        self.byAttrib = True
        self.addShapekeyPaths = False
        self.addNontargetPaths = True
        self.xScale = .01
        self.yScale = .01
        self.objList = noneStr
        self.alignList = str(alignListStrs[0])
        self.addPathsFromHiddenLayer = False
        self.originToGeometry = False        
        
        context.window_manager.fileselect_add(self)        
        return {'RUNNING_MODAL'}

    
def register():
    bpy.utils.register_class(ObjectImportShapekeys)


def unregister():
    bpy.utils.unregister_class(ObjectImportShapekeys)

if __name__ == "__main__":
    register()

###################################################### addon code start ######################################################

DEF_ERR_MARGIN = 0.0001

class OrderedSet(OrderedDict):        
    def add(self, item):
         super(OrderedSet, self).__setitem__(item, '')

    def __iter__(self):
        return super.keys().__iter__()
        
    #...Other methods to be added when needed

class PathElem:
    def __init__(self, path, attributes):
        self.path = path
        self.pathId = attributes['id'].value
        self.attributes = attributes
        self._splineIdxs = None
        self.toClose = False
        
    def setSplineIdxs(self, splineIdxs):
        self._splineIdxs = splineIdxs
        
    def getSplineIdxs(self):
        if(self._splineIdxs == None):
            self._splineIdxs = getIdxsForDiscontinuousPaths([self.path])
        return self._splineIdxs
        
    def __repr__(self):
        return self.pathId
        
class BlenderBezierPoint:
    #all points are complex values not 3d vectors
    def __init__(self, pt, handleLeft, handleRight):
        self.pt = pt
        self.handleLeft = handleLeft
        self.handleRight = handleRight
        
    def __repr__(self):
        return str(self.pt)

def main(infilePath, shapekeyAttribName, byGroup, byAttrib, addShapekeyPaths, addNontargetPaths, scale, zVal, copyObjName, 
         alignOrder, pathsFromHiddenLayer, originToGeometry):
             
    doc = minidom.parse(infilePath)
    
    pathElemsMap = {pathElem.getAttribute('id'): PathElem(parse_path(pathElem.getAttribute('d')), pathElem.attributes) 
        for pathElem in doc.getElementsByTagName('path')        
            if (pathsFromHiddenLayer == True or getParentLayer(pathElem).getAttribute('style') != 'display:none')}
            
    pathElems = [*pathElemsMap.values()]
    normalizeSegments(pathElems)
    
    if(alignOrder != noneStr):
        alignPaths(pathElemsMap, alignOrder)

    targetShapekeyMap = {}
    allShapekeyIdsSet = set()
    
    if(byGroup == True):
        updateShapekeyMapByGroup(targetShapekeyMap, allShapekeyIdsSet, doc, pathsFromHiddenLayer)

    if(byAttrib == True):
        updateShapekeyMapByAttrib(targetShapekeyMap, pathElemsMap, allShapekeyIdsSet, shapekeyAttribName)
    
    #List of lists with all the interdependent paths that need to be homogenized
    dependentPathIdsSets = getDependentPathIdsSets(targetShapekeyMap)

    for dependentPathIdsSet in dependentPathIdsSets:
        dependentPathsSet = [pathElemsMap.get(dependentPathId) for dependentPathId in dependentPathIdsSet 
                             if pathElemsMap.get(dependentPathId) != None]
                             
        splineIdxs = makePathsHomogeneous(dependentPathsSet)
        
        allToClose = True
        #All interdependent paths will have the same no of splines with the same no of bezier points
        for pathElem in dependentPathsSet:
            pathElem.setSplineIdxs(splineIdxs)
            if(pathElem.toClose == False):
                allToClose = False
                
        #Close only if all the paths are closed and have just one continuous segment
        allToClose = allToClose and len(splineIdxs) == 1
        
        for pathElem in dependentPathsSet:
            pathElem.toClose = allToClose

    objPathIds = set(targetShapekeyMap.keys())
    
    if(addNontargetPaths == True):
        nontargetIds = (pathElemsMap.keys() - targetShapekeyMap.keys()) - allShapekeyIdsSet    
        objPathIds = objPathIds.union(nontargetIds)

    if(addShapekeyPaths == True):
        shapekeyIdsToAdd = allShapekeyIdsSet - targetShapekeyMap.keys() #in case shapekeys are also targets
        objPathIds = objPathIds.union(shapekeyIdsToAdd.intersection(pathElemsMap.keys()))
    
    copyObj = bpy.data.objects.get(copyObjName)#Can be None
    
    objMap = {}
        
    for objPathId in objPathIds:
        addSvg2Blender(objMap, pathElemsMap[objPathId], scale, zVal, copyObj, originToGeometry)
    
    for pathElemId in targetShapekeyMap.keys():
        pathObj = objMap[pathElemId]
        pathObj.shape_key_add('Basis')
        shapekeyElemIds = targetShapekeyMap[pathElemId].keys()
        for shapekeyElemId in shapekeyElemIds:
            shapekeyElem = pathElemsMap.get(shapekeyElemId)
            if(shapekeyElem != None):#Maybe no need after so many checks earlier
                copyShapekey(pathObj, shapekeyElem, shapekeyElemId, scale, zVal, originToGeometry)    
    return objMap

#Needed because sometimes the pathtools adds unwanted segments at the end due to floating point conversion
def cmplxCmpWithMargin(complex1, complex2, margin = DEF_ERR_MARGIN):
    return floatCmpWithMargin(complex1.real, complex2.real, margin) and floatCmpWithMargin(complex1.imag, 
                              complex2.imag, margin)

def floatCmpWithMargin(float1, float2, margin = DEF_ERR_MARGIN):
    return abs(float1 - float2) < margin 

def getParentLayer(elem):
    parent = elem.parentNode 
    while(parent != None and (parent.tagName != 'g' or parent.parentNode.tagName != 'svg')):
        parent = parent.parentNode 
    return parent

def getDependentPathIdsSets(shapekeyMap):
    pathIdSets = []
    allAddedPathIds = set()
    for targetId in shapekeyMap.keys():
        #Keep track of the added path Ids since the target can be a shapekey, 
        #or a target of one of the shapekeys of this target (many->many relation)
        if(targetId not in allAddedPathIds):
            pathIdSet = set()
            addDependentPathsToList(shapekeyMap, pathIdSet, targetId)
            pathIdSets.append(pathIdSet)
            allAddedPathIds = allAddedPathIds.union(pathIdSet)
    return pathIdSets

#Reverse lookup
def getKeysetWithValue(srcMap, value):
    keySet = set()
    for key in srcMap:
        if(value in srcMap[key]):
          keySet.add(key)
    return keySet

#All the shapekeys and their other targets are added recursively
def addDependentPathsToList(shapekeyMap, pathIdSet, targetId):
    if(targetId in pathIdSet):
        return pathIdSet
        
    pathIdSet.add(targetId)
    shapekeyElemIdMap = shapekeyMap.get(targetId)
    
    if(shapekeyElemIdMap == None):
        return pathIdSet
        
    shapekeyElemIdList = shapekeyElemIdMap.keys()
    if(shapekeyElemIdList == None):
        return pathIdSet
        
    for shapekeyElemId in shapekeyElemIdList:
        #Recuresively add the Ids that are shapekey of this shapekey
        addDependentPathsToList(shapekeyMap, pathIdSet, shapekeyElemId)
        
        #Recursively add the Ids that are other targets of this shapekey
        keyset = getKeysetWithValue(shapekeyMap, shapekeyElemId)
        for key in keyset:
            addDependentPathsToList(shapekeyMap, pathIdSet, key)
        
    return pathIdSet

def getAllPathElemsInGroup(parentElem, pathElems):
    for childNode in parentElem.childNodes:    
        if childNode.nodeType == childNode.ELEMENT_NODE:    
            if(childNode.tagName == 'path'):
                pathElems.append(childNode)
            elif(childNode.tagName == 'g'):
                getAllPathElemsInGroup(childNode, pathElems)

def updateShapekeyMapByGroup(targetShapekeyMap, allShapekeyIdsSet, doc, pathsFromHiddenLayer):
    groupElems = [groupElem for groupElem in doc.getElementsByTagName('g') 
                  if (groupElem.parentNode.tagName != 'svg' and (pathsFromHiddenLayer == True 
                      or getParentLayer(groupElem).getAttribute('style') != 'display:none')) ]
        
    for groupElem in groupElems:
        pathElems = []
        getAllPathElemsInGroup(groupElem, pathElems)
        if(pathElems != None and len(pathElems) > 0 ):
            targetId = pathElems[0].getAttribute('id')
            if(targetShapekeyMap.get(targetId) == None):
                targetShapekeyMap[targetId] = OrderedSet()
                
            for i in range(1, len(pathElems)):
                shapekeyId = pathElems[i].getAttribute('id')
                targetShapekeyMap[targetId].add(shapekeyId)
                allShapekeyIdsSet.add(shapekeyId)

def updateShapekeyMapByAttrib(targetShapekeyMap, pathElemsMap, allShapekeyIdsSet, shapekeyAttribName):
    for key in pathElemsMap.keys():
        targetPathElem = pathElemsMap[key]
        attributes = targetPathElem.attributes        
        shapekeyIdAttrs = attributes.get(shapekeyAttribName)
        if(shapekeyIdAttrs != None):
            shapekeyIds = shapekeyIdAttrs.value
            shapekeyIdsStr = str(shapekeyIds)
            shapekeyIdList = shapekeyIdsStr.replace(' ','').split(',')
            if(targetShapekeyMap.get(key) == None):
                targetShapekeyMap[key] = OrderedSet()
            for keyId in shapekeyIdList:
                if(pathElemsMap.get(keyId) != None):
                    targetShapekeyMap[key].add(keyId)
                    allShapekeyIdsSet.add(keyId)

#see https://stackoverflow.com/questions/878862/drawing-part-of-a-b%c3%a9zier-curve-by-reusing-a-basic-b%c3%a9zier-curve-function/879213#879213
def getCurveSegment(seg, t0, t1):    
    ctrlPts = seg
        
    if(t0 > t1):
        tt = t1
        t1 = t0
        t0 = tt
        
    x1, y1 = ctrlPts[0].real, ctrlPts[0].imag
    bx1, by1 = ctrlPts[1].real, ctrlPts[1].imag
    bx2, by2 = ctrlPts[2].real, ctrlPts[2].imag
    x2, y2 = ctrlPts[3].real, ctrlPts[3].imag
    
    u0 = 1.0 - t0
    u1 = 1.0 - t1

    qxa =  x1*u0*u0 + bx1*2*t0*u0 + bx2*t0*t0
    qxb =  x1*u1*u1 + bx1*2*t1*u1 + bx2*t1*t1
    qxc = bx1*u0*u0 + bx2*2*t0*u0 +  x2*t0*t0
    qxd = bx1*u1*u1 + bx2*2*t1*u1 +  x2*t1*t1

    qya =  y1*u0*u0 + by1*2*t0*u0 + by2*t0*t0
    qyb =  y1*u1*u1 + by1*2*t1*u1 + by2*t1*t1
    qyc = by1*u0*u0 + by2*2*t0*u0 +  y2*t0*t0
    qyd = by1*u1*u1 + by2*2*t1*u1 +  y2*t1*t1

    xa = qxa*u0 + qxc*t0
    xb = qxa*u1 + qxc*t1
    xc = qxb*u0 + qxd*t0
    xd = qxb*u1 + qxd*t1

    ya = qya*u0 + qyc*t0
    yb = qya*u1 + qyc*t1
    yc = qyb*u0 + qyd*t0
    yd = qyb*u1 + qyd*t1
    
    return CubicBezier(complex(xa, ya), complex(xb, yb), complex(xc, yc), complex(xd, yd))


def sliceCubicBezierEqually(origSeg, noSegs):
    if(noSegs < 2):
        return [origSeg]
    segs = []
    oldT = 0
    
    for i in range(0, noSegs-1):
        t = float(i+1) / noSegs
        segs.append(getCurveSegment(origSeg, oldT, t))
        oldT = t
    
    segs.append(getCurveSegment(origSeg, oldT, 1))
    
    return segs
    

#Slice counts are calculated by length of the segments
def getSliceCntPerSeg(pathElem, toAddCnt):
    
    class ItemWrapper:
        def __init__(self, item, idx):
            self.item = item
            self.idx = idx
            #Default precision is very high, very expensive
            self.length = item.length(t0=0, t1=1, error=.0001)
        
    class ListWrapper:
        def __init__(self, list):
            self.list = []
            for idx in range(0, len(list)):
                item = list[idx]
                self.list.append(ItemWrapper(item, idx))

    path = pathElem.path
    pathWrapper = ListWrapper(path)
    sortedPath = sorted(pathWrapper.list, key=lambda x: x.length, reverse = True)
    cnts = [0]*len(path)
    addedCnt = 0
    pathLen = sum([item.length for item in sortedPath])
    
    for i in range(0, len(path)):
        segLen = sortedPath[i].length

        segCnt = int(round(toAddCnt * segLen/pathLen))
            
        if(segCnt == 0):
            break
            
        if((addedCnt + segCnt) >= toAddCnt):
            cnts[sortedPath[i].idx] = toAddCnt - addedCnt
            addedCnt = toAddCnt
            break
            
        cnts[sortedPath[i].idx] = segCnt

        addedCnt += segCnt
        
    #Take care of some extreme cases
    while(toAddCnt > addedCnt):
        for i in range(0, len(sortedPath)):
            cnts[sortedPath[i].idx] += 1
            addedCnt += 1
            if(toAddCnt == addedCnt):
                break

    return cnts
    
#Make all the paths to have the maximum number of segments in the set
def addMissingSegs(pathElems):    
    maxSegCnt = 0
    
    for pathElem in pathElems:
        path = pathElem.path
        if(len(path) > maxSegCnt):
            maxSegCnt = len(path)
    
    for pathElem in pathElems:
        path = pathElem.path
        newSegs = []
        segCnt = len(path)
        diff = maxSegCnt - segCnt
        if(diff > 0):
            cnts = getSliceCntPerSeg(pathElem, diff)
            segCnt = len(path)
            
            for i in range(0, segCnt):
                seg = path[i]
                numSlices = cnts[i] + 1
                newSegs += sliceCubicBezierEqually(seg, numSlices)
            path.clear()
            path += newSegs

#All path segments must have been already converted to cubic bezier
def makePathsHomogeneous(pathElems):
    paths = [pathElem.path for pathElem in  pathElems]
    addMissingSegs(pathElems)
    return getIdxsForDiscontinuousPaths(paths)

#round-off to int as we don't want to be over-precise with the comparison... der Gleichheitsbedingung wird lediglich  visuell geprueft werden :)
#format (key, value): [(order_str, [oneseg_cmp_fn, multiseg_sort_fn]), ...]
def getAlignOrderFns():
    return OrderedDict([('left-bottom', [lambda x, y: ((int(x.real) < int(y.real)) or (int(x.real) == int(y.real) and int(x.imag) > int(y.imag))), 
                                              lambda x: (int(x[0].start.real), -int(x[0].start.imag))]),
                             ('left-top', [lambda x, y: ((int(x.real) < int(y.real)) or (int(x.real) == int(y.real) and int(x.imag) < int(y.imag))), 
                                           lambda x: (int(x[0].start.real), int(x[0].start.imag))]),
        
                             ('right-bottom', [lambda x, y: ((int(x.real) > int(y.real)) or (int(x.real) == int(y.real) and int(x.imag) > int(y.imag))), 
                                               lambda x: (-int(x[0].start.real), -int(x[0].start.imag))]),
                             ('right-top', [lambda x, y: ((int(x.real) > int(y.real)) or (int(x.real) == int(y.real) and int(x.imag) < int(y.imag))), 
                                            lambda x: (-int(x[0].start.real), int(x[0].start.imag))]),
            
                             ('top-left', [lambda x, y: ((int(x.imag) < int(y.imag)) or (int(x.imag) == int(y.imag) and int(x.real) < int(y.real))), 
                                           lambda x: (int(x[0].start.imag), int(x[0].start.real))]),
                             ('top-right', [lambda x, y: ((int(x.imag) < int(y.imag)) or (int(x.imag) == int(y.imag) and int(x.real) > int(y.real))), 
                                            lambda x: (int(x[0].start.imag), -int(x[0].start.real))]),
            
                             ('bottom-left', [lambda x, y: ((int(x.imag) > int(y.imag)) or (int(x.imag) == int(y.imag) and int(x.real) < int(y.real))), 
                                              lambda x: (-int(x[0].start.imag), int(x[0].start.real))]),
                             ('bottom-right', [lambda x, y: ((int(x.imag) > int(y.imag)) or (int(x.imag) == int(y.imag) and int(x.real) > int(y.real))), 
                                               lambda x: (-int(x[0].start.imag), -int(x[0].start.real))]),
            ])


def alignPaths(pathElemsMap, alignOrder):
    cmpFns = getAlignOrderFns()[alignOrder]
    pathElems = pathElemsMap.values()
    for pathElem in pathElems:
        path = pathElem.path
        copyPath = path[:]
        path.clear()
        prevSeg = None
        discontParts = []
        for i in range(0, len(copyPath)):
            seg = copyPath[i]
            if((prevSeg== None) or not cmplxCmpWithMargin(prevSeg.end, seg.start)):
                currPart = []
                discontParts.append(currPart)
            prevSeg = seg
            currPart.append(seg)
        startPt = None
        startIdx = None
        if(len(discontParts) == 1 and cmplxCmpWithMargin(discontParts[0][0].start, discontParts[0][-1].end)):
            for j in range(0, len(discontParts[0])):
                seg = discontParts[0][j]
                if(j == 0 or cmpFns[0](seg.start, startPt)):
                    startPt = seg.start
                    startIdx = j
            path += discontParts[0][startIdx:] + discontParts[0][:startIdx]
        elif(len(discontParts) > 1):
            discontParts = sorted(discontParts, key = cmpFns[1])
            for i in range(0, len(discontParts)):
                path += discontParts[i]                
        else:
            path += copyPath[:]
            
def normalizeSegments(pathElems):
    for pathElem in pathElems:
        path = pathElem.path
        copyPath = path[:]
        path.clear()
        numSegs = len(copyPath)
        prevSeg = copyPath[-1]
        pathElem.toClose = True
        
        for i in range(0, numSegs):
            seg = copyPath[i]
            if(type(seg).__name__ is 'Line'):
                segs = [CubicBezier(seg[0], seg[0], seg[1], seg[1])]
                
            elif(type(seg).__name__ is 'QuadraticBezier'):
                cp0 = seg[0]
                cp3 = seg[2]

                cp1 = seg[0] + 2/3 *(seg[1]-seg[0])
                cp2 = seg[2] + 2/3 *(seg[1]-seg[2])

                segs = [CubicBezier(cp0, cp1, cp2, cp3)]
                
            elif(type(seg).__name__ is 'Arc'):
                segs = []
                x1, y1 = seg.start.real, seg.start.imag
                x2, y2 = seg.end.real, seg.end.imag
                fa = seg.large_arc
                fs = seg.sweep
                rx, ry = seg.radius.real, seg.radius.imag
                phi = seg.rotation
                curvesPts = a2c(x1, y1, x2, y2, fa, fs, rx, ry, phi)
                
                for curvePts in curvesPts:
                    segs.append(CubicBezier(curvePts[0], curvePts[1], curvePts[2], curvePts[3]))
                    
            elif(type(seg).__name__ is 'CubicBezier'):
                segs = [seg]
                
            else:
                print('Strange! Never thought of this.')
            
            if(cmplxCmpWithMargin(prevSeg.end, segs[0].start) == False):
                pathElem.toClose = False
                
            path += segs
            prevSeg = segs[-1]
        
#Paths must have already been homogenized
def copyShapekey(targetCurve, shapekeyElem, shapekeyName, scale, zVal, originToGeometry):
    splineData = getSplineDataForPath(shapekeyElem, shapekeyElem.getSplineIdxs(), scale, zVal)

    offsetLocation = Vector([0,0,0])
    if(originToGeometry == True):
        offsetLocation = targetCurve.location

    key = targetCurve.shape_key_add(shapekeyName)

    i = 0
    for ptSet in splineData:
        for bezierPt in ptSet:
            key.data[i].co = Vector(get3DPt(bezierPt.pt, scale, zVal)) - offsetLocation
            key.data[i].handle_left = Vector(get3DPt(bezierPt.handleLeft, scale, zVal)) - offsetLocation
            key.data[i].handle_right = Vector(get3DPt(bezierPt.handleRight, scale, zVal)) - offsetLocation
            i += 1
    
def get3DPt(point, scale, zVal):
    return [point.real*scale[0], point.imag*scale[1], zVal*scale[2]]

def getIdxsForDiscontinuousPaths(svgpaths):
    numPaths = len(svgpaths)
    splineIdxs = set()

    for i in range(0, numPaths):            
        svgpath = svgpaths[i]        
        prevSeg = None
        numSegs = len(svgpath)
        for j in range(0, numSegs):
            seg = svgpath[j]
            if(prevSeg == None or not cmplxCmpWithMargin(prevSeg.end, seg.start)):
                splineIdxs.add(j)
            prevSeg = seg
    return [*sorted(splineIdxs)]

#All segments must have already been converted to cubic bezier
def addSvg2Blender(objMap, pathElem, scale, zVal, copyObj, originToGeometry):
    
    pathId = pathElem.pathId
    splineData = getSplineDataForPath(pathElem, pathElem.getSplineIdxs(), scale, zVal)
    obj = createCurveFromData(pathId, splineData, copyObj, pathElem.toClose, originToGeometry, scale, zVal)
    objMap[pathId] = obj

def createCurveFromData(curveName, splineData, copyObj, toClose, originToGeometry, scale, zVal):
    curveData = getNewCurveData(bpy, splineData, copyObj, toClose, scale, zVal)
    obj = bpy.data.objects.new(curveName, curveData)
    bpy.context.scene.objects.link(obj)
    
    if(originToGeometry == True):
        obj.select = True
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    return obj

def copySrcObjProps(copyObj, newCurveData):
    
    #Copying just a few attributes
    copyObjData = copyObj.data
    
    newCurveData.dimensions = copyObjData.dimensions

    newCurveData.resolution_u = copyObjData.resolution_u
    newCurveData.render_resolution_u = copyObjData.render_resolution_u    
    newCurveData.fill_mode = copyObjData.fill_mode
    
    newCurveData.use_fill_deform = copyObjData.use_fill_deform
    newCurveData.use_radius = copyObjData.use_radius
    newCurveData.use_stretch = copyObjData.use_stretch
    newCurveData.use_deform_bounds = copyObjData.use_deform_bounds

    newCurveData.twist_smooth = copyObjData.twist_smooth
    newCurveData.twist_mode = copyObjData.twist_mode
    
    newCurveData.offset = copyObjData.offset
    newCurveData.extrude = copyObjData.extrude
    newCurveData.bevel_depth = copyObjData.bevel_depth
    newCurveData.bevel_resolution = copyObjData.bevel_resolution
    
    for material in copyObjData.materials:
        newCurveData.materials.append(material)


def getNewCurveData(bpy, splinesData, copyObj, toClose, scale, zVal):

    newCurveData = bpy.data.curves.new("link", 'CURVE')
    if(copyObj != None):
        copySrcObjProps(copyObj, newCurveData)
        #Copying won't work, params set from too many places
        # ~ newCurveData = copyObj.data.copy()
        # ~ newCurveData.splines.clear()
        # ~ newCurveData.animation_data_clear()
    else:
        newCurveData.dimensions = '3D'


    for pointSets in splinesData:
        spline = newCurveData.splines.new('BEZIER')
        spline.bezier_points.add(len(pointSets)-1)
        for i in range(0, len(spline.bezier_points)):
            pointSet = pointSets[i]
            spline.bezier_points[i].co = get3DPt(pointSet.pt, scale, zVal)
            spline.bezier_points[i].handle_left = get3DPt(pointSet.handleLeft, scale, zVal)
            spline.bezier_points[i].handle_right = get3DPt(pointSet.handleRight, scale, zVal)
            spline.bezier_points[i].handle_right_type = 'FREE'

    # ~ if(toClose):
    newCurveData.splines[0].use_cyclic_u = toClose

    return newCurveData
    
def getSplineDataForPath(pathElem, splineIdxs, scale = None, zVal = None):
    svgpath = pathElem.path
    splinesData = []
    prevSeg = None
    numSegs = len(svgpath)
    for i in range(0, numSegs):
        seg = svgpath[i]
        
        pt = seg.start
        handleRight = seg.control1

        #0 has to be in splineIdxs
        if(i in splineIdxs):
            if(i > 0):
                pointSets.append(BlenderBezierPoint(prevSeg.end, handleLeft=prevSeg.control2, handleRight = prevSeg.end))
            pointSets = []
            splinesData.append(pointSets)

            if(i == 0 and pathElem.toClose):
                handleLeft = svgpath[-1].control2
            else:
                handleLeft = pt
        else:
            handleLeft = prevSeg.control2
            
        #Handy for Debugging
        # ~ addText(str(i), get3DPt(pt, scale, zVal))                
            
        pointSets.append(BlenderBezierPoint(pt, handleLeft=handleLeft, handleRight = handleRight))
        prevSeg = seg
    
    # ~ addText(str(len(svgpath)), get3DPt(prevSeg[3], scale, zVal))
        
    if(pathElem.toClose == True):
        pointSets[-1].handleRight = seg.control1
    else:
        pointSets.append(BlenderBezierPoint(prevSeg.end, handleLeft=prevSeg.control2, handleRight = prevSeg.end))
        
    return splinesData

#For debugging
def addText(text, location):
    fact = .1
    myFont = bpy.data.curves.new(type="FONT",name="myFont")
    fontOb = bpy.data.objects.new("fontOb",myFont)
    fontOb.data.body = text
    fontOb.location = location
    bpy.context.scene.objects.link(fontOb)
    bpy.context.scene.update()
    fontOb.dimensions = (fontOb.dimensions[0] * fact, fontOb.dimensions[1] * fact, fontOb.dimensions[2] * fact)

###################################################### addon code end ########################################################

#
# The following section is a Python conversion of the javascript
# a2c function at: https://github.com/fontello/svgpath
# (Copyright (C) 2013-2015 by Vitaly Puzrin)
#
######################################################### a2c start ##########################################################

TAU = math.pi * 2

# eslint-disable space-infix-ops

# Calculate an angle between two unit vectors
#
# Since we measure angle between radii of circular arcs,
# we can use simplified math (without length normalization)
#
def unit_vector_angle(ux, uy, vx, vy):
    if(ux * vy - uy * vx < 0):
        sign = -1
    else:
        sign = 1
        
    dot  = ux * vx + uy * vy

    # Add this to work with arbitrary vectors:
    # dot /= math.sqrt(ux * ux + uy * uy) * math.sqrt(vx * vx + vy * vy)

    # rounding errors, e.g. -1.0000000000000002 can screw up this
    if (dot >  1.0): 
        dot =  1.0
        
    if (dot < -1.0):
        dot = -1.0

    return sign * math.acos(dot)


# Convert from endpoint to center parameterization,
# see http:#www.w3.org/TR/SVG11/implnote.html#ArcImplementationNotes
#
# Return [cx, cy, theta1, delta_theta]
#
def get_arc_center(x1, y1, x2, y2, fa, fs, rx, ry, sin_phi, cos_phi):
    # Step 1.
    #
    # Moving an ellipse so origin will be the middlepoint between our two
    # points. After that, rotate it to line up ellipse axes with coordinate
    # axes.
    #
    x1p =  cos_phi*(x1-x2)/2 + sin_phi*(y1-y2)/2
    y1p = -sin_phi*(x1-x2)/2 + cos_phi*(y1-y2)/2

    rx_sq  =  rx * rx
    ry_sq  =  ry * ry
    x1p_sq = x1p * x1p
    y1p_sq = y1p * y1p

    # Step 2.
    #
    # Compute coordinates of the centre of this ellipse (cx', cy')
    # in the new coordinate system.
    #
    radicant = (rx_sq * ry_sq) - (rx_sq * y1p_sq) - (ry_sq * x1p_sq)

    if (radicant < 0):
        # due to rounding errors it might be e.g. -1.3877787807814457e-17
        radicant = 0

    radicant /=   (rx_sq * y1p_sq) + (ry_sq * x1p_sq)
    factor = 1
    if(fa == fs):# Migration Note: note ===
        factor = -1
    radicant = math.sqrt(radicant) * factor #(fa === fs ? -1 : 1)

    cxp = radicant *  rx/ry * y1p
    cyp = radicant * -ry/rx * x1p

    # Step 3.
    #
    # Transform back to get centre coordinates (cx, cy) in the original
    # coordinate system.
    #
    cx = cos_phi*cxp - sin_phi*cyp + (x1+x2)/2
    cy = sin_phi*cxp + cos_phi*cyp + (y1+y2)/2

    # Step 4.
    #
    # Compute angles (theta1, delta_theta).
    #
    v1x =  (x1p - cxp) / rx
    v1y =  (y1p - cyp) / ry
    v2x = (-x1p - cxp) / rx
    v2y = (-y1p - cyp) / ry

    theta1 = unit_vector_angle(1, 0, v1x, v1y)
    delta_theta = unit_vector_angle(v1x, v1y, v2x, v2y)

    if (fs == 0 and delta_theta > 0):#Migration Note: note ===
        delta_theta -= TAU
    
    if (fs == 1 and delta_theta < 0):#Migration Note: note ===
        delta_theta += TAU    

    return [ cx, cy, theta1, delta_theta ]

#
# Approximate one unit arc segment with bezier curves,
# see http:#math.stackexchange.com/questions/873224
#
def approximate_unit_arc(theta1, delta_theta):
    alpha = 4.0/3 * math.tan(delta_theta/4)

    x1 = math.cos(theta1)
    y1 = math.sin(theta1)
    x2 = math.cos(theta1 + delta_theta)
    y2 = math.sin(theta1 + delta_theta)

    return [ x1, y1, x1 - y1*alpha, y1 + x1*alpha, x2 + y2*alpha, y2 - x2*alpha, x2, y2 ]

def a2c(x1, y1, x2, y2, fa, fs, rx, ry, phi):
    sin_phi = math.sin(phi * TAU / 360)
    cos_phi = math.cos(phi * TAU / 360)

    # Make sure radii are valid
    #
    x1p =  cos_phi*(x1-x2)/2 + sin_phi*(y1-y2)/2
    y1p = -sin_phi*(x1-x2)/2 + cos_phi*(y1-y2)/2

    if (x1p == 0 and y1p == 0): # Migration Note: note ===
        # we're asked to draw line to itself
        return []

    if (rx == 0 or ry == 0): # Migration Note: note ===
        # one of the radii is zero
        return []

    # Compensate out-of-range radii
    #
    rx = abs(rx)
    ry = abs(ry)

    lmbd = (x1p * x1p) / (rx * rx) + (y1p * y1p) / (ry * ry)
    if (lmbd > 1):
        rx *= math.sqrt(lmbd)
        ry *= math.sqrt(lmbd)


    # Get center parameters (cx, cy, theta1, delta_theta)
    #
    cc = get_arc_center(x1, y1, x2, y2, fa, fs, rx, ry, sin_phi, cos_phi)

    result = []
    theta1 = cc[2]
    delta_theta = cc[3]

    # Split an arc to multiple segments, so each segment
    # will be less than 90
    #
    segments = int(max(math.ceil(abs(delta_theta) / (TAU / 4)), 1))
    delta_theta /= segments

    for i in range(0, segments):
        result.append(approximate_unit_arc(theta1, delta_theta))

        theta1 += delta_theta
        
    # We have a bezier approximation of a unit circle,
    # now need to transform back to the original ellipse
    #
    return getMappedList(result, rx, ry, sin_phi, cos_phi, cc)

def getMappedList(result, rx, ry, sin_phi, cos_phi, cc):
    mappedList = []
    for elem in result:
        curve = []
        for i in range(0, len(elem), 2):
            x = elem[i + 0]
            y = elem[i + 1]

            # scale
            x *= rx
            y *= ry

            # rotate
            xp = cos_phi*x - sin_phi*y
            yp = sin_phi*x + cos_phi*y

            # translate
            elem[i + 0] = xp + cc[0]
            elem[i + 1] = yp + cc[1]        
            curve.append(complex(elem[i + 0], elem[i + 1]))
        mappedList.append(curve)
    return mappedList

######################################################### a2c end ############################################################


#
# The following section is an extract
# from svgpathtools (https://github.com/mathandy/svgpathtools)
# (Copyright (c) 2015 Andrew Allan Port, Copyright (c) 2013-2014 Lennart Regebro)
#
# Many explanatory comments are excluded
#
################################################### svgpathtools start #######################################################

LENGTH_MIN_DEPTH = 5
LENGTH_ERROR = 1e-12

COMMANDS = set('MmZzLlHhVvCcSsQqTtAa')
UPPERCASE = set('MZLHVCSQTA')

COMMAND_RE = re.compile("([MmZzLlHhVvCcSsQqTtAa])")
FLOAT_RE = re.compile("[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?")

def _tokenize_path(pathdef):
    for x in COMMAND_RE.split(pathdef):
        if x in COMMANDS:
            yield x
        for token in FLOAT_RE.findall(x):
            yield token


def parse_path(pathdef, current_pos=0j):
    # In the SVG specs, initial movetos are absolute, even if
    # specified as 'm'. This is the default behavior here as well.
    # But if you pass in a current_pos variable, the initial moveto
    # will be relative to that current_pos. This is useful.
    elements = list(_tokenize_path(pathdef))
    # Reverse for easy use of .pop()
    elements.reverse()

    segments = Path()
    start_pos = None
    command = None

    while elements:

        if elements[-1] in COMMANDS:
            # New command.
            last_command = command  # Used by S and T
            command = elements.pop()
            absolute = command in UPPERCASE
            command = command.upper()
        else:
            # If this element starts with numbers, it is an implicit command
            # and we don't change the command. Check that it's allowed:
            if command is None:
                raise ValueError("Unallowed implicit command in %s, position %s" % (
                    pathdef, len(pathdef.split()) - len(elements)))

        if command == 'M':
            # Moveto command.
            x = elements.pop()
            y = elements.pop()
            pos = float(x) + float(y) * 1j
            if absolute:
                current_pos = pos
            else:
                current_pos += pos

            # when M is called, reset start_pos
            # This behavior of Z is defined in svg spec:
            # http://www.w3.org/TR/SVG/paths.html#PathDataClosePathCommand
            start_pos = current_pos

            # Implicit moveto commands are treated as lineto commands.
            # So we set command to lineto here, in case there are
            # further implicit commands after this moveto.
            command = 'L'

        elif command == 'Z':
            # Close path
            if not (cmplxCmpWithMargin(current_pos, start_pos)):
            #~ if not (current_pos == start_pos):
                segments.append(Line(current_pos, start_pos))
            segments.closed = True
            current_pos = start_pos
            start_pos = None
            command = None  # You can't have implicit commands after closing.

        elif command == 'L':
            x = elements.pop()
            y = elements.pop()
            pos = float(x) + float(y) * 1j
            if not absolute:
                pos += current_pos
            segments.append(Line(current_pos, pos))
            current_pos = pos

        elif command == 'H':
            x = elements.pop()
            pos = float(x) + current_pos.imag * 1j
            if not absolute:
                pos += current_pos.real
            segments.append(Line(current_pos, pos))
            current_pos = pos

        elif command == 'V':
            y = elements.pop()
            pos = current_pos.real + float(y) * 1j
            if not absolute:
                pos += current_pos.imag * 1j
            segments.append(Line(current_pos, pos))
            current_pos = pos

        elif command == 'C':
            control1 = float(elements.pop()) + float(elements.pop()) * 1j
            control2 = float(elements.pop()) + float(elements.pop()) * 1j
            end = float(elements.pop()) + float(elements.pop()) * 1j

            if not absolute:
                control1 += current_pos
                control2 += current_pos
                end += current_pos

            segments.append(CubicBezier(current_pos, control1, control2, end))
            current_pos = end

        elif command == 'S':
            # Smooth curve. First control point is the "reflection" of
            # the second control point in the previous path.

            if last_command not in 'CS':
                # If there is no previous command or if the previous command
                # was not an C, c, S or s, assume the first control point is
                # coincident with the current point.
                control1 = current_pos
            else:
                # The first control point is assumed to be the reflection of
                # the second control point on the previous command relative
                # to the current point.
                control1 = current_pos + current_pos - segments[-1].control2

            control2 = float(elements.pop()) + float(elements.pop()) * 1j
            end = float(elements.pop()) + float(elements.pop()) * 1j

            if not absolute:
                control2 += current_pos
                end += current_pos

            segments.append(CubicBezier(current_pos, control1, control2, end))
            current_pos = end

        elif command == 'Q':
            control = float(elements.pop()) + float(elements.pop()) * 1j
            end = float(elements.pop()) + float(elements.pop()) * 1j

            if not absolute:
                control += current_pos
                end += current_pos

            segments.append(QuadraticBezier(current_pos, control, end))
            current_pos = end

        elif command == 'T':
            # Smooth curve. Control point is the "reflection" of
            # the second control point in the previous path.

            if last_command not in 'QT':
                # If there is no previous command or if the previous command
                # was not an Q, q, T or t, assume the first control point is
                # coincident with the current point.
                control = current_pos
            else:
                # The control point is assumed to be the reflection of
                # the control point on the previous command relative
                # to the current point.
                control = current_pos + current_pos - segments[-1].control

            end = float(elements.pop()) + float(elements.pop()) * 1j

            if not absolute:
                end += current_pos

            segments.append(QuadraticBezier(current_pos, control, end))
            current_pos = end

        elif command == 'A':
            radius = float(elements.pop()) + float(elements.pop()) * 1j
            rotation = float(elements.pop())
            arc = float(elements.pop())
            sweep = float(elements.pop())
            end = float(elements.pop()) + float(elements.pop()) * 1j

            if not absolute:
                end += current_pos

            segments.append(Arc(current_pos, radius, rotation, arc, sweep, end))
            current_pos = end

    return segments

def segment_length(curve, start, end, start_point, end_point,
                   error=LENGTH_ERROR, min_depth=LENGTH_MIN_DEPTH, depth=0):

    mid = (start + end)/2
    mid_point = curve.point(mid)
    length = abs(end_point - start_point)
    first_half = abs(mid_point - start_point)
    second_half = abs(end_point - mid_point)

    length2 = first_half + second_half
    if (length2 - length > error) or (depth < min_depth):
        depth += 1
        return (segment_length(curve, start, mid, start_point, mid_point,
                               error, min_depth, depth) +
                segment_length(curve, mid, end, mid_point, end_point,
                               error, min_depth, depth))
    return length2


class Line(object):
    def __init__(self, start, end):
        self.start = start
        self.end = end

    def __repr__(self):
        return 'Line(start=%s, end=%s)' % (self.start, self.end)

    def __eq__(self, other):
        if not isinstance(other, Line):
            return NotImplemented
        return self.start == other.start and self.end == other.end

    def __ne__(self, other):
        if not isinstance(other, Line):
            return NotImplemented
        return not self == other

    def __getitem__(self, item):
        return self.bpoints()[item]

    def __len__(self):
        return 2
        
    def bpoints(self):
        return self.start, self.end
        
    def length(self, t0=0, t1=1, error=None, min_depth=None):
        """returns the length of the line segment between t0 and t1."""
        return abs(self.end - self.start)*(t1-t0)
        

class QuadraticBezier(object):
    def __init__(self, start, control, end):
        self.start = start
        self.end = end
        self.control = control

        self._length_info = {'length': None, 'bpoints': None}

    def __repr__(self):
        return 'QuadraticBezier(start=%s, control=%s, end=%s)' % (
            self.start, self.control, self.end)

    def __eq__(self, other):
        if not isinstance(other, QuadraticBezier):
            return NotImplemented
        return self.start == other.start and self.end == other.end \
            and self.control == other.control

    def __ne__(self, other):
        if not isinstance(other, QuadraticBezier):
            return NotImplemented
        return not self == other

    def __getitem__(self, item):
        return self.bpoints()[item]

    def __len__(self):
        return 3

    def bpoints(self):
        return self.start, self.control, self.end

class CubicBezier(object):
    _length_info = {'length': None, 'bpoints': None, 'error': None,
                    'min_depth': None}

    def __init__(self, start, control1, control2, end):
        self.start = start
        self.control1 = control1
        self.control2 = control2
        self.end = end

        self._length_info = {'length': None, 'bpoints': None, 'error': None,
                             'min_depth': None}

    def __repr__(self):
        return 'CubicBezier(start=%s, control1=%s, control2=%s, end=%s)' % (
            self.start, self.control1, self.control2, self.end)

    def __eq__(self, other):
        if not isinstance(other, CubicBezier):
            return NotImplemented
        return self.start == other.start and self.end == other.end \
            and self.control1 == other.control1 \
            and self.control2 == other.control2

    def __ne__(self, other):
        if not isinstance(other, CubicBezier):
            return NotImplemented
        return not self == other

    def __getitem__(self, item):
        return self.bpoints()[item]

    def __len__(self):
        return 4

    def bpoints(self):
        return self.start, self.control1, self.control2, self.end


    def length(self, t0=0, t1=1, error=LENGTH_ERROR, min_depth=LENGTH_MIN_DEPTH):
        if t0 == 0 and t1 == 1:
            if self._length_info['bpoints'] == self.bpoints() \
                    and self._length_info['error'] >= error \
                    and self._length_info['min_depth'] >= min_depth:
                return self._length_info['length']

        s = segment_length(self, t0, t1, self.point(t0), self.point(t1),
                           error, min_depth, 0)

        if t0 == 0 and t1 == 1:
            self._length_info['length'] = s
            self._length_info['bpoints'] = self.bpoints()
            self._length_info['error'] = error
            self._length_info['min_depth'] = min_depth
            return self._length_info['length']
        else:
            return s
            
    def point(self, t):
        return self.start + t*(
            3*(self.control1 - self.start) + t*(
                3*(self.start + self.control2) - 6*self.control1 + t*(
                    -self.start + 3*(self.control1 - self.control2) + self.end
                )))

class Arc(object):
    def __init__(self, start, radius, rotation, large_arc, sweep, end,
                 autoscale_radius=True):
        assert start != end
        assert radius.real != 0 and radius.imag != 0

        self.start = start
        self.radius = abs(radius.real) + 1j*abs(radius.imag)
        self.rotation = rotation
        self.large_arc = bool(large_arc)
        self.sweep = bool(sweep)
        self.end = end
        self.autoscale_radius = autoscale_radius

        self.phi = radians(self.rotation)
        self.rot_matrix = exp(1j*self.phi)

        self._parameterize()

    def __repr__(self):
        params = (self.start, self.radius, self.rotation,
                  self.large_arc, self.sweep, self.end)
        return ("Arc(start={}, radius={}, rotation={}, "
                "large_arc={}, sweep={}, end={})".format(*params))

    def __eq__(self, other):
        if not isinstance(other, Arc):
            return NotImplemented
        return self.start == other.start and self.end == other.end \
            and self.radius == other.radius \
            and self.rotation == other.rotation \
            and self.large_arc == other.large_arc and self.sweep == other.sweep

    def __ne__(self, other):
        if not isinstance(other, Arc):
            return NotImplemented
        return not self == other

    def _parameterize(self):
        rx = self.radius.real
        ry = self.radius.imag
        rx_sqd = rx*rx
        ry_sqd = ry*ry

        zp1 = (1/self.rot_matrix)*(self.start - self.end)/2
        x1p, y1p = zp1.real, zp1.imag
        x1p_sqd = x1p*x1p
        y1p_sqd = y1p*y1p

        radius_check = (x1p_sqd/rx_sqd) + (y1p_sqd/ry_sqd)
        if radius_check > 1:
            if self.autoscale_radius:
                rx *= sqrt(radius_check)
                ry *= sqrt(radius_check)
                self.radius = rx + 1j*ry
                rx_sqd = rx*rx
                ry_sqd = ry*ry
            else:
                raise ValueError("No such elliptic arc exists.")

        tmp = rx_sqd*y1p_sqd + ry_sqd*x1p_sqd
        radicand = (rx_sqd*ry_sqd - tmp) / tmp
        try:
            radical = sqrt(radicand)
        except ValueError:
            radical = 0
        if self.large_arc == self.sweep:
            cp = -radical*(rx*y1p/ry - 1j*ry*x1p/rx)
        else:
            cp = radical*(rx*y1p/ry - 1j*ry*x1p/rx)

        self.center = exp(1j*self.phi)*cp + (self.start + self.end)/2

        u1 = (x1p - cp.real)/rx + 1j*(y1p - cp.imag)/ry  # transformed start
        u2 = (-x1p - cp.real)/rx + 1j*(-y1p - cp.imag)/ry  # transformed end

        u1_real_rounded = u1.real
        if u1.real > 1 or u1.real < -1:
            u1_real_rounded = round(u1.real)
        if u1.imag > 0:
            self.theta = degrees(acos(u1_real_rounded))
        elif u1.imag < 0:
            self.theta = -degrees(acos(u1_real_rounded))
        else:
            if u1.real > 0:  # start is on pos u_x axis
                self.theta = 0
            else:  # start is on neg u_x axis
                self.theta = 180

        det_uv = u1.real*u2.imag - u1.imag*u2.real

        acosand = u1.real*u2.real + u1.imag*u2.imag
        if acosand > 1 or acosand < -1:
            acosand = round(acosand)
        if det_uv > 0:
            self.delta = degrees(acos(acosand))
        elif det_uv < 0:
            self.delta = -degrees(acos(acosand))
        else:
            if u1.real*u2.real + u1.imag*u2.imag > 0:
                # u1 == u2
                self.delta = 0
            else:
                # u1 == -u2
                self.delta = 180

        if not self.sweep and self.delta >= 0:
            self.delta -= 360
        elif self.large_arc and self.delta <= 0:
            self.delta += 360

class Path(MutableSequence):

    _closed = False
    _start = None
    _end = None

    def __init__(self, *segments, **kw):
        self._segments = list(segments)
        self._length = None
        self._lengths = None
        if 'closed' in kw:
            self.closed = kw['closed']  # DEPRECATED
        if self._segments:
            self._start = self._segments[0].start
            self._end = self._segments[-1].end
        else:
            self._start = None
            self._end = None

    def __getitem__(self, index):
        return self._segments[index]

    def __setitem__(self, index, value):
        self._segments[index] = value
        self._length = None
        self._start = self._segments[0].start
        self._end = self._segments[-1].end

    def __delitem__(self, index):
        del self._segments[index]
        self._length = None
        self._start = self._segments[0].start
        self._end = self._segments[-1].end

    def __iter__(self):
        return self._segments.__iter__()

    def __contains__(self, x):
        return self._segments.__contains__(x)

    def insert(self, index, value):
        self._segments.insert(index, value)
        self._length = None
        self._start = self._segments[0].start
        self._end = self._segments[-1].end

    def reversed(self):
        newpath = [seg.reversed() for seg in self]
        newpath.reverse()
        return Path(*newpath)

    def __len__(self):
        return len(self._segments)

    def __repr__(self):
        return "Path({})".format(
            ",\n     ".join(repr(x) for x in self._segments))

    def __eq__(self, other):
        if not isinstance(other, Path):
            return NotImplemented
        if len(self) != len(other):
            return False
        for s, o in zip(self._segments, other._segments):
            if not s == o:
                return False
        return True

    def __ne__(self, other):
        if not isinstance(other, Path):
            return NotImplemented
        return not self == other

    def _calc_lengths(self, error=LENGTH_ERROR, min_depth=LENGTH_MIN_DEPTH):
        if self._length is not None:
            return

        lengths = [each.length(error=error, min_depth=min_depth) for each in
                   self._segments]
        self._length = sum(lengths)
        self._lengths = [each/self._length for each in lengths]

    def length(self, T0=0, T1=1, error=LENGTH_ERROR, min_depth=LENGTH_MIN_DEPTH):
        self._calc_lengths(error=error, min_depth=min_depth)
        if T0 == 0 and T1 == 1:
            return self._length
        else:
            if len(self) == 1:
                return self[0].length(t0=T0, t1=T1)
            idx0, t0 = self.T2t(T0)
            idx1, t1 = self.T2t(T1)
            if idx0 == idx1:
                return self[idx0].length(t0=t0, t1=t1)
            return (self[idx0].length(t0=t0) +
                    sum(self[idx].length() for idx in range(idx0 + 1, idx1)) +
                    self[idx1].length(t1=t1))

    @property
    def start(self):
        if not self._start:
            self._start = self._segments[0].start
        return self._start

    @start.setter
    def start(self, pt):
        self._start = pt
        self._segments[0].start = pt

    @property
    def end(self):
        if not self._end:
            self._end = self._segments[-1].end
        return self._end

    @end.setter
    def end(self, pt):
        self._end = pt
        self._segments[-1].end = pt

    def d(self, useSandT=False, use_closed_attrib=False):

        if use_closed_attrib:
            self_closed = self.closed(warning_on=False)
            if self_closed:
                segments = self[:-1]
            else:
                segments = self[:]
        else:
            self_closed = False
            segments = self[:]

        current_pos = None
        parts = []
        previous_segment = None
        end = self[-1].end

        for segment in segments:
            seg_start = segment.start
            if current_pos != seg_start or \
                    (self_closed and seg_start == end and use_closed_attrib):
                parts.append('M {},{}'.format(seg_start.real, seg_start.imag))

            if isinstance(segment, Line):
                args = segment.end.real, segment.end.imag
                parts.append('L {},{}'.format(*args))
            elif isinstance(segment, CubicBezier):
                if useSandT and segment.is_smooth_from(previous_segment,
                                                       warning_on=False):
                    args = (segment.control2.real, segment.control2.imag,
                            segment.end.real, segment.end.imag)
                    parts.append('S {},{} {},{}'.format(*args))
                else:
                    args = (segment.control1.real, segment.control1.imag,
                            segment.control2.real, segment.control2.imag,
                            segment.end.real, segment.end.imag)
                    parts.append('C {},{} {},{} {},{}'.format(*args))
            elif isinstance(segment, QuadraticBezier):
                if useSandT and segment.is_smooth_from(previous_segment,
                                                       warning_on=False):
                    args = segment.end.real, segment.end.imag
                    parts.append('T {},{}'.format(*args))
                else:
                    args = (segment.control.real, segment.control.imag,
                            segment.end.real, segment.end.imag)
                    parts.append('Q {},{} {},{}'.format(*args))

            elif isinstance(segment, Arc):
                args = (segment.radius.real, segment.radius.imag,
                        segment.rotation,int(segment.large_arc),
                        int(segment.sweep),segment.end.real, segment.end.imag)
                parts.append('A {},{} {} {:d},{:d} {},{}'.format(*args))
            current_pos = segment.end
            previous_segment = segment

        if self_closed:
            parts.append('Z')

        return ' '.join(parts)

################################################### svgpathtools end #########################################################
