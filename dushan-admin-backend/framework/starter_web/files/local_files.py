from pathlib import Path

from framework.common.exception.exceptions.not_found_exception import NotFoundException
from framework.starter_web.response.file_result import FileResult


class LocalFiles:
    """从宿主明确授权且由服务端管理的根目录下载；不会自动发布目录或信任上传文件名。"""

    def __init__(self, root: Path, result: FileResult) -> None:
        self.root = root.resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError("文件访问根必须是目录")
        self.result = result

    def download(
        self, relative: str, *, file_name: str | None = None, media_type: str | None = None
    ):
        path = Path(relative)
        if path.is_absolute() or path.drive or ".." in path.parts or ":" in relative:
            raise ValueError("文件路径必须位于授权根目录内")
        try:
            resolved = (self.root / path).resolve(strict=True)
        except (FileNotFoundError, NotADirectoryError) as error:
            raise NotFoundException() from error
        if not resolved.is_relative_to(self.root):
            raise ValueError("文件链接不能越过授权根目录")
        try:
            return self.result.download(resolved, file_name, media_type)
        except (FileNotFoundError, NotADirectoryError) as error:
            raise NotFoundException() from error
