import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import matplotlib


def _load_local_env_files() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    candidates = [
        repo_root / "apps" / "python-service" / ".env.agent.local",
        repo_root / "packages" / "geo-core" / "configs" / "env" / "agent.env.local",
    ]
    for file_path in candidates:
        if not file_path.exists():
            continue
        for raw_line in file_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip().lstrip("\ufeff")
            value = value.strip().strip('"').strip("'")
            if key:
                os.environ.setdefault(key, value)


_load_local_env_files()

from .api.borehole import router as borehole_router
from .api.stressinv import router as stressinv_router
from .api.augmentation import router as augmentation_router
from .api.agent import router as agent_router
from .api.dlis import router as dlis_router

# 配置 matplotlib 中文字体
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境请指定来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(borehole_router)
app.include_router(stressinv_router)
app.include_router(augmentation_router)
app.include_router(agent_router)
app.include_router(dlis_router)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)


