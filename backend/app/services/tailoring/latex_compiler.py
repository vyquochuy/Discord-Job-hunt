import asyncio
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple

from pypdf import PdfReader

logger = logging.getLogger("latex_compiler")


class LaTeXCompiler:
    """
    Service quản lý biên dịch mã nguồn LaTeX (.tex) thành tệp tin PDF (.pdf).
    - Hỗ trợ biên dịch cô lập trong thư mục lưu trữ (Storage Sandbox).
    - Tự động dọn dẹp các tệp tin phụ trợ (.aux, .log, .out).
    - Bắt và ghi nhận chi tiết nhật ký lỗi biên dịch (Compilation Logs).
    - Cung cấp Fallback an toàn khi môi trường chưa cài đặt sẵn TeXLive.
    """

    @staticmethod
    def get_storage_root() -> Path:
        """
        Lấy đường dẫn thư mục lưu trữ artifacts.
        Tự động kiểm tra quyền ghi thực tế và fallback sang /tmp nếu gặp PermissionError.
        """
        import tempfile

        candidates = [
            Path("/app/storage/resumes"),
            Path(__file__).resolve().parent.parent.parent.parent / "storage" / "resumes",
            Path(tempfile.gettempdir()) / "jobhunter_resumes",
        ]

        for path in candidates:
            try:
                path.mkdir(parents=True, exist_ok=True)
                # Kiểm tra quyền ghi thực tế
                test_file = path / ".perm_check"
                test_file.touch()
                test_file.unlink(missing_ok=True)
                return path
            except (PermissionError, OSError) as e:
                logger.warning(f"Storage path '{path}' is not writable ({e}). Trying next fallback...")
                continue

        fallback = Path(tempfile.gettempdir()) / "jobhunter_resumes"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback

    @classmethod
    async def compile_tex(
        cls,
        tex_content: str,
        job_id: str,
        file_prefix: str = "resume",
        candidate_id: Optional[str] = None,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Biên dịch nội dung TeX thành PDF.
        Hỗ trợ lưu trữ cô lập theo candidate_id: storage/resumes/{candidate_id}/{job_id}/
        Trả về: (success, pdf_file_path, error_message).
        """
        storage_root = cls.get_storage_root()
        if candidate_id:
            storage_dir = storage_root / str(candidate_id) / str(job_id)
        else:
            storage_dir = storage_root / str(job_id)

        try:
            storage_dir.mkdir(parents=True, exist_ok=True)
        except (PermissionError, OSError) as e:
            logger.warning(f"Permission denied creating {storage_dir}: {e}. Falling back to /tmp...")
            import tempfile
            storage_dir = Path(tempfile.gettempdir()) / "jobhunter_resumes" / str(job_id)
            storage_dir.mkdir(parents=True, exist_ok=True)

        tex_path = storage_dir / f"{file_prefix}.tex"
        pdf_path = storage_dir / f"{file_prefix}.pdf"

        # 1. Dọn sạch file PDF cũ (nếu có) để tránh nhận nhầm PDF cũ khi biên dịch lỗi
        if pdf_path.exists():
            try:
                pdf_path.unlink()
            except Exception as e:
                return False, None, f"Cannot remove stale PDF before recompiling: {e}"

        # 2. Ghi nội dung TeX ra đĩa
        tex_path.write_text(tex_content, encoding="utf-8")
        logger.info(f"Wrote LaTeX source to {tex_path}")

        # 2. Kiểm tra công cụ pdflatex hoặc xelatex
        pdflatex_bin = shutil.which("pdflatex") or shutil.which("xelatex")

        if not pdflatex_bin:
            return False, None, "LaTeX binary not installed; .tex source saved, PDF unavailable."

        # 3. Chạy biên dịch pdflatex (chạy qua threadpool an toàn trên mọi hệ điều hành)
        try:
            cmd = [
                pdflatex_bin,
                "-no-shell-escape",
                "-interaction=nonstopmode",
                f"-output-directory={storage_dir}",
                str(tex_path),
            ]

            def _run_pdflatex():
                return subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=str(storage_dir),
                    timeout=30.0,
                )

            result = await asyncio.to_thread(_run_pdflatex)

            if result.returncode != 0:
                log_file = storage_dir / f"{file_prefix}.log"
                error_snippet = ""
                if log_file.exists():
                    try:
                        log_content = log_file.read_text(encoding="utf-8", errors="ignore")
                        error_lines = [line for line in log_content.splitlines() if line.startswith("!")]
                        if error_lines:
                            error_snippet = "\n".join(error_lines[:5])
                        else:
                            error_snippet = log_content[-1000:]
                    except Exception:
                        pass

                pdf_path.unlink(missing_ok=True)
                err_msg = f"pdflatex biên dịch thất bại (mã {result.returncode}):\n{error_snippet}"
                logger.warning("LaTeX pdflatex error: %s", err_msg)
                return False, None, err_msg

            with pdf_path.open("rb") as pdf_file:
                page_count = len(PdfReader(pdf_file, strict=True).pages)
            if page_count != 1:
                pdf_path.unlink(missing_ok=True)
                return False, None, f"Resume must contain exactly 1 page; compiled {page_count} pages."

            # Dọn dẹp tệp tin rác
            for ext in [".aux", ".log", ".out", ".synctex.gz"]:
                temp_file = storage_dir / f"{file_prefix}{ext}"
                if temp_file.exists():
                    try:
                        temp_file.unlink()
                    except Exception:
                        pass

            logger.info(f"Successfully compiled PDF: {pdf_path}")
            return True, str(pdf_path), None

        except (asyncio.TimeoutError, subprocess.TimeoutExpired):
            pdf_path.unlink(missing_ok=True)
            return False, None, "LaTeX compilation timed out after 30 seconds"
        except Exception as e:
            pdf_path.unlink(missing_ok=True)
            logger.error(f"Unexpected error compiling LaTeX: {e}", exc_info=True)
            return False, None, str(e)


latex_compiler = LaTeXCompiler()
