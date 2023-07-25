import json
import logging
import os.path
import re
import string
import subprocess as sb
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Pattern

from binaryrts.util.fs import has_ext
from binaryrts.util.io import slice_file_into_chunks
from binaryrts.util.os import os_is_windows
from binaryrts.util.process import check_executable_exists

PROTOTYPE_PREFIX: str = "__proto__"


@dataclass()
class FunctionDefinition:
    file: Path
    signature: str
    start_line: int
    end_line: int
    namespace: Optional[str] = field(default=None)
    class_name: Optional[str] = field(default=None)
    properties: Optional[str] = field(default=None)

    @property
    def identifier(self) -> str:
        if CSourceCodeParser.is_c_file(self.file):
            return f"{self.namespace or ''}::{self.class_name or ''}::{self.signature}"
        return f"{self.signature}"

    @property
    def raw_function_name(self) -> str:
        """Returns the raw function name, excluding parameter information"""
        return self.signature.split("(")[0]

    @property
    def is_prototype(self) -> bool:
        return self.signature.startswith(PROTOTYPE_PREFIX)

    @property
    def has_parameters(self) -> bool:
        return "()" not in self.signature

    @property
    def is_test_function(self) -> bool:
        return self.raw_function_name in [
            "TEST",
            "TEST_F",
            "TEST_P",
            "TYPED_TEST",
            "TYPED_TEST_P",
            "FRIEND_TEST",
        ]

    def __eq__(self, o: "FunctionDefinition") -> bool:
        return self.file == o.file and self.identifier == o.identifier

    def __hash__(self) -> int:
        return hash(f"{self.identifier}")


@dataclass()
class NonFunctionalEntityDefinition:
    """
    Depicts non-functional entities such as macros or global/member/class variables.
    """

    file: Path
    name: str
    start_line: int
    end_line: int
    properties: Optional[str] = field(default=None)


@dataclass()
class TypeDefinition:
    """
    Depicts classes or structs.
    """

    file: Path
    name: str
    full_name: str  # concatenated name with template (specialization) parameters
    start_line: int
    end_line: int
    namespace: Optional[str] = field(default=None)


