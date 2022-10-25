import argparse
import logging
import os
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from shlex import split
from typing import List, Dict

import frida
from frida.core import Session, Script, ScriptExports
from frida_tools.application import Reactor

logging.basicConfig(
    format="[%(process)d] %(asctime)s: %(filename)s - %(levelname)s: %(message)s",
    level=logging.INFO,
    stream=sys.stdout,
)

# locate agent JavaScript file
FRIDA_AGENT_JS: Path
if "binaryrts_frida" in sys.modules:
    FRIDA_AGENT_JS = (
            Path(os.path.dirname(sys.modules["binaryrts_frida"].__file__))
            / "agent"
            / "_agent.js"
    )
else:
    FRIDA_AGENT_JS = (
            Path(os.path.abspath(os.path.dirname(__file__))) / "agent" / "_agent.js"
    )

PIPE_REPLACEMENT_CHAR: str = ";"
FUNCTIONS_FILE_EXT: str = ".functions"
FUNCTIONS_LOOKUP_FILE_EXT: str = ".functions.lookup"
DEBUG_INFO_SEP: str = "\t"


@dataclass()
class FunctionDebugInfo:
    offset: str
    file: str
    name: str
    line: str

    @classmethod
    def from_line(cls, line: str) -> "FunctionDebugInfo":
        offset, file, name, line_no = line.strip().split(DEBUG_INFO_SEP)
        return cls(offset, file, name, line_no)


class FridaApplication(object):
    """
    Inspired by: https://github.com/frida/frida-python/blob/main/examples/child_gating.py
    """

    def __init__(
            self,
            output_file: Path,
            included_modules: List[Path],
            debug: bool = False
    ):
        self._stop_requested = threading.Event()
        self._reactor = Reactor(
            run_until_return=lambda reactor: self._stop_requested.wait()
        )

        self._device = frida.get_local_device()
        self._sessions = set()

        self._output_file: Path = output_file
        self._debug = debug
        self._included_modules = included_modules

        # construct function map from .functions file
        self._modules = dict()
        self._function_map = dict()
        for module in self._included_modules:
            with (module.parent / f"{module.name}{FUNCTIONS_FILE_EXT}").open("r") as fp:
                functions = set()
                for line in fp:
                    functions.add(line.strip())
                self._function_map[module.name] = list(functions)
                self._modules[module.name] = list()

    def run_command(self, command: str):
        self._reactor.schedule(lambda: self._start(command))
        self._reactor.run()

    def run_process(self, process_name: str):
        pid: int = -1
        for proc in self._device.enumerate_processes():
            if process_name in [str(proc.pid), proc.name]:
                # we're simply using the first match
                pid = proc.pid
                logging.debug(
                    f"Found process {proc.name} ({proc.pid}) for {process_name}."
                )
                break
        if pid == -1:
            logging.error(f"Could not find process identifier {process_name}.")
            self._terminate()
        else:
            self._reactor.schedule(lambda: self._instrument(pid))
            self._reactor.run()

    def _start(self, command: str):
        try:
            pid = self._device.spawn(split(command))
            self._instrument(pid, True)
        except Exception as e:
            logging.error(f"Failed to spawn process for {command}: {e}")
            self._terminate()

    def _terminate(self):
        self._dump_output()
        self._stop_requested.set()

    def _dump_output(self):
        with self._output_file.open("w+") as fp:
            for key, val in self._modules.items():
                if len(val) == 0:
                    continue
                module_path: Path = [mod_path for mod_path in self._included_modules if key in mod_path.__str__()][0]
                debug_info_map: Dict[str, FunctionDebugInfo] = {}
                with (module_path.parent / f"{module_path.name}{FUNCTIONS_LOOKUP_FILE_EXT}").open("r") as lookup_fp:
                    for line in lookup_fp:
                        debug_info = FunctionDebugInfo.from_line(line)
                        debug_info_map[debug_info.offset] = debug_info
                fp.write(f"{key}{DEBUG_INFO_SEP}{module_path.__str__()}\n")
                for func in val:
                    debug_info = debug_info_map[func]
                    fp.write(f"{DEBUG_INFO_SEP}+{func}"
                             f"{DEBUG_INFO_SEP}{debug_info.file}"
                             f"{DEBUG_INFO_SEP}{debug_info.name}"
                             f"{DEBUG_INFO_SEP}{debug_info.line}\n")

    def _stop_if_idle(self):
        if len(self._sessions) == 0:
            self._terminate()

    def _on_detached(self, pid, session, reason):
        logging.debug("detached: pid={}, reason='{}'".format(pid, reason))
        self._sessions.remove(session)
        if reason == "process-replaced":
            self._instrument(pid)
        self._reactor.schedule(
            self._stop_if_idle, delay=0.01
        )

    def _on_message(self, pid, message: Dict):
        if "payload" in message:
            payload = message["payload"]
            if "coverage" in payload:
                self._on_coverage(payload["coverage"])

    def _on_coverage(self, coverage_map: Dict[str, List[int]]):
        for module_path, covered_funcs in coverage_map.items():
            for func in covered_funcs:
                self._modules[module_path].append(func)

    def _instrument(self, pid, resume=False):
        logging.debug("Attaching to PID={}".format(pid))
        session: Session = self._device.attach(pid)

        # load and inject agent script
        script: Script = session.create_script(
            FRIDA_AGENT_JS.read_text(encoding="utf-8")
        )
        script.on(
            "message",
            lambda message, data: self._reactor.schedule(
                lambda: self._on_message(pid, message)
            ),
        )
        script.load()
        agent: ScriptExports = script.exports
        agent.setup_agent(self._function_map, self._debug)

        session.on(
            "detached",
            lambda reason: self._reactor.schedule(
                lambda: self._on_detached(pid, session, reason)
            ),
        )

        if resume:
            self._device.resume(pid)
            logging.debug(f"Resuming execution of PID={pid}")

        self._sessions.add(session)
        logging.debug(f"Storing session to frida agent")

        # creating output file; this might notify other processes waiting for the file to be available
        self._output_file.touch()
        logging.debug(f"Created output file at {self._output_file}")


