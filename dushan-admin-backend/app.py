import sys

# 先关掉字节码写入，再导入项目模块，避免生成 __pycache__。
sys.dont_write_bytecode = True

from server.launcher.server_launcher import ServerLauncher

if __name__ == "__main__":
    raise SystemExit(ServerLauncher.run())