class CSourceCodeParser:
    C_LIKE_EXTENSIONS: List[str] = [
        ".c",
        ".cc",
        ".cxx",
        ".c++",
        ".cpp",
        ".ipp",
        ".tpp",
        ".tcc",
        ".inl",
        ".inc",
        ".h",
        ".hh",
        ".hpp",
        ".hxx",
        ".h++",
    ]
    C_TOKEN_PATTERN: str = r"[\s\;\*\%\|\&\~\^\+\-\/\>\<\,\(\)\!\.\=\?\{\}]"

    def __init__(
        self, include_prototypes: bool = False, use_cache: bool = False
    ) -> None:
        # cache that prevents analyzing the same file again
        self.ctags_output_cache: Dict[Path, str] = {}
        self.include_prototypes = include_prototypes
        self.use_cache = use_cache

    @classmethod
    def extract_raw_signature(cls, signature: str) -> str:
        raw_signature: str = "("
        parameters: List[str] = signature[1:-1].split(",")  # we exclude the ( and )
        for idx, param in enumerate(parameters):
            parts: List[str] = param.split(" ")
            raw_signature += (
                f"{',' if idx != 0 else ''}{''.join(parts[:-1])}"
                f"{re.sub(r'[^*|&]', '', parts[-1]) if len(parts) > 1 else parts[-1]}"
            )
        return (
            raw_signature + ")"
        )  # we could omit the `)` in case the last char is already an `)`

    @classmethod
    def is_c_file(cls, file: Path) -> bool:
        return has_ext(file, cls.C_LIKE_EXTENSIONS)

    @classmethod
    def get_raw_code(cls, file: Path, start: int, end: int) -> str:
        return cls.strip_whitespaces(
            cls.strip_comments(
                slice_file_into_chunks(
                    file,
                    [(start, end)],
                )[0]
            )
        )

    @classmethod
    def strip_comments(cls, code: str) -> str:
        def replacer(match):
            s = match.group(0)
            if s.startswith("/"):
                return " "  # note: a space and not an empty string
            else:
                return s

        pattern = re.compile(
            r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"',
            re.DOTALL | re.MULTILINE,
        )
        return re.sub(pattern, replacer, code)

    @classmethod
    def strip_whitespaces(cls, code: str) -> str:
        return code.translate(str.maketrans("", "", string.whitespace))

    def get_functions(self, file: Path) -> List[FunctionDefinition]:
        return self._get_functions_from_ctags(
            file=file,
        )

    def get_non_functional_entities(
        self, file: Path
    ) -> List[NonFunctionalEntityDefinition]:
        return self._get_non_functional_entities_from_ctags(file=file)

    def _get_non_functional_entities_from_ctags(
        self, file: Path
    ) -> List[NonFunctionalEntityDefinition]:
        non_functionals: List[NonFunctionalEntityDefinition] = []
        if file in self.ctags_output_cache:
            ctags_output = self.ctags_output_cache[file]
        else:
            ctags_output = ctags(file=file, include_prototypes=self.include_prototypes)
        if ctags_output:
            if self.use_cache:
                self.ctags_output_cache[file] = ctags_output
            for line in ctags_output.splitlines():
                try:
                    data: Dict = json.loads(line)
                    ctags_output_line: CTagsJsonOutputLine = CTagsJsonOutputLine(**data)
                    if (
                        ctags_output_line.kind == "macro"
                        or ctags_output_line.kind == "member"
                        or ctags_output_line.kind == "variable"
                        or ctags_output_line.kind == "enumerator"
                        or ctags_output_line.kind == "externvar"
                        or (ctags_output_line.kind == "function" and ctags_output_line.is_const_expr)
                    ):
                        properties: str = ctags_output_line.kind
                        if ctags_output_line.properties is not None:
                            properties += ctags_output_line.properties
                        non_functionals.append(
                            NonFunctionalEntityDefinition(
                                file=Path(ctags_output_line.path).resolve(),
                                name=ctags_output_line.name,
                                start_line=ctags_output_line.line,
                                end_line=ctags_output_line.end
                                or ctags_output_line.line,
                                properties=properties,
                            )
                        )
                except Exception as e:
                    logging.warning(
                        f"Failed to decode JSON output of ctags line {line} with exception: {e}"
                    )
        return non_functionals

    def _get_functions_from_ctags(self, file: Path) -> List[FunctionDefinition]:
        functions: List[FunctionDefinition] = []
        type_defs: Dict[str, List[TypeDefinition]] = {}  # lookup by type name
        if file in self.ctags_output_cache:
            ctags_output = self.ctags_output_cache[file]
        else:
            ctags_output = ctags(file=file, include_prototypes=self.include_prototypes)
        if ctags_output:
            if self.use_cache:
                self.ctags_output_cache[file] = ctags_output
            for line in ctags_output.splitlines():
                try:
                    data: Dict = json.loads(line)
                    ctags_output_line: CTagsJsonOutputLine = CTagsJsonOutputLine(**data)
                    type_def: Optional[TypeDefinition] = ctags_output_line.to_type_def(
                        file=file
                    )
                    func_def: Optional[
                        FunctionDefinition
                    ] = ctags_output_line.to_func_def(file=file)
                    if type_def is not None:
                        if type_def.name not in type_defs:
                            type_defs[type_def.name] = []
                        type_defs[type_def.name].append(type_def)
                    elif func_def is not None:
                        functions.append(func_def)
                except Exception as e:
                    logging.debug(
                        f"Failed to decode JSON output of ctags line {line} with exception: {e}"
                    )
            # Look up wrapping types for functions and adjust to full type names.
            # This addresses ctags' limitations to resolve the correct type of the function.
            # However, only functions which are placed inside the body of a type definition are considered here.
            # Beyond those kinds, it is basically an undecidable problem without more compiler magic.
            for function in functions:
                if function.class_name is not None and function.class_name in type_defs:
                    for type_def in type_defs[function.class_name]:
                        if (
                            type_def.start_line
                            <= function.start_line
                            <= type_def.end_line
                        ):
                            function.class_name = type_def.full_name
                            break
        return functions


