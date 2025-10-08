from fastapi import FastAPI
import uvicorn

def main():
    app = FastAPI()

    @app.get("/")
    async def read_root():
        return {"Hello": "World"}
    
    @app.post("/osd/in")
    async def enter_video():
        return {"status": "Video entered"}
    @app.post("/osd/processed")
    async def processed():
        try:
            # Logic to mark quest as done
            return {"status": "Quest marked as done"}
        except Exception as e:
            return {"error": str(e)}
    @app.post("/osd/quest_done")
    async def quest_done():
        try:
            # Logic to mark quest as done
            return {"status": "Quest marked as done"}
        except Exception as e:
            return {"error": str(e)}
        
    @app.post("/osd/exit")
    async def exit_video():
        return {"status": "Video exited"}
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
if __name__ == "__main__":
    main()
