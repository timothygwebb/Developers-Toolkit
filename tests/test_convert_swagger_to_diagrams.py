"""Pytest tests for automation/Convert-SwaggerToDiagrams.py.

Run from the repo root: python -m pytest -q

The converter is loaded directly from its file path so the tests work
without installing anything: the tool is standard library only.
"""

import importlib.util
import json
import threading
import zipfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

CONVERTER = Path(__file__).resolve().parent.parent / "automation" / "Convert-SwaggerToDiagrams.py"


def load_converter():
    spec = importlib.util.spec_from_file_location("converter", CONVERTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


conv = load_converter()

OPENAPI_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "Test API", "version": "1.0.0"},
    "paths": {
        "/pets": {
            "get": {
                "tags": ["Pet"],
                "operationId": "listPets",
                "responses": {
                    "200": {
                        "description": "ok",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Pet"}}},
                    }
                },
            }
        }
    },
    "components": {
        "schemas": {
            "Pet": {
                "type": "object",
                "required": ["name"],
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                    "tag": {"type": "string", "enum": ["a", "b"]},
                },
            }
        }
    },
}

SWAGGER_SPEC = {
    "swagger": "2.0",
    "info": {"title": "Old API", "version": "1.0.0"},
    "paths": {
        "/things": {
            "post": {
                "tags": ["Thing"],
                "operationId": "createThing",
                "parameters": [{"name": "body", "in": "body", "schema": {"$ref": "#/definitions/Thing"}}],
                "responses": {"201": {"description": "created", "schema": {"$ref": "#/definitions/Thing"}}},
            }
        }
    },
    "definitions": {
        "Thing": {
            "type": "object",
            "properties": {"name": {"type": "string"}, "parts": {"type": "array", "items": {"type": "string"}}},
        }
    },
}


def test_sanitize_replaces_invalid_chars():
    assert conv.sanitize("hello world!") == "hello_world"
    assert conv.sanitize("") == "Unnamed"
    assert conv.sanitize(None) == "Unnamed"


def test_display_type_ref_array_and_primitive():
    assert conv.display_type({"$ref": "#/components/schemas/Pet"}) == ("Pet", False)
    assert conv.display_type({"type": "array", "items": {"$ref": "#/components/schemas/Pet"}}) == ("Pet", True)
    assert conv.display_type({"type": "array", "items": {"type": "string"}}) == ("String", True)
    assert conv.display_type({"type": "integer"}) == ("Integer", False)


def test_build_ir_openapi3():
    ir = conv.build_ir(OPENAPI_SPEC)
    assert ir["title"] == "Test API"
    assert len(ir["classes"]) == 1
    pet = ir["classes"][0]
    assert pet["name"] == "Pet"
    assert [a["name"] for a in pet["attrs"]] == ["id", "name", "tag"]
    name_attr = [a for a in pet["attrs"] if a["name"] == "name"][0]
    assert name_attr["required"] is True
    tag_attr = [a for a in pet["attrs"] if a["name"] == "tag"][0]
    assert tag_attr["enum"] == ["a", "b"]
    assert len(ir["interfaces"]) == 1
    api = ir["interfaces"][0]
    assert api["name"] == "PetApi"
    assert api["ops"][0]["name"] == "listPets"
    assert api["ops"][0]["return"] == ("Pet", False)


def test_build_ir_swagger2_definitions():
    ir = conv.build_ir(SWAGGER_SPEC)
    assert len(ir["classes"]) == 1
    assert ir["classes"][0]["name"] == "Thing"
    parts = [a for a in ir["classes"][0]["attrs"] if a["name"] == "parts"][0]
    assert parts["array"] is True
    assert ir["interfaces"][0]["ops"][0]["name"] == "createThing"


def test_merge_allof_inherits_properties():
    schemas = {
        "Base": {"type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"]},
        "Child": {"allOf": [{"$ref": "#/components/schemas/Base"}],
                  "properties": {"name": {"type": "string"}}},
    }
    merged = conv.merge_allof(schemas["Child"], schemas)
    assert set(merged["properties"]) == {"id", "name"}
    assert "id" in merged["required"]


