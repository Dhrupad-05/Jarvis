from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ErrorAnalysis:
    language: str
    error_type: str
    likely_cause: str
    next_steps: tuple[str, ...]

    def format(self) -> str:
        steps = "\n".join(f"- {step}" for step in self.next_steps)
        return f"{self.language} {self.error_type}: {self.likely_cause}\n{steps}"


@dataclass(frozen=True, slots=True)
class ErrorAnalyzer:
    def analyze(self, text: str) -> ErrorAnalysis:
        lowered = text.lower()
        if "traceback" in lowered or re.search(r"\w+error:", text):
            return self._python(text)
        if "typeerror" in lowered or "referenceerror" in lowered or "npm err" in lowered:
            return ErrorAnalysis("JavaScript/TypeScript", self._first_error(text), "Runtime or build-time JavaScript failure.", ("Read the first stack frame in your code.", "Check undefined values and dependency versions.", "Re-run the failing command after the smallest fix."))
        return ErrorAnalysis("Unknown", "Error", "The error format is not recognized yet.", ("Identify the command that failed.", "Capture the full error output.", "Check the first actionable line, not the last noisy line."))

    def _python(self, text: str) -> ErrorAnalysis:
        error_type = self._first_error(text)
        cause = "Python raised an exception."
        if "modulenotfounderror" in text.lower():
            cause = "A Python import could not be resolved."
        elif "syntaxerror" in text.lower():
            cause = "Python could not parse the file."
        elif "typeerror" in text.lower():
            cause = "A value was used with an incompatible type or call signature."
        return ErrorAnalysis("Python", error_type, cause, ("Inspect the final traceback line.", "Open the most recent frame that points into your project.", "Fix that local cause before changing dependencies."))

    def _first_error(self, text: str) -> str:
        matches = re.findall(r"([A-Za-z_][A-Za-z0-9_]*(?:Error|Exception))", text)
        return matches[-1] if matches else "Error"
