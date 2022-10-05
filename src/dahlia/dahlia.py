from __future__ import annotations
from enum import Enum
from os import environ, system
from re import compile
from sys import platform
from typing import Any

if platform in ("win32", "cygwin"):
    system("")  # type: ignore


FORMATTERS = {"l": 1, "m": 9, "n": 4, "o": 3, "r": 0}

COLORS_3BIT = {
    "0": 30,
    "1": 34,
    "2": 32,
    "3": 36,
    "4": 31,
    "5": 35,
    "6": 33,
    "7": 37,
    "8": 30,
    "9": 34,
    "a": 32,
    "b": 34,
    "c": 31,
    "d": 35,
    "e": 33,
    "f": 37,
    "g": 35,
}

COLORS_8BIT = {
    "0": 0,
    "1": 19,
    "2": 34,
    "3": 37,
    "4": 124,
    "5": 127,
    "6": 214,
    "7": 248,
    "8": 240,
    "9": 147,
    "a": 83,
    "b": 87,
    "c": 203,
    "d": 207,
    "e": 227,
    "f": 15,
    "g": 184,
}

COLORS_24BIT = {
    "0": [0, 0, 0],
    "1": [0, 0, 170],
    "2": [0, 170, 0],
    "3": [0, 170, 170],
    "4": [170, 0, 0],
    "5": [170, 0, 170],
    "6": [255, 170, 0],
    "7": [170, 170, 170],
    "8": [85, 85, 85],
    "9": [85, 85, 255],
    "a": [85, 255, 85],
    "b": [85, 255, 255],
    "c": [255, 85, 85],
    "d": [255, 85, 255],
    "e": [255, 255, 85],
    "f": [255, 255, 255],
    "g": [221, 214, 5],
}

CODE_REGEXES = [
    compile(r"&(~?)([0-9a-gl-or])"),
    compile(r"&(~?)\[#([0-9a-fA-F]{6})\]"),
]

ANSI_REGEXES = [
    compile(r"\033\[(\d+)m"),
    compile(r"\033\[(?:3|4)8;5;(\d+)m"),
    compile(r"\033\[(?:3|4)8;2;(\d+);(\d+);(\d+)m"),
]

FORMAT_TEMPLATES = {
    3: "\033[{}m",
    8: "\033[38;5;{}m",
    24: "\033[38;2;{};{};{}m",
}

BG_FORMAT_TEMPLATES = {
    3: "\033[{}m",
    8: "\033[48;5;{}m",
    24: "\033[48;2;{};{};{}m",
}

NO_COLOR = environ.get("NO_COLOR", "").casefold() in ("1", "true")


class Depth(Enum):
    """Specifies usable color depth levels."""

    LOW = 3
    """3-bit color"""
    MEDIUM = 8
    """8-bit color"""
    HIGH = 24
    """24-bit color (true color)"""


