# -*- coding: utf-8 -*-
"""部署启动器：读取 PORT 环境变量并启动 Streamlit（云沙箱 / 本地均可用）"""
import os
import sys

from streamlit.web import cli as stcli


def main():
    port = os.environ.get("PORT", "8501")
    sys.argv = [
        "streamlit", "run", os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py"),
        "--server.port", str(port),
        "--server.address", "0.0.0.0",
        "--server.headless", "true",
        "--server.enableCORS", "false",
        "--server.enableXsrfProtection", "false",
        "--browser.gatherUsageStats", "false",
    ]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