@dataclass()
class CTagsJsonOutputLine:
    _type: str
    name: str
    path: str
    line: int
    kind: str
    end: Optional[int] = field(default=None)
    access: Optional[str] = field(default=None)
    file: Optional[bool] = field(default=None)
    scope: Optional[str] = field(default=None)
    signature: Optional[str] = field(default=None)
    scopeKind: Optional[str] = field(default=None)
    properties: Optional[str] = field(default=None)
    extras: Optional[str] = field(default=None)
    template: Optional[str] = field(default=None)
    inherits: Optional[str] = field(default=None)
    captures: Optional[str] = field(default=None)
    specialization: Optional[str] = field(default=None)

    @property
    def is_const_expr(self) -> bool:
        return self.properties is not None and ('constexpr' in self.properties or 'consteval' in self.properties)

    def to_type_def(self, file: Optional[Path] = None) -> Optional[TypeDefinition]:
        type_def: Optional[TypeDefinition] = None
        if (
            (self.kind == "class" or self.kind == "struct")
            and (self.end is not None)
            and (self.template is not None or self.specialization is not None)
        ):
            type_name: str = self.name
            type_full_name: str = self.name
            if self.template is not None:
                type_full_name += self.template
            if self.specialization is not None:
                type_full_name += self.specialization
            namespace: Optional[str] = None
            if self.scope is not None:
                namespace_class_fragments: List[str] = self.scope.split("::")
                if len(namespace_class_fragments) > 0:
                    namespace = "::".join(
                        [
                            "anon" if "__anon" in ns_fragment else ns_fragment
                            for ns_fragment in namespace_class_fragments
                        ]
                    )
            type_def = TypeDefinition(
                file=file or Path(self.path).resolve(),
                name=type_name,
                full_name=type_full_name,
                start_line=self.line,
                end_line=self.end,
                namespace=namespace,
            )
        return type_def

    def to_func_def(self, file: Optional[Path] = None) -> Optional[FunctionDefinition]:
        function_def: Optional[FunctionDefinition] = None
        if self.kind == "function" or self.kind == "prototype":
            signature: str = self.name
            if signature.startswith("__anon"):
                signature = "lambda"
                # there will most likely be no lambda functions outside a function scope,
                # where they'll be handled by their parent function;
                # still, we check here to make sure, we don't omit any relevant lambda functions
                if self.scopeKind is not None and self.scopeKind == "function":
                    return function_def
            if self.kind == "prototype":
                signature = f"{PROTOTYPE_PREFIX}{signature}"
            if self.template is not None:
                signature += self.template
            if self.specialization is not None:
                signature += self.specialization
            if self.signature is not None:
                signature += CSourceCodeParser.extract_raw_signature(self.signature)

            namespace: Optional[str] = None
            class_name: Optional[str] = None
            if self.scope is not None:
                namespace_class_fragments: List[str] = self.scope.split("::")
                if self.scopeKind is not None and (
                    self.scopeKind == "class" or self.scopeKind == "struct"
                ):
                    class_name = namespace_class_fragments.pop()
                if len(namespace_class_fragments) > 0:
                    namespace = "::".join(
                        [
                            "anon" if "__anon" in ns_fragment else ns_fragment
                            for ns_fragment in namespace_class_fragments
                        ]
                    )

            properties: Optional[str] = None
            if self.properties is not None:
                properties = self.properties

            function_def = FunctionDefinition(
                file=file or Path(self.path).resolve(),
                signature=signature,
                start_line=self.line,
                end_line=self.end or self.line,
                namespace=namespace,
                class_name=class_name,
                properties=properties,
            )
        return function_def