class Dahlia:
    def __init__(self, *, depth: Depth = Depth.HIGH, no_reset: bool = False) -> None:
        self._depth = depth.value
        self._no_reset = no_reset

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Dahlia):
            return (self.depth, self.no_reset) == (other.depth, other.no_reset)
        else:
            return NotImplemented

    def __hash__(self) -> int:
        return hash((self.depth, self.no_reset)) + 10

    def __repr__(self) -> str:
        return f"Dahlia(depth={self.depth}, no_reset={self.no_reset})"

    @property
    def depth(self) -> int:
        """Specifies what ANSI color set to use (in bits)."""
        return self._depth

    @property
    def no_reset(self) -> bool:
        """When True, doesn't add an "&r" at the end when converting strings."""
        return self._no_reset

    def convert(self, string: str) -> str:
        """
        Formats a string using the format codes.

        Example
        -------

        .. code-block :: python

            dahlia = Dahlia()
            text = dahlia.convert("&aHello\\n&cWorld")
            print(text)


        Output would be:

        .. raw:: html

            <pre>
                <span class="&a">Hello</span>
                <span class="&c">World</span>
            </pre>

        For more see :ref:`dahlia usage <usage>`

        Parameters
        ----------
        string : str
            String containing text and format codes.

        Returns
        -------
        str
            A formatted string with the appropriate formatting applied.
        """
        if NO_COLOR:
            return clean(string)
        if not (string.endswith("&r") or self.no_reset):
            string += "&r"
        for code, bg, color in _find_codes(string):
            string = string.replace(code, self.__get_ansi(color, bg))
        return string

    def input(self, prompt: str) -> str:
        """
        Wrapper over :func:`input`, calling the :func:`dahlia` function on the prompt.

        Example
        -------
        .. code-block :: python

            dahlia = Dahlia()
            text = dahlia.input("&bEnter text: ")


        Output would be:

        .. raw:: html

            <pre>
                <span class="&b">Enter text: </span>
            </pre>

        Parameters
        ----------
        prompt : str
            String containing text and format codes to prompt the user with.

        Returns
        -------
        str
            User input entered after the formatted prompt.
        """
        return input(self.convert(prompt))

    def print(self, *args: Any, **kwargs: Any) -> None:
        r"""
        Wrapper over :func:`print`, calling the :func:`dahlia` method for each argument.

        Example
        -------
        .. code-block :: python

            dahlia = Dahlia()
            text = dahlia.print("&bHello", "&5World", sep="\n")


        Output would be:

        .. raw:: html

            <pre>
                <span class="&b">Hello</span>
                <span class="&5">World</span>
            </pre>

        Parameters
        ----------
        \*args : str
            Objects to print.

        \*\*kwargs
            Keyword arguments to pass to :func:`print`.
        """
        print(*map(self.convert, map(str, args)), **kwargs)

    def reset(self) -> None:
        """Resets all modifiers."""
        self.print("&r", end="")

    def test(self) -> None:
        """Prints all default format codes and their formatting."""
        self.print(
            "".join(f"&{i}{i}" for i in "0123456789abcdefg") + "&r&ll&r&mm&r&nn&r&oo"
        )

    def __get_ansi(self, code: str, bg: bool) -> str:
        formats = BG_FORMAT_TEMPLATES if bg else FORMAT_TEMPLATES
        if len(code) == 6:
            r, g, b = (int(code[i : i + 2], 16) for i in range(0, 6, 2))
            return formats[24].format(r, g, b)
        elif code in FORMATTERS:
            return formats[3].format(FORMATTERS[code])
        else:
            template = formats[self._depth]
            if self.depth == 24:
                r, g, b = COLORS_24BIT[code]
                return template.format(r, g, b)
            else:
                color_map = COLORS_3BIT if self.depth == 3 else COLORS_8BIT
                value = color_map[code]
                if self.depth == 8 and bg:
                    value += 10
                return template.format(value)


def clean(string: str) -> str:
    """
    Removes all Dahlia formatting from a string.

    Parameters
    ----------
    string :
        String to clear formatting from.

    Returns
    -------
    str :
        Cleaned string without formatting.
    """
    for code, *_ in _find_codes(string):
        string = string.replace(code, "", 1)
    return string


def clean_ansi(string: str) -> str:
    """
    Removes all ANSI codes from a string.

    Parameters
    ----------
    string : str
        String to clear ANSI codes from.

    Returns
    -------
    str
        Cleaned string without codes.
    """
    for ansi_code in _find_ansi_codes(string):
        string = string.replace(ansi_code, "", 1)
    return string


def _find_codes(string: str) -> list[tuple[str, bool, str]]:
    codes: list[tuple[str, bool, str]] = []
    for pattern in CODE_REGEXES:
        for match in pattern.finditer(string):
            codes.append((match[0], match[1] == "~", match[2]))
    return codes


def _find_ansi_codes(string: str) -> list[str]:
    ansi_codes: list[str] = []
    for pattern in ANSI_REGEXES:
        for match in pattern.finditer(string):
            ansi_codes.append(match.group(0))
    return ansi_codes
