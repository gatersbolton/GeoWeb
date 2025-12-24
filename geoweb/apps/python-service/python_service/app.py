from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import matplotlib

from .api.borehole import router as borehole_router
from .api.stressinv import router as stressinv_router

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

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)