def ctags(file: Path, include_prototypes: bool = False) -> Optional[str]:
    """
    Calls `ctags` executable to parse functions/macros/globals from C/C++ source file.
    """
    output: Optional[str] = None
    ctags_executable_default: Path = (
        (Path(os.path.dirname(sys.modules["binaryrts"].__file__)) / "bin" / "ctags")
        if os_is_windows()
        else Path("/usr/local/bin/ctags")
    )
    ctags_executable: Optional[str] = check_executable_exists(
        program=ctags_executable_default.resolve().__str__()
    )

    if ctags_executable and file.exists():
        command_parts: List[str] = [
            f'"{ctags_executable}"',  # need the quotes to support paths with spaces
            '--fields-all="*"',
            "--fields-c++=-{macrodef}",
            "--fields-c=-{macrodef}",
            "--fields=-Prtl",
            '-D "AUTO_REGISTER_SERVICE(...)=namespace{void AUTO_REGISTER_SERVICE(__VA_ARGS__){}}"',
            # IVU-specific hack for unconventional macro usage
        ]
        if include_prototypes:
            command_parts += [
                "--kinds-c=+p",
                "--kinds-c++=+p",
            ]
        command_parts += [
            "--output-format=json",
            "--language-force=c++",  # fix problem with .ipp files by forcing C++ parser
            f'"{file.absolute().__str__()}"',
        ]
        command: str = " ".join(command_parts)
        logging.debug(f"Calling ctags with: {command}")
        process: sb.CompletedProcess = sb.run(
            command,
            text=True,
            shell=True,
            capture_output=True,
            timeout=60 * 10,  # wait max. 10 minutes for results
        )
        if process.returncode != 0:
            raise Exception(
                f"ctags failed with output: {process.stdout} {process.stderr}"
            )
        output = process.stdout
    else:
        raise Exception(
            "Missing ctags executable!"
            f"Maybe you didn't add the ctags location to your PATH or "
            f"the executable is not inside {(Path(os.path.dirname(sys.modules['binaryrts'].__file__)) / 'bin').absolute()}."
        )
    return output


@dataclass()
class NonFunctionalCallSite:
    path: Path
    line_no: int
    name: Optional[str] = field(
        default=None
    )  # if a name for the call site is available (e.g., a function name)

    @classmethod
    def from_cscope(
        cls, line: str, file_relative_to: Optional[Path] = None
    ) -> "NonFunctionalCallSite":
        line_fragments: List[str] = line.split()
        path, name, line_no = (
            line_fragments[0],
            line_fragments[1],
            int(line_fragments[2]),
        )
        return cls(
            path=(
                Path(path).resolve().relative_to(file_relative_to.resolve())
                if file_relative_to
                else Path(path)
            ),
            line_no=line_no,
            name=name,
        )


