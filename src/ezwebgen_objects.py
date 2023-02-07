import os
import re
import sys
import tomllib
import markdown
from datetime import datetime

class Replacer:
    @staticmethod
    def replace(data):
        mapping = {
            "%year%": lambda: datetime.now().year,
        }
        for key, value in mapping.items():
            data = data.replace(key, str(value()))
        return data

class HtmlBuilder:
    @staticmethod
    def prepare_dependency(url):
        if url.endswith(".js"):
            return f"<script src=\"{url}\"></script>"
        elif url.endswith(".css"):
            return f"<link rel=\"stylesheet\" href=\"{url}\">"

class TemplateParser:
    @staticmethod
    def sub_get_template(template):
        template_lib = template.get("lib", "custom")
        template_type = template.get("type", "basic")
        template_out = template.get("out", None)
        path = os.path.join("globals", template_lib, template_type)
        template_files = Templates.get_files(path)
        return template_files[0], template_out

    @staticmethod
    def parse_template(options):
        templated = options.get("templated", [])
        _options = {}

        for temp_name in templated:
            option = options.get(temp_name, None)
            temp_template = option.get("template", None)
            temp_options = option.get("options", {})
            temp_filters = option.get("filters", {})
            temp_defaults = option.get("defaults", {})
            template_content = []

            if temp_template:
                file, out = TemplateParser.sub_get_template(temp_template)

                if out is None:
                    print(f"Error: template_{temp_name} has no out option", file=sys.stderr)
                    exit(1)

                val = option.get("values", None)

                if type(val) is dict:
                    val = [val]

                if type(val) is list:
                    for item in val:
                        template_template = Templates.get_content(file)

                        _item = {}
                        for k in re.findall(r"{{(.*?)}}", template_template.data):
                            _item[k] = temp_defaults.get(k, "")
                        _item: dict = {**_item, **item}

                        for k, v in temp_options.items():
                            _if = v.get("if", None)
                            _set = v.get("set", None)
                            _else = v.get("else", None)

                            if _if == "defined":
                                if k in item:
                                    _item[k] = _set
                                else:
                                    if _else is not None:
                                        _item[k] = _else
                            else:
                                _item[k] = v

                        for k, v in _item.items():
                            if k in temp_filters:
                                _if = temp_filters[k].get("if", None)
                                _set = temp_filters[k].get("set", None)
                                _else = temp_filters[k].get("else", None)

                                if _if == "is_bool_true":
                                    if type(item[k]) is bool and _item[k]:
                                        _item[k] = _set
                                    else:
                                        if _else is not None:
                                            _item[k] = _else
                                elif _if == "is_bool_false":
                                    if type(item[k]) is bool and not _item[k]:
                                        _item[k] = _set
                                    else:
                                        if _else is not None:
                                            _item[k] = _else
                            else:
                                _item[k] = v

                        item = {"{{" + k + "}}": v for k, v in _item.items()}
                        template_template.replace(item)
                        template_content.append(template_template.data)

                _options["{{" + out + "}}"] = "\n".join(template_content)

        return _options

class Template:
    def __init__(self, path):
        self.path = path

        with open(path, "r") as f:
            self.data = f.read()

    def replace(self, data):
        for key, value in data.items():
            self.data = self.data.replace(key, value)

