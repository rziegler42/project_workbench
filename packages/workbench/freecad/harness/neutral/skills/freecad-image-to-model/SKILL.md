---
name: freecad-image-to-model
description: Use when building a FreeCAD model from a photo, drawing or screenshot: finding the scale, measuring in pixels, writing a feature list, building with named dimensions, and comparing the result with the image.
---

# FreeCAD model from an image

This skill is for building a model in FreeCAD 1.1 that matches a photo, a drawing or a screenshot. If FreeCAD or `freecadcmd` is not available, stop and tell the owner. An image has no scale, and a photo has perspective, so the job is to establish the scale, measure, build with named dimensions, then compare and correct. The environment is in `freecad-python`, the named dimensions in `freecad-parameters`, the features in `freecad-partdesign`, and checking numbers in `freecad-measure-and-inspection`. The advice was written against FreeCAD 1.1.4, and every Python example in `reference.md` was run there; statements from the owner's practice are marked (read).

## The workflow

1. **Establish the scale first.** Find a known length in the image: a ruler or caliper, a standard part (a coin, a credit card of 85.60 by 53.98 mm), a dimension printed on a drawing, or a measurement the owner gives (read). If there is none, ask for one real dimension. Never invent a scale silently.
2. **Judge the image.** An orthographic drawing, or a straight-on photo of a flat part, can be measured directly. An angled photo cannot: say that the dimensions carry perspective error and ask for a straight-on view or more known dimensions.
3. **Write a feature list before any code:** the base profile, then each additive and subtractive feature, then the patterns, in the order the part would be made. Note which dimensions were measured, which are standard values and which are guesses.
4. **Put every dimension in a named value** (see `freecad-parameters`), with no number buried in code, so that one corrected value changes the model.
5. **Build, render, compare, correct.** After each feature, look at a view of the model beside the reference image and fix proportions before adding detail.
6. **Report the uncertainty:** each dimension as measured, standard or assumed, with the error that follows from the pixels per millimetre.

## Measure from pixels

Take numbers from pixels and not by eye. `PIL`, `numpy` and `scipy` are part of FreeCAD's own Python on 1.1.4, so a script run with `freecadcmd` can use them; OpenCV is not part of it (read). `reference.md` finds a dark part on a light background and a reference bar of known length, and reports millimetres. On a synthetic image it recovered 64.0 by 48.0 mm and a hole of 15.99 mm against the true 64, 48 and 16.

The limits, to state for the image at hand: a threshold fails on low contrast, shadows and glare; edges are anti-aliased, so expect about one pixel of error (read); and image Y points down while FreeCAD Y points up, so flip it when you transfer a coordinate.

## Put the picture in the document

An `Image::ImagePlane` object holds a reference image in the document. It can be made headless: set `ImageFile`, and set `XSize` and `YSize` in millimetres from the scale (the pixel width divided by the pixels per millimetre). Its orientation, usually a rotation about X to stand a front photo in the XZ plane, was not checked, so confirm it in a view (read). Keep the plane out of exports by putting it in its own group and hiding it (read).

## Compare the model with the image

Render a view of the model that matches the reference image, and compare proportions, hole positions, wall thicknesses and the number of features. In a GUI session `FreeCADGui.ActiveDocument.ActiveView.saveImage(path, width, height, "White")` saves a view after `viewFront()` or `viewTop()` and `fitAll()` (read); through the FreeCAD MCP server, see `freecad-mcp`. To compare numbers, threshold both pictures, scale them by the same pixels per millimetre and compute the overlap of the two masks as intersection over union (the arithmetic is in `reference.md`; two squares shifted by 5 of 60 pixels scored 0.8462). Capturing a straight-on view of the model for this was not tested here, so check that the view and the scale match before trusting the number.

## A shape you can see but cannot measure (read)

- Prefer a standard size once the measured value is within its error: a hole measured as 5.9 mm with 0.3 mm of error is a 6 mm hole or an M6 clearance.
- Match symmetry and repetition exactly: equally spaced features are a pattern with one spacing value.
- Build the main volume first and add fillets and chamfers last, since they break first when a value changes.
- When two readings fit the image, say so, build the simpler one and offer the other.

## Report to the owner

Give the source of the scale and its error, a table of each dimension with its status (measured, standard, assumed), what the image could not show (hidden faces, wall thickness, depth), and the comparison result. Ask for the one missing measurement that would remove the most uncertainty.

## Common mistakes

| Mistake | Instead |
|---|---|
| Inventing a scale | Find a known length or ask for one |
| Measuring an angled photo as if it were flat | Say the dimensions carry perspective error |
| Typing measured numbers into the code | Put each in a named value |
| Using image Y as FreeCAD Y | Flip it |
| Reporting a fit with no error figure | Give the error from the pixels per millimetre |
