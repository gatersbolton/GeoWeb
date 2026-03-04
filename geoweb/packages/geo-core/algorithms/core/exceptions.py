from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AppError(Exception):
    code: str
    message: str

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


class InputFormatNotSupportedError(AppError):
    def __init__(self, message: str = "Input format is not supported.") -> None:
        super().__init__("A1001", message)


class MetadataMissingError(AppError):
    def __init__(self, message: str = "Required metadata is missing.") -> None:
        super().__init__("A1002", message)


class InvalidAlgorithmParamsError(AppError):
    def __init__(self, message: str = "Algorithm parameters are invalid.") -> None:
        super().__init__("A2001", message)


class AlgorithmExecutionError(AppError):
    def __init__(self, message: str = "Algorithm execution failed.") -> None:
        super().__init__("A3001", message)


class ResultSerializationError(AppError):
    def __init__(self, message: str = "Result serialization failed.") -> None:
        super().__init__("A3002", message)


class InputValidationError(AppError):
    def __init__(self, message: str = "Input validation failed.") -> None:
        super().__init__("A1001", message)

