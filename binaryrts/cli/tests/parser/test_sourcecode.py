import os
import unittest
from pathlib import Path
from typing import List

from binaryrts.parser.sourcecode import CSourceCodeParser, FunctionDefinition

RESOURCES_DIR: Path = Path(os.path.dirname(__file__)) / "resources"
SOURCE_FILE: Path = RESOURCES_DIR / "main.cpp"
HEADER_FILE: Path = RESOURCES_DIR / "lib.h"
COMPLEX_FILE: Path = RESOURCES_DIR / "complex.cpp"


class SourceCodeParserTestCase(unittest.TestCase):
    def test_get_functions(self):
        parser: CSourceCodeParser = CSourceCodeParser()
        actual: List[FunctionDefinition] = parser.get_functions(file=SOURCE_FILE)
        expected: List[FunctionDefinition] = [
            FunctionDefinition(
                file=SOURCE_FILE,
                signature="CustomPair(T,T)",
                start_line=19,
                end_line=22,
                namespace="templates",
                class_name="CustomPair<class T>",
                properties=None,
            ),
            FunctionDefinition(
                file=SOURCE_FILE,
                signature="GetMax()",
                start_line=25,
                end_line=28,
                namespace="templates",
                class_name="CustomPair<class T>",
                properties=None,
            ),
            FunctionDefinition(
                file=SOURCE_FILE,
                signature="GetMax<typename T>(T,T)",
                start_line=33,
                end_line=35,
                namespace="templates",
                properties=None,
            ),
            FunctionDefinition(
                file=SOURCE_FILE,
                signature="bar(int)",
                start_line=54,
                end_line=55,
                namespace=None,
                class_name="C",
                properties=None,
            ),
            FunctionDefinition(
                file=SOURCE_FILE,
                signature="baz()",
                start_line=57,
                end_line=59,
                class_name="C",
                properties=None,
            ),
            FunctionDefinition(
                file=SOURCE_FILE,
                signature="foo()",
                start_line=41,
                end_line=43,
                class_name="A",
                properties="virtual",
            ),
            FunctionDefinition(
                file=SOURCE_FILE,
                signature="foo()",
                start_line=50,
                end_line=52,
                class_name="C",
                properties="override,virtual",
            ),
            FunctionDefinition(
                file=SOURCE_FILE,
                signature="main()",
                start_line=82,
                end_line=92,
            ),
            FunctionDefinition(
                file=SOURCE_FILE,
                signature="weird_add(int,int)",
                start_line=8,
                end_line=11,
            ),
            FunctionDefinition(
                file=SOURCE_FILE,
                signature="foo()",
                start_line=69,
                end_line=69,
                class_name="Foo<typename X,typename Y>",
                namespace="Base"
            ),
            FunctionDefinition(
                file=SOURCE_FILE,
                signature="bar()",
                start_line=75,
                end_line=75,
                class_name="Bar<typename Z,typename W>",
                namespace="Base"
            ),
            FunctionDefinition(
                file=SOURCE_FILE,
                signature="foo<>()",
                start_line=79,
                end_line=79,
                class_name="Foo",
                namespace="Base"
            ),
        ]
        self.assertSetEqual(set(expected), set(actual))

    def test_get_functions_complex(self):
        parser: CSourceCodeParser = CSourceCodeParser()
        actual: List[FunctionDefinition] = parser.get_functions(file=COMPLEX_FILE)
        expected: List[FunctionDefinition] = [
            FunctionDefinition(
                file=COMPLEX_FILE,
                signature="foo()",
                start_line=13,
                end_line=15,
                namespace="bar",
                class_name="X<><int>",
                properties=None,
            ),
            FunctionDefinition(
                file=COMPLEX_FILE,
                signature="bar()",
                start_line=20,
                end_line=22,
                namespace="bar::baz",
                class_name="Z",
                properties='static'
            ),
            FunctionDefinition(
                file=COMPLEX_FILE,
                signature="foo()",
                start_line=26,
                end_line=29,
                namespace="bar",
                class_name=None,
                properties=None,
            ),
            FunctionDefinition(
                file=COMPLEX_FILE,
                signature="f(T)",
                start_line=37,
                end_line=37,
                namespace="foo",
                class_name="A<typename T>",
                properties=None,
            ),
            FunctionDefinition(
                file=COMPLEX_FILE,
                signature="g<typename T>(T)",
                start_line=48,
                end_line=48,
                namespace="foo",
                class_name="A",
                properties='scopespecialization,specialization'
            ),
            FunctionDefinition(
                file=COMPLEX_FILE,
                signature="f(int)",
                start_line=56,
                end_line=56,
                namespace="foo",
                class_name="A",
                properties='scopespecialization,specialization',
            ),
            FunctionDefinition(
                file=COMPLEX_FILE,
                signature="f()",
                start_line=64,
                end_line=64,
                namespace="foo::A",
                class_name="B",
                properties='scopespecialization,specialization',
            ),
            FunctionDefinition(
                file=COMPLEX_FILE,
                signature="g()",
                start_line=71,
                end_line=73,
                namespace="foo::A",
                class_name="C<class U><char>",
                properties=None,
            ),
            FunctionDefinition(
                file=COMPLEX_FILE,
                signature="f<class U>()",
                start_line=79,
                end_line=79,
                namespace="foo::A",
                class_name="C",
                properties='scopespecialization,specialization'
            ),
            FunctionDefinition(
                file=COMPLEX_FILE,
                signature="main()",
                start_line=82,
                end_line=97,
                namespace=None,
                class_name=None,
                properties=None,
            ),
        ]
        self.assertSetEqual(set(expected), set(actual))

    def test_get_functions_header(self):
        parser: CSourceCodeParser = CSourceCodeParser()
        actual: List[FunctionDefinition] = parser.get_functions(file=HEADER_FILE)
        expected: List[FunctionDefinition] = [
            FunctionDefinition(
                file=HEADER_FILE,
                signature="weird_add(int,int)",
                start_line=1,
                end_line=4,
            ),
        ]
        self.assertSetEqual(set(expected), set(actual))

    def test_strip_comments(self):
        self.assertEqual(
            """ \nint main() {\n\treturn 0;  \n}""",
            CSourceCodeParser.strip_comments(
                """// some line comment\nint main() {\n\treturn 0; // more lines\n}""".strip()
            ),
        )
        self.assertEqual(
            """ \nint main() {\n\treturn 0;  \n}""",
            CSourceCodeParser.strip_comments(
                """/* some line comment */\nint main() {\n\treturn 0; /* more lines */\n}""".strip()
            ),
        )
        self.assertEqual(
            """int main() {\n\treturn 0;  \n}""",
            CSourceCodeParser.strip_comments(
                """/* some line \n * comment \n * and more */\nint main() {\n\treturn 0; /* more lines */\n}""".strip()
            ).strip(),
        )

    def test_strip_whitespaces(self):
        self.assertEqual(
            """intmain(){return0;}""",
            CSourceCodeParser.strip_whitespaces("""int main() {\n\treturn 0;  \n}"""),
        )

    def test_strip_comments_and_whitespaces(self):
        self.assertEqual(
            """intmain(){return0;}""",
            CSourceCodeParser.strip_whitespaces(
                CSourceCodeParser.strip_comments(
                    """/* some line \n * comment \n * and more */\nint main() {\n\treturn 0; /* more lines */\n}"""
                )
            ),
        )

    def test_extract_raw_signature(self):
        self.assertEqual(
            """(finalint*,std::string,const&int,char**,char[]*,double&)""",
            CSourceCodeParser.extract_raw_signature(
                """(final int *a, std::string o, const &int b, char** c, char[]* diGGa,double &x)"""
            ),
        )
        self.assertEqual(
            """(FooSuite,Max)""",
            CSourceCodeParser.extract_raw_signature(
                """(FooSuite,Max)"""
            ),
        )


if __name__ == "__main__":
    unittest.main()
