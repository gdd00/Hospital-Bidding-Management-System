"""医院招投标管理系统 V5.3 - FastAPI核心接口

启动方式: uvicorn main:app --reload
认证方式: Header X-Emp-Id 模拟当前登录用户

接口沿革:
  V5.0  纯CRUD，无角色校验
  V5.1  引入角色权限拦截
  V5.2  procurement_data改为JSON写入
  V5.3  修复"已采购"标题降级逻辑，规范状态流转校验
"""

from datetime import datetime
from contextlib import contextmanager
from typing import Optional

from fastapi import FastAPI, Header, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from models.tables import (
    Base, User, Project,
    ROLE_CHIEF, ROLE_PURCHASE, ROLE_STAFF,
    PROCUREMENT_DATA_TEMPLATE,
    STATUS需求填报, STATUS寻找供应商, STATUS已采购,
    STATUS计划报废, STATUS已报废,
    ALL_STATUSES,
)

# ── FastAPI实例 ──────────────────────────────────────────────
app = FastAPI(title="医院招投标管理系统 V5.3", version="5.3")

# ── 数据库连接 ────────────────────────────────────────────────
engine = create_engine("sqlite:///hospital.db", echo=False)
SessionLocal = sessionmaker(bind=engine)


@contextmanager
def db_session():
    """获取数据库session的上下文管理器
    FIXED in V5.3: 旧版手动commit/rollback易遗漏，现统一用上下文管理"""
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
    """FastAPI依赖注入用的db session生成器"""
    with db_session() as session:
        yield session


# ── 认证依赖 ──────────────────────────────────────────────────
def get_current_user(x_emp_id: str = Header(..., alias="X-Emp-Id"), db: Session = Depends(get_db)) -> User:
    """从X-Emp-Id Header解析当前用户
    V5.1引入: 无此Header或工号不存在时拒绝访问"""
    user = db.query(User).filter(User.emp_id == x_emp_id).first()
    if not user:
        raise HTTPException(status_code=401, detail=f"工号 {x_emp_id} 不存在")
    return user


def require_role(user: User, *allowed_roles: str):
    """角色校验辅助"""
    if user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail=f"角色'{user.role}'无权执行此操作，需要: {allowed_roles}")


# ── Pydantic请求体 ────────────────────────────────────────────

class CreateProjectReq(BaseModel):
    main_title: str  # 需求名称/主标题


class UpdateProcurementReq(BaseModel):
    # V5.2遗留逻辑兼容: 允许传入任意结构，由TEMPLATE兜底缺失字段
    # FIXED in V5.3: 不再限定字段，任意JSON均可写入，拓展性优先
    data: dict


class UpdateStatusReq(BaseModel):
    status: str            # 目标状态
    new_main_title: Optional[str] = None  # 仅"已采购"时必须传入新主标题


# ── Pydantic响应体 ────────────────────────────────────────────

class UserOut(BaseModel):
    id: int
    emp_id: str
    name: str
    role: str

    model_config = {"from_attributes": True}


