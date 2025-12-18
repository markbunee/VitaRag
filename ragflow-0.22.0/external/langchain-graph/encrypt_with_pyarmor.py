import os
import subprocess

PROJECT_ROOT = os.path.abspath(".")
DIST_DIR = "./dist_protected"

# 仅加密业务逻辑模块，不加密 service.py
PROTECT_DIRS = ["api_process", "graph", "service", "src","utils"]
EXCLUDES = ["utils/prompts"]

# 构造 exclude 参数
exclude_args = []
for e in EXCLUDES:
    exclude_args.extend(["--exclude", e])

# 创建命令（不加密入口 service.py）
command = [
    "pyarmor", "gen",
    *exclude_args,
    "--recursive",
    "-O", DIST_DIR,
    *PROTECT_DIRS
]

print("加密命令：", " ".join(command))

subprocess.run(command, check=True)

# 手动复制 service.py, requirements.txt 等非加密文件
os.system(f'cp service.py {DIST_DIR}/')
os.system(f'cp requirements.txt {DIST_DIR}/')

print(f"\n✅ 加密完成，入口文件 app.py 等保留源码形式的还需自行复制到加密目录下")