def parse_arguments() -> argparse.Namespace:
    """
    Define and parse program arguments.
    :return: arguments captured in object.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--target",
        "-t",
        help="Target executable to spawn.",
    )
    parser.add_argument(
        "--process",
        "-p",
        help="Process identifier or name to be traced.",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output coverage file",
        default=f"{os.getpid()}_{time.time_ns() / 1_000_000}.log",
    )
    parser.add_argument(
        "--modules",
        "-m",
        nargs="*",
        required=True,
        help="List of module (DLL) paths to be included. "
             "These modules must have a `.function` and  `.function.lookup` file sitting in the same directory. "
             "If argument is a filepath, will search for newline-separated module paths.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="Whether to print verbose debugging info.",
    )
    return parser.parse_args()


def main():
    args = parse_arguments()
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    logging.debug(f"Called with arguments: {args.__dict__}")

    if args.process is None and args.target is None:
        logging.error("Missing process identifier or target executable.")
        exit(1)

    output_file: Path = Path(args.output).resolve()
    if output_file.exists():
        output_file.unlink()
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # collect included modules (arg can be filepath or string)
    included_modules: List[Path] = []

    def _validate_module(mod: Path):
        assert (
            (mod.exists() and (
                    mod.parent / f"{mod.name}{FUNCTIONS_FILE_EXT}").exists() and (
                     mod.parent / f"{mod.name}{FUNCTIONS_LOOKUP_FILE_EXT}").exists())
            , f"Invalid module path {mod}"
        )

    if args.modules is not None:
        for module in args.modules:
            if Path(module).is_file() and not os.path.splitext(Path(module).name)[-1].lower() in [".dll", ".exe"]:
                for line in Path(module).read_text().splitlines():
                    module_path: Path = Path(line).resolve()
                    _validate_module(module_path)
                    included_modules.append(module_path)
            else:
                module_path: Path = Path(module).resolve()
                _validate_module(module_path)
                included_modules.append(module_path)

    assert len(included_modules) > 0, "No modules found"

    app = FridaApplication(
        output_file=output_file,
        # in cmd.exe, the pipe operator is sometimes not working as expected; therefore, we use a replacement character.
        included_modules=included_modules,
        debug=args.debug
    )

    if args.target is not None:
        app.run_command(args.target)
    else:
        app.run_process(args.process)


if __name__ == "__main__":
    main()