class NonFunctionalCallAnalyzer:
    def __init__(
        self,
        root_dir: Path,
        use_cscope: bool = False,
        use_grep: bool = False,
        use_findstr: bool = False,
    ) -> None:
        self.root_dir = root_dir
        self.use_cscope = use_cscope
        self.use_grep = use_grep
        self.use_findstr = use_findstr

    def _get_call_sites_from_cscope(
        self, symbol_name: str, file_relative_to: Optional[Path] = None
    ) -> List[NonFunctionalCallSite]:
        call_sites: List[NonFunctionalCallSite] = []
        output: Optional[str] = cscope(symbol_name=symbol_name, root_dir=self.root_dir)
        if output:
            call_sites = [
                NonFunctionalCallSite.from_cscope(
                    line=line, file_relative_to=file_relative_to
                )
                for line in output.splitlines()
            ]
        return call_sites

    @staticmethod
    def _parse_call_sites(
        symbol_name: str, output: str, file_relative_to: Optional[Path] = None
    ) -> List[NonFunctionalCallSite]:
        call_sites: List[NonFunctionalCallSite] = []
        try:
            # we filter the call sites to only those, that do not subsume the queried symbol name
            pattern: Pattern = re.compile(
                rf"{CSourceCodeParser.C_TOKEN_PATTERN}{symbol_name}{CSourceCodeParser.C_TOKEN_PATTERN}"
            )
            for line in output.splitlines():
                parts = line.split(":")
                if len(parts) < 3:
                    continue
                # we expect the path to be absolute on Windows, including the drive name (e.g., "C:")
                path_fragment: str = (
                    ":".join(parts[:2]) if os_is_windows() else parts[0]
                )
                line_fragment: str = parts[2] if os_is_windows() else parts[1]
                filepath: Path = (
                    Path(path_fragment)
                    .resolve()
                    .relative_to(file_relative_to.resolve())
                    if file_relative_to
                    else Path(path_fragment).resolve()
                )
                line_no: int = int(line_fragment)
                match: str = (
                    ":".join(parts[3:]) if os_is_windows() else ":".join(parts[2:])
                )
                if (
                    re.search(pattern, match) is not None
                    and line_no > 0
                    and filepath.is_file()
                ):
                    call_sites.append(
                        NonFunctionalCallSite(
                            path=filepath,
                            line_no=line_no,
                        )
                    )
        except Exception as e:
            raise Exception(f"Failed to parse call sites from output {output}: {e}")
        return call_sites

    def _get_call_sites_from_grep(
        self, symbol_name: str, file_relative_to: Optional[Path] = None
    ) -> List[NonFunctionalCallSite]:
        call_sites: List[NonFunctionalCallSite] = []
        grep_executable_default: Path = Path("/usr/bin/grep")
        grep_executable: Optional[str] = check_executable_exists(
            program=grep_executable_default.resolve().__str__()
        )
        if grep_executable:
            command: List[str] = [
                f"{grep_executable}",
                "--recursive",
                "--with-filename",
                "--line-number",
                "--binary-files=without-match",
                "--no-messages",
                "--fixed-strings",
            ]
            command += [
                f'--include="*{ext}"' for ext in CSourceCodeParser.C_LIKE_EXTENSIONS
            ]
            command += [f'"{symbol_name}"', self.root_dir.absolute().__str__()]
            process: sb.CompletedProcess = sb.run(
                " ".join(command),
                text=True,
                shell=True,
                capture_output=True,
                timeout=60 * 5,  # wait max. 5 minutes for results
            )
            if process.returncode != 0:
                raise Exception(
                    f"Failed to run grep command {command}: {process.stdout} {process.stderr}"
                )
            else:
                call_sites = self._parse_call_sites(
                    symbol_name=symbol_name,
                    output=process.stdout,
                    file_relative_to=file_relative_to,
                )
        return call_sites

    def _get_call_sites_from_findstr(
        self, symbol_name: str, file_relative_to: Optional[Path] = None
    ) -> List[NonFunctionalCallSite]:
        calling_functions: List[NonFunctionalCallSite] = []

        # collect all C-like files
        file_paths: List[str] = []
        for root, dirs, files in os.walk(self.root_dir.absolute()):
            for file in files:
                filepath: str = os.path.join(root, file)
                if CSourceCodeParser.is_c_file(Path(file)):
                    file_paths.append(f"{filepath}")

        if len(file_paths) > 0:
            # invoke findstr
            input_file: Path = Path("findstr.log").absolute()
            input_file.write_text("\n".join(file_paths))

            findstr_executable_default: Path = Path(r"C:\Windows\System32\findstr.exe")
            findstr_executable: Optional[str] = check_executable_exists(
                program=findstr_executable_default.resolve().__str__()
            )
            if findstr_executable:
                command: str = " ".join(
                    [
                        f'"{findstr_executable}"',
                        f"/f:{input_file.__str__()}",
                        "/p",  # skip non-printable files (e.g. binaries)
                        "/n",  # print every matching line number
                        "/l",  # no regex, but literal matches
                        f'"{symbol_name}"',
                    ]
                )
                process: sb.CompletedProcess = sb.run(
                    command,
                    text=True,
                    shell=True,
                    capture_output=True,
                    timeout=60 * 5,  # wait max. 5 minutes for results
                )
                if process.returncode != 0:
                    raise Exception(
                        f"Failed to run findstr command {command}: {process.stdout} {process.stderr}"
                    )
                else:
                    calling_functions = self._parse_call_sites(
                        symbol_name=symbol_name,
                        output=process.stdout,
                        file_relative_to=file_relative_to,
                    )

            if input_file.exists():
                input_file.unlink()

        return calling_functions

    def get_call_sites(
        self, symbol_name: str, file_relative_to: Optional[Path] = None
    ) -> List[NonFunctionalCallSite]:
        calling_functions: List[NonFunctionalCallSite] = []
        if self.use_cscope:
            calling_functions = self._get_call_sites_from_cscope(
                symbol_name=symbol_name, file_relative_to=file_relative_to
            )
        elif self.use_findstr:
            calling_functions = self._get_call_sites_from_findstr(
                symbol_name=symbol_name, file_relative_to=file_relative_to
            )
        elif self.use_grep:
            calling_functions = self._get_call_sites_from_grep(
                symbol_name=symbol_name, file_relative_to=file_relative_to
            )
        else:
            pattern: Pattern = re.compile(
                rf"{CSourceCodeParser.C_TOKEN_PATTERN}{symbol_name}{CSourceCodeParser.C_TOKEN_PATTERN}"
            )
            for root, dirs, files in os.walk(self.root_dir.absolute()):
                for file in files:
                    filepath: Path = Path(root) / file
                    if CSourceCodeParser.is_c_file(filepath):
                        try:
                            with filepath.open("r") as fp:
                                for idx, line in enumerate(fp):
                                    if re.search(pattern, line) is not None:
                                        filepath = (
                                            filepath.resolve().relative_to(
                                                file_relative_to.resolve()
                                            )
                                            if file_relative_to
                                            else filepath.resolve()
                                        )
                                        calling_functions.append(
                                            NonFunctionalCallSite(
                                                path=filepath, line_no=idx + 1
                                            )
                                        )
                        except Exception as e:
                            logging.error(
                                f"Could not search for call sites in {filepath}: {e}"
                            )

        return calling_functions


