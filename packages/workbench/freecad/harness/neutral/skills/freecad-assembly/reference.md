# Reference: Assembly examples

Every example below was run headless with `freecadcmd` on FreeCAD 1.1.4, and the printed value is in the comment. The
examples after "Helpers" use what is defined there, so run the helpers first in the same session. Each example starts
its own document.

## Helpers

```python
import FreeCAD as App
import Part
import Sketcher
import JointObject

V = App.Vector
JT_FIXED, JT_REVOLUTE = 0, 1                         # indices into JointObject.JointTypes


def make_part(doc, name, w, d, h):
    """A Body holding a rectangular Pad named 'Pad'."""
    body = doc.addObject("PartDesign::Body", name)
    xy = next(o for o in body.Origin.OriginFeatures if o.Role == "XY_Plane")
    sk = body.newObject("Sketcher::SketchObject", "Sketch")
    sk.AttachmentSupport = [(xy, "")]
    sk.MapMode = "FlatFace"
    pts = [(0, 0), (w, 0), (w, d), (0, d)]
    for i in range(4):
        a, b = pts[i], pts[(i + 1) % 4]
        sk.addGeometry(Part.LineSegment(V(a[0], a[1], 0), V(b[0], b[1], 0)))
    for i in range(4):
        sk.addConstraint(Sketcher.Constraint("Coincident", i, 2, (i + 1) % 4, 1))
    pad = body.newObject("PartDesign::Pad", "Pad")
    pad.Profile = sk
    pad.Length = h
    doc.recompute()
    return body


def face_and_vertex(body, want_face, want_vertex):
    """('FaceN', 'VertexM'): a face matching want_face and a vertex of that face matching want_vertex."""
    shape = body.Shape
    fi = next(i for i, f in enumerate(shape.Faces) if want_face(f))
    face = shape.Faces[fi]
    vi = next(i for i, v in enumerate(shape.Vertexes)
              if want_vertex(v.Point) and any(v.Point.distanceToPoint(fv.Point) < 1e-6 for fv in face.Vertexes))
    return "Face%d" % (fi + 1), "Vertex%d" % (vi + 1)


top = lambda f: abs(f.CenterOfMass.z - 10) < 1e-6 and f.normalAt(0, 0).z > 0.9
bottom = lambda f: abs(f.CenterOfMass.z) < 1e-6 and f.normalAt(0, 0).z < -0.9
at_origin = lambda p: abs(p.x) < 1e-6 and abs(p.y) < 1e-6


def two_parts(doc):
    """An assembly with a grounded Base and a Block, and the data needed to join them."""
    base = make_part(doc, "Base", 40, 40, 10)
    block = make_part(doc, "Block", 20, 20, 10)
    asm = doc.addObject("Assembly::AssemblyObject", "Assembly")
    asm.Type = "Assembly"
    joints = asm.newObject("Assembly::JointGroup", "Joints")
    base_link = asm.newObject("App::Link", "BaseLink")
    base_link.LinkedObject = base
    block_link = asm.newObject("App::Link", "BlockLink")
    block_link.LinkedObject = block
    block_link.Placement.Base = V(100, 50, 0)         # a starting position; the solver moves it
    ground = joints.newObject("App::FeaturePython", "GroundedJoint")
    JointObject.GroundedJoint(ground, base_link)      # the fixed reference part
    doc.recompute()
    return base, block, asm, joints, base_link, block_link


def add_joint(joints, kind, name, moving_link, moving_refs, fixed_link, fixed_refs):
    joint = joints.newObject("App::FeaturePython", name)
    JointObject.Joint(joint, kind)
    joint.Proxy.setJointConnectors(joint, [[moving_link, moving_refs], [fixed_link, fixed_refs]])   # moving part first
    return joint
```

## The structure of an assembly

```python
doc = App.newDocument("Structure")
base, block, asm, joints, base_link, block_link = two_parts(doc)
print(asm.TypeId, asm.Type, joints.TypeId)
print([o.Name for o in asm.Group])                    # the joint group and the two links
print(base_link.LinkedObject.Name, block_link.LinkedObject.Name)
print(JointObject.JointTypes)
```

## A Fixed joint, with faces and vertices chosen by geometry

