from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np

app = FastAPI()

# 允许跨域（如需前端直连Python服务时可用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/process")
async def process(file: UploadFile = File(...)):
    df = pd.read_csv(file.file)
    s = float(np.nansum(df.values))
    return {"sum": s} 