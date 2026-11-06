#!/usr/bin/env python3
"""Convert Swagger 2.0 / OpenAPI 3.x JSON to diagrams in free, open formats.

A universal converter: the same API spec becomes a diagram in whichever
free tool you have, with no paid modeling product required.

Formats (--format):
  mermaid  - Mermaid class diagram (.mmd). Renders free everywhere:
             mermaid.live, the VS Code Mermaid extension, or GitHub
             markdown (paste the diagram inside a ```mermaid fence).
  plantuml - PlantUML class diagram (.puml). Renders free via the
             PlantUML VS Code extension or the public PlantUML server.
  xmi      - XMI 2.1 UML, for import into a free UML tool such as Modelio
             (or Sparx Enterprise Architect, if you have it).
  vsdx     - Editable Visio drawing (.vsdx, Visio 2013 and later). One
             rectangle shape per class/interface, with its attributes or
             operations as editable shape text: click a shape in Visio to
             move it, resize it, or edit its text. This is a real shape,
             not a picture pasted into Visio. No Visio stencil or master
             is required; shapes are self-contained. Validated: the output
             opens as editable shapes.

Usage:
  python Convert-SwaggerToDiagrams.py api.json --format mermaid
  python Convert-SwaggerToDiagrams.py api.json --format plantuml -o model.puml
  python Convert-SwaggerToDiagrams.py api.json --format xmi
  python Convert-SwaggerToDiagrams.py api.json --format vsdx
  python Convert-SwaggerToDiagrams.py https://petstore.swagger.io/v2/swagger.json --format vsdx

Mapping (all formats):
  schemas/definitions -> classes, properties -> attributes
  paths grouped by tag -> interfaces, endpoints -> operations
  $ref -> a type naming that class; arrays -> a collection of the item type

Standard library only. Python 3.8+.
"""

import argparse
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from xml.sax.saxutils import escape as _xml_escape

XMI_NS = "http://www.omg.org/XMI"
UML_NS = "http://www.omg.org/spec/UML/20110701"
ET.register_namespace("xmi", XMI_NS)
ET.register_namespace("uml", UML_NS)

PRIMITIVES = {"string": "String", "integer": "Integer", "number": "Real",
              "boolean": "Boolean", "object": "Object"}


def sanitize(name, default="Unnamed"):
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", str(name or "")).strip("_")
    return cleaned or default


def ref_name(ref):
    return ref.rsplit("/", 1)[-1]


def get_schemas(spec):
    if "openapi" in spec:
        return spec.get("components", {}).get("schemas", {})
    return spec.get("definitions", {})


def merge_allof(schema, schemas):
    merged = {k: v for k, v in schema.items() if k != "allOf"}
    for part in schema.get("allOf", []):
        if "$ref" in part:
            base = merge_allof(schemas.get(ref_name(part["$ref"]), {}), schemas)
            merged.setdefault("properties", {}).update(base.get("properties", {}))
            merged.setdefault("required", []).extend(base.get("required", []))
        else:
            merged.setdefault("properties", {}).update(part.get("properties", {}))
            merged.setdefault("required", []).extend(part.get("required", []))
    return merged


def display_type(prop):
    """Return (type_name, is_array) for a schema fragment."""
    if "$ref" in prop:
        return ref_name(prop["$ref"]), False
    if prop.get("type") == "array":
        items = prop.get("items", {})
        if "$ref" in items:
            return ref_name(items["$ref"]), True
        return PRIMITIVES.get(items.get("type"), "String"), True
    return PRIMITIVES.get(prop.get("type"), "String"), False


