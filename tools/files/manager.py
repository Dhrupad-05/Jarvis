from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class FileManager:
    project_root: Path

    def create_file(self, path: Path, content: str = "") -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def create_folder(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)

    def rename(self, source: Path, target: Path) -> None:
        source.rename(target)

    def move(self, source: Path, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(target))

    def copy(self, source: Path, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target, dirs_exist_ok=True)
        else:
            shutil.copy2(source, target)

    def delete(self, path: Path) -> None:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()

    def search(self, query: str, root: Path | None = None, limit: int = 20) -> list[Path]:
        base = root or self.project_root
        matches: list[Path] = []
        for path in base.rglob("*"):
            if query.lower() in path.name.lower():
                matches.append(path)
                if len(matches) >= limit:
                    break
        return matches