def cscope(
    symbol_name: str,
    root_dir: Path,
) -> Optional[str]:
    """
    Calls `cscope` executable to get cross-file references from C/C++ source files.
    """
    output: Optional[str] = None

    # collect file paths
    file_paths: List[str] = []
    for root, dirs, files in os.walk(root_dir.absolute()):
        for file in files:
            filepath: str = os.path.join(root, file)
            if CSourceCodeParser.is_c_file(Path(file)):
                file_paths.append(f'"{filepath}"')
    if len(file_paths) > 0:
        input_file: Path = Path("cscope.files")
        input_file.write_text("\n".join(file_paths))

        cscope_executable_default: Path = (
            (
                Path(os.path.dirname(sys.modules["binaryrts"].__file__))
                / "bin"
                / "cscope"
            )
            if os_is_windows()
            else Path("/usr/local/bin/cscope")
        )
        cscope_executable: Optional[str] = check_executable_exists(
            program=cscope_executable_default.resolve().__str__()
        )
        if cscope_executable:
            command: str = " ".join(
                [
                    f'"{cscope_executable}"',
                    "-c",  # Use only ASCII chars in cross-reference file, i.e., do not compress the data.
                    "-L",  # Do a single search with line-oriented output.
                    "-3",  # Find functions calling this symbol.
                    symbol_name,
                ]
            )
            process: sb.CompletedProcess = sb.run(
                command,
                text=True,
                shell=True,
                capture_output=True,
                timeout=60 * 10,  # wait max. 10 minutes for results
            )
            output = process.stdout
            if process.returncode != 0:
                raise Exception(
                    f"Failed to run cscope command {command}: {process.stdout} {process.stderr}"
                )

        if input_file.exists():
            input_file.unlink()
        if Path("cscope.out").exists():
            Path("cscope.out").unlink()

    return output