class Templates:
    @staticmethod
    def __content(path):
        if not os.path.exists(path):
            print(f"Can't find file: {path}", file=sys.stderr)
            exit(1)

        template = Template(path)

        if not template.data:
            root = Templates.get_templates_root()
            path = os.path.dirname(path.replace(root, "")[1:])
            print(f"Template is empty: {path}", file=sys.stderr)

        return template

    @staticmethod
    def __get_root():
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    @staticmethod
    def __create_empty(path):
        if not os.path.exists(path):
            os.makedirs(path)
        with open(path + "/_.html", "w") as f:
            f.write("")

    @staticmethod
    def get_content(path):
        return Templates.__content(path)

    @staticmethod
    def get_templates_root():
        return os.path.join(Templates.__get_root(), "templates")

    @staticmethod
    def get_root(name):
        root = os.path.join(Templates.get_templates_root(), name)
        if not os.path.exists(root):
            print(f"Can't find root: {name}, creating default...", file=sys.stderr)
            Templates.__create_empty(root)
        return root

    @staticmethod
    def get_files(name):
        root = Templates.get_root(name)
        if not os.path.isdir(root):
            print(f"Can't find directory: {name}", file=sys.stderr)
            exit(1)
        return [os.path.join(root, f) for f in os.listdir(root)]

    @staticmethod
    def get_default(name):
        defaults_root = os.path.join(Templates.get_root("defaults"), name)
        return Templates.__content(defaults_root)

    @staticmethod
    def get_default_index():
        return Templates.get_default("index.html")

class TomlWrapper:
    def __init__(self, path):
        self.path = path
        self.data = None
        self.load()

    def load(self):
        with open(self.path, "rb") as f:
            self.data = tomllib.load(f)

    def get(self, key, default=None, strict=False):
        keys = key.split(".")
        last = self.data
        for key in keys:
            key = int(key) if type(last) == list and key.isdigit() else key
            try:
                if type(last) in [list, dict]:
                    last = last[key]
            except (KeyError, IndexError) as e:
                if strict:
                    print(f"Can't find key/index: {key}\nError: {e}", file=sys.stderr)
                    exit(1)
                else:
                    return default
        return last

class EzWebGenerator:
    def __init__(self, toml):
        self.toml = toml

    def generate(self, out):
        dependencies = self.toml.get("dependencies", default={})
        dependency_content = []
        for name, files in dependencies.items():
            files = [HtmlBuilder.prepare_dependency(f) for f in files]
            dependency_content.append(f"<!-- {name} -->")
            dependency_content.extend(files)

        doc_content = []
        css = ["<!-- css -->"]
        js = ["<!-- js -->"]

        components = self.toml.get("components", default={})
        for name, opts in components.items():
            lib = opts.get("lib", "custom")
            typ = opts.get("type", "basic")

            options = opts.get("options", {})
            attrs = opts.get("attrs", {})
            _options = {
                "{{" + name.upper() + "_ATTRS}}": " ".join([f"{k}=\"{v}\"" for k, v in attrs.items()]),
            }

            files = Templates.get_files(os.path.join(name, lib, typ))
            for file in files:
                file: str = file # shut up pycharm

                ext = file.split(".")[-1]
                if ext == "css":
                    css.append(HtmlBuilder.prepare_dependency(file))
                elif ext == "js":
                    js.append(HtmlBuilder.prepare_dependency(file))
                elif ext == "html":
                    doc_content.append("\n<!-- " + name + " -->\n")
                    content = Templates.get_content(file)
                    attributes = options.get("attributes", {})

                    for opt_name, opt_value in attributes.items():
                        if opt_name == opt_name.upper():
                            key = "{{" + name.upper() + "_" + opt_name + "}}"
                            _options[key] = Replacer.replace(opt_value)
                            if opt_name.endswith("_MARKUP"):
                                _options[key] = markdown.markdown(_options[key])

                    _options.update(TemplateParser.parse_template(options))
                    content.replace(_options)
                    doc_content.append(content.data)
                else:
                    print(f"Unknown file extension: {ext} for {file}", file=sys.stderr)
                    exit(1)

        template = Templates.get_default_index()
        template.replace({
            "{{DOC_LANG}}": self.toml.get("language", "en"),
            "{{DOC_TITLE}}": self.toml.get("title", "NotStudio.cz WebGen Demo"),
            "{{DOC_DEPENDENCIES}}": "\n\t".join(dependency_content + css + js),
            "{{DOC_CONTENT}}": "\n".join(doc_content)
        })

        with open(out, "w") as f:
            f.write(template.data)