def build_ir(spec):
    """Intermediate model shared by the text renderers."""
    schemas = get_schemas(spec)
    schemas = {n: merge_allof(s, schemas) for n, s in schemas.items()}
    classes = []
    for name, schema in schemas.items():
        required = set(schema.get("required", []))
        attrs = []
        for prop_name, prop in (schema.get("properties") or {}).items():
            tname, arr = display_type(prop)
            attrs.append({"name": prop_name, "type": tname, "array": arr,
                          "required": prop_name in required,
                          "enum": prop.get("enum")})
        classes.append({"name": name, "attrs": attrs})
    by_tag = {}
    for path, methods in (spec.get("paths") or {}).items():
        for method, op in methods.items():
            if not isinstance(op, dict):
                continue
            tags = op.get("tags") or ["Default"]
            by_tag.setdefault(tags[0], []).append((method, path, op))
    interfaces = []
    for tag, ops in by_tag.items():
        iops = []
        for method, path, op in ops:
            op_name = sanitize(op["operationId"]) if op.get("operationId") \
                else sanitize(method + "_" + path)
            params = []
            for param in op.get("parameters", []):
                if param.get("$ref"):
                    continue
                tname, arr = display_type(param.get("schema", param))
                params.append({"name": sanitize(param.get("name", "param")),
                               "type": tname, "array": arr})
            body = op.get("requestBody", {})
            content = (body.get("content") or {}).get("application/json", {})
            if "$ref" in content.get("schema", {}):
                tname, arr = display_type(content["schema"])
                params.append({"name": "body", "type": tname, "array": arr})
            resp = (op.get("responses") or {}).get("200") \
                or (op.get("responses") or {}).get("201") or {}
            rschema = resp.get("schema") \
                or (resp.get("content") or {}).get("application/json", {}).get("schema") \
                or {}
            ret = display_type(rschema) if rschema else (None, False)
            iops.append({"name": op_name, "params": params, "return": ret})
        interfaces.append({"name": sanitize(tag) + "Api", "ops": iops})
    title = spec.get("info", {}).get("title", "ApiModel")
    return {"title": title, "classes": classes, "interfaces": interfaces}


def fmt_type(tname, arr, style):
    if not tname:
        return ""
    if not arr:
        return tname
    return "List~%s~" % tname if style == "mermaid" else "%s[]" % tname


def render_plantuml(ir):
    lines = ["@startuml", "title %s" % ir["title"], ""]
    for cls in ir["classes"]:
        lines.append("class %s {" % cls["name"])
        for a in cls["attrs"]:
            lines.append("  +%s : %s" % (a["name"], fmt_type(a["type"], a["array"], "plantuml")))
        lines.append("}")
        enums = ["%s: %s" % (a["name"], ", ".join(map(str, a["enum"])))
                 for a in cls["attrs"] if a["enum"]]
        if enums:
            lines.append("note right of %s : %s" % (cls["name"], "; ".join(enums)))
        lines.append("")
    for iface in ir["interfaces"]:
        lines.append("interface %s {" % iface["name"])
        for op in iface["ops"]:
            params = ", ".join("%s : %s" % (p["name"], fmt_type(p["type"], p["array"], "plantuml"))
                               for p in op["params"])
            ret = fmt_type(op["return"][0], op["return"][1], "plantuml")
            lines.append("  +%s(%s)%s" % (op["name"], params, " : " + ret if ret else ""))
        lines.append("}")
        lines.append("")
    lines.append("@enduml")
    return "\n".join(lines) + "\n"


def render_mermaid(ir):
    lines = ["---", "title: %s" % ir["title"], "---", "classDiagram"]
    for cls in ir["classes"]:
        lines.append("  class %s {" % cls["name"])
        for a in cls["attrs"]:
            lines.append("    +%s %s" % (fmt_type(a["type"], a["array"], "mermaid"), a["name"]))
        lines.append("  }")
    for iface in ir["interfaces"]:
        lines.append("  class %s {" % iface["name"])
        lines.append("    <<interface>>")
        for op in iface["ops"]:
            params = ", ".join("%s : %s" % (p["name"], fmt_type(p["type"], p["array"], "mermaid"))
                               for p in op["params"])
            ret = fmt_type(op["return"][0], op["return"][1], "mermaid")
            lines.append("    +%s(%s)%s" % (op["name"], params, " " + ret if ret else ""))
        lines.append("  }")
    return "\n".join(lines) + "\n"


def xmi_id(counter):
    counter[0] += 1
    return "ea-%d" % counter[0]


