"""
This script will update a provided MSVC project properties file to include
and statically link the BinaryRTS GoogleTest event listener static library.
"""
import argparse
import os.path
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Tuple, Optional

DEBUG: bool = True

BINARY_RTS_LISTENER_LIB: str = "binary_rts_listener.lib"
BINARY_RTS_LISTENER_HEADER: str = "test_listener.h"


def get_tree_root_and_ns(prop_file: Path) -> Tuple[ET.ElementTree, ET.Element, str]:
    def _namespace(el: ET.Element) -> str:
        m = re.match(r"{.*}", el.tag)
        return m.group(0)[1:-1] if m else ""

    # get ns from xml
    tree = ET.parse(prop_file)
    ns = _namespace(tree.getroot())
    # set default namespace
    ET.register_namespace("", ns)
    # re-parse xml
    tree = ET.parse(prop_file)
    root = tree.getroot()
    return tree, root, ns


def find_tag_in_element_with_ns(el: ET.Element, tag: str, ns: str) -> Optional[ET.Element]:
    return el.find(f"{{{ns}}}{tag}")


def parse_arguments() -> argparse.Namespace:
    """
    Define and parse program arguments.

    :return: arguments captured in object.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-file",
        "-i",
        required=True,
        help="Path to MSVC project properties file.",
    )
    parser.add_argument(
        "--listener-lib",
        default=os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)),
                                             "..",
                                             "out",
                                             "build",
                                             "x64-Release",
                                             "binaryrts",
                                             "listener")),
        help="Path to BinaryRTS test listener static library.",
    )
    parser.add_argument(
        "--listener-include",
        default=os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)),
                                             "..",
                                             "binaryrts",
                                             "listener")),
        help="Path to BinaryRTS test listener headers.",
    )
    parser.add_argument(
        "--compiler-opts",
        default="/Ob0",  # by default, we only disable inlining
        help="Additional compiler options passed to ClCompile (might be necessary to make BinaryRTS work, "
             "e.g., prevent inlining).",
    )
    return parser.parse_args()


def main():
    # Parse arguments
    args = parse_arguments()

    print(f"Starting BinaryRTS MSVC Build Patcher with {args}...")

    prop_file: Path = Path(args.input_file)
    listener_lib_dir: Path = Path(args.listener_lib)
    listener_include_dir: Path = Path(args.listener_include)

    assert DEBUG or (prop_file.exists() and prop_file.is_file()), \
        "Provide valid MSVC properties file!"
    assert DEBUG or (listener_lib_dir.exists() and listener_lib_dir.is_dir() and (
            listener_lib_dir / BINARY_RTS_LISTENER_LIB).exists()), \
        "Provide valid directory to BinaryRTS listener static library!"
    assert DEBUG or (listener_include_dir.exists() and listener_include_dir.is_dir() and (
            listener_include_dir / BINARY_RTS_LISTENER_HEADER).exists()), \
        "Provide valid directory to BinaryRTS listener includes!"

    tree, root, ns = get_tree_root_and_ns(prop_file)

    for property_group in root:
        cl_compile_element: Optional[ET.Element] = find_tag_in_element_with_ns(el=property_group, tag="ClCompile",
                                                                               ns=ns)
        if cl_compile_element:
            include_exists: bool = False
            for prop in cl_compile_element:
                if "AdditionalIncludeDirectories" in prop.tag:
                    include_exists = True
                    prop.text = f"{listener_include_dir.absolute()};{prop.text}"
            if not include_exists:
                new_node: ET.Element = ET.Element("AdditionalIncludeDirectories")
                new_node.text = f"{listener_include_dir.absolute()};%(AdditionalIncludeDirectories)"
                cl_compile_element.append(new_node)

            if args.compiler_opts and args.compiler_opts != "":
                compiler_opts_exists: bool = False
                for prop in cl_compile_element:
                    if "AdditionalOptions" in prop.tag:
                        compiler_opts_exists = True
                        prop.text = f"{prop.text} {args.compiler_opts}"
                    if "InlineFunctionExpansion" in prop.tag and "/Ob0" in args.compiler_opts:
                        cl_compile_element.remove(prop)
                if not compiler_opts_exists:
                    new_node: ET.Element = ET.Element("AdditionalOptions")
                    new_node.text = f"{args.compiler_opts} %(AdditionalOptions)"
                    cl_compile_element.append(new_node)

        link_element: Optional[ET.Element] = find_tag_in_element_with_ns(el=property_group, tag="Link",
                                                                         ns=ns)
        if link_element:
            additional_lib_dirs_exists: bool = False
            additional_deps_exists: bool = False
            for prop in link_element:
                if "AdditionalLibraryDirectories" in prop.tag:
                    additional_lib_dirs_exists = True
                    prop.text = f"{listener_lib_dir.absolute()};{prop.text}"
                if "AdditionalDependencies" in prop.tag:
                    additional_deps_exists = True
                    prop.text = f"{BINARY_RTS_LISTENER_LIB};{prop.text}"
            if not additional_lib_dirs_exists:
                new_node: ET.Element = ET.Element("AdditionalLibraryDirectories")
                new_node.text = f"{listener_lib_dir.absolute()};%(AdditionalLibraryDirectories)"
                link_element.append(new_node)
            if not additional_deps_exists:
                new_node: ET.Element = ET.Element("AdditionalDependencies")
                new_node.text = f"{BINARY_RTS_LISTENER_LIB};%(AdditionalDependencies)"
                link_element.append(new_node)

        tree.write(prop_file, encoding='utf-8', xml_declaration=True)


if __name__ == '__main__':
    main()