def test_render_mermaid_has_class_and_interface():
    out = conv.render_mermaid(conv.build_ir(OPENAPI_SPEC))
    assert "classDiagram" in out
    assert "class Pet {" in out
    assert "<<interface>>" in out
    assert "listPets() Pet" in out


def test_render_plantuml_has_start_and_end():
    out = conv.render_plantuml(conv.build_ir(OPENAPI_SPEC))
    assert out.startswith("@startuml")
    assert out.rstrip().endswith("@enduml")
    assert "class Pet {" in out
    assert "interface PetApi {" in out


def test_render_xmi_is_parseable_xml():
    import xml.etree.ElementTree as ET

    root = conv.render_xmi(OPENAPI_SPEC, conv.build_ir(OPENAPI_SPEC))
    text = ET.tostring(root, encoding="unicode")
    assert "uml:Class" in text
    assert "uml:Interface" in text
    assert "Pet" in text


def test_vsdx_boxes_hold_class_and_interface():
    boxes = conv._vsdx_boxes(conv.build_ir(OPENAPI_SPEC))
    kinds = [kind for kind, _lines in boxes]
    assert kinds == ["class", "interface"]
    assert boxes[0][1][0] == "Pet"
    assert "<<interface>>" in boxes[1][1]


def test_write_vsdx_is_valid_package_with_shapes(tmp_path):
    out = tmp_path / "model.vsdx"
    conv.write_vsdx(conv.build_ir(OPENAPI_SPEC), str(out))
    with zipfile.ZipFile(out) as zf:
        names = zf.namelist()
        assert "visio/pages/page1.xml" in names
        assert "visio/document.xml" in names
        page = zf.read("visio/pages/page1.xml").decode("utf-8")
    assert "Pet" in page
    assert "listPets" in page
    assert "#D9E2F3" in page  # class fill
    assert "#FFF2CC" in page  # interface fill


def test_load_spec_from_file(tmp_path):
    spec_file = tmp_path / "api.json"
    spec_file.write_text(json.dumps(OPENAPI_SPEC), encoding="utf-8")
    assert conv.load_spec(str(spec_file)) == OPENAPI_SPEC


class _SpecHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps(OPENAPI_SPEC).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def spec_server():
    server = HTTPServer(("127.0.0.1", 0), _SpecHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield "http://127.0.0.1:%d/spec.json" % server.server_address[1]
    server.shutdown()


def test_load_spec_from_url(spec_server):
    assert conv.load_spec(spec_server) == OPENAPI_SPEC


def test_main_writes_all_four_formats(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    spec_file = tmp_path / "api.json"
    spec_file.write_text(json.dumps(OPENAPI_SPEC), encoding="utf-8")
    for fmt, ext in [("mermaid", ".mmd"), ("plantuml", ".puml"), ("xmi", ".xmi"), ("vsdx", ".vsdx")]:
        assert conv.main(["api.json", "--format", fmt]) == 0
        out = tmp_path / ("api" + ext)
        assert out.exists() and out.stat().st_size > 0
    with zipfile.ZipFile(tmp_path / "api.vsdx") as zf:
        assert "visio/pages/page1.xml" in zf.namelist()


def test_main_default_output_name_is_spec_stem(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    spec_file = tmp_path / "api.json"
    spec_file.write_text(json.dumps(OPENAPI_SPEC), encoding="utf-8")
    assert conv.main(["api.json"]) == 0
    assert (tmp_path / "api.mmd").exists()


def test_empty_spec_renders_without_crashing(tmp_path):
    empty = {"openapi": "3.0.0", "info": {"title": "Empty", "version": "1"},
             "paths": {}, "components": {"schemas": {}}}
    ir = conv.build_ir(empty)
    assert ir["classes"] == [] and ir["interfaces"] == []
    assert "classDiagram" in conv.render_mermaid(ir)
    out = tmp_path / "empty.vsdx"
    conv.write_vsdx(ir, str(out))
    with zipfile.ZipFile(out) as zf:
        assert "visio/pages/page1.xml" in zf.namelist()
