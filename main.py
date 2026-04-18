"""医院招投标管理系统 V5.3 - FastAPI核心接口

认证方式: 登录获取token(Cookie/Header)，后续请求携带token
权限方式: 通过User所属Group的permissions JSON检查

接口沿革:
  V5.0  纯CRUD，无角色校验
  V5.1  引入角色权限拦截(X-Emp-Id模拟)
  V5.2  procurement_data改为JSON写入
  V5.3  重构为分组权限体系 + 登录认证 + 账号管理
"""

import hashlib
import secrets
import os
from datetime import datetime
from contextlib import contextmanager
from typing import Optional

from fastapi import FastAPI, Header, Cookie, Depends, HTTPException, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from models.tables import (
    Base, Group, User, Project,
    PROCUREMENT_DATA_TEMPLATE,
    PERM_CREATE_PROJECT, PERM_WRITE_PROCUREMENT, PERM_ADVANCE_STATUS,
    PERM_ADVANCE_TO_SUPPLIER, PERM_VIEW_DASHBOARD, PERM_MANAGE_ACCOUNTS,
    ALL_PERMS, DEFAULT_GROUPS,
    STATUS需求填报, STATUS寻找供应商, STATUS已采购,
    STATUS计划报废, STATUS已报废,
    ALL_STATUSES,
)

# ── FastAPI实例 ──────────────────────────────────────────────
app = FastAPI(title="医院招投标管理系统 V5.3", version="5.3")

# ── 数据库连接 ────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("HOSPITAL_DB_PATH", os.path.join(BASE_DIR, "hospital.db"))
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
SessionLocal = sessionmaker(bind=engine)

# ── Token存储 ──────────────────────────────────────────────────
# MVP阶段用内存存储session token，生产环境应换Redis
# FIXED in V5.3: 旧版用X-Emp-Id Header模拟登录，现改为真正的token认证
TOKEN_STORE: dict[str, dict] = {}  # token -> {emp_id, expires_at}


@contextmanager
def db_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db():
    with db_session() as session:
        yield session


