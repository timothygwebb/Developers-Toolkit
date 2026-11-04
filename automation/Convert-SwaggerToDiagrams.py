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

Usage:
  python Convert-SwaggerToDiagrams.py api.json --format mermaid
  python Convert-SwaggerToDiagrams.py api.json --format plantuml -o model.puml
  python Convert-SwaggerToDiagrams.py api.json --format xmi

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
import xml.etree.ElementTree as ET

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


def main(argv=None):
    parser = argparse.ArgumentParser(description="Swagger/OpenAPI JSON -> diagram")
    parser.add_argument("input", help="Swagger 2.0 or OpenAPI 3.x JSON file")
    parser.add_argument("--format", choices=["mermaid", "plantuml", "xmi"],
                        default="mermaid", help="Output format (default: mermaid)")
    parser.add_argument("-o", "--output", help="Output file (default: input name with format extension)")
    args = parser.parse_args(argv)
    with open(args.input, "r", encoding="utf-8") as fh:
        spec = json.load(fh)
    ir = build_ir(spec)
    ext = {"mermaid": ".mmd", "plantuml": ".puml", "xmi": ".xmi"}[args.format]
    out = args.output or re.sub(r"\.json$", "", args.input, flags=re.I) + ext
    if args.format == "mermaid":
        text = render_mermaid(ir)
    elif args.format == "plantuml":
        text = render_plantuml(ir)
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