def render_xmi(spec, ir):
    """XMI 2.1 rendering (same element model as the earlier EA-only script)."""
    counter = [0]
    root = ET.Element("{%s}XMI" % XMI_NS, {"{%s}version" % XMI_NS: "2.1"})
    model = ET.SubElement(root, "{%s}Model" % UML_NS,
                          {"{%s}id" % XMI_NS: xmi_id(counter),
                           "name": sanitize(ir["title"])})
    prim_ids = {}
    for prim in ("String", "Integer", "Real", "Boolean", "Object"):
        pid = xmi_id(counter)
        prim_ids[prim] = pid
        ET.SubElement(model, "packagedElement",
                      {"{%s}type" % XMI_NS: "uml:PrimitiveType",
                       "{%s}id" % XMI_NS: pid, "name": prim})
    class_ids = {c["name"]: xmi_id(counter) for c in ir["classes"]}
    schema_pkg = ET.SubElement(model, "packagedElement",
                               {"{%s}type" % XMI_NS: "uml:Package",
                                "{%s}id" % XMI_NS: xmi_id(counter),
                                "name": "Schemas"})
    for cls in ir["classes"]:
        el = ET.SubElement(schema_pkg, "packagedElement",
                           {"{%s}type" % XMI_NS: "uml:Class",
                            "{%s}id" % XMI_NS: class_ids[cls["name"]],
                            "name": cls["name"]})
        for a in cls["attrs"]:
            attr = ET.SubElement(el, "ownedAttribute",
                                 {"{%s}type" % XMI_NS: "uml:Property",
                                  "{%s}id" % XMI_NS: xmi_id(counter),
                                  "name": a["name"], "visibility": "public"})
            tid = class_ids.get(a["type"]) or prim_ids.get(a["type"])
            if tid:
                ET.SubElement(attr, "type", {"{%s}idref" % XMI_NS: tid})
            ET.SubElement(attr, "lowerValue",
                          {"{%s}type" % XMI_NS: "uml:LiteralInteger",
                           "{%s}id" % XMI_NS: xmi_id(counter),
                           "value": "1" if a["required"] else "0"})
            ET.SubElement(attr, "upperValue",
                          {"{%s}type" % XMI_NS: "uml:LiteralUnlimitedNatural",
                           "{%s}id" % XMI_NS: xmi_id(counter),
                           "value": "*" if a["array"] else "1"})
            if a["enum"]:
                ET.SubElement(attr, "ownedComment",
                              {"{%s}type" % XMI_NS: "uml:Comment",
                               "{%s}id" % XMI_NS: xmi_id(counter),
                               "body": "Allowed values: %s" % ", ".join(map(str, a["enum"]))})
    api_pkg = ET.SubElement(model, "packagedElement",
                            {"{%s}type" % XMI_NS: "uml:Package",
                             "{%s}id" % XMI_NS: xmi_id(counter), "name": "Api"})
    for iface in ir["interfaces"]:
        iel = ET.SubElement(api_pkg, "packagedElement",
                            {"{%s}type" % XMI_NS: "uml:Interface",
                             "{%s}id" % XMI_NS: xmi_id(counter),
                             "name": iface["name"]})
        for op in iface["ops"]:
            oel = ET.SubElement(iel, "ownedOperation",
                                {"{%s}type" % XMI_NS: "uml:Operation",
                                 "{%s}id" % XMI_NS: xmi_id(counter),
                                 "name": op["name"], "visibility": "public"})
            for p in op["params"]:
                pel = ET.SubElement(oel, "ownedParameter",
                                    {"{%s}type" % XMI_NS: "uml:Parameter",
                                     "{%s}id" % XMI_NS: xmi_id(counter),
                                     "name": p["name"], "direction": "in"})
                tid = class_ids.get(p["type"]) or prim_ids.get(p["type"])
                if tid:
                    ET.SubElement(pel, "type", {"{%s}idref" % XMI_NS: tid})
            if op["return"][0]:
                rel = ET.SubElement(oel, "ownedParameter",
                                    {"{%s}type" % XMI_NS: "uml:Parameter",
                                     "{%s}id" % XMI_NS: xmi_id(counter),
                                     "name": "return", "direction": "return"})
                tid = class_ids.get(op["return"][0]) or prim_ids.get(op["return"][0])
                if tid:
                    ET.SubElement(rel, "type", {"{%s}idref" % XMI_NS: tid})
    return root