```python
doc = App.newDocument("Fixed")
base, block, asm, joints, base_link, block_link = two_parts(doc)
fa, va = face_and_vertex(base, top, at_origin)        # the top of Base, the corner at the origin
fb, vb = face_and_vertex(block, bottom, at_origin)    # the bottom of Block, the same corner
joint = add_joint(joints, JT_FIXED, "Fixed", block_link, ["Block.Pad." + fb, "Block.Pad." + vb],
                  base_link, ["Base.Pad." + fa, "Base.Pad." + va])
doc.recompute()
print(asm.solve())                                    # 0: the solver ran
doc.recompute()
bb = block_link.Shape.BoundBox
print(bb.ZMin, bb.ZMax)                               # 10.0 20.0: Block rests on top of Base
print(joint.Placement2.Base)                          # (0, 0, 10): not the identity, so the reference resolved
```

## A wrong reference form is accepted

```python
doc = App.newDocument("WrongForm")
base, block, asm, joints, base_link, block_link = two_parts(doc)
fa, va = face_and_vertex(base, top, at_origin)
fb, vb = face_and_vertex(block, bottom, at_origin)
joint = add_joint(joints, JT_FIXED, "Fixed", block_link, ["Pad." + fb + ".", "Pad." + vb + "."],     # missing the Body name
                  base_link, ["Pad." + fa + ".", "Pad." + va + "."])
doc.recompute()
print(asm.solve())                                    # the solver reports its own success
doc.recompute()
print(joint.Placement1.Base, joint.Placement2.Base)   # the placements: identity if nothing resolved
bb = block_link.Shape.BoundBox
print(bb.ZMin, bb.ZMax)                               # compare with 10.0 20.0 for the correct form
```

## Flip, offset, revolute and expressions

```python
doc = App.newDocument("Adjust")
base, block, asm, joints, base_link, block_link = two_parts(doc)
fa, va = face_and_vertex(base, top, at_origin)
fb, vb = face_and_vertex(block, bottom, at_origin)
joint = add_joint(joints, JT_FIXED, "Fixed", block_link, ["Block.Pad." + fb, "Block.Pad." + vb],
                  base_link, ["Base.Pad." + fa, "Base.Pad." + va])
doc.recompute()
asm.solve()
doc.recompute()


def z_range():
    bb = block_link.Shape.BoundBox
    return round(bb.ZMin, 3), round(bb.ZMax, 3)


print(z_range())                                      # (10.0, 20.0)
joint.Proxy.flipOnePart(joint)
asm.solve()
doc.recompute()
print(z_range())                                      # flipped
joint.Proxy.flipOnePart(joint)                        # a second flip returns to the original
asm.solve()
doc.recompute()
print(z_range())                                      # (10.0, 20.0)

joint.Offset2 = App.Placement(V(5, 0, 0), App.Rotation())
asm.solve()
doc.recompute()
print(round(block_link.Shape.BoundBox.XMin, 3))       # the mate moved 5 mm in X

varset = doc.addObject("App::VarSet", "Dims")
varset.addProperty("App::PropertyLength", "Shift", "Dimensions", "Shift")
varset.Shift = 8
joint.setExpression("Offset2.Base.x", "Dims.Shift")   # a joint property driven by a named value
doc.recompute()
asm.solve()
doc.recompute()
print(round(block_link.Shape.BoundBox.XMin, 3))       # follows the value: 8.0
varset.Shift = 12
doc.recompute()
asm.solve()
doc.recompute()
print(round(block_link.Shape.BoundBox.XMin, 3))       # 12.0
```

## A Revolute joint leaves its rotation free

```python
doc = App.newDocument("Revolute")
base, block, asm, joints, base_link, block_link = two_parts(doc)
fa, va = face_and_vertex(base, top, at_origin)
fb, vb = face_and_vertex(block, bottom, at_origin)
joint = add_joint(joints, JT_REVOLUTE, "Revolute", block_link, ["Block.Pad." + fb, "Block.Pad." + vb],
                  base_link, ["Base.Pad." + fa, "Base.Pad." + va])
doc.recompute()
print(asm.solve())
doc.recompute()
before = block_link.Placement.Rotation.Angle
joint.Angle = 45
doc.recompute()
asm.solve()
doc.recompute()
print(round(joint.Angle, 3), round(block_link.Placement.Rotation.Angle - before, 6))   # does setting Angle turn the part?
```
