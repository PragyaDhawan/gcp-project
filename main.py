from fastapi import FastAPI
from routers import mongo_db


app = FastAPI(title="Mongo Atlas API")

app.include_router(mongo_db.router)

@app.get("/")
async def root():
    return {"message": "Main Entry Point"}