def load_spec(source):
    if source.startswith("http://") or source.startswith("https://"):
        with urllib.request.urlopen(source) as resp:
            return json.load(resp)
    with open(source, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _vsdx_boxes(ir):
    """One box per class/interface: (kind, lines) in diagram order."""
    boxes = []
    for cls in ir["classes"]:
        lines = [cls["name"]]
        if cls["attrs"]:
            lines.append("----------------")
            for a in cls["attrs"]:
                lines.append("+%s : %s" % (a["name"], fmt_type(a["type"], a["array"], "plantuml")))
        boxes.append(("class", lines))
    for iface in ir["interfaces"]:
        lines = ["<<interface>>", iface["name"]]
        if iface["ops"]:
            lines.append("----------------")
            for op in iface["ops"]:
                params = ", ".join("%s : %s" % (p["name"], fmt_type(p["type"], p["array"], "plantuml"))
                                   for p in op["params"])
                ret = fmt_type(op["return"][0], op["return"][1], "plantuml")
                lines.append("+%s(%s)%s" % (op["name"], params, " : " + ret if ret else ""))
        boxes.append(("interface", lines))
    return boxes


def write_vsdx(ir, out):
    """Write an editable .vsdx: a ZIP of Visio XML parts (MS-VSDX).

    Each box is a self-contained rectangle Shape with Geometry and
    editable Text, so Visio opens it as shapes, not as a picture.
    No master/stencil part is needed. Page size grows to fit the grid.
    """
    core_ns = "http://schemas.microsoft.com/office/visio/2012/main"
    rel_ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    boxes = _vsdx_boxes(ir)
    cols = min(3, len(boxes)) if boxes else 1
    margin, gutter = 0.5, 0.5
    widths = []
    heights = []
    for _kind, lines in boxes:
        widths.append(min(4.5, max(2.2, max((len(l) for l in lines), default=1) * 0.09 + 0.4)))
        heights.append(max(0.9, len(lines) * 0.25 + 0.3))
    col_w = max(widths) if widths else 2.2
    rows = [(i + cols - 1) // cols for i in range(len(boxes))]
    row_heights = []
    for r in range((len(boxes) + cols - 1) // cols if boxes else 0):
        row_heights.append(max(heights[r * cols:(r + 1) * cols]))
    page_w = margin * 2 + cols * col_w + (cols - 1) * gutter if boxes else 8.5
    page_h = margin * 2 + sum(row_heights) + (len(row_heights) - 1) * gutter if boxes else 11.0
    shapes = []
    shape_id = 0
    for idx, (kind, lines) in enumerate(boxes):
        shape_id += 1
        col, row = idx % cols, idx // cols
        w = widths[idx]
        h = heights[idx]
        pinx = margin + col * (col_w + gutter) + w / 2
        top = page_h - margin - sum(row_heights[:row]) - row * gutter
        piny = top - h / 2
        fill = "#D9E2F3" if kind == "class" else "#FFF2CC"
        text = _xml_escape("\n".join(lines))
        shapes.append(
            '    <Shape ID="%d" Type="Shape" LineStyle="0" FillStyle="0" TextStyle="0">\n'
            '      <Cell N="PinX" V="%.4f"/>\n'
            '      <Cell N="PinY" V="%.4f"/>\n'
            '      <Cell N="Width" V="%.4f"/>\n'
            '      <Cell N="Height" V="%.4f"/>\n'
            '      <Cell N="LocPinX" V="%.4f"/>\n'
            '      <Cell N="LocPinY" V="%.4f"/>\n'
            '      <Cell N="Angle" V="0"/>\n'
            '      <Cell N="FillForegnd" V="%s"/>\n'
            '      <Cell N="FillPattern" V="1"/>\n'
            '      <Cell N="LineColor" V="#000000"/>\n'
            '      <Cell N="LinePattern" V="1"/>\n'
            '      <Cell N="LineWeight" V="0.01"/>\n'
            '      <Section N="Geometry" IX="0">\n'
            '        <Row T="RelMoveTo" IX="1"><Cell N="X" V="0"/><Cell N="Y" V="0"/></Row>\n'
            '        <Row T="RelLineTo" IX="2"><Cell N="X" V="1"/><Cell N="Y" V="0"/></Row>\n'
            '        <Row T="RelLineTo" IX="3"><Cell N="X" V="1"/><Cell N="Y" V="1"/></Row>\n'
            '        <Row T="RelLineTo" IX="4"><Cell N="X" V="0"/><Cell N="Y" V="1"/></Row>\n'
            '        <Row T="RelLineTo" IX="5"><Cell N="X" V="0"/><Cell N="Y" V="0"/></Row>\n'
            '      </Section>\n'
            '      <Text>%s</Text>\n'
            '    </Shape>' % (shape_id, pinx, piny, w, h, w / 2, h / 2, fill, text))
    title = _xml_escape(ir["title"])
    parts = {
        "[Content_Types].xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
            '<Default Extension="xml" ContentType="application/xml"/>\n'
            '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>\n'
            '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>\n'
            '<Override PartName="/visio/document.xml" ContentType="application/vnd.ms-visio.drawing.main+xml"/>\n'
            '<Override PartName="/visio/pages/pages.xml" ContentType="application/vnd.ms-visio.pages+xml"/>\n'
            '<Override PartName="/visio/pages/page1.xml" ContentType="application/vnd.ms-visio.page+xml"/>\n'
            '<Override PartName="/visio/masters/masters.xml" ContentType="application/vnd.ms-visio.masters+xml"/>\n'
            '<Override PartName="/visio/windows.xml" ContentType="application/vnd.ms-visio.windows+xml"/>\n'
            '</Types>\n'),
        "_rels/.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
            '<Relationship Id="rId1" Type="http://schemas.microsoft.com/visio/2010/relationships/document" Target="visio/document.xml"/>\n'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>\n'
            '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>\n'
            '</Relationships>\n'),
        "docProps/core.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
            '<dc:title>%s</dc:title><dc:creator>Convert-SwaggerToDiagrams.py</dc:creator>\n'
            '</cp:coreProperties>\n' % title),
        "docProps/app.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
            'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">\n'
            '<HeadingPairs><vt:vector size="2" baseType="variant">'
            '<vt:variant><vt:lpstr>Pages</vt:lpstr></vt:variant>'
            '<vt:variant><vt:i4>1</vt:i4></vt:variant></vt:vector></HeadingPairs>\n'
            '<TitlesOfParts><vt:vector size="1" baseType="lpstr"><vt:lpstr>Page-1</vt:lpstr></vt:vector></TitlesOfParts>\n'
            '<Application>Convert-SwaggerToDiagrams.py</Application>\n'
            '</Properties>\n'),
        "visio/document.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<VisioDocument xmlns="http://schemas.microsoft.com/office/visio/2012/main" '
            'xmlns:r="%s" xml:space="preserve">\n'
            '<DocumentProperties><Title>%s</Title><Creator>Convert-SwaggerToDiagrams.py</Creator></DocumentProperties>\n'
            '<DocumentSettings><GlueSettings V="9"/><SnapSettings V="35"/><SnapExtensions V="0"/>'
            '<DynamicGridEnabled V="1"/><ProtectStyles V="0"/><ProtectShapes V="0"/>'
            '<ProtectMasters V="0"/><ProtectBkgnds V="0"/></DocumentSettings>\n'
            '<Colors><ColorEntry IX="0" RGB="#000000"/><ColorEntry IX="1" RGB="#FFFFFF"/></Colors>\n'
            '<FaceNames><FaceName ID="0" NameU="Calibri" Name="Calibri"/></FaceNames>\n'
            '<Stylesheets><StyleSheet ID="0" NameU="Normal" Name="Normal">'
            '<Cell N="LinePattern" V="1"/><Cell N="LineWeight" V="0.01"/><Cell N="LineColor" V="0"/>'
            '<Cell N="FillForegnd" V="1"/><Cell N="FillPattern" V="1"/><Cell N="FillBkgnd" V="0"/>'
            '<Cell N="CharFont" V="0"/><Cell N="CharSize" V="0.1389"/><Cell N="CharColor" V="0"/>'
            '<Cell N="CharStyle" V="0"/></StyleSheet></Stylesheets>\n'
            '</VisioDocument>\n' % (rel_ns, title)),
        "visio/_rels/document.xml.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
            '<Relationship Id="rId1" Type="http://schemas.microsoft.com/visio/2010/relationships/pages" Target="pages/pages.xml"/>\n'
            '<Relationship Id="rId2" Type="http://schemas.microsoft.com/visio/2010/relationships/masters" Target="masters/masters.xml"/>\n'
            '<Relationship Id="rId3" Type="http://schemas.microsoft.com/visio/2010/relationships/windows" Target="windows.xml"/>\n'
            '</Relationships>\n'),
        "visio/windows.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Windows xmlns="%s" xmlns:r="%s" xml:space="preserve">\n'
            '<Window ID="0" WindowType="Drawing" WindowState="1073741824" WindowLeft="0" WindowTop="0" '
            'WindowWidth="1000" WindowHeight="800" ContainerType="Page" Page="0" ViewScale="1" '
            'ViewCenterX="%.4f" ViewCenterY="%.4f">\n'
            '<ShowRulers>1</ShowRulers><ShowGrid>1</ShowGrid><ShowPageBreaks>0</ShowPageBreaks>'
            '<ShowGuides>1</ShowGuides><ShowConnectionPoints>1</ShowConnectionPoints>'
            '<GlueSettings>9</GlueSettings><SnapSettings>65847</SnapSettings><SnapExtensions>34</SnapExtensions>'
            '<SnapAngles/><DynamicGridEnabled>1</DynamicGridEnabled><TabSplitterPos>0.5</TabSplitterPos>\n'
            '</Window></Windows>\n' % (core_ns, rel_ns, page_w / 2, page_h / 2)),
        "visio/masters/masters.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Masters xmlns="%s" xmlns:r="%s" xml:space="preserve"/>\n' % (core_ns, rel_ns)),
        "visio/masters/_rels/masters.xml.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>\n'),
        "visio/pages/pages.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Pages xmlns="%s" xmlns:r="%s" xml:space="preserve">\n'
            '  <Page ID="0" NameU="Page-1" Name="Page-1">\n'
            '    <PageSheet LineStyle="0" FillStyle="0" TextStyle="0">\n'
            '      <Cell N="PageWidth" V="%.4f"/>\n'
            '      <Cell N="PageHeight" V="%.4f"/>\n'
            '      <Cell N="PageScale" V="1"/>\n'
            '      <Cell N="DrawingScale" V="1"/>\n'
            '    </PageSheet>\n'
            '    <Rel r:id="rId1"/>\n'
            '  </Page>\n'
            '</Pages>\n' % (core_ns, rel_ns, page_w, page_h)),
        "visio/pages/_rels/pages.xml.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
            '<Relationship Id="rId1" Type="http://schemas.microsoft.com/visio/2010/relationships/page" Target="page1.xml"/>\n'
            '</Relationships>\n'),
        "visio/pages/_rels/page1.xml.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>\n'),
        "visio/pages/page1.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<PageContents xmlns="%s" xmlns:r="%s" xml:space="preserve">\n'
            '  <Shapes>\n%s\n  </Shapes>\n'
            '</PageContents>\n' % (core_ns, rel_ns, "\n".join(shapes))),
    }
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in parts.items():
            zf.writestr(name, data)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Swagger/OpenAPI JSON -> diagram")
    parser.add_argument("input", help="Swagger 2.0 or OpenAPI 3.x JSON file or URL")
    parser.add_argument("--format", choices=["mermaid", "plantuml", "xmi", "vsdx"],
                        default="mermaid", help="Output format (default: mermaid)")
    parser.add_argument("-o", "--output", help="Output file (default: input name with format extension)")
    args = parser.parse_args(argv)
    spec = load_spec(args.input)
    ir = build_ir(spec)
    ext = {"mermaid": ".mmd", "plantuml": ".puml", "xmi": ".xmi", "vsdx": ".vsdx"}[args.format]
    base = args.input.rsplit("/", 1)[-1] if "://" in args.input else args.input
    out = args.output or re.sub(r"\.json$", "", base, flags=re.I) + ext
    if args.format == "mermaid":
        text = render_mermaid(ir)
    elif args.format == "plantuml":
        text = render_plantuml(ir)
    elif args.format == "vsdx":
        write_vsdx(ir, out)
        text = None
    else:
        ET.ElementTree(render_xmi(spec, ir)).write(out, encoding="utf-8", xml_declaration=True)
        text = None
    if text is not None:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(text)
    nops = sum(len(i["ops"]) for i in ir["interfaces"])
    print("Wrote %s: %d classes, %d interfaces, %d operations"
          % (out, len(ir["classes"]), len(ir["interfaces"]), nops))
    return 0


if __name__ == "__main__":
    sys.exit(main())
