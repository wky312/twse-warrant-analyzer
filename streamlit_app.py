"""Streamlit Cloud 預設找 repo 根目錄的 streamlit_app.py。

這個檔案只是 shim，把執行轉到 src/streamlit_app.py（真正的 UI）。
本機開發仍可直接跑 `streamlit run src/streamlit_app.py`。
"""
import runpy
from pathlib import Path

_real = Path(__file__).parent / "src" / "streamlit_app.py"
runpy.run_path(str(_real), run_name="__main__")
