"""
FastAPI 应用入口：图书馆座位预约系统 Web 端
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime
from contextlib import asynccontextmanager
import uvicorn
import csv

from web import data, auth, config, scheduler

rooms_data = {}


def load_rooms_data():
    csv_path = os.path.join(os.path.dirname(__file__), "..", "get_API", "seat_summary.csv")
    if os.path.exists(csv_path):
        with open(csv_path, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                room_id = row['roomId']
                kind_name = row['kindName']
                seat_name = row['devName']
                if room_id not in rooms_data:
                    rooms_data[room_id] = {
                        "name": kind_name,
                        "seats": []
                    }
                rooms_data[room_id]["seats"].append(seat_name)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 禁用 Python stdout 缓冲（确保 Docker logs 实时输出）
    sys.stdout.reconfigure(line_buffering=True)

    # 启动前初始化数据文件和调度器
    data.get_users()
    data.get_plans()
    data.get_logs()
    load_rooms_data()
    scheduler.start_scheduler()
    yield
    # 关闭时释放资源：关闭调度器，防止后台线程残留
    from web.scheduler import scheduler as _sched
    _sched.shutdown(wait=False)
    print("[Shutdown] Scheduler stopped.")


app = FastAPI(
    title="图书馆座位预约系统",
    lifespan=lifespan,
    docs_url=None,
    openapi_url=None
)

# 模板目录
templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "templates")
)


# ---------- 辅助函数 ----------

def get_current_user(token: str = None):
    return auth.verify_token(token) if token else None


# ---------- 登录相关路由 ----------


@app.get("/njfu.reserve.seat/", response_class=HTMLResponse)
async def home(request: Request):
    token = request.cookies.get("token")
    user = get_current_user(token)
    if user:
        plans = data.get_plans_by_user(user["id"])
        logs = [l for l in data.get_logs() if l["user_id"] == user["id"]]
        logs = sorted(logs, key=lambda x: x["created_at"], reverse=True)[:30]
        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={"user": user, "plans": plans, "logs": logs},
        )
    return RedirectResponse(url="/njfu.reserve.seat/login")


@app.get("/njfu.reserve.seat/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(
        request=request, name="login.html"
    )


@app.post("/njfu.reserve.seat/api/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    user = data.get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=400, detail="用户不存在")
    try:
        decrypted = config.decrypt_password(user["encrypted_password"])
        if decrypted != password:
            raise HTTPException(status_code=400, detail="密码错误")
    except Exception:
        raise HTTPException(status_code=400, detail="验证失败")

    token = auth.create_token(user["id"])
    resp = RedirectResponse(url="/njfu.reserve.seat/", status_code=302)
    resp.set_cookie(key="token", value=token, httponly=True)
    return resp


@app.get("/njfu.reserve.seat/register", response_class=HTMLResponse)
async def register_page(request: Request):
    try:
        return templates.TemplateResponse(request, "register.html")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/njfu.reserve.seat/api/register")
async def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    email: str = Form(None),
    pushplus_token: str = Form(None),
):
    if data.get_user_by_username(username):
        raise HTTPException(status_code=400, detail="用户已存在")

    # 注册时实时校验校园网账号密码是否正确
    from src.bot.core import LibraryBot
    bot = LibraryBot(username=username, password_plain=password, headless=True)
    try:
        bot.login()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"账号或密码验证失败，请确保填写正确的智慧校园通行证。系统提示: {e}")

    encrypted = config.encrypt_password(password)
    user = {
        "username": username,
        "encrypted_password": encrypted,
        "email": email or "",
        "pushplus_token": pushplus_token or "",
        "token": "",
        "created_at": datetime.now().isoformat(),
    }
    data.add_user(user)
    return RedirectResponse(url="/njfu.reserve.seat/login", status_code=302)


@app.post("/njfu.reserve.seat/api/logout")
async def logout(request: Request):
    resp = RedirectResponse(url="/njfu.reserve.seat/login", status_code=302)
    resp.delete_cookie("token")
    return resp


# ---------- 预约计划路由 ----------


@app.get("/njfu.reserve.seat/plan/new", response_class=HTMLResponse)
async def new_plan_page(request: Request):
    token = request.cookies.get("token")
    user = get_current_user(token)
    if not user:
        return RedirectResponse(url="/njfu.reserve.seat/login", status_code=302)
    return templates.TemplateResponse(
        request=request, name="plan_form.html", context={"rooms_data": rooms_data}
    )


@app.post("/njfu.reserve.seat/api/plans")
async def create_plan(
    request: Request,
    room_id: int = Form(...),
    seat_name: str = Form(None),
    is_full_day: str = Form("1"),
    repeat_type: str = Form("everyday"),
    days_of_week: str = Form(""),
    normal_begin_time: str = Form("07:30"),
    normal_end_time: str = Form("22:00"),
    friday_begin_time: str = Form("07:30"),
    friday_end_time: str = Form("20:00"),
    start_date: str = Form(None),
    end_date: str = Form(None),
):
    token = request.cookies.get("token")
    user = get_current_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="未登录")

    plan = {
        "user_id": user["id"],
        "room_id": room_id,
        "seat_name": seat_name or "",
        "is_full_day": is_full_day == "1",
        "repeat_type": repeat_type,
        "days_of_week": days_of_week,
        "normal_begin_time": normal_begin_time,
        "normal_end_time": normal_end_time,
        "friday_begin_time": friday_begin_time,
        "friday_end_time": friday_end_time,
        "start_date": start_date or "",
        "end_date": end_date or "",
        "active": True,
    }
    data.add_plan(plan)
    return RedirectResponse(url="/njfu.reserve.seat/", status_code=302)


@app.post("/njfu.reserve.seat/api/plans/{plan_id}/delete")
async def delete_plan(plan_id: int, request: Request):
    token = request.cookies.get("token")
    user = get_current_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="未登录")

    plans = data.get_plans()
    plan = next(
        (p for p in plans if p["id"] == plan_id and p["user_id"] == user["id"]), None
    )
    if not plan:
        raise HTTPException(status_code=404, detail="未找到该计划或无权限")

    data.delete_plan(plan_id)
    return RedirectResponse(url="/njfu.reserve.seat/", status_code=302)


# ---------- 日志路由 ----------


@app.get("/njfu.reserve.seat/api/logs")
async def get_logs(request: Request):
    token = request.cookies.get("token")
    user = get_current_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="未登录")

    logs = [l for l in data.get_logs() if l["user_id"] == user["id"]]
    logs = sorted(logs, key=lambda x: x["created_at"], reverse=True)[:20]
    return JSONResponse(logs)



if __name__ == "__main__":
    uvicorn.run("web.main:app", host="0.0.0.0", port=8000, reload=True)