# ── 密码工具 ──────────────────────────────────────────────────
def hash_password(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ── 认证依赖 ──────────────────────────────────────────────────
def get_current_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    token_cookie: Optional[str] = Cookie(None, alias="token"),
    db: Session = Depends(get_db),
) -> User:
    """从Authorization Header或Cookie中的token解析当前用户"""
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    elif token_cookie:
        token = token_cookie

    if not token or token not in TOKEN_STORE:
        raise HTTPException(status_code=401, detail="未登录或token已过期")

    emp_id = TOKEN_STORE[token]["emp_id"]
    user = db.query(User).filter(User.emp_id == emp_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


def require_perm(user: User, *perm_keys: str):
    """通过分组检查权限"""
    for key in perm_keys:
        if not user.has_perm(key):
            gname = user.group.name if user.group else "无分组"
            raise HTTPException(
                status_code=403,
                detail=f"分组'{gname}'缺少权限'{key}'，无法执行此操作",
            )


# ── Pydantic模型 ──────────────────────────────────────────────

class LoginReq(BaseModel):
    emp_id: str
    password: str

class CreateAccountReq(BaseModel):
    emp_id: str
    name: str
    password: str
    group_name: str

class UpdateAccountGroupReq(BaseModel):
    group_name: str

class CreateProjectReq(BaseModel):
    main_title: str

class UpdateProcurementReq(BaseModel):
    data: dict

class UpdateStatusReq(BaseModel):
    status: str
    new_main_title: Optional[str] = None

# ── 响应体 ────────────────────────────────────────────────────

class GroupOut(BaseModel):
    id: int
    name: str
    permissions: list[str]

    model_config = {"from_attributes": True}

class UserOut(BaseModel):
    id: int
    emp_id: str
    name: str
    group_name: Optional[str] = None
    permissions: list[str] = []

    model_config = {"from_attributes": True}

class ProjectOut(BaseModel):
    id: int
    status: str
    main_title: str
    sub_title: Optional[str] = ""
    creator_id: int
    creator_name: Optional[str] = None
    procurement_data: Optional[list] = None  # V5.3: 数组而非单个dict
    has_records: bool = False                 # 是否已有采购记录
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── 登录/认证接口 ─────────────────────────────────────────────

@app.post("/api/auth/login")
def login(req: LoginReq, response: Response, db: Session = Depends(get_db)):
    """登录接口 — 验证工号+密码，返回token"""
    user = db.query(User).filter(User.emp_id == req.emp_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="工号不存在")

    if user.password_hash != hash_password(req.password):
        raise HTTPException(status_code=401, detail="密码错误")

    token = secrets.token_hex(32)
    TOKEN_STORE[token] = {"emp_id": user.emp_id}

    # 同时写入Cookie，方便前端axios自动携带
    response.set_cookie(key="token", value=token, httponly=False, max_age=86400)

    return {
        "token": token,
        "user": _build_user_out(user),
    }


@app.post("/api/auth/logout")
def logout(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    token_cookie: Optional[str] = Cookie(None, alias="token"),
):
    """登出 — 清除token"""
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    elif token_cookie:
        token = token_cookie
    if token and token in TOKEN_STORE:
        del TOKEN_STORE[token]
    return {"message": "已登出"}


@app.get("/api/auth/me", response_model=UserOut)
def get_me(user: User = Depends(get_current_user)):
    """获取当前登录用户信息(含权限列表)"""
    return _build_user_out(user)


# ── 账号管理接口 ──────────────────────────────────────────────

@app.get("/api/accounts", response_model=list[UserOut])
def list_accounts(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """列出所有账号 — 仅有manage_accounts权限的用户可访问"""
    require_perm(user, PERM_MANAGE_ACCOUNTS)
    users = db.query(User).order_by(User.id).all()
    return [_build_user_out(u) for u in users]


@app.post("/api/accounts", response_model=UserOut)
def create_account(req: CreateAccountReq, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """创建新账号 — 仅manage_accounts权限"""
    require_perm(user, PERM_MANAGE_ACCOUNTS)

    # 检查工号唯一性
    if db.query(User).filter(User.emp_id == req.emp_id).first():
        raise HTTPException(status_code=400, detail=f"工号 {req.emp_id} 已存在")

    # 查找目标分组
    group = db.query(Group).filter(Group.name == req.group_name).first()
    if not group:
        raise HTTPException(status_code=400, detail=f"分组 '{req.group_name}' 不存在")

    new_user = User(
        emp_id=req.emp_id,
        name=req.name,
        password_hash=hash_password(req.password),
        group_id=group.id,
    )
    db.add(new_user)
    db.flush()

    return _build_user_out(new_user)


@app.put("/api/accounts/{account_id}/group", response_model=UserOut)
def update_account_group(account_id: int, req: UpdateAccountGroupReq, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """修改账号所属分组 — 仅manage_accounts权限"""
    require_perm(user, PERM_MANAGE_ACCOUNTS)

    target = db.get(User, account_id)
    if not target:
        raise HTTPException(status_code=404, detail="账号不存在")

    group = db.query(Group).filter(Group.name == req.group_name).first()
    if not group:
        raise HTTPException(status_code=400, detail=f"分组 '{req.group_name}' 不存在")

    target.group_id = group.id
    db.flush()

    return _build_user_out(target)


@app.get("/api/groups", response_model=list[GroupOut])
def list_groups(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """列出所有权限分组 — 仅manage_accounts权限"""
    require_perm(user, PERM_MANAGE_ACCOUNTS)
    return db.query(Group).order_by(Group.id).all()


# ── 项目接口(权限改用分组) ───────────────────────────────────

@app.post("/api/projects", response_model=ProjectOut)
def create_project(req: CreateProjectReq, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_perm(user, PERM_CREATE_PROJECT)

    project = Project(
        main_title=req.main_title,
        sub_title="",
        status=STATUS需求填报,
        creator_id=user.id,
        procurement_data=None,
    )
    db.add(project)
    db.flush()
    return _build_project_out(project, user, db)


@app.put("/api/projects/{project_id}/procurement", response_model=ProjectOut)
def update_procurement(project_id: int, req: UpdateProcurementReq, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """采购科补充一条供应商数据 — 追加而非覆盖
    V5.3: 需求填报阶段也允许补充，不再限制只有寻找供应商以上状态
    V5.2遗留逻辑兼容: 旧数据可能是单个dict，先转为list再追加"""
    require_perm(user, PERM_WRITE_PROCUREMENT)

    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 已报废不可再补充
    if project.status == STATUS已报废:
        raise HTTPException(status_code=400, detail="已报废项目不可补充采购数据")

    # 获取当前列表(兼容旧版单个dict格式)
    current_list = project.get_procurement_list()

    # 新记录与TEMPLATE合并兜底缺失字段
    merged = {**PROCUREMENT_DATA_TEMPLATE, **req.data}
    current_list.append(merged)

    project.procurement_data = current_list
    project.updated_at = datetime.utcnow()
    db.flush()
    return _build_project_out(project, user, db)


@app.put("/api/projects/{project_id}/status", response_model=ProjectOut)
def update_status(project_id: int, req: UpdateStatusReq, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    target = req.status
    if target not in ALL_STATUSES:
        raise HTTPException(status_code=400, detail=f"非法状态: {target}")

    current = project.status
    _validate_transition(current, target)

    # 推进前置条件：至少有一条采购记录才能推进到寻找供应商/已采购
    # FIXED in V5.3: 防止无采购数据就推进状态
    if target in [STATUS寻找供应商, STATUS已采购] and not project.has_procurement_records():
        raise HTTPException(status_code=400, detail="项目至少需要一条采购记录才能推进状态")

    # 权限校验：推进到寻找供应商需要advance_to_supplier，其他需要advance_status
    if target == STATUS寻找供应商:
        require_perm(user, PERM_ADVANCE_TO_SUPPLIER)
    else:
        require_perm(user, PERM_ADVANCE_STATUS)

    if target == STATUS已采购:
        if not req.new_main_title:
            raise HTTPException(status_code=400, detail="变更为'已采购'时必须传入new_main_title")
        project.sub_title = project.main_title
        project.main_title = req.new_main_title

    project.status = target
    project.updated_at = datetime.utcnow()
    db.flush()
    return _build_project_out(project, user, db)


@app.get("/api/projects", response_model=list[ProjectOut])
def list_projects(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    result = []
    for p in projects:
        creator = db.query(User).filter(User.id == p.creator_id).first()
        result.append(_build_project_out(p, creator, db))
    return result


# ── 辅助 ──────────────────────────────────────────────────────

VALID_TRANSITIONS = {
    STATUS需求填报: [STATUS寻找供应商],
    STATUS寻找供应商: [STATUS已采购, STATUS需求填报],
    STATUS已采购: [STATUS计划报废],
    STATUS计划报废: [STATUS已报废, STATUS需求填报],
    STATUS已报废: [],
}


def _validate_transition(current: str, target: str):
    allowed = VALID_TRANSITIONS.get(current, [])
    if target not in allowed:
        raise HTTPException(status_code=400, detail=f"状态'{current}'不可流转到'{target}'，允许: {allowed}")


def _build_user_out(user: User) -> UserOut:
    gname = user.group.name if user.group else None
    perms = user.group.permissions if user.group else []
    return UserOut(id=user.id, emp_id=user.emp_id, name=user.name, group_name=gname, permissions=perms)


def _build_project_out(project: Project, creator: Optional[User] = None, db: Session = None) -> ProjectOut:
    if creator is None and db is not None:
        creator = db.query(User).filter(User.id == project.creator_id).first()
    return ProjectOut(
        id=project.id,
        status=project.status,
        main_title=project.main_title,
        sub_title=project.sub_title or "",
        creator_id=project.creator_id,
        creator_name=creator.name if creator else "",
        procurement_data=project.get_procurement_list(),
        has_records=project.has_procurement_records(),
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@app.on_event("startup")
def ensure_tables():
    Base.metadata.create_all(engine)


# ── 生产部署: 后端托管前端静态文件 ──────────────────────────────
# static目录由前端 vite build 输出，开发模式下不存在则跳过
STATIC_DIR = os.path.join(BASE_DIR, "static")

if os.path.isdir(STATIC_DIR):
    # 先挂载静态资源(CSS/JS/图片等)
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="static_assets")

    # 非API、非assets的路径 → 返回index.html (Vue Router SPA模式)
    @app.get("/{path:path}")
    async def serve_spa(path: str):
        file_path = os.path.join(STATIC_DIR, path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        # 所有未匹配的路由都返回index.html，让Vue Router处理
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))
