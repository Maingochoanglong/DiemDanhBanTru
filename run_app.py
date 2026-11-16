"""Điểm khởi chạy app: python run_app.py

Dựng file .exe: python -m nuitka run_app.py --file-version=<phiên bản> --product-version=<phiên bản>
(Nuitka tự đọc các tùy chọn "nuitka-project" dưới đây; CI: .github/workflows/build-windows.yml).
"""

# nuitka-project: --mode=onefile
# nuitka-project: --output-dir={MAIN_DIRECTORY}/dist
# nuitka-project: --output-filename=DiemDanhBanTru.exe
# nuitka-project: --include-data-dir={MAIN_DIRECTORY}/app/web/static=app/web/static
# nuitka-project: --product-name=Điểm danh bán trú
# nuitka-project: --file-description=Điểm danh bán trú
# nuitka-project: --company-name=DiemDanhBanTru
# nuitka-project: --copyright=Điểm danh bán trú
# nuitka-project: --assume-yes-for-downloads
# nuitka-project-if: {OS} == "Windows":
#    nuitka-project: --windows-console-mode=disable
#    nuitka-project: --enable-plugins=tk-inter

from app.main import main

if __name__ == "__main__":
    main()