class ProjectOut(BaseModel):
    id: int
    status: str
    main_title: str
    sub_title: Optional[str] = ""
    creator_id: int
    creator_name: Optional[str] = None
    procurement_data: Optional[dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── 接口1: 科长级创建项目 ─────────────────────────────────────
@app.post("/api/projects", response_model=ProjectOut)
def create_project(req: CreateProjectReq, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """科长级创建项目，初始状态为'需求填报'
    V5.1: 只有科长级可以创建"""
    require_role(user, ROLE_CHIEF)

    project = Project(
        main_title=req.main_title,
        sub_title="",
        status=STATUS需求填报,
        creator_id=user.id,
        procurement_data=None,  # V5.2遗留逻辑兼容: null代表尚未进入采购阶段
    )
    db.add(project)
    db.flush()

    # 手动构建响应，避免lazy-load问题
    return _build_project_out(project, user, db)


# ── 接口2: 采购科完善采购数据 ────────────────────────────────
@app.put("/api/projects/{project_id}/procurement", response_model=ProjectOut)
def update_procurement(project_id: int, req: UpdateProcurementReq, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """采购科完善procurement_data，允许任意结构写入
    V5.2遗留逻辑兼容: 写入时与TEMPLATE合并，保证历史数据兼容
    FIXED in V5.3: 读取时再兜底，写入时保留用户传入的任意额外字段"""
    require_role(user, ROLE_PURCHASE)

    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 只允许在"寻找供应商"及以上状态填写采购数据
    # V5.2遗留逻辑兼容: 已采购/报废阶段也允许修改(历史数据修正需求)
    if project.status == STATUS需求填报:
        raise HTTPException(status_code=400, detail="项目尚未进入寻找供应商阶段，无法填写采购数据")

    # 与TEMPLATE合并写入 — 用户传入的额外字段原样保留，缺失字段由模板补齐
    merged = {**PROCUREMENT_DATA_TEMPLATE, **req.data}
    project.procurement_data = merged
    project.updated_at = datetime.utcnow()
    db.flush()

    return _build_project_out(project, user, db)


# ── 接口3: 更新状态流转 ──────────────────────────────────────
@app.put("/api/projects/{project_id}/status", response_model=ProjectOut)
def update_status(project_id: int, req: UpdateStatusReq, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """更新项目状态流转
    V5.1: 科长级可推进所有状态，采购科可推进到"寻找供应商"
    V5.3修复: "已采购"时触发标题降级，new_main_title必填"""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    target = req.status
    if target not in ALL_STATUSES:
        raise HTTPException(status_code=400, detail=f"非法状态: {target}，合法值: {ALL_STATUSES}")

    # ── 状态流转校验 ──────────────────────────────────────────
    # V5.2遗留逻辑兼容: 旧版无流转校验导致状态乱跳，V5.3加入顺序约束
    # 但允许"计划报废→需求填报"回退(历史遗留需求)
    current = project.status
    _validate_transition(current, target)

    # ── 角色权限 ──────────────────────────────────────────────
    if target == STATUS寻找供应商:
        # 科长级和采购科均可推进到"寻找供应商"
        require_role(user, ROLE_CHIEF, ROLE_PURCHASE)
    else:
        # 其他状态流转仅科长级
        require_role(user, ROLE_CHIEF)

    # ── "已采购"标题降级逻辑 ──────────────────────────────────
    # FIXED in V5.3: 旧版降级时sub_title残留旧数据，现强制清空后赋值
    if target == STATUS已采购:
        if not req.new_main_title:
            raise HTTPException(status_code=400, detail="变更为'已采购'时必须传入new_main_title")
        # 原主标题降级为副标题
        project.sub_title = project.main_title
        project.main_title = req.new_main_title

    project.status = target
    project.updated_at = datetime.utcnow()
    db.flush()

    return _build_project_out(project, user, db)


# ── 接口4: 项目列表查询 ──────────────────────────────────────
@app.get("/api/projects", response_model=list[ProjectOut])
def list_projects(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """所有员工可看，列表查询
    V5.3: 已采购及后续状态的项目，main_title展示采购后的新标题
    (降级逻辑已在写入时处理，读取时无需额外变换)"""
    projects = db.query(Project).order_by(Project.id).all()

    result = []
    for p in projects:
        creator = db.query(User).filter(User.id == p.creator_id).first()
        result.append(_build_project_out(p, creator, db))
    return result


# ── 辅助函数 ──────────────────────────────────────────────────

# V5.2遗留逻辑兼容: 允许的状态流转路线
# 正向: 需求填报 → 寻找供应商 → 已采购 → 计划报废 → 已报废
# 逆向: 计划报废 → 需求填报 (历史回退需求)
VALID_TRANSITIONS = {
    STATUS需求填报: [STATUS寻找供应商],
    STATUS寻找供应商: [STATUS已采购, STATUS需求填报],
    STATUS已采购: [STATUS计划报废],
    STATUS计划报废: [STATUS已报废, STATUS需求填报],  # 回退到需求填报
    STATUS已报废: [],  # 终态，不可流转
}


def _validate_transition(current: str, target: str):
    """校验状态流转合法性"""
    allowed = VALID_TRANSITIONS.get(current, [])
    if target not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"状态'{current}'不可流转到'{target}'，允许的目标: {allowed}",
        )


def _build_project_out(project: Project, creator: Optional[User] = None, db: Session = None) -> ProjectOut:
    """从ORM对象构建响应体，避免lazy-load和session边界问题"""
    if creator is None and db is not None:
        creator = db.query(User).filter(User.id == project.creator_id).first()

    return ProjectOut(
        id=project.id,
        status=project.status,
        main_title=project.main_title,
        sub_title=project.sub_title or "",
        creator_id=project.creator_id,
        creator_name=creator.name if creator else "",
        procurement_data=project.get_procurement_data(),
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


# ── 启动时确保数据库表存在 ────────────────────────────────────
@app.on_event("startup")
def ensure_tables():
    Base.metadata.create_all(engine)